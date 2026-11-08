import pytest
from app import db
from app.models.usuario import Usuario, Rol

@pytest.fixture
def usuario_admin(app):
    with app.app_context():
        return Usuario.query.filter_by(dni="00000000").first()

# US-001 — login correcto redirige segun rol
def test_login_admin_exitoso(client):
    r = client.post("/login", data={"dni":"00000000","password":"admin123"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "Dashboard".encode() in r.data

def test_login_mozo_exitoso(client):
    r = client.post("/login", data={"dni":"11111111","password":"admin123"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "Mozo".encode() in r.data

def test_login_cocinero_exitoso(client):
    r = client.post("/login", data={"dni":"22222222","password":"admin123"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "Cocinero".encode() in r.data

def test_login_bartender_exitoso(client):
    r = client.post("/login", data={"dni":"33333333","password":"admin123"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "Bartender".encode() in r.data

def test_login_cajero_exitoso(client):
    r = client.post("/login", data={"dni":"44444444","password":"admin123"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "Cajero".encode() in r.data

# US-001 — credenciales incorrectas no revelan cual campo fallo
def test_login_password_incorrecta(client):
    r = client.post("/login", data={"dni":"00000000","password":"mal"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "Usuario o contraseña incorrectos".encode() in r.data

def test_login_dni_inexistente(client):
    r = client.post("/login", data={"dni":"99999999","password":"admin123"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "Usuario o contraseña incorrectos".encode() in r.data

# US-001 — usuario inactivo no puede entrar
def test_login_usuario_inactivo(client, app):
    with app.app_context():
        u = Usuario.query.filter_by(dni="44444444").first()
        u.activo = False
        db.session.commit()

    r = client.post("/login", data={"dni":"44444444","password":"admin123"},
                    follow_redirects=True)
    assert "Usuario o contraseña incorrectos".encode() in r.data

    with app.app_context():
        u = Usuario.query.filter_by(dni="44444444").first()
        u.activo = True
        db.session.commit()

# US-002 — modelo usuario tiene los campos correctos
def test_modelo_usuario_campos(usuario_admin, app):
    with app.app_context():
        u = Usuario.query.filter_by(dni="00000000").first()
        assert u.nombre   == "Admin"
        assert u.apellido == "Principal"
        assert u.activo   == True
        assert u.rol.nombre == "admin"

# US-002 — check_password funciona correctamente
def test_check_password_correcto(app):
    with app.app_context():
        u = Usuario.query.filter_by(dni="00000000").first()
        assert u.check_password("admin123") == True
        assert u.check_password("wrongpass") == False