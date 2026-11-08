import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY                     = os.getenv("SECRET_KEY", "dev-solo-para-desarrollo")
    SQLALCHEMY_DATABASE_URI        = os.getenv("DATABASE_URL", "sqlite:///quinuaq.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Origenes permitidos para Socket.IO. Vacio = solo el mismo origen.
    SOCKETIO_CORS_ORIGINS = [o.strip() for o in os.getenv("SOCKETIO_CORS_ORIGINS", "").split(",") if o.strip()] or None

    # Peru no usa horario de verano: UTC-5 todo el anio
    UTC_OFFSET_HORAS = int(os.getenv("UTC_OFFSET_HORAS", "-5"))

    IGV = "0.18"


class TestConfig(Config):
    TESTING          = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY       = "test"
