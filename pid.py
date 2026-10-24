"""El PID que convierte el error del centro en velocidad, por eje.

Un PID por eje: entra el error (ancla de la mano menos centro, en unidades
normalizadas del frame), sale una velocidad en mm/s para el eje. No hay
modelo del brazo: las ganancias se ajustan a ojo con el hardware enfrente.

Decisiones contra el ruido y contra el hardware:

    - zona muerta: debajo del umbral el error cuenta como cero. El esqueleto
      de MediaPipe tiembla un par de píxeles; sin esto el brazo vibra siempre.
    - la derivada usa el error del frame anterior y sale ya dividida por dt:
      a 30 fps un dt ruidoso mata al término D.
    - anti-windup: la integral se frena a sí misma en el tope de salida, así
      que si el brazo demora en alcanzar, el PID no carga deuda infinita.
    - salida limitada a vmax (mm/s): es lo único que le pasa al feed del jog
      de GRBL.

Es una clase con estado, pero pura computación: funciona con errores
fabricados, sin cámara ni serial (así la testean los tests).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Pid:
    """Ganancias y estado de un eje.

    kp/ki/kd en mm/s por unidad de error (o por unidad de error·segundo para
    la integral). El error entra normalizado 0-1, así que kp=60 significa:
    "si la mano está a media cámara de distancia, quiero 30 mm/s".
    """

    kp: float
    ki: float = 0.0
    kd: float = 0.0
    muerto: float = 0.012
    vmax: float = 30.0
    _integral: float = field(default=0.0)
    _error_previo: float | None = field(default=None)

    def paso(self, error: float, dt: float) -> float:
        """Un paso del lazo: error -> velocidad del eje, en mm/s."""
        if abs(error) <= self.muerto:
            error = 0.0

        if self.ki:
            # Anti-windup: la integral sola no puede pedir más que vmax.
            tope = self.vmax / self.ki
            self._integral = max(-tope, min(self._integral + error * dt, tope))

        p = self.kp * error
        i = self.ki * self._integral

        d = 0.0
        if self.kd and self._error_previo is not None and dt > 0.0:
            d = self.kd * (error - self._error_previo) / dt
        self._error_previo = error

        return max(-self.vmax, min(p + i + d, self.vmax))

    def reset(self) -> None:
        """Se olvidó la historia: para arrancar de nuevo con la mano viva."""
        self._integral = 0.0
        self._error_previo = None
