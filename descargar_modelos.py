"""Descarga del checkpoint de MediaPipe que usa este proyecto.

Se ejecuta al construir la imagen (ver Dockerfile). El modelo se baja una
vez y queda en $MODELOS_DIR, así el arranque no depende de internet.

Este proyecto no entrena ni clasifica gestos: el único checkpoint es el
hand landmarker de fábrica.
"""

import os
import urllib.request
from pathlib import Path

CHECKPOINTS = {
    "hand_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/latest/hand_landmarker.task"
    ),
}


def descargar() -> None:
    destino = Path(os.environ.get("MODELOS_DIR", "/modelos"))
    destino.mkdir(parents=True, exist_ok=True)

    for nombre, url in CHECKPOINTS.items():
        ruta = destino / nombre
        if ruta.exists():
            print(f"ya estaba: {ruta}")
            continue
        print(f"bajando {nombre}...")
        urllib.request.urlretrieve(url, ruta)
        print(f"descargado: {ruta} ({ruta.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    descargar()
