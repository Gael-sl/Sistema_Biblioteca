from datetime import datetime, timezone
from flask import Blueprint, render_template, session, g, current_app, request, redirect, url_for, flash
from models import Libro, Usuario
from utils import login_required

public_bp = Blueprint("public", __name__)

@public_bp.before_app_request
def load_current_user():
    g.user = None
    if request.endpoint and request.endpoint.startswith("static"):
        return
    uid = session.get("user_id")
    if not uid:
        return

    # 1) Cierre por inactividad
    ahora = datetime.now(timezone.utc).timestamp()
    limite = current_app.config.get("IDLE_TIMEOUT_MINUTES", 30) * 60
    ultimo = session.get("last_seen", ahora)
    if ahora - ultimo > limite:
        session.clear()
        flash("Tu sesión se cerró por inactividad. Inicia sesión de nuevo.", "warning")
        return redirect(url_for("auth.login"))

    # 2) El empleado debe seguir existiendo y activo (si lo desactivan, se le saca)
    user = Usuario.query.get(uid)
    if not user or not user.activo:
        session.clear()
        flash("Tu cuenta fue desactivada o eliminada.", "error")
        return redirect(url_for("auth.login"))

    # 3) El rol se toma siempre de la BD (si lo cambian, aplica de inmediato)
    session["role"] = user.role
    session["username"] = user.username
    session["last_seen"] = ahora
    g.user = {"id": user.id, "username": user.username, "role": user.role}

@public_bp.route("/menu")
@login_required
def menu():
    return render_template("menu.html", user=g.user)

@public_bp.route("/catalogo")
def catalogo_publico():
    """4.4 — Catálogo público sin login."""
    libros = Libro.query.filter_by(activo=True).order_by(Libro.titulo).all()
    grupos = {}
    for libro in libros:
        key = f"{libro.titulo}-{libro.autor}"
        if key not in grupos:
            grupos[key] = {
                "titulo": libro.titulo,
                "autor": libro.autor,
                "genero": libro.genero,
                "disponibles": libro.disponibles,
                "total": 1,
                "isbn": libro.isbn,
                "id": libro.id
            }
        else:
            grupos[key]["total"] += 1
            grupos[key]["disponibles"] += libro.disponibles

    return render_template("catalogo_publico.html", libros=grupos.values())
