from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Rol(db.Model):
    __tablename__ = "roles"
    id     = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(20), nullable=False, unique=True)
    activo = db.Column(db.Boolean, default=True)
    usuarios = db.relationship("Usuario", backref="rol", lazy=True)

class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"
    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(100), nullable=False)
    apellido      = db.Column(db.String(100), nullable=False)
    dni           = db.Column(db.String(8),   nullable=False, unique=True)
    rol_id        = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    activo        = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)