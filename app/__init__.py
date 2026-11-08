from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from app.config import Config

db            = SQLAlchemy()
login_manager = LoginManager()
socketio      = SocketIO()
csrf          = CSRFProtect()


def create_app(config_class=Config, **overrides):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config.update(overrides)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view    = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."
    socketio.init_app(app, cors_allowed_origins=app.config["SOCKETIO_CORS_ORIGINS"])

    from app import models  # noqa: F401  registra todos los modelos
    from app.models.usuario import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    from app.routes.auth   import auth_bp
    from app.routes.admin  import admin_bp
    from app.routes.mozo   import mozo_bp
    from app.routes.cocina import cocina_bp
    from app.routes.bar    import bar_bp
    from app.routes.cajero import cajero_bp

    for bp in (auth_bp, admin_bp, mozo_bp, cocina_bp, bar_bp, cajero_bp):
        app.register_blueprint(bp)

    from app import sockets  # noqa: F401  handlers de Socket.IO
    from app.cli import registrar_comandos
    registrar_comandos(app)

    return app
