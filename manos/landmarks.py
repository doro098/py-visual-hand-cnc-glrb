"""Motor landmarks: el esqueleto de 21 puntos, sin clasificar nada.

Usa el Hand Landmarker de MediaPipe Tasks en modo VIDEO, que trackea entre
frames y no re-detecta la mano cara: es lo que mantiene los FPS altos.

`num_manos` arranca en 1: el lazo persigue un único blanco, y trackear dos
manos es el doble de cómputo para nada.
"""

import os
from pathlib import Path

import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from .base import Mano

MODELOS_DIR = Path(os.environ.get("MODELOS_DIR", "/modelos"))
MODELO = MODELOS_DIR / "hand_landmarker.task"


class Landmarks:
    nombre = "landmarks"

    def __init__(self, num_manos: int = 1) -> None:
        if not MODELO.exists():
            raise FileNotFoundError(
                f"falta el modelo {MODELO}; corré descargar_modelos.py"
            )
        opciones = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(MODELO)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_manos,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(opciones)

    def manos(self, frame_rgb: np.ndarray, timestamp_ms: int) -> list[Mano]:
        resultado = self._landmarker.detect_for_video(
            _imagen(frame_rgb), timestamp_ms
        )
        return _a_manos(resultado.hand_landmarks, resultado.handedness)


def _a_manos(por_mano, por_lateralidad) -> list[Mano]:
    """Traduce la salida del landmarker a la interfaz del proyecto."""
    salidas = []
    for i, puntos in enumerate(por_mano):
        categoria = por_lateralidad[i][0] if i < len(por_lateralidad) else None
        salidas.append(
            Mano(
                puntos=[(p.x, p.y) for p in puntos],
                lateralidad=categoria.category_name if categoria else "?",
            )
        )
    return salidas


def _imagen(frame_rgb: np.ndarray) -> "mp.Image":
    # mp.Image no copia: el buffer que le pasamos tiene que ser RGB y contiguo.
    return mp.Image(
        image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame_rgb)
    )
