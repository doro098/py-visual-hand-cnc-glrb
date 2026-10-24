"""Tests del PID con errores fabricados.

Sin cámara, sin serial, sin numpy: pid.Pid es computación pura, así que esto
corre en el host.

kp=100 significa: 1.0 de error (la mano en el borde del frame) pediría
100 mm/s, que vmax recorta. Los números de los tests se eligen para que la
salida quepa o no quepa, según lo que se quiere probar.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pid import Pid  # noqa: E402

DT = 1 / 30.0  # un frame de la cámara


def test_la_zona_muerta_no_inspira_salida():
    p = Pid(kp=100.0, muerto=0.02)
    assert p.paso(0.015, DT) == 0.0  # dentro de la zona: cero
    # fuera de la zona muerta sale la P con el error entero
    assert p.paso(0.03, DT) == pytest.approx(3.0)


def test_la_salida_va_del_lado_del_error():
    assert Pid(kp=100.0).paso(0.4, DT) > 0.0
    assert Pid(kp=100.0).paso(-0.4, DT) < 0.0


def test_la_salida_se_frena_en_vmax():
    p = Pid(kp=100.0, vmax=30.0)
    assert p.paso(5.0, DT) == 30.0
    assert p.paso(-5.0, DT) == -30.0


def test_la_integral_no_carga_deuda_infinita():
    # Solo I: kp=0, ki>0. Con error grande constante, saturar no es generar
    # deuda: la integral se frena en vmax/ki...
    p = Pid(kp=0.0, ki=10.0, vmax=30.0, muerto=0.0)
    for _ in range(500):
        p.paso(1.0, DT)
    assert p.paso(1.0, DT) == pytest.approx(30.0)
    assert p._integral <= 30.0 / 10.0 + 1e-9


def test_la_derivada_reacciona_al_salto():
    p = Pid(kp=0.0, kd=5.0, muerto=0.0)
    assert p.paso(0.1, DT) == 0.0  # sin error previo, no hay D que inventar
    # el error subió 0.1: D pide 5 * 0.1/dt = 15 mm/s
    assert p.paso(0.2, DT) == pytest.approx(15.0)


def test_reset_borra_toda_la_memoria():
    p = Pid(kp=10.0, ki=10.0, muerto=0.0)
    for _ in range(50):
        p.paso(0.5, DT)
    p.reset()
    # se comporta como un PID recién nacido: idéntico, error por error
    q = Pid(kp=10.0, ki=10.0, muerto=0.0)
    for _ in range(3):
        assert p.paso(0.3, DT) == pytest.approx(q.paso(0.3, DT))
        assert p.paso(-0.1, DT) == pytest.approx(q.paso(-0.1, DT))
