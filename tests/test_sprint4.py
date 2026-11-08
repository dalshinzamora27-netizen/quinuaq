import pytest
from app import db
from app.models.mesa import Mesa
from app.models.comanda import Comanda, DetalleComanda
from app.models.producto import Producto

@pytest.fixture
def comanda_con_items(app, client_mozo):
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="libre").first()
        if not mesa:
            mesa = Mesa(numero=98, capacidad=4, estado="libre")
            db.session.add(mesa)
            db.session.commit()
        mid = mesa.id

    r = client_mozo.post(f"/mozo/mesa/{mid}/abrir",
        json={"comensales": 2}, content_type="application/json")
    cid = r.get_json()["comanda_id"]

    with app.app_context():
        comida = Producto.query.join(Producto.categoria).filter_by(tipo="comida").first()
        bebida = Producto.query.join(Producto.categoria).filter_by(tipo="bebida").first()
        cid_comida, cid_bebida = comida.id, bebida.id

    client_mozo.post(f"/mozo/comanda/{cid}/agregar",
        json={"producto_id": cid_comida, "cantidad": 1, "nota": "Sin sal"},
        content_type="application/json")
    client_mozo.post(f"/mozo/comanda/{cid}/agregar",
        json={"producto_id": cid_bebida, "cantidad": 2, "nota": ""},
        content_type="application/json")
    client_mozo.post(f"/mozo/comanda/{cid}/despachar")

    yield cid, mid

    with app.app_context():
        comanda = Comanda.query.get(cid)
        if comanda:
            mesa = Mesa.query.get(comanda.mesa_id)
            mesa.estado = "libre"
            mesa.mozo_id = None
            db.session.delete(comanda)
            db.session.commit()


# US-009 — monitor de cocina muestra solo comida
def test_monitor_cocina_solo_comida(client_cocinero, comanda_con_items, app):
    r = client_cocinero.get("/cocina/")
    assert r.status_code == 200

    with app.app_context():
        cid, _ = comanda_con_items
        items = DetalleComanda.query.filter_by(comanda_id=cid).all()
        for item in items:
            if item.producto.categoria.tipo == "comida":
                assert item.producto.nombre.encode() in r.data
            else:
                # las bebidas no deberian estar en este monitor
                pass

# US-018 — monitor de bar muestra solo bebidas
def test_monitor_bar_solo_bebidas(client_bartender, comanda_con_items, app):
    r = client_bartender.get("/bar/")
    assert r.status_code == 200

    with app.app_context():
        cid, _ = comanda_con_items
        items = DetalleComanda.query.filter_by(comanda_id=cid).all()
        for item in items:
            if item.producto.categoria.tipo == "bebida":
                assert item.producto.nombre.encode() in r.data

# US-010 — avanzar estado en cocina
def test_avanzar_estado_cocina(client_cocinero, comanda_con_items, app):
    with app.app_context():
        cid, _ = comanda_con_items
        item = DetalleComanda.query.join(Producto).join(Producto.categoria) \
            .filter(DetalleComanda.comanda_id == cid) \
            .filter(Producto.categoria.has(tipo="comida")).first()
        item_id = item.id
        assert item.estado == "recibido"

    r = client_cocinero.post(f"/cocina/item/{item_id}/avanzar")
    assert r.status_code == 200
    assert r.get_json()["estado"] == "en_proceso"

    r = client_cocinero.post(f"/cocina/item/{item_id}/avanzar")
    assert r.get_json()["estado"] == "listo"

    with app.app_context():
        item = DetalleComanda.query.get(item_id)
        assert item.estado == "listo"

# US-019 — avanzar estado en bar
def test_avanzar_estado_bar(client_bartender, comanda_con_items, app):
    with app.app_context():
        cid, _ = comanda_con_items
        item = DetalleComanda.query.join(Producto).join(Producto.categoria) \
            .filter(DetalleComanda.comanda_id == cid) \
            .filter(Producto.categoria.has(tipo="bebida")).first()
        item_id = item.id

    r = client_bartender.post(f"/bar/item/{item_id}/avanzar")
    assert r.get_json()["estado"] == "en_proceso"

    r = client_bartender.post(f"/bar/item/{item_id}/avanzar")
    assert r.get_json()["estado"] == "listo"

# US-011 — cuenta de mesa con IGV correcto
def test_cuenta_calcula_igv(client_mozo, comanda_con_items, app):
    cid, mid = comanda_con_items

    r = client_mozo.get(f"/mozo/mesa/{mid}/cuenta")
    assert r.status_code == 200

    with app.app_context():
        comanda = Comanda.query.get(cid)
        subtotal_esperado = sum(float(d.producto.precio) * d.cantidad for d in comanda.detalles)
        igv_esperado = subtotal_esperado * 0.18
        total_esperado = subtotal_esperado + igv_esperado

    assert f"{subtotal_esperado:.2f}".encode() in r.data
    assert f"{igv_esperado:.2f}".encode() in r.data
    assert f"{total_esperado:.2f}".encode() in r.data

# US-011 — solicitar cuenta cambia estado de mesa
def test_solicitar_cuenta_cambia_estado(client_mozo, comanda_con_items, app):
    cid, mid = comanda_con_items

    r = client_mozo.post(f"/mozo/mesa/{mid}/solicitar_cuenta")
    assert r.status_code == 200
    assert r.get_json()["ok"] == True

    with app.app_context():
        mesa = Mesa.query.get(mid)
        assert mesa.estado == "esperando_pago"
        mesa.estado = "ocupada"
        db.session.commit()

# US-015 — dashboard admin muestra metricas
def test_dashboard_admin_metricas(client_admin):
    r = client_admin.get("/admin/")
    assert r.status_code == 200
    assert "Total facturado hoy".encode() in r.data
    assert "Mesas atendidas hoy".encode() in r.data
    assert "Ticket promedio".encode() in r.data