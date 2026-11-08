from flask import Blueprint, render_template
from app.permisos import rol_requerido
from app.services import estaciones

bar_bp = Blueprint("bar", __name__, url_prefix="/bar")


# US-018 — Monitor de bar (solo bebidas)
@bar_bp.route("/")
@rol_requerido("bartender")
def dashboard():
    return render_template("bar/monitor.html", items=estaciones.items_en_cola("bebida"))


# US-019 — Avanzar estado: recibido -> en_proceso -> listo
@bar_bp.route("/item/<int:item_id>/avanzar", methods=["POST"])
@rol_requerido("bartender")
def avanzar_item(item_id):
    return estaciones.avanzar_item(item_id, "bebida", "bebidas_listas_bar")
