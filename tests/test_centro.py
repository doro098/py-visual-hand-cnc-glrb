"""Tests del centro cartesiano y del ancla, con una mano fabricada."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from centro import Centro, anclar, centrar, error_de  # noqa: E402
from manos.base import Mano  # noqa: E402


def _mano_fabricada() -> Mano:
    """21 puntos, casi todos fuera del camino del ancla.

    Si anclar() agarra un punto que no sea (0, 5, 17), el promedio sale mal
    y el test lo ve: solo esos tres definen la respuesta.
    """
    puntos = [(0.9, 0.9)] * 21
    puntos[0] = (0.2, 0.8)   # muñeca
    puntos[5] = (0.3, 0.4)   # base del índice
    puntos[17] = (0.7, 0.3)  # base del meñique
    return Mano(puntos=puntos, lateralidad="Right")


def test_el_ancla_es_el_centro_de_la_palma():
    assert anclar(_mano_fabricada()) == pytest.approx((0.4, 0.5))


def test_el_error_es_ancla_menos_centro():
    ex, ey = error_de((0.7, 0.3), Centro())
    assert ex == pytest.approx(0.2)   # mano a la derecha del centro
    assert ey == pytest.approx(-0.2)  # y más arriba (la y del frame va hacia abajo)


def test_centrar_muta_el_centro():
    c = Centro()
    centrar(c, (0.25, 0.75))
    assert (c.x, c.y) == (0.25, 0.75)
