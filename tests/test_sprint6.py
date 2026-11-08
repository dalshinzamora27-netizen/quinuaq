import pytest
from app import db
from app.models.mesa import Mesa
from app.models.comanda import Comanda
from app.models.producto import Producto
from app.models.venta import Venta

# US-016 — pagina de reportes carga correctamente
def test_reportes_carga(client_admin):
    r = client_admin.get("/admin/reportes")
    assert r.status_code == 200
    assert "Reporte mensual".encode() in r.data
    assert "Top 10".encode() in r.data

# US-016 — filtro por defecto usa el mes actual
def test_reportes_filtro_default(client_admin):
    r = client_admin.get("/admin/reportes")
    assert r.status_code == 200
    # debe incluir los inputs de fecha con algun valor
    assert b'type="date"' in r.data

# US-016 — filtro por rango de fechas personalizado
def test_reportes_rango_personalizado(client_admin):
    r = client_admin.get("/admin/reportes?desde=2026-01-01&hasta=2026-12-31&orden=ingresos")
    assert r.status_code == 200
    assert "2026-01-01".encode() in r.data
    assert "2026-12-31".encode() in r.data

# US-016 — ordenar por unidades vs ingresos cambia el orden
def test_reportes_orden_unidades(client_admin):
    r = client_admin.get("/admin/reportes?orden=unidades")
    assert r.status_code == 200
    assert b'value="unidades" selected' in r.data

def test_reportes_orden_ingresos(client_admin):
    r = client_admin.get("/admin/reportes?orden=ingresos")
    assert r.status_code == 200
    assert b'value="ingresos" selected' in r.data

# US-016 — rango sin ventas muestra mensaje vacio
def test_reportes_rango_sin_ventas(client_admin):
    r = client_admin.get("/admin/reportes?desde=2020-01-01&hasta=2020-01-02")
    assert r.status_code == 200
    assert "No hay ventas registradas".encode() in r.data

# US-016 — metricas del rango son coherentes con las ventas reales
def test_reportes_metricas_coherentes(client_admin, app):
    with app.app_context():
        total_ventas_bd = Venta.query.count()

    r = client_admin.get("/admin/reportes?desde=2020-01-01&hasta=2030-12-31")
    assert r.status_code == 200
    # si hay ventas en BD, deben aparecer reflejadas en el rango amplio
    if total_ventas_bd > 0:
        assert b"No hay ventas registradas" not in r.data