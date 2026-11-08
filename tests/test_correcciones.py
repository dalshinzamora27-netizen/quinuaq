"""Tests de regresion: permisos por rol, CSRF y errores de logica corregidos."""
from datetime import timedelta
import pytest
from app import create_app, db
from app.config import TestConfig
from app.models import Mesa, Producto, Comanda, DetalleComanda, Venta, Usuario
from app.services.tiempo import ahora_utc


def _producto(tipo):
    return Producto.query.join(Producto.categoria).filter_by(tipo=tipo).first().id


@pytest.fixture
def comanda(app, client_mozo):
    """Comanda abierta en la mesa 1 con un plato de comida y una bebida, sin despachar."""
    with app.app_context():
        mid = Mesa.query.filter_by(numero=1).first().id
        comida, bebida = _producto("comida"), _producto("bebida")
    cid = client_mozo.post(f"/mozo/mesa/{mid}/abrir", json={"comensales": 2}).get_json()["comanda_id"]
    for pid in (comida, bebida):
        client_mozo.post(f"/mozo/comanda/{cid}/agregar", json={"producto_id": pid, "cantidad": 1})
    return cid, mid


# ---------- Permisos por rol ----------

@pytest.mark.parametrize("url", [
    "/admin/", "/admin/usuarios", "/admin/carta", "/admin/reportes",
    "/cocina/", "/bar/", "/cajero/", "/cajero/cierre",
])
def test_mozo_no_accede_a_otras_areas(client_mozo, url):
    assert client_mozo.get(url).status_code == 403


def test_mozo_no_puede_crear_usuarios(client_mozo, app):
    r = client_mozo.post("/admin/usuarios/crear", json={
        "nombre": "Intruso", "apellido": "X", "dni": "12121212", "password": "123456", "rol_id": 1})
    assert r.status_code == 403
    with app.app_context():
        assert Usuario.query.filter_by(dni="12121212").first() is None


def test_cocinero_no_puede_cobrar(client_cocinero):
    assert client_cocinero.post("/cajero/mesa/1/confirmar", json={}).status_code == 403


def test_admin_accede_a_todo(client_admin):
    for url in ("/mozo/", "/cocina/", "/bar/", "/cajero/"):
        assert client_admin.get(url).status_code == 200


def test_sin_sesion_redirige_al_login(client):
    r = client.get("/admin/")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


# ---------- CSRF ----------

def test_post_sin_token_csrf_es_rechazado(tmp_path):
    app = create_app(TestConfig, WTF_CSRF_ENABLED=True,
                     SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'csrf.db'}")
    with app.app_context():
        db.create_all()
    r = app.test_client().post("/login", data={"dni": "00000000", "password": "admin123"})
    assert r.status_code == 400


# ---------- Pantallas ----------

def test_pantalla_de_mesas_carga(client_mozo):
    r = client_mozo.get("/mozo/")
    assert r.status_code == 200
    assert b"Mesa 1" in r.data


# ---------- Flujo de comanda ----------

def test_platos_no_despachados_no_aparecen_en_cocina(client_cocinero, comanda, app):
    with app.app_context():
        item = DetalleComanda.query.filter_by(comanda_id=comanda[0]).first()
        assert item.estado == "pendiente"
        nombre = item.producto.nombre
    assert nombre.encode() not in client_cocinero.get("/cocina/").data


def test_despachar_dos_veces_no_reenvia(client_mozo, comanda):
    cid, _ = comanda
    r1 = client_mozo.post(f"/mozo/comanda/{cid}/despachar").get_json()
    r2 = client_mozo.post(f"/mozo/comanda/{cid}/despachar").get_json()
    assert (r1["cocina"], r1["bar"]) == (1, 1)
    assert (r2["cocina"], r2["bar"]) == (0, 0)


def test_no_se_elimina_plato_ya_enviado(client_mozo, comanda, app):
    cid, _ = comanda
    client_mozo.post(f"/mozo/comanda/{cid}/despachar")
    with app.app_context():
        item_id = DetalleComanda.query.filter_by(comanda_id=cid).first().id
    r = client_mozo.post(f"/mozo/item/{item_id}/eliminar")
    assert r.status_code == 400
    with app.app_context():
        assert db.session.get(DetalleComanda, item_id) is not None


def test_cocina_no_avanza_bebidas(client_cocinero, client_mozo, comanda, app):
    cid, _ = comanda
    client_mozo.post(f"/mozo/comanda/{cid}/despachar")
    with app.app_context():
        bebida = (DetalleComanda.query.join(Producto).join(Producto.categoria)
                  .filter(DetalleComanda.comanda_id == cid)
                  .filter(Producto.categoria.has(tipo="bebida")).first())
        item_id = bebida.id
    assert client_cocinero.post(f"/cocina/item/{item_id}/avanzar").status_code == 400


def test_no_se_agrega_producto_no_disponible(client_mozo, comanda, app):
    cid, _ = comanda
    with app.app_context():
        p = Producto.query.first()
        p.disponible = False
        db.session.commit()
        pid = p.id
    r = client_mozo.post(f"/mozo/comanda/{cid}/agregar", json={"producto_id": pid, "cantidad": 1})
    assert r.status_code == 400


def test_estado_de_mesa_invalido(client_mozo):
    r = client_mozo.post("/mozo/mesa/1/estado", json={"estado": "inventado"})
    assert r.status_code == 400


def test_no_se_libera_mesa_con_comanda_abierta(client_mozo, comanda):
    _, mid = comanda
    r = client_mozo.post(f"/mozo/mesa/{mid}/estado", json={"estado": "libre"})
    assert r.status_code == 400


# ---------- Caja y reportes ----------

def _cobrar(client_mozo, client_cajero, cid, mid, app):
    client_mozo.post(f"/mozo/mesa/{mid}/solicitar_cuenta")
    with app.app_context():
        comanda = db.session.get(Comanda, cid)
        subtotal = sum(float(d.producto.precio) * d.cantidad for d in comanda.detalles)
    total = round(subtotal * 1.18, 2)
    r = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo": "nota_venta", "pagos": [{"metodo": "efectivo", "monto": total}]})
    assert r.status_code == 200, r.get_json()
    return r.get_json(), total


def test_metodo_de_pago_invalido(client_mozo, client_cajero, comanda):
    _, mid = comanda
    client_mozo.post(f"/mozo/mesa/{mid}/solicitar_cuenta")
    r = client_cajero.post(f"/cajero/mesa/{mid}/confirmar",
        json={"tipo": "boleta", "pagos": [{"metodo": "bitcoin", "monto": 1}]})
    assert r.status_code == 400


def test_dashboard_solo_cuenta_ventas_de_hoy(client_admin, client_mozo, client_cajero, comanda, app):
    cid, mid = comanda
    _, total = _cobrar(client_mozo, client_cajero, cid, mid, app)

    # una venta de hace 3 dias no debe sumarse a "hoy"
    with app.app_context():
        vieja = Venta.query.first()
        db.session.add(Venta(comanda_id=vieja.comanda_id, cajero_id=vieja.cajero_id, tipo="nota_venta",
                             numero="NV-999999", subtotal=100, igv=18, total=118,
                             emitida_en=ahora_utc() - timedelta(days=3)))
        db.session.commit()

    html = client_admin.get("/admin/").data.decode()
    assert f"S/ {total:.2f}" in html
    assert "S/ 118.00" not in html


def test_correlativo_no_se_repite_tras_borrar(client_mozo, client_cajero, app):
    """Con 2 ventas, si se borra la primera, la siguiente debe ser NV-000003 (no repetir NV-000002)."""
    numeros = []
    for numero_mesa in (1, 2, 3):
        with app.app_context():
            mid = Mesa.query.filter_by(numero=numero_mesa).first().id
            pid = _producto("comida")
        cid = client_mozo.post(f"/mozo/mesa/{mid}/abrir", json={"comensales": 1}).get_json()["comanda_id"]
        client_mozo.post(f"/mozo/comanda/{cid}/agregar", json={"producto_id": pid, "cantidad": 1})
        datos, _ = _cobrar(client_mozo, client_cajero, cid, mid, app)
        numeros.append(datos["numero"])
        if numero_mesa == 2:
            with app.app_context():
                Venta.query.filter_by(numero="NV-000001").delete()
                db.session.commit()
    assert numeros == ["NV-000001", "NV-000002", "NV-000003"]
