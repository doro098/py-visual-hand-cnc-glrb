"""Tests del canal GRBL en seco: formato de jog, jog nulo, tope de feed, 0x85.

El backend serial no se testea acá: pide el Uno enchufado. Todo lo que
prueba esto es el camino que comparte con el modo real (la construcción de
los comandos), que es donde el formato importa.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from grbl import Grbl, Seco  # noqa: E402


def test_el_jog_habla_idioma_grbl():
    canal = Seco()
    brazo = Grbl(canal, feed_max=10000)
    # hipotenusa de 0.9 y 1.2 = 1.5 mm; 1.5 mm en 30 ms son 3000 mm/min.
    comando = brazo.jog(0.9, -1.2, 0.03)
    assert comando == "$J=G91 X+0.900 Y-1.200 F3000"
    assert canal.lineas == [comando]


def test_el_jog_nulo_no_se_manda():
    canal = Seco()
    brazo = Grbl(canal)
    assert brazo.jog(0.0, 0.0, 0.03) is None
    assert canal.lineas == []


def test_el_feed_tope_no_se_supera():
    canal = Seco()
    brazo = Grbl(canal, feed_max=600)
    # 10 mm en 30 ms pedirían 20000 mm/min: queda en el feed_max.
    assert brazo.jog(10.0, 0.0, 0.03).endswith("F600")


def test_cancelar_manda_el_byte_realtime():
    canal = Seco()
    brazo = Grbl(canal)
    brazo.cancelar()
    assert canal.brutos == [0x85]
