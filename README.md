# mano-pap

La cámara sigue a la mano. La webcam va montada sobre un brazo de dos ejes
(dos motores paso a paso, movidos por un Arduino Uno con GRBL); la mano es
el blanco, y un PID por eje mantiene el ancla de la palma en el centro del
frame. La ventana muestra el video, el centro, el ancla, la línea de error
y un strip-chart con la historia del error horizontal y vertical.

## El lazo

    cámara → MediaPipe (21 landmarks) → ancla de la palma
    ancla vs centro cartesiano → error (ex, ey)
    PID ex, PID ey → velocidad en mm/s → jog $J=G91 X.. Y.. F..
    GRBL (Arduino Uno) → 2 motores paso a paso → mueve la cámara

- Mano perdida: byte realtime `0x85` (cancela los jogs y vacía el planner:
  el brazo para en el acto).
- Sin Uno enchufado: modo **seco**, los `$J=` salen por stdout y el lazo
  completo se prueba igual (gráfico incluido).

## Hardware

- Arduino Uno + shield GRBL, firmware **GRBL v1.1** (gnea/grbl, flasheado
  con avrdude — es un paso aparte, no lo hace este repo).
- Puesta a punto en GRBL: `$100/$101` (pasos/mm de cada eje, según tus
  tornillos y drivers), `$110/$111` (velocidad máxima) y sobre todo
  `$120/$121` (aceleración): la latencia del lazo va con la aceleración
  (`dt > v²/(2·a·(N-1))` en la wiki de GRBL). Braza corto = subí `a`.
- Cámara: la USB del brazo (XZD), montada por `by-id` como `/dev/cam.brazo`
  para que los índices de V4L2 — que cambian con cada desenchufe — no
  importen. MJPG pedido; es la misma del otro proyecto.

## Correr

    docker compose up                        # modo seco, PID imprimiendo
    docker compose run --rm pap python -m pytest tests -q

Serial real:

    GRBL_PUERTO=/dev/ttyUSB0 docker compose up pap

(si cambiaste env o devices, `docker compose up -d` recrea; el `restart`
no recarga eso).

## Ajustes

| Cosa | Dónde |
|---|---|
| Ganancias del PID | `--kp --ki --kd` (arranque sugerido: 60 / 8 / 0) |
| Zona muerta (el esqueleto tiembla) | `--muerto` (default 0.012) |
| Velocidad y feed máximos | `--vmax` (mm/s), `--feed` (mm/min) |
| Brazo que corre al revés | `--sentido-x` / `--sentido-y` con `-1` |

Teclas: `c` calibra el centro a la posición de la mano, `espacio` pausa/
reanuda (la pausa manda `0x85`), `g` esqueleto, `q`/`ESC` salir.

## Estructura

    manos/          motor landmarks (heredado de py-visual-hands)
    centro.py       centro cartesiano, ancla de la palma, error
    pid.py          el PID (puro, testeado con errores fabricados)
    grbl.py         canales seco/serial: $J=, acks, 0x85
    renderer.py     overlay: ejes, cross, ancla, error, strip-chart semi-transparente
    ventana.py      el loop
    tests/          pid, centro, grbl — corren en el host, sin hardware

## Versiones

La rama de origen de este proyecto es py-visual-hands (mismo motor, misma
ventana SDL/Wayland, mismo contenedor Debian). De hecho la imagen Docker
de acá **hereda** de `py-visual-hands-manos:latest`: trae mediapipe,
opencv y pygame instalados, así que el build de este repo no baja
paquetes (el pip solo agrega pyserial y pytest, ~1 MB) y reusa el
`hand_landmarker.task` de `/modelos`. Las decisiones de diseño
están en `docs/DECISIONES.md`.
