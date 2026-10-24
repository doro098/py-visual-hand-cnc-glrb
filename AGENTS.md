# AGENTS.md — mano-pap: la cámara sigue a la mano

## Objetivo

Que la cámara (montada sobre un brazo de 2 ejes) sostenga a la mano en el
centro del frame. El lazo: la ancla de la palma contra un centro cartesiano,
el error horizontal y vertical va a un PID por eje, y la velocidad que sale
se manda al Arduino Uno (GRBL v1.1) como jog incremental para mover los dos
motores paso a paso. Una ventana SDL2 muestra el video con el cross del
centro, la ancla, la línea de error y un strip-chart del error.

## Entorno

Contenedor Debian (bookworm), como en py-visual-hands: el host es Alpine con
Python 3.14 y no hay wheels de mediapipe ni opencv para musl. La imagen de
este repo hereda `py-visual-hands-manos:latest` (el ambiente ya está
instalado, el build no baja paquetes salvo pyserial/pytest). El compose
corre con `user: "1000:1000"` para el socket Wayland del host, con `/dev/dri`
para que SDL escale en la Vega 8, y con los nodos de video mapeados.

## Cámara

El compose arranca en la cámara del brazo (`CAMARA=/dev/cam.brazo`: el
by-id del host de la XZD montado con nombre estable, entrega color),
pidiendo MJPG: sin eso el bus USB no llega a 30 fps. Los índices de video
cambian con cada desenchufe, la ruta `/dev/cam.brazo` no.

## Motor

Uno solo: `landmarks`. La interfaz es la heredada:

    manos(frame_rgb: ndarray, timestamp_ms: int) -> list[Mano]

`num_manos=1`: el lazo persigue un blanco, trackear dos es cómputo al aire.

## Ancla y error

El ancla es el centro de la palma: promedio de los puntos 0 (muñeca), 5
(base del índice) y 17 (base del meñique). Las puntas crujen; la palma es
estable. El error va en coordenadas normalizadas 0-1 (`centro.error_de`);
el signo que termina en el brazo lo corrigen `SENTIDO_X/Y`, porque depende
del wiring mecánico.

## PID

`pid.Pid` es computación pura: entra error (normalizado), sale mm/s. Tiene
zona muerta (el esqueleto tiembla), anti-windup (la integral se frena en
vmax/ki) y salida limitada a vmax. Se testea con errores fabricados, sin
cámara ni serial, en el host. Defaults: kp=60, ki=8, kd=0.

## GRBL

`grbl.py` con dos canales: `Seco` (default: imprime los `$J=`, cero
hardware) y `Serial` (el Uno a 115200, espera el `ok` de cada comando para
mantener el planner fino). La unidad de mando es el jog incremental corto
(`$J=G91 X.. Y.. F..`, cada uno dura un frame de la loop, con dt sujeto a
0.02–0.06 s según la wiki de GRBL). El freno es el byte realtime `0x85`,
que va cuando la mano desaparece y al salir o pausar.

## Iterar

El código va montado como volumen (`. /` → `/app`): editar un `.py` en el
host no exige re-buildear.

    docker compose restart pap

`restart` no incorpora mounts ni devices nuevos: para el compose hace falta
`docker compose up -d`.

## Comandos

    docker compose up                                    # seco
    GRBL_PUERTO=/dev/ttyUSB0 docker compose up pap       # con el Uno
    docker compose run --rm pap python -m pytest tests -q

## Docs

    README.md             el lazo, el hardware, los ajustes
    docs/DECISIONES.md    por qué GRBL, por qué jog, por qué seco, qué se tiró
