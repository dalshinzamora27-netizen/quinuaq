from flask import Blueprint, render_template
from app.permisos import rol_requerido
from app.services import estaciones

cocina_bp = Blueprint("cocina", __name__, url_prefix="/cocina")


# US-009 — Monitor de cocina (solo comida)
@cocina_bp.route("/")
@rol_requerido("cocinero")
def dashboard():
    return render_template("cocina/monitor.html", items=estaciones.items_en_cola("comida"))


# US-010 — Avanzar estado: recibido -> en_proceso -> listo
@cocina_bp.route("/item/<int:item_id>/avanzar", methods=["POST"])
@rol_requerido("cocinero")
def avanzar_item(item_id):
    return estaciones.avanzar_item(item_id, "comida", "mesa_lista_cocina")
