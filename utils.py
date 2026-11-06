import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import session, redirect, url_for, flash


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------
# Zonas horarias permitidas en el panel de Administración (horas respecto a UTC)
ZONAS_HORARIAS_PERMITIDAS = {"-8", "-7", "-6", "-5", "0"}


def ahora_local() -> datetime:
    """Fecha/hora local de la biblioteca.

    Prioridad:
      1) Configuración guardada en el Panel de Admin ('zona_horaria', por defecto -7 Sinaloa/Pacífico).
      2) Variable de entorno APP_UTC_OFFSET en .env.
      3) Hora del sistema operativo.
    """
    offset = None
    try:
        from models import Configuracion
        fila = Configuracion.query.filter_by(clave="zona_horaria").first()
        if fila and fila.valor in ZONAS_HORARIAS_PERMITIDAS:
            offset = fila.valor
    except Exception:
        pass

    if offset is None:
        offset = os.environ.get("APP_UTC_OFFSET", "-7")

    try:
        return datetime.now(timezone(timedelta(hours=float(offset))))
    except ValueError:
        return datetime.now().astimezone()


def hoy():
    """Fecha local de hoy (date)."""
    return ahora_local().date()


# ---------------------------------------------------------------------------
# Conversión segura de datos de formularios
# ---------------------------------------------------------------------------
def to_int(valor, default=0, minimo=None, maximo=None) -> int:
    """Convierte a int sin tronar con texto basura y lo limita a [minimo, maximo]."""
    try:
        n = int(float(str(valor).strip()))
    except (TypeError, ValueError):
        n = default
    if minimo is not None:
        n = max(minimo, n)
    if maximo is not None:
        n = min(maximo, n)
    return n


def to_float(valor, default=0.0, minimo=None, maximo=None) -> float:
    """Convierte a float sin tronar con texto basura y lo limita a [minimo, maximo]."""
    try:
        n = float(str(valor).strip().replace(",", ""))
        if n != n or n in (float("inf"), float("-inf")):  # NaN / infinito
            raise ValueError
    except (TypeError, ValueError):
        n = default
    if minimo is not None:
        n = max(minimo, n)
    if maximo is not None:
        n = min(maximo, n)
    return n


# ---------------------------------------------------------------------------
# Autenticación / autorización
# ---------------------------------------------------------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)
    return wrapper

def is_admin() -> bool:
    return session.get("role") == "admin"

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        if not is_admin():
            flash("Solo un administrador puede acceder a esta sección", "error")
            return redirect(url_for("public.menu")) # o donde sea la ruta principal
        return view_func(*args, **kwargs)
    return wrapper
