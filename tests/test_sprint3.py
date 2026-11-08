import pytest
from app import db
from app.models.mesa import Mesa
from app.models.comanda import Comanda, DetalleComanda
from app.models.producto import Producto

@pytest.fixture
def mesa_libre(app):
    with app.app_context():
        m = Mesa.query.filter_by(estado="libre").first()
        if not m:
            m = Mesa(numero=99, capacidad=4, estado="libre")
            db.session.add(m)
            db.session.commit()
        return m.id

# US-006 — abrir comanda
def test_abrir_comanda_mesa_libre(client_mozo, mesa_libre, app):
    r = client_mozo.post(f"/mozo/mesa/{mesa_libre}/abrir",
        json={"comensales": 3}, content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] == True
    assert "comanda_id" in data

    with app.app_context():
        mesa = Mesa.query.get(mesa_libre)
        assert mesa.estado == "ocupada"
        comanda = Comanda.query.get(data["comanda_id"])
        assert comanda.comensales == 3
        assert comanda.estado == "abierta"

        # limpiar
        db.session.delete(comanda)
        mesa.estado = "libre"
        mesa.mozo_id = None
        db.session.commit()

def test_no_abrir_comanda_mesa_ocupada(client_mozo, app):
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="ocupada").first()
        if not mesa:
            mesa = Mesa.query.first()
            mesa.estado = "ocupada"
            db.session.commit()
        mid = mesa.id

    r = client_mozo.post(f"/mozo/mesa/{mid}/abrir",
        json={"comensales": 2}, content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["ok"] == False

# US-007 — agregar items
@pytest.fixture
def comanda_abierta(app, client_mozo, mesa_libre):
    r = client_mozo.post(f"/mozo/mesa/{mesa_libre}/abrir",
        json={"comensales": 2}, content_type="application/json")
    cid = r.get_json()["comanda_id"]
    yield cid
    with app.app_context():
        comanda = Comanda.query.get(cid)
        if comanda:
            mesa = Mesa.query.get(comanda.mesa_id)
            mesa.estado = "libre"
            mesa.mozo_id = None
            db.session.delete(comanda)
            db.session.commit()

def test_agregar_item_comida(client_mozo, comanda_abierta, app):
    with app.app_context():
        producto = Producto.query.join(Producto.categoria).filter_by(tipo="comida").first()
        pid = producto.id

    r = client_mozo.post(f"/mozo/comanda/{comanda_abierta}/agregar",
        json={"producto_id": pid, "cantidad": 2, "nota": "Sin cebolla"},
        content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["ok"] == True

    with app.app_context():
        item = DetalleComanda.query.filter_by(comanda_id=comanda_abierta).first()
        assert item.cantidad == 2
        assert item.nota == "Sin cebolla"
        assert item.estado == "pendiente"  # aun no se envia a cocina

def test_agregar_item_bebida(client_mozo, comanda_abierta, app):
    with app.app_context():
        producto = Producto.query.join(Producto.categoria).filter_by(tipo="bebida").first()
        pid = producto.id

    r = client_mozo.post(f"/mozo/comanda/{comanda_abierta}/agregar",
        json={"producto_id": pid, "cantidad": 1, "nota": ""},
        content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["ok"] == True

def test_eliminar_item(client_mozo, comanda_abierta, app):
    with app.app_context():
        producto = Producto.query.first()
        item = DetalleComanda(comanda_id=comanda_abierta, producto_id=producto.id, cantidad=1)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    r = client_mozo.post(f"/mozo/item/{item_id}/eliminar")
    assert r.status_code == 200
    assert r.get_json()["ok"] == True

    with app.app_context():
        assert DetalleComanda.query.get(item_id) is None

# US-008 — despacho
def test_despachar_separa_cocina_y_bar(client_mozo, comanda_abierta, app):
    with app.app_context():
        comida  = Producto.query.join(Producto.categoria).filter_by(tipo="comida").first()
        bebida  = Producto.query.join(Producto.categoria).filter_by(tipo="bebida").first()

    client_mozo.post(f"/mozo/comanda/{comanda_abierta}/agregar",
        json={"producto_id": comida.id, "cantidad": 1, "nota": ""},
        content_type="application/json")
    client_mozo.post(f"/mozo/comanda/{comanda_abierta}/agregar",
        json={"producto_id": bebida.id, "cantidad": 1, "nota": ""},
        content_type="application/json")

    r = client_mozo.post(f"/mozo/comanda/{comanda_abierta}/despachar")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] == True
    assert data["cocina"] == 1
    assert data["bar"]    == 1

def test_modelo_comanda_relaciones(app, comanda_abierta):
    with app.app_context():
        comanda = Comanda.query.get(comanda_abierta)
        assert comanda.mesa is not None
        assert comanda.mozo is not None
        assert comanda.mozo.dni == "11111111"