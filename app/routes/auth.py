from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.usuario import Usuario

auth_bp = Blueprint("auth", __name__)

INICIO_POR_ROL = {
    "admin"     : "admin.dashboard",
    "mozo"      : "mozo.dashboard",
    "cocinero"  : "cocina.dashboard",
    "bartender" : "bar.dashboard",
    "cajero"    : "cajero.dashboard",
}


def _inicio(usuario):
    destino = INICIO_POR_ROL.get(usuario.rol.nombre)
    return redirect(url_for(destino)) if destino else None


# US-001 — Inicio de sesion con DNI
@auth_bp.route("/")
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _inicio(current_user) or render_template("login.html")

    if request.method == "POST":
        dni      = request.form.get("dni", "").strip()
        password = request.form.get("password", "")
        usuario  = Usuario.query.filter_by(dni=dni, activo=True).first()

        if usuario and usuario.check_password(password):
            respuesta = _inicio(usuario)
            if respuesta:
                login_user(usuario)
                return respuesta

        # mismo mensaje para DNI o contrasena incorrectos: no revela cual fallo
        flash("Usuario o contraseña incorrectos.")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
