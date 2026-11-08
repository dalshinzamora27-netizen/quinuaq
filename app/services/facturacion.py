"""Calculos de dinero. Se usa Decimal (no float) para evitar errores de redondeo."""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from flask import current_app

CENTIMO = Decimal("0.01")

TIPOS_COMPROBANTE = {"nota_venta": "NV", "boleta": "B001", "factura": "F001"}
METODOS_PAGO      = {"efectivo", "tarjeta", "yape_plin"}


def redondear(valor):
    return Decimal(valor).quantize(CENTIMO, rounding=ROUND_HALF_UP)


def a_decimal(valor):
    """Convierte un monto recibido (str, int o float) a Decimal. Lanza ValueError si no es valido."""
    try:
        return redondear(Decimal(str(valor)))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Monto inválido: {valor!r}")


def tasa_igv():
    return Decimal(current_app.config["IGV"])


def calcular_totales(detalles):
    """Recibe los DetalleComanda y devuelve (items, subtotal, igv, total).

    Los precios de la carta son la base imponible; el IGV se suma encima.
    """
    items    = []
    subtotal = Decimal("0")
    for d in detalles:
        precio = Decimal(d.producto.precio)
        total_item = precio * d.cantidad
        subtotal += total_item
        items.append({
            "nombre"  : d.producto.nombre,
            "cantidad": d.cantidad,
            "precio"  : redondear(precio),
            "total"   : redondear(total_item),
        })
    subtotal = redondear(subtotal)
    igv      = redondear(subtotal * tasa_igv())
    return items, subtotal, igv, subtotal + igv
