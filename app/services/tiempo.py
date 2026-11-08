from datetime import datetime, timedelta, timezone
from flask import current_app


def ahora_utc():
    """Fecha y hora actual en UTC, sin zona horaria (asi se guarda en la BD)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _offset():
    return timedelta(hours=current_app.config["UTC_OFFSET_HORAS"])


def ahora_local():
    return ahora_utc() + _offset()


def rango_dia_utc(fecha_local=None):
    """Devuelve (inicio, fin) en UTC del dia local indicado (por defecto hoy).

    Las fechas se guardan en UTC, pero "hoy" para el restaurante es el dia
    en hora de Peru; sin este ajuste las ventas despues de las 7 p. m.
    caerian en el dia siguiente.
    """
    if fecha_local is None:
        fecha_local = ahora_local().date()
    inicio_local = datetime.combine(fecha_local, datetime.min.time())
    inicio_utc   = inicio_local - _offset()
    return inicio_utc, inicio_utc + timedelta(days=1)


def local_a_utc(dt_local):
    return dt_local - _offset()
