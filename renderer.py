"""Dibujo mínimo sobre el frame: esqueleto, lazo y gráfica del error.

La ventana ya no anima gestos: muestra el lazo. Encima del video van los
ejes del centro cartesiano (dos líneas de punta a punta del frame), el
cross del centro, el ancla de la mano, la línea de error entre ambos, y
abajo un strip-chart con la historia del error horizontal (ex) y vertical
(ey) de los últimos segundos. Nada tapa el video: la franja del gráfico
se oscurece al 50% y las trazas van encima.

Cuidado con los colores: el frame es RGB (va directo al buffer de pygame),
así que acá "rojo" se escribe (255, 0, 0), al revés de la convención BGR
con la que opencv suele documentar sus constantes.
"""

import cv2
import numpy as np

from manos.base import CONECTIVIDAD

BLANCO = (255, 255, 255)
ROJO = (255, 0, 0)
VERDE = (0, 255, 0)
AMARILLO = (255, 255, 0)  # traza de ex, el error horizontal
CIAN = (0, 255, 255)      # traza de ey, el error vertical
GRIS = (128, 128, 128)

RADIO_ERROR = 0.5  # la gráfica se escala para mostrar errores de hasta 0.5


def esqueleto(frame: np.ndarray, mano) -> None:
    """El esqueleto de 21 puntos, dibujado in-place sobre el frame."""
    alto, ancho = frame.shape[:2]
    pixeles = [(int(x * ancho), int(y * alto)) for x, y in mano.puntos]
    for a, b in CONECTIVIDAD:
        cv2.line(frame, pixeles[a], pixeles[b], CIAN, 1, cv2.LINE_AA)
    for punto in pixeles:
        cv2.circle(frame, punto, 2, CIAN, -1, cv2.LINE_AA)


def lazo(frame: np.ndarray, centro, ancla: tuple[float, float] | None) -> None:
    """El eje cartesiano del centro, el ancla de la mano y la línea de error.

    Los ejes son dos líneas finas de punta a punta del frame que se cruzan
    en el centro; el cross grueso de arriba marca el propio centro.
    """
    alto, ancho = frame.shape[:2]
    cx, cy = round(centro.x * ancho), round(centro.y * alto)

    # Ejes: finos, referencian el centro sobre todo el frame.
    cv2.line(frame, (0, cy), (ancho - 1, cy), BLANCO, 1, cv2.LINE_AA)
    cv2.line(frame, (cx, 0), (cx, alto - 1), BLANCO, 1, cv2.LINE_AA)

    # El centro, de un vistazo: cross grueso.
    brazo = 14
    cv2.line(frame, (cx - brazo, cy), (cx + brazo, cy), BLANCO, 2, cv2.LINE_AA)
    cv2.line(frame, (cx, cy - brazo), (cx, cy + brazo), BLANCO, 2, cv2.LINE_AA)

    if ancla is None:
        return

    ax, ay = round(ancla[0] * ancho), round(ancla[1] * alto)
    cv2.line(frame, (cx, cy), (ax, ay), ROJO, 2, cv2.LINE_AA)
    cv2.circle(frame, (ax, ay), 6, VERDE, -1, cv2.LINE_AA)


def grafico(frame: np.ndarray, historia) -> None:
    """El strip-chart del error: una traza por eje, abajo del frame.

    `historia` es una deque de tuplas (ex, ey) normalizadas; la escala
    soporta errores de hasta RADIO_ERROR por lado. La franja va
    semi-transparente sobre el video: se oscurece al 50%, no lo tapa.
    """
    alto, ancho = frame.shape[:2]
    panel = max(alto // 5, 60)
    y0 = alto - panel

    # Transparencia barata: oscurecer la franja al 50% en vez de taparla
    # con negro sólido. El video se sigue viendo detrás de las trazas.
    frame[y0:alto, :] = frame[y0:alto, :] // 2
    cv2.rectangle(frame, (0, y0), (ancho - 1, alto - 1), GRIS, 1)

    y_cero = y0 + panel // 2
    cv2.line(frame, (0, y_cero), (ancho - 1, y_cero), GRIS, 1)

    if not historia:
        return

    ultimo_x, ultimo_y = historia[-1]
    etiqueta = f"ex (amarillo) {ultimo_x:+.3f}    ey (cian) {ultimo_y:+.3f}"
    cv2.putText(
        frame, etiqueta, (8, y0 + 18),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, GRIS, 1, cv2.LINE_AA,
    )

    if len(historia) < 2:
        return

    mitad = panel // 2 - 6  # margen entre la traza y el borde del panel
    factor = mitad / RADIO_ERROR

    def traza(indice: int, color: tuple[int, int, int]) -> None:
        n = len(historia)
        puntos = []
        for i, (ex, ey) in enumerate(historia):
            error = (ex, ey)[indice]
            error = max(-RADIO_ERROR, min(error, RADIO_ERROR))
            x = round(i * (ancho - 1) / (n - 1))
            y = y_cero - round(error * factor)
            puntos.append((x, y))
        cv2.polylines(frame, [np.array(puntos, np.int32)], False, color, 1, cv2.LINE_AA)

    traza(0, AMARILLO)
    traza(1, CIAN)
