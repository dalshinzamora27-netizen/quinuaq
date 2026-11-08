from flask_login import current_user
from app import socketio


@socketio.on("connect")
def conectar(auth=None):
    # Solo usuarios con sesion iniciada reciben los eventos en tiempo real
    if not current_user.is_authenticated:
        return False
