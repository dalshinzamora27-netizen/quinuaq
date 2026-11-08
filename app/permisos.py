from functools import wraps
from flask import abort, request, jsonify
from flask_login import current_user, login_required


def rol_requerido(*roles):
    """Restringe una ruta a los roles indicados. El admin siempre tiene acceso.

    Uso:
        @bp.route("/")
        @rol_requerido("mozo")
        def vista(): ...
    """
    permitidos = set(roles) | {"admin"}

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(*args, **kwargs):
            if current_user.rol.nombre not in permitidos:
                if request.is_json or request.method != "GET":
                    return jsonify({"ok": False, "error": "No tienes permiso para esta acción."}), 403
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador
