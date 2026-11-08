from app import db

class Categoria(db.Model):
    __tablename__ = "categorias"
    id        = db.Column(db.Integer, primary_key=True)
    nombre    = db.Column(db.String(100), nullable=False, unique=True)
    tipo      = db.Column(db.String(20), nullable=False)  # comida o bebida
    activo    = db.Column(db.Boolean, default=True)
    productos = db.relationship("Producto", backref="categoria", lazy=True)

class Producto(db.Model):
    __tablename__ = "productos"
    id           = db.Column(db.Integer, primary_key=True)
    nombre       = db.Column(db.String(100), nullable=False)
    descripcion  = db.Column(db.String(255))
    precio       = db.Column(db.Numeric(10, 2), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    disponible   = db.Column(db.Boolean, default=True)