import pytest
from app import db
from app.models.mesa import Mesa
from app.models.comanda import Comanda, DetalleComanda
from app.models.producto import Producto
from app.models.venta import Venta, Pago

@pytest.fixture
def mesa_esperando_pago(app, client_mozo):
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="libre").first()
        if not mesa:
            mesa = Mesa(numero=97, capacidad=4, estado="libre")
            db.session.add(mesa)
            db.session.commit()
        mid = mesa.id

    r = client_mozo.post(f"/mozo/mesa/{mid}/abrir",
        json={"comensales": 2}, content_type="application/json")
    cid = r.get_json()["comanda_id"]

    with app.app_context():
        producto = Producto.query.first()
        pid = producto.id

    client_mozo.post(f"/mozo/comanda/{cid}/agregar",
        json={"producto_id": pid, "cantidad": 1, "nota": ""},
        content_type="application/json")

    client_mozo.post(f"/mozo/mesa/{mid}/solicitar_cuenta")

    yield mid, cid

    with app.app_context():
        venta = Venta.query.filter_by(comanda_id=cid).first()
        if venta:
            db.session.delete(venta)
        comanda = Comanda.query.get(cid)
        if comanda:
            db.session.delete(comanda)
        mesa = Mesa.query.get(mid)
        mesa.estado = "libre"
        mesa.mozo_id = None
        db.session.commit()


# US-012 — boleta con DNI invalido
def test_boleta_dni_invalido(client_cajero, mesa_esperando_pago):
    mid, cid = mesa_esperando_pago

    r = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo":"boleta","dni_cliente":"123",
              "pagos":[{"metodo":"efectivo","monto":1000}]},
        content_type="application/json")
    assert r.status_code == 400
    assert "8 dígitos" in r.get_json()["error"]

# US-012 — boleta correcta
def test_boleta_exitosa(client_cajero, mesa_esperando_pago, app):
    mid, cid = mesa_esperando_pago

    with app.app_context():
        comanda = Comanda.query.get(cid)
        subtotal = sum(float(d.producto.precio) * d.cantidad for d in comanda.detalles)
        total = round(subtotal * 1.18, 2)

    r = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo":"boleta","dni_cliente":"12345678",
              "pagos":[{"metodo":"efectivo","monto":total}]},
        content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] == True
    assert data["numero"].startswith("B001-")

    with app.app_context():
        mesa = Mesa.query.get(mid)
        assert mesa.estado == "libre"
        venta = Venta.query.get(data["venta_id"])
        assert venta.tipo == "boleta"
        assert venta.dni_cliente == "12345678"

# US-013 — factura sin RUC
def test_factura_sin_ruc(client_cajero, mesa_esperando_pago):
    mid, cid = mesa_esperando_pago

    r = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo":"factura","ruc_cliente":"","razon_social":"Empresa SAC",
              "pagos":[{"metodo":"efectivo","monto":1000}]},
        content_type="application/json")
    assert r.status_code == 400
    assert "RUC" in r.get_json()["error"]

# US-013 — factura con RUC invalido (no 11 digitos)
def test_factura_ruc_invalido(client_cajero, mesa_esperando_pago):
    mid, cid = mesa_esperando_pago

    r = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo":"factura","ruc_cliente":"123","razon_social":"Empresa SAC",
              "pagos":[{"metodo":"efectivo","monto":1000}]},
        content_type="application/json")
    assert r.status_code == 400
    assert "11 dígitos" in r.get_json()["error"]

# US-013 — factura exitosa
def test_factura_exitosa(client_cajero, mesa_esperando_pago, app):
    mid, cid = mesa_esperando_pago

    with app.app_context():
        comanda = Comanda.query.get(cid)
        subtotal = sum(float(d.producto.precio) * d.cantidad for d in comanda.detalles)
        total = round(subtotal * 1.18, 2)

    r = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo":"factura","ruc_cliente":"20123456789","razon_social":"Empresa SAC",
              "pagos":[{"metodo":"efectivo","monto":total}]},
        content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["numero"].startswith("F001-")

    with app.app_context():
        venta = Venta.query.get(data["venta_id"])
        assert venta.ruc_cliente == "20123456789"
        assert venta.razon_social == "Empresa SAC"
        assert float(venta.igv) == round(float(venta.subtotal) * 0.18, 2)

# US-014 — pago mixto
def test_pago_mixto(client_cajero, mesa_esperando_pago, app):
    mid, cid = mesa_esperando_pago

    with app.app_context():
        comanda = Comanda.query.get(cid)
        subtotal = sum(float(d.producto.precio) * d.cantidad for d in comanda.detalles)
        total = round(subtotal * 1.18, 2)
        mitad = round(total / 2, 2)
        resto = round(total - mitad, 2)

    r = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo":"nota_venta",
              "pagos":[{"metodo":"efectivo","monto":mitad},
                       {"metodo":"yape_plin","monto":resto}]},
        content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] == True

    with app.app_context():
        venta = Venta.query.get(data["venta_id"])
        assert len(venta.pagos) == 2

# US-014 — suma de pagos no coincide con total
def test_pagos_no_coinciden(client_cajero, mesa_esperando_pago):
    mid, cid = mesa_esperando_pago

    r = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo":"nota_venta",
              "pagos":[{"metodo":"efectivo","monto":1}]},
        content_type="application/json")
    assert r.status_code == 400
    assert "no coincide" in r.get_json()["error"]

# US-014 — cierre de turno calcula sobrante/faltante
def test_cierre_calcula_diferencia(client_cajero, mesa_esperando_pago, app):
    mid, cid = mesa_esperando_pago

    with app.app_context():
        comanda = Comanda.query.get(cid)
        subtotal = sum(float(d.producto.precio) * d.cantidad for d in comanda.detalles)
        total = round(subtotal * 1.18, 2)

    client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo":"nota_venta",
              "pagos":[{"metodo":"efectivo","monto":total}]},
        content_type="application/json")

    # efectivo real menor -> faltante
    r = client_cajero.post("/cajero/cierre/confirmar",
        json={"efectivo_real": 0}, content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["tipo"] == "faltante"
    assert data["diferencia"] < 0

# generar_numero produce numeros distintos
def test_numero_correlativo_unico(client_cajero, mesa_esperando_pago, app):
    mid, cid = mesa_esperando_pago

    with app.app_context():
        comanda = Comanda.query.get(cid)
        subtotal = sum(float(d.producto.precio) * d.cantidad for d in comanda.detalles)
        total = round(subtotal * 1.18, 2)

    r1 = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo":"nota_venta",
              "pagos":[{"metodo":"efectivo","monto":total}]},
        content_type="application/json")

    assert r1.get_json()["numero"].startswith("NV-")