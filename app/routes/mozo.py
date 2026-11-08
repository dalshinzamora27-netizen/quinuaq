from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db, socketio
from app.permisos import rol_requerido
from app.models.mesa import Mesa
from app.models.comanda import Comanda, DetalleComanda
from app.models.producto import Categoria, Producto
from app.services.facturacion import calcular_totales
from app.services.tiempo import ahora_utc

mozo_bp = Blueprint("mozo", __name__, url_prefix="/mozo")

ESTADOS_MESA = {"libre", "ocupada", "esperando_pago", "mantenimiento"}


def _error(mensaje, codigo=400):
    return jsonify({"ok": False, "error": mensaje}), codigo


def _emitir_mesa(mesa):
    socketio.emit("mesa_actualizada", {"id": mesa.id, "estado": mesa.estado})


def _comanda_abierta(mesa_id):
    return Comanda.query.filter_by(mesa_id=mesa_id, estado="abierta").first()


@mozo_bp.route("/")
@rol_requerido("mozo")
def dashboard():
    mesas = Mesa.query.order_by(Mesa.numero).all()
    return render_template("mozo/mesas.html", mesas=mesas)


# US-005 — Cambio manual de estado de mesa
@mozo_bp.route("/mesa/<int:mesa_id>/estado", methods=["POST"])
@rol_requerido("mozo")
def cambiar_estado(mesa_id):
    mesa  = Mesa.query.get_or_404(mesa_id)
    nuevo = (request.get_json(silent=True) or {}).get("estado")

    if nuevo not in ESTADOS_MESA:
        return _error("Estado de mesa no válido.")
    if nuevo == "libre" and _comanda_abierta(mesa.id):
        return _error("La mesa tiene una comanda abierta; debe pasar por caja antes de liberarse.")

    mesa.estado = nuevo
    db.session.commit()
    _emitir_mesa(mesa)
    return jsonify({"ok": True})


# US-006 — Abrir comanda en mesa
@mozo_bp.route("/mesa/<int:mesa_id>/abrir", methods=["POST"])
@rol_requerido("mozo")
def abrir_comanda(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)

    if mesa.estado != "libre":
        return _error("La mesa no está libre.")

    try:
        comensales = int((request.get_json(silent=True) or {}).get("comensales", 1))
    except (TypeError, ValueError):
        return _error("Número de comensales inválido.")
    if comensales < 1:
        return _error("Debe haber al menos un comensal.")

    comanda = Comanda(mesa_id=mesa.id, mozo_id=current_user.id,
                      comensales=comensales, estado="abierta")
    db.session.add(comanda)
    mesa.estado  = "ocupada"
    mesa.mozo_id = current_user.id
    db.session.commit()

    _emitir_mesa(mesa)
    return jsonify({"ok": True, "comanda_id": comanda.id})


# US-007/008 — Pantalla de comanda activa de una mesa
@mozo_bp.route("/mesa/<int:mesa_id>/comanda")
@rol_requerido("mozo")
def ver_comanda(mesa_id):
    mesa    = Mesa.query.get_or_404(mesa_id)
    comanda = _comanda_abierta(mesa.id)

    if not comanda:
        return _error("No hay comanda abierta para esta mesa.", 404)

    categorias = Categoria.query.filter_by(activo=True).all()
    productos  = Producto.query.filter_by(disponible=True).all()

    return render_template("mozo/comanda.html",
        mesa=mesa, comanda=comanda, categorias=categorias, productos=productos)


# US-007 — Agregar plato a la comanda
@mozo_bp.route("/comanda/<int:comanda_id>/agregar", methods=["POST"])
@rol_requerido("mozo")
def agregar_item(comanda_id):
    comanda = Comanda.query.get_or_404(comanda_id)
    if comanda.estado != "abierta":
        return _error("La comanda ya está cerrada.")

    data = request.get_json(silent=True) or {}
    try:
        producto_id = int(data["producto_id"])
        cantidad    = int(data.get("cantidad", 1))
    except (KeyError, TypeError, ValueError):
        return _error("Producto o cantidad inválidos.")
    if cantidad < 1:
        return _error("La cantidad debe ser al menos 1.")

    producto = db.session.get(Producto, producto_id)
    if not producto or not producto.disponible:
        return _error("El producto no está disponible.")

    item = DetalleComanda(comanda_id=comanda.id, producto_id=producto.id,
                          cantidad=cantidad, nota=(data.get("nota") or "").strip()[:255],
                          estado="pendiente")
    db.session.add(item)
    db.session.commit()
    return jsonify({"ok": True, "item_id": item.id})


# US-007 — Quitar plato (solo mientras no se haya enviado a cocina/bar)
@mozo_bp.route("/item/<int:item_id>/eliminar", methods=["POST"])
@rol_requerido("mozo")
def eliminar_item(item_id):
    item = DetalleComanda.query.get_or_404(item_id)
    if item.estado != "pendiente":
        return _error("El plato ya fue enviado a cocina/bar y no se puede quitar.")
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


# US-008 — Despachar items pendientes a cocina/bar
@mozo_bp.route("/comanda/<int:comanda_id>/despachar", methods=["POST"])
@rol_requerido("mozo")
def despachar(comanda_id):
    comanda = Comanda.query.get_or_404(comanda_id)
    items   = DetalleComanda.query.filter_by(comanda_id=comanda.id, estado="pendiente").all()

    cocina_items, bar_items = [], []
    ahora = ahora_utc()

    for item in items:
        item.estado     = "recibido"
        item.enviado_en = ahora
        payload = {
            "item_id"  : item.id,
            "producto" : item.producto.nombre,
            "cantidad" : item.cantidad,
            "nota"     : item.nota,
            "mesa"     : comanda.mesa.numero,
            "mozo"     : comanda.mozo.nombre,
        }
        if item.producto.categoria.tipo == "bebida":
            bar_items.append(payload)
        else:
            cocina_items.append(payload)

    # primero se guarda; solo despues se avisa a cocina/bar
    db.session.commit()

    if cocina_items:
        socketio.emit("nuevo_pedido_cocina", {"items": cocina_items})
    if bar_items:
        socketio.emit("nuevo_pedido_bar", {"items": bar_items})

    return jsonify({"ok": True, "cocina": len(cocina_items), "bar": len(bar_items)})


# US-011 — Previsualizacion de cuenta de mesa
@mozo_bp.route("/mesa/<int:mesa_id>/cuenta")
@rol_requerido("mozo")
def ver_cuenta(mesa_id):
    mesa    = Mesa.query.get_or_404(mesa_id)
    comanda = _comanda_abierta(mesa.id)

    if not comanda:
        return _error("No hay comanda abierta.", 404)

    items, subtotal, igv, total = calcular_totales(comanda.detalles)
    return render_template("mozo/cuenta.html",
        mesa=mesa, comanda=comanda, items=items,
        subtotal=subtotal, igv=igv, total=total)


# US-011 — Solicitar cuenta (cambia estado a esperando_pago)
@mozo_bp.route("/mesa/<int:mesa_id>/solicitar_cuenta", methods=["POST"])
@rol_requerido("mozo")
def solicitar_cuenta(mesa_id):
    mesa = Mesa.query.get_or_404(mesa_id)
    if not _comanda_abierta(mesa.id):
        return _error("La mesa no tiene una comanda abierta.")

    mesa.estado = "esperando_pago"
    db.session.commit()
    _emitir_mesa(mesa)
    return jsonify({"ok": True})
