import time
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import check_password_hash
from extensions import db
from models import Usuario, registrar_log
from utils import login_required

auth_bp = Blueprint("auth", __name__)

# Protección contra fuerza bruta (en memoria; suficiente para un solo servidor).
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 5 * 60
_intentos_fallidos = {}  # clave -> [contador, timestamp_primer_fallo]


def _clave_intento(username: str) -> str:
    return f"{request.remote_addr}|{username.lower()}"


def _segundos_bloqueo(clave: str) -> int:
    registro = _intentos_fallidos.get(clave)
    if not registro:
        return 0
    contador, desde = registro
    transcurrido = time.time() - desde
    if transcurrido > BLOQUEO_SEGUNDOS:
        _intentos_fallidos.pop(clave, None)
        return 0
    return int(BLOQUEO_SEGUNDOS - transcurrido) if contador >= MAX_INTENTOS else 0


@auth_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "GET" and session.get("user_id"):
        return redirect(url_for("public.menu"))

    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()[:80]
        password = request.form.get("password") or ""
        clave = _clave_intento(username)

        espera = _segundos_bloqueo(clave)
        if espera:
            minutos = max(1, round(espera / 60))
            error = f"Demasiados intentos fallidos. Intenta de nuevo en {minutos} min."
            return render_template("login.html", error=error), 429

        user = Usuario.query.filter(Usuario.username.ilike(username)).first()
        if user and user.activo and user.check_password(password):
            _intentos_fallidos.pop(clave, None)
            session.clear()  # evita fijación de sesión
            session.permanent = True
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            session["last_seen"] = datetime.now(timezone.utc).timestamp()
            registrar_log("Login", f"Usuario {user.username} inició sesión")
            db.session.commit()
            return redirect(url_for("public.menu"))

        contador, desde = _intentos_fallidos.get(clave, [0, time.time()])
        _intentos_fallidos[clave] = [contador + 1, desde]
        if contador + 1 >= MAX_INTENTOS:
            registrar_log("Login bloqueado", f"{MAX_INTENTOS} intentos fallidos para '{username}'")
            db.session.commit()
        # Mensaje genérico: no revela si el usuario existe
        error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)

@auth_bp.route("/logout")
@login_required
def logout():
    registrar_log("Logout", f"Usuario {session.get('username')} cerró sesión")
    db.session.commit()
    session.clear()
    return redirect(url_for("auth.login"))
