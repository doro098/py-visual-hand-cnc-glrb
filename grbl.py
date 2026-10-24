"""El puente Python → GRBL: jogs incrementales cortos y freno inmediato.

GRBL v1.1 (gnea/grbl flasheado en el Arduino Uno) mueve los dos motores
paso a paso del brazo. El lazo no manda posiciones absolutas: manda jogs
incrementales cortos (`$J=G91 X.. Y.. F..`) de la velocidad que pide el PID.
GRBL planifica siempre hasta frenar dentro de lo encolado: con un solo jog
en el buffer la latencia es la mínima posible, y el comando realtime 0x85
cancela el jog en curso y vacía la cola, que es el freno sin soft-reset.

El canal por defecto es `seco`: imprime los comandos y no toca hardware. Es
cómo se prueba el lazo completo (PID + gráfico) sin el brazo enchufado, y el
mismo camino que usan los tests. `serial` habla con el Uno a 115200, espera
el `ok` de cada comando antes de mandar el siguiente (buffer fino siempre)
e importe pyserial solo si se usa.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

# Byte realtime de cancelación de jog de GRBL v1.1. Va solo, sin \n, y no
# recibe respuesta: corta el movimiento y vacía el planner.
JOG_CANCEL = 0x85


class Seco:
    """Canal sin hardware: imprime y guarda lo mandado (así se testea)."""

    nombre = "seco"

    def __init__(self) -> None:
        self.lineas: list[str] = []
        self.brutos: list[int] = []

    def conectar(self) -> None:
        self.lineas.clear()
        self.brutos.clear()

    def escribir(self, texto: str) -> None:
        sys.stdout.write(f"{texto}\n")
        self.lineas.append(texto)

    def escribir_byte(self, byte: int) -> None:
        print(f"{byte:#04x}  # realtime: cancel jog", flush=True)
        self.brutos.append(byte)

    def cerrar(self) -> None:
        pass


class Serial:
    """Canal real con el Uno."""

    nombre = "serial"

    def __init__(self, puerto: str, baudios: int = 115200, espera: float = 0.5) -> None:
        import serial  # pyserial: se instala junto con los requerimientos

        self._puerto = serial.Serial(puerto, baudios, timeout=espera)

    def conectar(self) -> None:
        # GRBL se reinicia al abrir el puerto: la bienvenida llega sola. El
        # \r\n\r\n fuerza el "ok" final si el boot ya había terminado.
        self._puerto.write(b"\r\n\r\n")
        while True:
            linea = self._linea()
            if linea.startswith("Grbl"):
                print(linea)
            if linea == "ok":
                return
            if linea.startswith("error:"):
                raise RuntimeError(f"grbl rechazó el handshake: {linea}")

    def escribir(self, texto: str) -> None:
        """Manda un comando y espera el ack: mantiene el buffer en un jog."""
        self._puerto.write((texto + "\n").encode("ascii"))
        respuesta = self._ack()
        if respuesta.startswith("error:"):
            sys.stderr.write(f"grbl {respuesta}: {texto}\n")

    def escribir_byte(self, byte: int) -> None:
        # Realtime: sin \n y sin respuesta.
        self._puerto.write(bytes([byte]))

    def cerrar(self) -> None:
        self._puerto.close()

    def _linea(self) -> str:
        return self._puerto.readline().decode("ascii", "replace").strip()

    def _ack(self) -> str:
        vacios = 0
        while vacios < 10:
            linea = self._linea()
            if linea == "ok" or linea.startswith("error:"):
                return linea
            # Los mensajes sueltos (<status|reportes>, bienvenida) no son ack.
            vacios += 0 if linea else 1
        return "error: grbl no responde"


@dataclass
class Grbl:
    """Las acciones del brazo sobre un canal, ya sea seco o serial."""

    canal: Seco | Serial
    feed_max: float = 600.0  # mm/min; GRBL lo recorta igual con $110/$111

    def conectar(self) -> None:
        self.canal.conectar()

    def jog(self, dx: float, dy: float, dt: float) -> str | None:
        """Un jog incremental corto: distancia = velocidad pedida * dt.

        El feed sale de la propia distancia y del dt, porque en GRBL el F de
        un jog es no-modal: cada $J= lleva el suyo. Devuelve el comando (o
        None si el movimiento es nulo).
        """
        distancia = math.hypot(dx, dy)
        if distancia < 0.001:
            return None
        feed = min(distancia / max(dt, 1e-6) * 60.0, self.feed_max)
        comando = f"$J=G91 X{dx:+.3f} Y{dy:+.3f} F{feed:.0f}"
        self.canal.escribir(comando)
        return comando

    def cancelar(self) -> None:
        """Freno: cancela el jog en curso y vacía lo encolado. Sin soft-reset."""
        self.canal.escribir_byte(JOG_CANCEL)

    def cerrar(self) -> None:
        self.canal.cerrar()
