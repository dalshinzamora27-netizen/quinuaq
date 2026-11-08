"""Logica comun de las estaciones de preparacion (cocina = comida, bar = bebida)."""
from flask import jsonify
from app import db, socketio
from app.models.comanda import DetalleComanda
from app.models.producto import Producto, Categoria

SIGUIENTE_ESTADO = {"recibido": "en_proceso", "en_proceso": "listo"}


def items_en_cola(tipo):
    """Items ya despachados y aun no listos, del mas antiguo al mas nuevo."""
    return (DetalleComanda.query
        .join(Producto).join(Categoria)
        .filter(Categoria.tipo == tipo)
        .filter(DetalleComanda.estado.in_(SIGUIENTE_ESTADO.keys()))
        .order_by(DetalleComanda.enviado_en.asc())
        .all())


def avanzar_item(item_id, tipo, evento_completo):
    item = DetalleComanda.query.get_or_404(item_id)

    if item.producto.categoria.tipo != tipo:
        return jsonify({"ok": False, "error": "Este producto no corresponde a esta estación."}), 400
    if item.estado not in SIGUIENTE_ESTADO:
        return jsonify({"ok": False, "error": f"El item está en estado '{item.estado}' y no se puede avanzar."}), 400

    item.estado = SIGUIENTE_ESTADO[item.estado]
    db.session.commit()

    socketio.emit("item_actualizado", {"item_id": item.id, "estado": item.estado, "tipo": tipo})

    comanda    = item.comanda
    pendientes = [d for d in comanda.detalles
                  if d.producto.categoria.tipo == tipo and d.estado != "listo"]
    if not pendientes:
        socketio.emit(evento_completo, {"mesa": comanda.mesa.numero, "mozo_id": comanda.mozo_id})

    return jsonify({"ok": True, "estado": item.estado})
