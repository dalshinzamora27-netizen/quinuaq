from app import db

class Mesa(db.Model):
    __tablename__ = "mesas"
    id        = db.Column(db.Integer, primary_key=True)
    numero    = db.Column(db.Integer, nullable=False, unique=True)
    capacidad = db.Column(db.Integer, default=4)
    estado    = db.Column(db.String(20), default="libre")
    mozo_id   = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    mozo      = db.relationship("Usuario", backref="mesas", lazy=True)