"""El centro cartesiano del frame y el error que le sigue.

El lazo busca que el ancla de la mano caiga en este punto del frame. Arranca
en el medio (0.5, 0.5) y se recalibra en vivo: la tecla `c` de la ventana
hace que el centro pase a donde está la mano en ese momento.

Todo son coordenadas normalizadas 0-1, como las que entrega MediaPipe.
"""

from __future__ import annotations

from dataclasses import dataclass

from manos.base import Mano

# El ancla es el centro de la palma: promedio de la muñeca (0), la base del
# índice (5) y la base del meñique (17). Las puntas de los dedos crujen con
# cada frame; la palma es lo estable.
_MUNECA = 0
_BASE_INDICE = 5
_BASE_MENIQUE = 17


@dataclass
class Centro:
    """Punto del frame donde el brazo sostiene la mano. Mutado al calibrar."""

    x: float = 0.5
    y: float = 0.5


def anclar(mano: Mano) -> tuple[float, float]:
    """El punto de la mano que el PID persigue, en coordenadas del frame."""
    anclas = [mano.puntos[i] for i in (_MUNECA, _BASE_INDICE, _BASE_MENIQUE)]
    return (
        sum(x for x, _ in anclas) / len(anclas),
        sum(y for _, y in anclas) / len(anclas),
    )


def error_de(ancla: tuple[float, float], centro: Centro) -> tuple[float, float]:
    """La distancia de la mano al centro: lo único que le importa al PID.

    Es positivo hacia la derecha y hacia abajo (la y del frame crece hacia
    abajo). El sentido respecto del brazo real lo corrige SENTIDO_X/Y en la
    ventana, no acá.
    """
    return (ancla[0] - centro.x, ancla[1] - centro.y)


def centrar(centro: Centro, ancla: tuple[float, float]) -> None:
    """Calibración: el centro pasa a la mano. Muta el centro, no devuelve nada."""
    centro.x = ancla[0]
    centro.y = ancla[1]
