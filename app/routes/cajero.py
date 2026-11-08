from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app import db, socketio
from app.permisos import rol_requerido
from app.models.mesa import Mesa
from app.models.comanda import Comanda
from app.models.venta import Venta, Pago
from app.services.facturacion import (calcular_totales, a_decimal,
                                      TIPOS_COMPROBANTE, METODOS_PAGO)
from app.services.tiempo import ahora_utc, rango_dia_utc

cajero_bp = Blueprint("cajero", __name__, url_prefix="/cajero")


def _error(mensaje, codigo=400):
    return jsonify({"ok": False, "error": mensaje}), codigo


def _comanda_abierta(mesa_id):
    return Comanda.query.filter_by(mesa_id=mesa_id, estado="abierta").first()


@cajero_bp.route("/")
@rol_requerido("cajero")
def dashboard():
    mesas = Mesa.query.filter_by(estado="esperando_pago").order_by(Mesa.numero).all()
    return render_template("cajero/cuentas.html", mesas=mesas)


@cajero_bp.route("/mesa/<int:mesa_id>/emitir")
@rol_requerido("cajero")
def emitir(mesa_id):
    mesa    = Mesa.query.get_or_404(mesa_id)
    comanda = _comanda_abierta(mesa.id)
    if not comanda:
        return _error("No hay comanda abierta para esta mesa.", 404)

    items, subtotal, igv, total = calcular_totales(comanda.detalles)
    return render_template("cajero/emitir.html",
        mesa=mesa, comanda=comanda, items=items,
        subtotal=subtotal, igv=igv, total=total)


def generar_numero(tipo):
    """Siguiente numero correlativo por tipo de comprobante (ej. B001-000042).

    Se basa en el ultimo numero emitido y no en un conteo, para que borrar
    una venta anterior no provoque un numero repetido.
    """
    prefijo = TIPOS_COMPROBANTE[tipo]
    ultima  = (Venta.query.filter_by(tipo=tipo)
               .order_by(Venta.id.desc()).first())
    correlativo = int(ultima.numero.split("-")[-1]) + 1 if ultima else 1
    return f"{prefijo}-{correlativo:06d}"


# US-012 / US-013 / US-014 — Emitir comprobante y registrar pagos
@cajero_bp.route("/mesa/<int:mesa_id>/confirmar", methods=["POST"])
@rol_requerido("cajero")
def confirmar_venta(mesa_id):
    mesa    = Mesa.query.get_or_404(mesa_id)
    comanda = _comanda_abierta(mesa.id)
    if not comanda:
        return _error("No hay comanda abierta.", 404)
    if not comanda.detalles:
        return _error("La comanda no tiene productos.")

    data = request.get_json(silent=True) or {}
    tipo = data.get("tipo")
    if tipo not in TIPOS_COMPROBANTE:
        return _error("Tipo de comprobante no válido.")

    dni_cliente  = (data.get("dni_cliente")  or "").strip()
    ruc_cliente  = (data.get("ruc_cliente")  or "").strip()
    razon_social = (data.get("razon_social") or "").strip()

    if dni_cliente and (not dni_cliente.isdigit() or len(dni_cliente) != 8):
        return _error("El DNI debe tener exactamente 8 dígitos numéricos.")

    if tipo == "factura":
        if not ruc_cliente.isdigit() or len(ruc_cliente) != 11:
            return _error("El RUC debe tener exactamente 11 dígitos numéricos.")
        if not razon_social:
            return _error("La razón social es obligatoria para factura.")

    _, subtotal, igv, total = calcular_totales(comanda.detalles)

    # US-014 — metodos de pago mixtos
    pagos_data = data.get("pagos") or []
    if not pagos_data:
        return _error("Debe registrar al menos un método de pago.")

    pagos = []
    try:
        for p in pagos_data:
            metodo, monto = p.get("metodo"), a_decimal(p.get("monto"))
            if metodo not in METODOS_PAGO:
                return _error(f"Método de pago no válido: {metodo}.")
            if monto <= 0:
                return _error("Los montos de pago deben ser mayores a cero.")
            pagos.append((metodo, monto))
    except (ValueError, AttributeError):
        return _error("Formato de pagos inválido.")

    suma_pagos = sum(m for _, m in pagos)
    if suma_pagos != total:
        return _error(f"La suma de pagos (S/ {suma_pagos:.2f}) no coincide con el total (S/ {total:.2f}).")

    venta = Venta(
        comanda_id   = comanda.id,
        cajero_id    = current_user.id,
        tipo         = tipo,
        numero       = generar_numero(tipo),
        dni_cliente  = dni_cliente or None,
        ruc_cliente  = ruc_cliente if tipo == "factura" else None,
        razon_social = razon_social if tipo == "factura" else None,
        subtotal     = subtotal,
        igv          = igv,
        total        = total,
        estado       = "pagada",
    )
    venta.pagos = [Pago(metodo=m, monto=monto) for m, monto in pagos]
    db.session.add(venta)

    comanda.estado     = "pagada"
    comanda.cerrada_en = ahora_utc()
    mesa.estado        = "libre"
    mesa.mozo_id       = None
    db.session.commit()

    socketio.emit("mesa_actualizada", {"id": mesa.id, "estado": mesa.estado})
    return jsonify({"ok": True, "venta_id": venta.id, "numero": venta.numero})


def _ventas_del_dia():
    inicio, fin = rango_dia_utc()
    return (Venta.query
        .filter_by(cajero_id=current_user.id, estado="pagada")
        .filter(Venta.emitida_en >= inicio, Venta.emitida_en < fin)
        .all())


def _desglose(ventas):
    desglose = {m: Decimal("0.00") for m in ("efectivo", "tarjeta", "yape_plin")}
    for v in ventas:
        for p in v.pagos:
            desglose[p.metodo] = desglose.get(p.metodo, Decimal("0.00")) + Decimal(p.monto)
    return desglose


# US-014 — Cierre de turno (ventas del dia del cajero)
@cajero_bp.route("/cierre")
@rol_requerido("cajero")
def cierre():
    ventas   = _ventas_del_dia()
    desglose = _desglose(ventas)
    return render_template("cajero/cierre.html",
        ventas=ventas, desglose=desglose, total_esperado=sum(desglose.values()))


@cajero_bp.route("/cierre/confirmar", methods=["POST"])
@rol_requerido("cajero")
def confirmar_cierre():
    try:
        efectivo_real = a_decimal((request.get_json(silent=True) or {}).get("efectivo_real", 0))
    except ValueError:
        return _error("Monto de efectivo inválido.")

    efectivo_esperado = _desglose(_ventas_del_dia())["efectivo"]
    diferencia = efectivo_real - efectivo_esperado

    return jsonify({
        "ok"               : True,
        "efectivo_esperado": float(efectivo_esperado),
        "efectivo_real"    : float(efectivo_real),
        "diferencia"       : float(diferencia),
        "tipo"             : "sobrante" if diferencia > 0 else ("faltante" if diferencia < 0 else "exacto"),
    })
