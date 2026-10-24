# No reinstalamos un ambiente que ya existe: py-visual-hands-manos (la
# imagen hermana de este proyecto, mismo motor y misma ventana) trae
# Debian + mediapipe + opencv + pygame andando, y el hand_landmarker.task
# en /modelos. Desde esa imagen heredamos y solo copiamos el código de
# mano-pap: el pip de abajo no baja nada nuevo, los requisitos ya están
# satisfechos salvo pyserial (que solo se usa con el Uno enchufado) y
# pytest, unos MB en total.
FROM py-visual-hands-manos:latest

ENV PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    MODELOS_DIR=/modelos

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt

COPY . /app

# Idempotente: si el checkpoint ya está (como en la imagen hermana),
# imprime "ya estaba" y no baja nada. Sirve si algún día se construye
# sin la imagen hermana.
RUN python descargar_modelos.py

# Corre como el usuario del host (uid 1000) porque el socket de Wayland es
# 755 y solo el dueño puede conectarse. Sin passwd propio, HOME=/tmp.
USER 1000:1000

CMD ["python", "ventana.py"]
