import pytest
from app import db
from app.models.producto import Categoria, Producto
from app.models.mesa import Mesa

# US-003 — categorias existen en BD
def test_categorias_existen(app):
    with app.app_context():
        cats = Categoria.query.all()
        nombres = [c.nombre for c in cats]
        assert "Entradas"        in nombres
        assert "Platos de fondo" in nombres
        assert "Especiales"      in nombres
        assert "Postres"         in nombres
        assert "Bebidas"         in nombres

def test_categorias_tienen_tipo(app):
    with app.app_context():
        bebidas = Categoria.query.filter_by(nombre="Bebidas").first()
        assert bebidas.tipo == "bebida"
        entradas = Categoria.query.filter_by(nombre="Entradas").first()
        assert entradas.tipo == "comida"

# US-004 — productos
def test_productos_existen(app):
    with app.app_context():
        total = Producto.query.count()
        assert total >= 12

def test_toggle_producto(client_admin, app):
    with app.app_context():
        p = Producto.query.first()
        estado_original = p.disponible
        pid = p.id

    r = client_admin.post(f"/admin/carta/toggle/{pid}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] == True
    assert data["disponible"] != estado_original

    # revertir
    client_admin.post(f"/admin/carta/toggle/{pid}")

def test_agregar_producto(client_admin, app):
    with app.app_context():
        cat = Categoria.query.first()
        cid = cat.id

    r = client_admin.post("/admin/carta/agregar",
        json={"nombre":"Test producto","descripcion":"desc","precio":"9.99","categoria_id": cid},
        content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["ok"] == True

    with app.app_context():
        p = Producto.query.filter_by(nombre="Test producto").first()
        assert p is not None
        assert float(p.precio) == 9.99
        db.session.delete(p)
        db.session.commit()

def test_eliminar_producto(client_admin, app):
    with app.app_context():
        cat = Categoria.query.first()
        p = Producto(nombre="Para eliminar", precio=5.00, categoria_id=cat.id)
        db.session.add(p)
        db.session.commit()
        pid = p.id

    r = client_admin.post(f"/admin/carta/eliminar/{pid}")
    assert r.status_code == 200
    assert r.get_json()["ok"] == True

    with app.app_context():
        assert Producto.query.get(pid) is None

# US-005 — mesas
def test_mesas_existen(app):
    with app.app_context():
        total = Mesa.query.count()
        assert total == 10

def test_mesas_estado_inicial_libre(app):
    with app.app_context():
        libres = Mesa.query.filter_by(estado="libre").count()
        assert libres >= 1

def test_cambiar_estado_mesa(client_admin, app):
    with app.app_context():
        m = Mesa.query.first()
        mid = m.id

    r = client_admin.post(f"/mozo/mesa/{mid}/estado",
        json={"estado":"ocupada"},
        content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["ok"] == True

    with app.app_context():
        m = Mesa.query.get(mid)
        assert m.estado == "ocupada"
        m.estado = "libre"
        db.session.commit()

def test_estados_validos_mesa(app):
    with app.app_context():
        estados = ["libre","ocupada","esperando_pago","mantenimiento"]
        m = Mesa.query.first()
        assert m.estado in estados

# US-002 — crear usuario desde admin
def test_crear_usuario(client_admin, app):
    with app.app_context():
        from app.models.usuario import Rol
        rol = Rol.query.filter_by(nombre="mozo").first()
        rid = rol.id

    r = client_admin.post("/admin/usuarios/crear",
        json={"nombre":"Test","apellido":"User","dni":"99887766",
              "password":"test123","rol_id": rid},
        content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["ok"] == True

    with app.app_context():
        from app.models.usuario import Usuario
        u = Usuario.query.filter_by(dni="99887766").first()
        assert u is not None
        db.session.delete(u)
        db.session.commit()