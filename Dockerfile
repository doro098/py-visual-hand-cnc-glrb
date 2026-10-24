FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODELOS_DIR=/modelos

# libsdl2 con soporte wayland (nativo en tu KDE) y x11 (fallback vía XWayland).
# libgl1/libegl1 y el dri de mesa para que SDL acelere en la Vega 8.
# libgles2 lo cargan las bindings C de MediaPipe en runtime (libGLESv2.so.2).
# libglib2.0-0 la pide opencv al importar.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsdl2-2.0-0 \
        libsdl2-image-2.0-0 \
        libgl1 \
        libegl1 \
        libgles2 \
        libgl1-mesa-dri \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app

# El checkpoint se baja al construir, no al arrancar: el contenedor puede
# quedarse sin internet y la app igual levanta.
RUN mkdir -p "$MODELOS_DIR" && python descargar_modelos.py

# Corre como el usuario del host (uid 1000) porque el socket de Wayland es
# 755 y solo el dueño puede conectarse. Sin passwd propio, HOME=/tmp.
USER 1000:1000
ENV HOME=/tmp

CMD ["python", "ventana.py"]
