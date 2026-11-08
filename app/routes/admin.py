from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from sqlalchemy import func
from app import db
from app.permisos import rol_requerido
from app.models.producto import Categoria, Producto
from app.models.mesa import Mesa
from app.models.usuario import Usuario, Rol
from app.models.comanda import Comanda, DetalleComanda
from app.models.venta import Venta
from app.services.facturacion import a_decimal
from app.services.tiempo import ahora_local, local_a_utc, rango_dia_utc

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _error(mensaje, codigo=400):
    return jsonify({"ok": False, "error": mensaje}), codigo


# US-015 — Dashboard con metricas del dia
@admin_bp.route("/")
@rol_requerido("admin")
def dashboard():
    inicio, fin = rango_dia_utc()
    ventas_hoy  = Venta.query.filter(Venta.estado == "pagada",
                                     Venta.emitida_en >= inicio,
                                     Venta.emitida_en < fin).all()

    total_facturado_hoy = sum((Decimal(v.total) for v in ventas_hoy), Decimal("0.00"))
    mesas_atendidas_hoy = len(ventas_hoy)
    ticket_promedio     = (total_facturado_hoy / mesas_atendidas_hoy) if mesas_atendidas_hoy else Decimal("0.00")

    return render_template("admin/dashboard.html",
        total_mesas         = Mesa.query.count(),
        mesas_ocupadas      = Mesa.query.filter(Mesa.estado != "libre").count(),
        total_productos     = Producto.query.count(),
        total_usuarios      = Usuario.query.filter_by(activo=True).count(),
        total_facturado_hoy = total_facturado_hoy,
        mesas_atendidas_hoy = mesas_atendidas_hoy,
        ticket_promedio     = ticket_promedio,
    )


# --- CARTA (US-003 / US-004) ---
@admin_bp.route("/carta")
@rol_requerido("admin")
def carta():
    categorias = Categoria.query.filter_by(activo=True).all()
    productos  = Producto.query.all()
    return render_template("admin/carta.html", categorias=categorias, productos=productos)


@admin_bp.route("/carta/toggle/<int:producto_id>", methods=["POST"])
@rol_requerido("admin")
def toggle_producto(producto_id):
    p = Producto.query.get_or_404(producto_id)
    p.disponible = not p.disponible
    db.session.commit()
    return jsonify({"ok": True, "disponible": p.disponible})


@admin_bp.route("/carta/agregar", methods=["POST"])
@rol_requerido("admin")
def agregar_producto():
    data   = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return _error("El nombre es obligatorio.")
    try:
        precio       = a_decimal(data.get("precio"))
        categoria_id = int(data.get("categoria_id"))
    except (ValueError, TypeError):
        return _error("Precio o categoría inválidos.")
    if precio <= 0:
        return _error("El precio debe ser mayor a cero.")
    if not db.session.get(Categoria, categoria_id):
        return _error("La categoría no existe.")

    p = Producto(nombre=nombre[:100], descripcion=(data.get("descripcion") or "")[:255],
                 precio=precio, categoria_id=categoria_id, disponible=True)
    db.session.add(p)
    db.session.commit()
    return jsonify({"ok": True, "id": p.id})


@admin_bp.route("/carta/eliminar/<int:producto_id>", methods=["POST"])
@rol_requerido("admin")
def eliminar_producto(producto_id):
    p = Producto.query.get_or_404(producto_id)
    # un producto que ya aparece en comandas forma parte del historial de ventas
    if DetalleComanda.query.filter_by(producto_id=p.id).first():
        return _error("Este producto ya tiene pedidos registrados. Márcalo como no disponible en lugar de eliminarlo.")
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok": True})


# --- USUARIOS (US-002) ---
@admin_bp.route("/usuarios")
@rol_requerido("admin")
def usuarios():
    return render_template("admin/usuarios.html",
        usuarios=Usuario.query.all(), roles=Rol.query.all())


@admin_bp.route("/usuarios/crear", methods=["POST"])
@rol_requerido("admin")
def crear_usuario():
    data     = request.get_json(silent=True) or {}
    nombre   = (data.get("nombre") or "").strip()
    apellido = (data.get("apellido") or "").strip()
    dni      = (data.get("dni") or "").strip()
    password = data.get("password") or ""

    if not nombre or not apellido:
        return _error("Nombre y apellido son obligatorios.")
    if not dni.isdigit() or len(dni) != 8:
        return _error("El DNI debe tener exactamente 8 dígitos numéricos.")
    if len(password) < 6:
        return _error("La contraseña debe tener al menos 6 caracteres.")
    if Usuario.query.filter_by(dni=dni).first():
        return _error("Ya existe un usuario con ese DNI.")
    try:
        rol = db.session.get(Rol, int(data.get("rol_id")))
    except (TypeError, ValueError):
        rol = None
    if not rol:
        return _error("Rol no válido.")

    u = Usuario(nombre=nombre, apellido=apellido, dni=dni, rol_id=rol.id, activo=True)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return jsonify({"ok": True, "id": u.id})


@admin_bp.route("/usuarios/toggle/<int:usuario_id>", methods=["POST"])
@rol_requerido("admin")
def toggle_usuario(usuario_id):
    u = Usuario.query.get_or_404(usuario_id)
    if u.id == current_user.id:
        return _error("No puedes desactivar tu propia cuenta.")
    u.activo = not u.activo
    db.session.commit()
    return jsonify({"ok": True, "activo": u.activo})


# US-016 — Reporte mensual y ranking de platos
@admin_bp.route("/reportes")
@rol_requerido("admin")
def reportes():
    desde_str = request.args.get("desde")
    hasta_str = request.args.get("hasta")

    try:
        desde_local = datetime.strptime(desde_str, "%Y-%m-%d")
        hasta_local = datetime.strptime(hasta_str, "%Y-%m-%d") + timedelta(days=1)
    except (TypeError, ValueError):
        # por defecto: el mes actual (en hora local)
        hoy = ahora_local()
        desde_local = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        hasta_local = hoy.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        desde_str   = desde_local.strftime("%Y-%m-%d")
        hasta_str   = (hasta_local - timedelta(days=1)).strftime("%Y-%m-%d")

    desde, hasta = local_a_utc(desde_local), local_a_utc(hasta_local)
    orden = "ingresos" if request.args.get("orden") == "ingresos" else "unidades"

    unidades = func.sum(DetalleComanda.cantidad)
    ingresos = func.sum(DetalleComanda.cantidad * Producto.precio)

    # solo cuentan los platos de comandas efectivamente cobradas
    top10 = (db.session.query(Producto.nombre,
                              unidades.label("unidades"),
                              ingresos.label("ingresos"))
        .join(DetalleComanda, DetalleComanda.producto_id == Producto.id)
        .join(Comanda, Comanda.id == DetalleComanda.comanda_id)
        .filter(Comanda.estado == "pagada",
                Comanda.abierta_en >= desde, Comanda.abierta_en < hasta)
        .group_by(Producto.nombre)
        .order_by((ingresos if orden == "ingresos" else unidades).desc())
        .limit(10)
        .all())

    ventas_rango   = Venta.query.filter(Venta.emitida_en >= desde, Venta.emitida_en < hasta).all()
    total_ingresos = sum((Decimal(v.total) for v in ventas_rango), Decimal("0.00"))

    return render_template("admin/reportes.html",
        top10=top10, orden=orden, desde=desde_str, hasta=hasta_str,
        total_ingresos=total_ingresos, total_ventas=len(ventas_rango))
