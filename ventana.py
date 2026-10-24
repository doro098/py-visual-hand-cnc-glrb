"""La ventana. Cámara → MediaPipe → PID → GRBL → dibujo, todo en el mismo loop.

El ancla de la mano se mide contra el centro cartesiano del frame. El error
horizontal y vertical entra a un PID por eje, y la velocidad que sale se
manda a GRBL como un jog incremental corto. Sin --serial corre en modo
seco: imprime los $J= y no toca hardware.

Teclas:
    ESC o q    salir
    c          calibrar: el centro pasa a donde está la mano ahora
    espacio    pausar/reanudar el lazo (la pausa manda 0x85 y frena el brazo)
    g          mostrar/ocultar el esqueleto

El loop corre a la velocidad de la inferencia: no hay sleep. El FPS real se
muestra en el título de la ventana.
"""

import argparse
import os
import sys
import time
from collections import deque

import cv2
import numpy as np

import centro as modulo_centro
import pid as modulo_pid
import renderer
from grbl import Grbl, Seco, Serial
from manos import cargar_motor

# Duración de cada jog, en segundos. La wiki de GRBL v1.1 pide jogs cortos
# (dt entre 0.025 y 0.06 s) para mantener el buffer del planner fino.
JOG_MIN = 0.02
JOG_MAX = 0.06
HISTORIA = 240  # ~8 s de error en la gráfica, a 30 fps


def _elegir_driver() -> str:
    """Prueba wayland, cae a x11. Si ya hay SDL_VIDEODRIVER seteado, respeta."""
    if "SDL_VIDEODRIVER" in os.environ:
        return os.environ["SDL_VIDEODRIVER"]

    import pygame

    errores = []
    for driver in ("wayland", "x11"):
        os.environ["SDL_VIDEODRIVER"] = driver
        try:
            pygame.display.init()
            pygame.display.quit()
            return driver
        except pygame.error as e:
            errores.append(f"  {driver}: {e}")

    sys.stderr.write("no hay display:\n" + "\n".join(errores) + "\n")
    raise SystemExit(1)


def _abrir_camara(indice: int, ancho: int, alto: int, fps: int) -> cv2.VideoCapture:
    """Abre la cámara pidiendo MJPG: sin eso, el bus USB no llega a los fps."""
    cam = cv2.VideoCapture(indice)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
    cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cam.set(cv2.CAP_PROP_FPS, fps)
    if not cam.isOpened():
        raise SystemExit(f"no se pudo abrir la cámara {indice}")
    return cam


def main() -> None:
    parser = argparse.ArgumentParser(
        description="La cámara, en el brazo de 2 ejes, sigue a la mano."
    )
    parser.add_argument("--camara", type=int, default=int(os.environ.get("CAMARA", "2")),
                        help="índice de la cámara (2 es la USB en este host)")
    parser.add_argument("--ancho", type=int, default=int(os.environ.get("ANCHO", "640")))
    parser.add_argument("--alto", type=int, default=int(os.environ.get("ALTO", "480")))
    parser.add_argument("--fps", type=int, default=int(os.environ.get("FPS", "30")),
                        help="fps pedidos a la cámara, no un tope del loop")
    parser.add_argument("--serial", default=os.environ.get("GRBL_PUERTO") or None,
                        help="puerto del Uno con GRBL; sin esto corre en modo seco")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--feed", type=float, default=float(os.environ.get("FEED", "600")),
                        help="feed máximo de los jogs, en mm/min")
    parser.add_argument("--kp", type=float, default=60.0,
                        help="ganancia P: mm/s por unidad de error del frame")
    parser.add_argument("--ki", type=float, default=8.0)
    parser.add_argument("--kd", type=float, default=0.0)
    parser.add_argument("--muerto", type=float, default=0.012,
                        help="error mínimo que mueve el brazo, en fracción del frame")
    parser.add_argument("--vmax", type=float, default=30.0,
                        help="velocidad máxima por eje, en mm/s")
    parser.add_argument("--sentido-x", type=float,
                        default=float(os.environ.get("SENTIDO_X", "1")),
                        help="+1 si con error x positivo el brazo debe acercarse; -1 si no")
    parser.add_argument("--sentido-y", type=float,
                        default=float(os.environ.get("SENTIDO_Y", "1")))
    args = parser.parse_args()

    driver = _elegir_driver()
    import pygame

    pygame.init()
    cam = _abrir_camara(args.camara, args.ancho, args.alto, args.fps)
    ok, frame = cam.read()
    if not ok:
        raise SystemExit("la cámara no devuelve frames")
    alto, ancho = frame.shape[:2]

    pantalla = pygame.display.set_mode((ancho, alto), pygame.RESIZABLE)
    pygame.display.set_caption("mano-pap")

    motor = cargar_motor("landmarks")
    centro_actual = modulo_centro.Centro()
    ganancias = dict(
        kp=args.kp, ki=args.ki, kd=args.kd, muerto=args.muerto, vmax=args.vmax
    )
    pid_x = modulo_pid.Pid(**ganancias)
    pid_y = modulo_pid.Pid(**ganancias)

    if args.serial:
        canal = Serial(args.serial, args.baud)
        print(f"grbl serial: {args.serial} @ {args.baud} baudios")
    else:
        canal = Seco()
        print("grbl seco: los $J= salen por stdout, el brazo no se mueve")
    brazo = Grbl(canal, feed_max=args.feed)
    brazo.conectar()

    corriendo = True
    ver_esqueleto = True
    historia: deque[tuple[float, float]] = deque(maxlen=HISTORIA)
    ancla_actual: tuple[float, float] | None = None
    frenado = False  # el 0x85 ya va mandado mientras no hay mano; no repetir

    # MediaPipe en modo VIDEO pide timestamps monótonos: usamos el reloj del
    # loop y nos aseguramos de que nunca se repitan.
    ultimo_ts = 0
    fps_suave = 0.0
    reloj_anterior = time.perf_counter()

    print(
        f"display: {driver}  cámara: {args.camara} ({ancho}x{alto})  "
        f"kp={args.kp} ki={args.ki} kd={args.kd} muerto={args.muerto} vmax={args.vmax}"
    )

    try:
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    return
                if evento.type == pygame.KEYDOWN:
                    if evento.key in (pygame.K_ESCAPE, pygame.K_q):
                        return
                    if evento.key == pygame.K_c and ancla_actual:
                        modulo_centro.centrar(centro_actual, ancla_actual)
                        print(f"centro calibrado: ({centro_actual.x:.3f}, {centro_actual.y:.3f})")
                    if evento.key == pygame.K_g:
                        ver_esqueleto = not ver_esqueleto
                    if evento.key == pygame.K_SPACE:
                        corriendo = not corriendo
                        pid_x.reset()
                        pid_y.reset()
                        if not corriendo:
                            brazo.cancelar()
                        print(f"lazo {'corriendo' if corriendo else 'en pausa (0x85 mandado)'}")

            ok, frame = cam.read()
            if not ok:
                continue

            # MediaPipe quiere RGB contiguo; cv2 captura en BGR.
            rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            ts = max(int(time.monotonic() * 1000), ultimo_ts + 1)
            ultimo_ts = ts
            manos = motor.manos(rgb, ts)
            mano = manos[0] if manos else None

            ahora = time.perf_counter()
            dt = max(ahora - reloj_anterior, 1e-3)
            reloj_anterior = ahora

            ancla_actual = None
            if mano:
                ancla_actual = modulo_centro.anclar(mano)
                ex, ey = modulo_centro.error_de(ancla_actual, centro_actual)
                historia.append((ex, ey))
                if corriendo:
                    # El PID pide mm/s; el jog lleva distancia y feed. Cada
                    # jog dura un frame (con metros firmes de la wiki).
                    dt_jog = min(max(dt, JOG_MIN), JOG_MAX)
                    vx = pid_x.paso(ex, dt)
                    vy = pid_y.paso(ey, dt)
                    brazo.jog(
                        vx * dt_jog * args.sentido_x,
                        vy * dt_jog * args.sentido_y,
                        dt_jog,
                    )
                    frenado = False
            elif not frenado:
                # Mano perdida: freno inmediato y PID sin memoria. El 0x85 va
                # una sola vez por pérdida, no en cada frame.
                brazo.cancelar()
                pid_x.reset()
                pid_y.reset()
                frenado = True

            if ver_esqueleto and mano:
                renderer.esqueleto(rgb, mano)
            renderer.lazo(rgb, centro_actual, ancla_actual)
            renderer.grafico(rgb, historia)

            # frombuffer comparte memoria con el array, no lo copia: hay que
            # mantener rgb vivo mientras se usa la superficie. rgb se reasigna
            # al inicio del próximo frame, y la superficie vieja muere con él.
            superficie = pygame.image.frombuffer(rgb, (ancho, alto), "RGB")
            pantalla.blit(superficie, (0, 0))

            fps = 1.0 / dt
            fps_suave = fps if fps_suave == 0 else fps_suave * 0.9 + fps * 0.1
            modo_lazo = "corriendo" if corriendo else "PAUSA"
            pygame.display.set_caption(
                f"mano-pap — {canal.nombre} — {modo_lazo} — {fps_suave:.0f} fps"
            )
            pygame.display.flip()
    finally:
        brazo.cancelar()
        brazo.cerrar()
        cam.release()
        pygame.quit()


if __name__ == "__main__":
    main()
