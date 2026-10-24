"""El motor de mano. Uno solo: landmarks.

Se registra por nombre por si algún día aparece otro, pero acá el lazo solo
necesita el esqueleto de 21 puntos.

Los motores se importan perezosamente: `import manos` no carga mediapipe,
así que los tests de pid/centro/grbl corren en el host sin el contenedor.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Mano, Motor

MOTORES = {
    "landmarks": ("manos.landmarks", "Landmarks"),
}


def cargar_motor(nombre: str):
    """Instancia el motor por nombre, importando su módulo en el momento."""
    if nombre not in MOTORES:
        raise KeyError(f"motor desconocido: {nombre}. hay {', '.join(sorted(MOTORES))}")
    modulo, clase = MOTORES[nombre]
    return getattr(import_module(modulo), clase)()


__all__ = ["MOTORES", "cargar_motor", "Mano", "Motor"]
