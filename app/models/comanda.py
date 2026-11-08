from app import db
from app.services.tiempo import ahora_utc

class Comanda(db.Model):
    __tablename__ = "comandas"
    id          = db.Column(db.Integer, primary_key=True)
    mesa_id     = db.Column(db.Integer, db.ForeignKey("mesas.id"), nullable=False)
    mozo_id     = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    comensales  = db.Column(db.Integer, nullable=False)
    estado      = db.Column(db.String(20), default="abierta")
    abierta_en  = db.Column(db.DateTime, default=ahora_utc)
    cerrada_en  = db.Column(db.DateTime, nullable=True)

    mesa    = db.relationship("Mesa", backref="comandas", lazy=True)
    mozo    = db.relationship("Usuario", backref="comandas", lazy=True)
    detalles = db.relationship("DetalleComanda", backref="comanda", lazy=True, cascade="all, delete-orphan")

class DetalleComanda(db.Model):
    __tablename__ = "detalle_comanda"
    id          = db.Column(db.Integer, primary_key=True)
    comanda_id  = db.Column(db.Integer, db.ForeignKey("comandas.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    cantidad    = db.Column(db.Integer, default=1)
    nota        = db.Column(db.String(255))
    estado      = db.Column(db.String(20), default="pendiente")  # pendiente -> recibido -> en_proceso -> listo
    enviado_en  = db.Column(db.DateTime, default=ahora_utc)  # se actualiza al despachar

    producto = db.relationship("Producto", lazy=True)