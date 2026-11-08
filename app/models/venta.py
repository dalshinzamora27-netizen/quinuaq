from app import db
from app.services.tiempo import ahora_utc

class Venta(db.Model):
    __tablename__ = "ventas"
    id           = db.Column(db.Integer, primary_key=True)
    comanda_id   = db.Column(db.Integer, db.ForeignKey("comandas.id"), nullable=False)
    cajero_id    = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    tipo         = db.Column(db.String(20), nullable=False)  # nota_venta, boleta, factura
    numero       = db.Column(db.String(20), nullable=False)
    dni_cliente  = db.Column(db.String(8), nullable=True)
    ruc_cliente  = db.Column(db.String(11), nullable=True)
    razon_social = db.Column(db.String(150), nullable=True)
    subtotal     = db.Column(db.Numeric(10, 2), nullable=False)
    igv          = db.Column(db.Numeric(10, 2), nullable=False)
    total        = db.Column(db.Numeric(10, 2), nullable=False)
    estado       = db.Column(db.String(20), default="pagada")
    emitida_en   = db.Column(db.DateTime, default=ahora_utc)

    comanda = db.relationship("Comanda", backref="venta", lazy=True, uselist=False)
    cajero  = db.relationship("Usuario", lazy=True)
    pagos   = db.relationship("Pago", backref="venta", lazy=True, cascade="all, delete-orphan")

class Pago(db.Model):
    __tablename__ = "pagos"
    id       = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), nullable=False)
    metodo   = db.Column(db.String(20), nullable=False)  # efectivo, tarjeta, yape_plin
    monto    = db.Column(db.Numeric(10, 2), nullable=False)