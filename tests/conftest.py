"""Fixtures compartidas.

Cada test corre sobre una base SQLite nueva con los datos de demostracion,
asi los tests no dependen de (ni modifican) la base de datos real.
"""
import pytest
from app import create_app, db
from app.config import TestConfig
from app.cli import cargar_datos_demo, PASSWORD_DEMO


@pytest.fixture
def app(tmp_path):
    app = create_app(TestConfig, SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'test.db'}")
    with app.app_context():
        db.create_all()
        cargar_datos_demo()

    # No se deja un app_context abierto durante el test: si no, todas las
    # peticiones compartirian `g` y Flask-Login reutilizaria el mismo usuario.
    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def _login(app, dni):
    c = app.test_client()
    c.post("/login", data={"dni": dni, "password": PASSWORD_DEMO})
    return c


@pytest.fixture
def client_admin(app):
    return _login(app, "00000000")


@pytest.fixture
def client_mozo(app):
    return _login(app, "11111111")


@pytest.fixture
def client_cocinero(app):
    return _login(app, "22222222")


@pytest.fixture
def client_bartender(app):
    return _login(app, "33333333")


@pytest.fixture
def client_cajero(app):
    return _login(app, "44444444")
