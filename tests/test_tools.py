from datetime import date, timedelta

import pytest

from gastos_agent.tools import eliminar_gasto, listar_gastos, registrar_gasto, resumen_gastos


@pytest.fixture(autouse=True)
def db_temporal(tmp_path, monkeypatch):
    monkeypatch.setenv("GASTOS_DB", str(tmp_path / "test.db"))


def test_registrar_ok():
    r = registrar_gasto(3500, "Comida", "almuerzo", "2026-01-10")
    assert r["status"] == "success"
    assert r["gasto"]["categoria"] == "comida"
    assert r["gasto"]["id"] == 1


@pytest.mark.parametrize("monto", [0, -5, "abc", None, float("nan")])
def test_registrar_monto_invalido(monto):
    assert registrar_gasto(monto, "comida", "x")["status"] == "error"


def test_registrar_categoria_vacia():
    assert registrar_gasto(100, "  ", "x")["status"] == "error"


def test_registrar_fecha_invalida_y_futura():
    assert registrar_gasto(100, "ocio", "x", "10/01/2026")["status"] == "error"
    futura = (date.today() + timedelta(days=3)).isoformat()
    assert registrar_gasto(100, "ocio", "x", futura)["status"] == "error"


def test_listar_vacio():
    r = listar_gastos()
    assert r["status"] == "success" and r["gastos"] == []


def test_listar_filtros():
    registrar_gasto(100, "comida", "a", "2026-01-01")
    registrar_gasto(200, "transporte", "b", "2026-02-01")
    assert len(listar_gastos(categoria="Comida")["gastos"]) == 1
    assert len(listar_gastos(desde="2026-01-15")["gastos"]) == 1
    assert listar_gastos(desde="2026-03-01", hasta="2026-01-01")["status"] == "error"
    assert listar_gastos(limite=0)["status"] == "error"
    assert listar_gastos(desde="ayer")["status"] == "error"


def test_resumen():
    registrar_gasto(100, "comida", "a", "2026-01-01")
    registrar_gasto(50, "comida", "b", "2026-01-02")
    registrar_gasto(30, "ocio", "c", "2026-01-03")
    r = resumen_gastos()
    assert r["total"] == 180
    assert r["por_categoria"] == {"comida": 150, "ocio": 30}
    assert r["categoria_mayor_gasto"] == "comida"


def test_resumen_vacio_y_fechas_invalidas():
    r = resumen_gastos()
    assert r["status"] == "success" and r["total"] == 0
    assert resumen_gastos(hasta="mañana")["status"] == "error"


def test_eliminar():
    registrar_gasto(100, "comida", "a", "2026-01-01")
    assert eliminar_gasto(1)["status"] == "success"
    assert eliminar_gasto(1)["status"] == "error"  # ya no existe


@pytest.mark.parametrize("id_gasto", [0, -1, "x", None, 1.5])
def test_eliminar_id_invalido(id_gasto):
    assert eliminar_gasto(id_gasto)["status"] == "error"
