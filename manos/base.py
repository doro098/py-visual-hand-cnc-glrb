"""Interfaz del motor de mano.

Este proyecto tiene un solo motor, y expone lo mismo que en py-visual-hands:

    manos(frame_rgb: ndarray, timestamp_ms: int) -> list[Mano]

El frame llega en RGB. El motor no decide cómo se captura ni cómo se dibuja:
solo traduce la imagen en manos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    import numpy as np

# Los 21 puntos que predice MediaPipe para una mano. Orden fijo del modelo:
# 0 muñeca, 1-4 pulgar, 5-8 índice, 9-12 medio, 13-16 anular, 17-20 meñique.
PUNTOS = 21


@dataclass
class Mano:
    """Una mano detectada.

    `puntos` son 21 tuplas (x, y) normalizadas 0-1 sobre el frame, en el mismo
    orden que el modelo de MediaPipe. `lateralidad` es "Left" o "Right" tal
    cual lo predice el modelo.

    `gesto` queda en None: este proyecto no clasifica gestos, solo sigue.
    """

    puntos: list[tuple[float, float]]
    lateralidad: str
    gesto: str | None = None
    confianza: float | None = None


@runtime_checkable
class Motor(Protocol):
    nombre: str

    def manos(self, frame_rgb: np.ndarray, timestamp_ms: int) -> list[Mano]:
        ...


# Aristas del esqueleto, para dibujar. Es la conexión estándar de la mano de
# MediaPipe: dedo por dedo, más la base del meñique y la de la muñeca.
CONECTIVIDAD: Sequence[tuple[int, int]] = (
    (0, 1), (1, 2), (2, 3), (3, 4),        # pulgar
    (0, 5), (5, 6), (6, 7), (7, 8),        # índice
    (5, 9), (9, 10), (10, 11), (11, 12),   # medio
    (9, 13), (13, 14), (14, 15), (15, 16), # anular
    (13, 17), (17, 18), (18, 19), (19, 20),# meñique
    (0, 17),                                # base de la mano
)
