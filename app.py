import os
import json
import smtplib
import re
from collections import Counter
from datetime import datetime, timedelta
from email.message import EmailMessage
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, func
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "biblioteca.sqlite")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="bibliotecario")
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password, raw)


class UsuarioBiblioteca(db.Model):
    __tablename__ = "usuarios_biblioteca"
    id = db.Column(db.String(20), primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    correo = db.Column(db.String(120))
    telefono = db.Column(db.String(40))
    facultad = db.Column(db.String(120))
    carrera = db.Column(db.String(120))
    garantia_dinero = db.Column(db.Float, default=0)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)


class Libro(db.Model):
    __tablename__ = "libros"
    __table_args__ = (
        db.CheckConstraint('disponibles >= 0', name='check_disponibles_positivo'),
    )
    id = db.Column(db.String(20), primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(200))
    isbn = db.Column(db.String(80))
    genero = db.Column(db.String(120))
    tags = db.Column(db.String(400))
    costo = db.Column(db.Float, default=0)
    cantidad = db.Column(db.Integer, default=1)
    disponibles = db.Column(db.Integer, default=1)
    veces_rentado = db.Column(db.Integer, default=0)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Prestamo(db.Model):
    __tablename__ = "prestamos"
    id = db.Column(db.Integer, primary_key=True)
    libro_id = db.Column(db.String, db.ForeignKey("libros.id"), nullable=False)
    usuario_id = db.Column(db.String, db.ForeignKey("usuarios_biblioteca.id"), nullable=False)
    fecha_salida = db.Column(db.Date, nullable=False)
    fecha_devolucion_esperada = db.Column(db.Date, nullable=False)
    fecha_devolucion_real = db.Column(db.Date)
    estado = db.Column(db.String(40), default="activo")

    libro = db.relationship("Libro")
    usuario = db.relationship("UsuarioBiblioteca")


class Configuracion(db.Model):
    __tablename__ = "configuracion"
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(120), unique=True, nullable=False)
    valor = db.Column(db.String(255), nullable=False)


class Multa(db.Model):
    __tablename__ = "multas"
    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey("prestamos.id"), nullable=False)
    tipo = db.Column(db.String(40), default="retraso")
    monto = db.Column(db.Float, default=0)
    descripcion = db.Column(db.Text)
    pagado = db.Column(db.Boolean, default=False)

    prestamo = db.relationship("Prestamo")


class Recomendacion(db.Model):
    __tablename__ = "recomendaciones"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.String, db.ForeignKey("usuarios_biblioteca.id"), nullable=False)
    libros_base = db.Column(db.Text)
    libros_recomendados = db.Column(db.Text)
    scores = db.Column(db.Text)
    email_enviado = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship("UsuarioBiblioteca")


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def is_admin() -> bool:
    return session.get("role") == "admin"


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if not is_admin():
            flash("Solo un administrador puede acceder a esta sección", "error")
            return redirect(url_for("menu"))
        return view_func(*args, **kwargs)

    return wrapper


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Envía un correo simple. Usa variables de entorno SMTP_* si existen; si no, deja un stub exitoso."""

    host = os.environ.get("SMTP_HOST")
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")
    port = int(os.environ.get("SMTP_PORT", 587))
    sender = os.environ.get("SMTP_FROM", user or "noreply@biblioteca.local")

    if not host or not user or not password:
        # Stub: se asume éxito y se deja trazado en consola para pruebas locales
        print(f"[EMAIL STUB] Para: {to_email} | Asunto: {subject}\n{body}")
        return True

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)
        return True
    except Exception as exc:  # pragma: no cover - fallback
        print(f"[EMAIL ERROR] {exc}")
        return False


def get_config_map() -> dict:
    rows = Configuracion.query.all()
    return {row.clave: row.valor for row in rows}


def seed_data() -> None:
    db.create_all()
    if Usuario.query.count() == 0:
        admin = Usuario(
            username="admin",
            password=generate_password_hash("admin123"),
            role="admin",
            activo=True,
        )
        biblio = Usuario(
            username="bibliotecario",
            password=generate_password_hash("biblio123"),
            role="bibliotecario",
            activo=True,
        )
        db.session.add_all([admin, biblio])

    if Configuracion.query.count() == 0:
        defaults = {
            "dias_prestamo": "7",
            "limite_libros": "3",
            "multa_retraso": "5.00",
            "multa_leve": "20.00",
            "multa_moderado": "50.00",
            "multa_grave": "100.00",
        }
        for clave, valor in defaults.items():
            db.session.add(Configuracion(clave=clave, valor=str(valor)))

    if Libro.query.count() == 0:
        libros_seed = [
            {
                "id": "QR0001",
                "titulo": "Cien años de soledad",
                "autor": "Gabriel García Márquez",
                "isbn": "978-0307474728",
                "genero": "Realismo mágico",
                "tags": "clasico,latinoamerica,familia,saga",
                "costo": 350.0,
                "cantidad": 3,
                "disponibles": 3,
            },
            {
                "id": "QR0002",
                "titulo": "Don Quijote de la Mancha",
                "autor": "Miguel de Cervantes",
                "isbn": "978-8420412146",
                "genero": "Clásico",
                "tags": "clasico,aventura,espanol,caballeria",
                "costo": 420.0,
                "cantidad": 2,
                "disponibles": 2,
            },
            {
                "id": "QR0003",
                "titulo": "El principito",
                "autor": "Antoine de Saint-Exupéry",
                "isbn": "978-0156012195",
                "genero": "Filosofía",
                "tags": "infantil,filosofia,amistad,reflexion",
                "costo": 180.0,
                "cantidad": 5,
                "disponibles": 5,
            },
            {
                "id": "QR0004",
                "titulo": "1984",
                "autor": "George Orwell",
                "isbn": "978-0451524935",
                "genero": "Distopía",
                "tags": "distopia,ciencia_ficcion,politica,futuro",
                "costo": 290.0,
                "cantidad": 2,
                "disponibles": 2,
            },
            {
                "id": "QR0005",
                "titulo": "Rayuela",
                "autor": "Julio Cortázar",
                "isbn": "978-8437604572",
                "genero": "Novela experimental",
                "tags": "experimental,latinoamerica,vanguardia,filosofia",
                "costo": 380.0,
                "cantidad": 2,
                "disponibles": 2,
            },
            {
                "id": "QR0006",
                "titulo": "La Biblioteca de la Medianoche",
                "autor": "Matt Haig",
                "isbn": "978-0525559474",
                "genero": "Ficción contemporánea",
                "tags": "fantasia,filosofia,vida,decisiones,esperanza",
                "costo": 320.0,
                "cantidad": 2,
                "disponibles": 2,
            },
            {
                "id": "QR0007",
                "titulo": "Cumbres borrascosas",
                "autor": "Emily Brontë",
                "isbn": "978-0141439556",
                "genero": "Romance gótico",
                "tags": "clasico,romance,gotico,drama,pasion",
                "costo": 280.0,
                "cantidad": 2,
                "disponibles": 2,
            },
            {
                "id": "QR0008",
                "titulo": "Fabricante de lágrimas",
                "autor": "Erin Doom",
                "isbn": "978-8408276456",
                "genero": "Romance juvenil",
                "tags": "romance,juvenil,drama,dark_romance,contemporaneo",
                "costo": 250.0,
                "cantidad": 2,
                "disponibles": 2,
            },
            {
                "id": "QR0009",
                "titulo": "El principito (Ilustrado)",
                "autor": "Antoine de Saint-Exupéry",
                "isbn": "978-0156013987",
                "genero": "Filosofía",
                "tags": "infantil,filosofia,amistad,reflexion,ilustrado",
                "costo": 220.0,
                "cantidad": 3,
                "disponibles": 3,
            },
            {
                "id": "QR0010",
                "titulo": "Orgullo y prejuicio",
                "autor": "Jane Austen",
                "isbn": "978-0141439518",
                "genero": "Romance clásico",
                "tags": "clasico,romance,ingles,sociedad,amor",
                "costo": 300.0,
                "cantidad": 2,
                "disponibles": 2,
            },
        ]
        for data in libros_seed:
            db.session.add(Libro(**data))

    if UsuarioBiblioteca.query.count() == 0:
        usuarios_seed = [
            {
                "id": "USR001",
                "nombre": "Juan Pérez",
                "correo": "juan@email.com",
                "telefono": "555-1234",
                "facultad": "Ingeniería",
                "carrera": "Sistemas",
            },
            {
                "id": "USR002",
                "nombre": "María García",
                "correo": "maria@email.com",
                "telefono": "555-5678",
                "facultad": "Ciencias",
                "carrera": "Biología",
            },
            {
                "id": "USR003",
                "nombre": "Carlos López",
                "correo": "carlos@email.com",
                "telefono": "555-9012",
                "facultad": "Humanidades",
                "carrera": "Derecho",
            },
        ]
        for data in usuarios_seed:
            db.session.add(UsuarioBiblioteca(**data))

    db.session.commit()


@app.before_request
def load_current_user():
    g.user = None
    if session.get("user_id"):
        g.user = {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "role": session.get("role"),
        }


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = Usuario.query.filter(Usuario.username.ilike(username)).first()
        if user and user.activo and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("menu"))
        error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/menu")
@login_required
def menu():
    return render_template("menu.html", user=g.user)


@app.route("/admin")
@admin_required
def admin_panel():
    config = get_config_map()
    hoy = datetime.utcnow().date()
    
    stats = {
        "total_libros": Libro.query.filter_by(activo=True).count(),
        "usuarios_biblioteca": UsuarioBiblioteca.query.filter_by(activo=True).count(),
        "prestamos_activos": Prestamo.query.filter_by(estado="activo").count(),
        "devoluciones_hoy": Prestamo.query.filter(
            Prestamo.estado == "devuelto",
            func.date(Prestamo.fecha_devolucion_real) == hoy
        ).count(),
        "multas_pendientes": Multa.query.filter_by(pagado=False).count(),
        "usuarios_sistema": Usuario.query.count(),
    }

    # Top 10 libros más rentados
    top_libros = (
        db.session.query(Libro.titulo, func.count(Prestamo.id).label("total_rentas"))
        .join(Prestamo, Libro.id == Prestamo.libro_id)
        .group_by(Libro.id, Libro.titulo)
        .order_by(desc("total_rentas"))
        .limit(10)
        .all()
    )

    # Top 10 usuarios más activos
    top_usuarios = (
        db.session.query(UsuarioBiblioteca.nombre, func.count(Prestamo.id).label("total_prestamos"))
        .join(Prestamo, UsuarioBiblioteca.id == Prestamo.usuario_id)
        .group_by(UsuarioBiblioteca.id, UsuarioBiblioteca.nombre)
        .order_by(desc("total_prestamos"))
        .limit(10)
        .all()
    )

    # Préstamos por día (última semana)
    hace_7_dias = hoy - timedelta(days=7)
    prestamos_por_dia = (
        db.session.query(func.date(Prestamo.fecha_salida).label("dia"), func.count(Prestamo.id).label("total"))
        .filter(Prestamo.fecha_salida >= hace_7_dias)
        .group_by("dia")
        .order_by("dia")
        .all()
    )

    # Preparar datos para gráficos en formato JSON
    chart_data = {
        "topLibros": {
            "labels": [titulo[:30] for titulo, total in top_libros],
            "data": [int(total) for titulo, total in top_libros]
        },
        "topUsuarios": {
            "labels": [nombre[:25] for nombre, total in top_usuarios],
            "data": [int(total) for nombre, total in top_usuarios]
        },
        "tendencia": {
            "labels": [dia.strftime('%d/%m') if hasattr(dia, 'strftime') else str(dia) for dia, total in prestamos_por_dia],
            "data": [int(total) for dia, total in prestamos_por_dia]
        }
    }

    # Alertas de retraso
    alertas_retraso = (
        db.session.query(
            Prestamo,
            UsuarioBiblioteca.nombre.label("usuario_nombre"),
            Libro.titulo.label("libro_titulo"),
            func.cast(
                (func.julianday(func.date("now", "localtime")) - func.julianday(Prestamo.fecha_devolucion_esperada)),
                db.Integer
            ).label("dias_retraso")
        )
        .join(UsuarioBiblioteca, Prestamo.usuario_id == UsuarioBiblioteca.id)
        .join(Libro, Prestamo.libro_id == Libro.id)
        .filter(Prestamo.estado == "activo", Prestamo.fecha_devolucion_esperada < hoy)
        .order_by(desc("dias_retraso"))
        .limit(10)
        .all()
    )

    # Usuarios con multas pendientes
    usuarios_con_multas = (
        db.session.query(
            UsuarioBiblioteca.nombre,
            func.sum(Multa.monto).label("total_multas")
        )
        .join(Prestamo, UsuarioBiblioteca.id == Prestamo.usuario_id)
        .join(Multa, Prestamo.id == Multa.prestamo_id)
        .filter(Multa.pagado == False)
        .group_by(UsuarioBiblioteca.id, UsuarioBiblioteca.nombre)
        .having(func.sum(Multa.monto) > 0)
        .limit(10)
        .all()
    )

    # Libros con inventario bajo
    libros_inventario_bajo = (
        Libro.query.filter(Libro.activo == True, Libro.disponibles <= 1)
        .order_by(Libro.disponibles.asc())
        .limit(10)
        .all()
    )

    # Devoluciones pendientes (retrasados)
    devoluciones_pendientes = Prestamo.query.filter(
        Prestamo.estado == "activo",
        Prestamo.fecha_devolucion_esperada < hoy
    ).count()

    # Usuarios activos de la biblioteca
    usuarios_biblioteca = UsuarioBiblioteca.query.filter_by(activo=True).order_by(UsuarioBiblioteca.nombre).all()

    # Usuarios del sistema
    usuarios_sistema = Usuario.query.order_by(Usuario.created_at.desc()).all()

    # Últimas recomendaciones
    ultimas_rec = (
        Recomendacion.query.order_by(desc(Recomendacion.fecha_creacion))
        .limit(5)
        .all()
    )
    for rec in ultimas_rec:
        try:
            rec.count = len(json.loads(rec.libros_recomendados or "[]"))
        except Exception:
            rec.count = 0

    return render_template(
        "admin.html",
        stats=stats,
        config=config,
        chart_data=chart_data,
        top_libros=top_libros,
        top_usuarios=top_usuarios,
        prestamos_por_dia=prestamos_por_dia,
        alertas_retraso=alertas_retraso,
        usuarios_con_multas=usuarios_con_multas,
        libros_inventario_bajo=libros_inventario_bajo,
        devoluciones_pendientes=devoluciones_pendientes,
        usuarios_biblioteca=usuarios_biblioteca,
        usuarios_sistema=usuarios_sistema,
        ultimas_rec=ultimas_rec,
    )


@app.route("/admin/usuarios", methods=["POST"])
@admin_required
def crear_usuario_sistema():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    role = request.form.get("role") or "bibliotecario"

    if not username or not password:
        flash("Usuario y contraseña son obligatorios", "error")
        return redirect(url_for("admin_panel"))

    if Usuario.query.filter(Usuario.username.ilike(username)).first():
        flash("El nombre de usuario ya existe", "error")
        return redirect(url_for("admin_panel"))

    user = Usuario(username=username, password=generate_password_hash(password), role=role)
    db.session.add(user)
    db.session.commit()
    flash("Usuario creado", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/usuarios/<int:user_id>/editar", methods=["POST"])
@admin_required
def editar_usuario_sistema(user_id: int):
    user = Usuario.query.get(user_id)
    if not user:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("admin_panel"))

    nuevo_username = (request.form.get("username") or user.username).strip()
    nuevo_role = request.form.get("role") or user.role
    nueva_clave = request.form.get("password") or None

    existente = Usuario.query.filter(Usuario.username.ilike(nuevo_username)).first()
    if existente and existente.id != user.id:
        flash("Ya existe otro usuario con ese nombre", "error")
        return redirect(url_for("admin_panel"))

    user.username = nuevo_username
    user.role = nuevo_role
    if nueva_clave:
        user.password = generate_password_hash(nueva_clave)

    db.session.commit()
    flash("Usuario actualizado", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/usuarios/<int:user_id>/eliminar", methods=["POST"])
@admin_required
def eliminar_usuario_sistema(user_id: int):
    if session.get("user_id") == user_id:
        flash("No puedes eliminar tu propio usuario", "error")
        return redirect(url_for("admin_panel"))

    user = Usuario.query.get(user_id)
    if not user:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("admin_panel"))

    if user.role == "admin":
        admins = Usuario.query.filter_by(role="admin").count()
        if admins <= 1:
            flash("Debe quedar al menos un administrador", "error")
            return redirect(url_for("admin_panel"))

    db.session.delete(user)
    db.session.commit()
    flash("Usuario eliminado", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/configuracion", methods=["POST"])
@admin_required
def guardar_configuracion():
    try:
        params_config = [
            "dias_prestamo", "limite_libros", "multa_retraso",
            "multa_leve", "multa_moderado", "multa_grave"
        ]
        for param in params_config:
            valor = request.form.get(param)
            if valor:
                config_row = Configuracion.query.filter_by(clave=param).first()
                if config_row:
                    config_row.valor = str(valor)
                else:
                    db.session.add(Configuracion(clave=param, valor=str(valor)))
        
        db.session.commit()
        flash("Configuración actualizada correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar configuración: {e}", "error")
    
    return redirect(url_for("admin_panel"))


@app.route("/inventario", methods=["GET"])
@login_required
def inventario():
    libros = Libro.query.filter_by(activo=True).order_by(Libro.titulo).all()
    return render_template("inventario.html", libros=libros)


@app.route("/libros/agregar", methods=["POST"])
@login_required
def agregar_libro():
    if not is_admin():
        flash("Solo un administrador puede agregar libros", "error")
        return redirect(url_for("inventario"))
    data = request.form
    nuevo_id = generar_codigo_libro()
    libro = Libro(
        id=nuevo_id,
        titulo=data.get("titulo"),
        cantidad=int(data.get("cantidad", 1)),
        disponibles=int(data.get("cantidad", 1)),
        autor=data.get("autor"),
        isbn=data.get("isbn"),
        genero=data.get("genero"),
        tags=data.get("tags"),
        costo=float(data.get("costo", 0)),
    )
    db.session.add(libro)
    db.session.commit()
    flash(f"Libro {libro.titulo} agregado", "success")
    return redirect(url_for("inventario"))


@app.route("/libros/<libro_id>/editar", methods=["POST"])
@admin_required
def editar_libro(libro_id: str):
    libro = Libro.query.get(libro_id)
    if not libro:
        flash("Libro no encontrado", "error")
        return redirect(url_for("inventario"))

    data = request.form
    prestados = Prestamo.query.filter_by(libro_id=libro_id, estado="activo").count()
    nueva_cantidad = int(data.get("cantidad", libro.cantidad) or libro.cantidad)
    if nueva_cantidad < prestados:
        nueva_cantidad = prestados
    solicitados_disponibles = int(data.get("disponibles", libro.disponibles) or libro.disponibles)
    nuevos_disponibles = min(max(solicitados_disponibles, 0), max(nueva_cantidad - prestados, 0))

    libro.titulo = data.get("titulo") or libro.titulo
    libro.autor = data.get("autor") or libro.autor
    libro.isbn = data.get("isbn") or libro.isbn
    libro.genero = data.get("genero") or libro.genero
    libro.tags = data.get("tags") or libro.tags
    libro.costo = float(data.get("costo", libro.costo) or libro.costo)
    libro.cantidad = nueva_cantidad
    libro.disponibles = nuevos_disponibles
    libro.activo = bool(data.get("activo"))

    db.session.commit()
    flash("Libro actualizado", "success")
    return redirect(url_for("inventario"))


@app.route("/libros/<libro_id>/eliminar", methods=["POST"])
@admin_required
def eliminar_libro(libro_id: str):
    libro = Libro.query.get(libro_id)
    if not libro:
        flash("Libro no encontrado", "error")
        return redirect(url_for("inventario"))
    prestamos_activos = Prestamo.query.filter_by(libro_id=libro_id, estado="activo").count()
    if prestamos_activos > 0:
        flash("No se puede dar de baja un libro con préstamos activos", "error")
        return redirect(url_for("inventario"))

    libro.activo = False
    libro.disponibles = 0
    db.session.commit()
    flash("Libro dado de baja", "success")
    return redirect(url_for("inventario"))


def generar_codigo_libro() -> str:
    prefijo = "QR"
    existentes = [
        int(libro.id.replace(prefijo, ""))
        for libro in Libro.query.filter(Libro.id.like(f"{prefijo}%")).all()
        if libro.id.replace(prefijo, "").isdigit()
    ]
    siguiente = max(existentes) + 1 if existentes else 1
    return f"{prefijo}{siguiente:04d}"


@app.route("/usuarios-biblioteca")
@login_required
def listar_usuarios_biblioteca():
    """Lista todos los usuarios de biblioteca"""
    usuarios = UsuarioBiblioteca.query.order_by(UsuarioBiblioteca.nombre).all()
    return render_template("listar_usuarios.html", usuarios=usuarios)


@app.route("/usuarios-biblioteca/nuevo")
@login_required
def agregar_usuario_biblioteca():
    """Muestra formulario para agregar nuevo usuario con preview"""
    return render_template("agregar_usuario.html")


@app.route("/usuarios-biblioteca/crear", methods=["POST"])
@login_required
def crear_usuario_biblioteca():
    """Crea un nuevo usuario con ID único y envía credencial por correo"""
    try:
        data = request.get_json()
        nuevo_id = data.get("id", "").strip()
        nombre = data.get("nombre", "").strip()
        correo = data.get("correo", "").strip()
        
        if not nuevo_id or not nombre or not correo:
            return jsonify({"success": False, "message": "Faltan datos obligatorios"}), 400
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", correo):
            return jsonify({"success": False, "message": "El formato del correo parece inválido"}), 400
        
        if UsuarioBiblioteca.query.filter_by(id=nuevo_id).first():
            return jsonify({"success": False, "message": "Ya existe un usuario con ese ID"}), 400
        
        # Crear usuario
        usuario = UsuarioBiblioteca(
            id=nuevo_id,
            nombre=nombre,
            correo=correo,
            telefono=data.get("telefono"),
            facultad=data.get("facultad"),
            carrera=data.get("carrera"),
            activo=True,
        )
        db.session.add(usuario)
        db.session.commit()
        
        # Enviar credencial por correo (opcional)
        try:
            enviar_credencial_email(usuario)
        except Exception as e:
            print(f"Error al enviar correo: {e}")
        
        return jsonify({"success": True, "message": "Usuario creado exitosamente"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/usuarios-biblioteca/<usuario_id>/editar", methods=["POST"])
@login_required
def editar_usuario_biblioteca(usuario_id: str):
    usuario = UsuarioBiblioteca.query.get(usuario_id)
    if not usuario:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("listar_usuarios_biblioteca"))

    data = request.form
    usuario.nombre = data.get("nombre") or usuario.nombre
    usuario.correo = data.get("correo") or usuario.correo
    usuario.telefono = data.get("telefono") or usuario.telefono
    usuario.facultad = data.get("facultad") or usuario.facultad
    usuario.carrera = data.get("carrera") or usuario.carrera
    usuario.activo = data.get("activo") == "1"
    db.session.commit()
    flash("Usuario actualizado", "success")
    return redirect(url_for("listar_usuarios_biblioteca"))


@app.route("/usuarios-biblioteca/<usuario_id>/eliminar", methods=["POST"])
@login_required
def eliminar_usuario_biblioteca(usuario_id: str):
    usuario = UsuarioBiblioteca.query.get(usuario_id)
    if not usuario:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("listar_usuarios_biblioteca"))
    usuario.activo = False
    db.session.commit()
    flash("Usuario dado de baja", "success")
    return redirect(url_for("listar_usuarios_biblioteca"))


def enviar_credencial_email(usuario: UsuarioBiblioteca):
    """Envía la credencial del usuario por correo electrónico"""
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    
    if not all([smtp_server, smtp_user, smtp_password]):
        print("Configuración SMTP no encontrada, no se enviará correo")
        return
    
    msg = EmailMessage()
    msg["Subject"] = "Tu Credencial de Biblioteca"
    msg["From"] = smtp_user
    msg["To"] = usuario.correo
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #667eea;">¡Bienvenido a la Biblioteca!</h2>
        <p>Hola <strong>{usuario.nombre}</strong>,</p>
        <p>Tu credencial de biblioteca ha sido creada exitosamente.</p>
        <div style="background: #f5f5f7; padding: 20px; border-radius: 10px; margin: 20px 0;">
          <p><strong>ID de Usuario:</strong> {usuario.id}</p>
          <p><strong>Facultad:</strong> {usuario.facultad or 'No especificado'}</p>
          <p><strong>Carrera:</strong> {usuario.carrera or 'No especificado'}</p>
        </div>
        <p>Presenta tu ID en la biblioteca para solicitar préstamos de libros.</p>
        <p style="color: #666; font-size: 12px; margin-top: 30px;">Este es un correo automático, por favor no respondas.</p>
      </body>
    </html>
    """
    
    msg.set_content(f"Tu credencial de biblioteca\n\nID: {usuario.id}\nNombre: {usuario.nombre}")
    msg.add_alternative(html, subtype="html")
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


def generar_recomendaciones(usuario_id: str, limite: int = 5, enviar_correo: bool = False):
    from includes.recomendaciones import SistemaRecomendacion
    from includes.email import EmailRecomendaciones

    usuario = UsuarioBiblioteca.query.filter_by(id=usuario_id, activo=True).first()
    if not usuario:
        return []

    prestamos_usuario = (
        Prestamo.query.filter_by(usuario_id=usuario_id)
        .join(Libro, Prestamo.libro_id == Libro.id)
        .add_entity(Libro)
        .all()
    )

    prestamos_libros = [libro for _, libro in prestamos_usuario]
    todos_libros = Libro.query.filter_by(activo=True).all()

    sistema = SistemaRecomendacion(prestamos_libros, todos_libros)
    recomendaciones = sistema.generar_recomendaciones(limite=limite)

    if not recomendaciones:
        return []

    base_libros = [libro.titulo for libro in prestamos_libros]
    import json
    nueva_rec = Recomendacion(
        usuario_id=usuario_id,
        libros_base=json.dumps(base_libros, ensure_ascii=False),
        libros_recomendados=json.dumps(recomendaciones, ensure_ascii=False),
        scores=json.dumps({rec["libro_id"]: rec["score"] for rec in recomendaciones}),
        email_enviado=False
    )
    db.session.add(nueva_rec)
    db.session.commit()

    if enviar_correo and usuario.correo and recomendaciones:
        host = os.environ.get("SMTP_HOST")
        user = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")
        port = int(os.environ.get("SMTP_PORT", 587))
        sender = os.environ.get("SMTP_FROM", user or "noreply@biblioteca.local")

        if not host or not user or not password:
            print(f"[STUB] Recomendaciones para {usuario.correo}: {recomendaciones}")
            nueva_rec.email_enviado = True
        else:
            email_sistema = EmailRecomendaciones(host, port, user, password, sender)
            enviado = email_sistema.enviar_recomendaciones(usuario.correo, usuario.nombre, recomendaciones)
            if enviado:
                nueva_rec.email_enviado = True

        db.session.commit()

    return recomendaciones


@app.route("/renta", methods=["GET", "POST"])
@login_required
def renta():
    config = get_config_map()
    libros = (
        Libro.query.filter_by(activo=True)
        .filter(Libro.disponibles > 0)
        .order_by(Libro.titulo)
        .all()
    )
    show_ticket = False
    prestamo = None
    usuario_data = None
    libro_data = None
    error = None

    if request.method == "POST" and request.form.get("confirmar_prestamo"):
        usuario_id = (request.form.get("usuario_id") or "").strip()
        libro_id = (request.form.get("libro_id_real") or request.form.get("libro_id") or "").strip()
        usuario_data = UsuarioBiblioteca.query.filter_by(id=usuario_id, activo=True).first()
        libro_data = Libro.query.filter_by(id=libro_id, activo=True).filter(Libro.disponibles > 0).first()
        if not usuario_data or not libro_data:
            error = "Usuario o libro no encontrado"
        else:
            limite = int(config.get("limite_libros", 3))
            prestamos_activos = (
                Prestamo.query.filter_by(usuario_id=usuario_id, estado="activo").count()
            )
            prestamo_duplicado = Prestamo.query.filter_by(usuario_id=usuario_id, libro_id=libro_id, estado="activo").first()
            
            if prestamos_activos >= limite:
                error = f"El usuario ha alcanzado el límite de {limite} libros"
            elif prestamo_duplicado:
                error = "El usuario ya tiene un préstamo activo de este mismo libro"
            else:
                try:
                    garantia = libro_data.costo * 0.20
                    fecha_salida = datetime.utcnow().date()
                    dias_prestamo = int(config.get("dias_prestamo", 7))
                    fecha_devolucion = fecha_salida + timedelta(days=dias_prestamo)
                    prestamo = Prestamo(
                        libro_id=libro_id,
                        usuario_id=usuario_id,
                        fecha_salida=fecha_salida,
                        fecha_devolucion_esperada=fecha_devolucion,
                        estado="activo",
                    )
                    libro_data.disponibles -= 1
                    libro_data.veces_rentado += 1
                    usuario_data.garantia_dinero += garantia
                    db.session.add(prestamo)
                    db.session.commit()
                    try:
                        generar_recomendaciones(usuario_id, enviar_correo=True)
                    except Exception as rec_exc:  # pragma: no cover - logging
                        print(f"[RECOMENDACIONES ERROR] {rec_exc}")
                    show_ticket = True
                except Exception as exc:  # pragma: no cover - safety net
                    db.session.rollback()
                    error = f"Error al procesar préstamo: {exc}"

    return render_template(
        "renta.html",
        libros=libros,
        config=config,
        show_ticket=show_ticket,
        prestamo=prestamo,
        usuario=usuario_data,
        libro=libro_data,
        error=error,
    )


@app.route("/admin/recomendaciones", methods=["GET", "POST"])
@admin_required
def admin_recomendaciones():
    recomendaciones = []
    seleccionado = None
    if request.method == "POST":
        usuario_id = (request.form.get("usuario_id") or "").strip()
        enviar = bool(request.form.get("enviar_correo"))
        recomendaciones = generar_recomendaciones(usuario_id, enviar_correo=enviar)
        seleccionado = UsuarioBiblioteca.query.get(usuario_id)
        if recomendaciones:
            flash("Recomendaciones generadas", "success")
        else:
            flash("No se generaron recomendaciones", "warning")

    usuarios = (
        UsuarioBiblioteca.query.filter_by(activo=True)
        .order_by(UsuarioBiblioteca.nombre)
        .all()
    )
    ultimas = Recomendacion.query.order_by(desc(Recomendacion.fecha_creacion)).limit(10).all()
    for rec in ultimas:
        try:
            rec.count = len(json.loads(rec.libros_recomendados or "[]"))
        except Exception:
            rec.count = 0

    return render_template(
        "recomendaciones.html",
        usuarios=usuarios,
        recomendaciones=recomendaciones,
        seleccionado=seleccionado,
        ultimas=ultimas,
    )


@app.route("/devoluciones", methods=["GET"])
@login_required
def devoluciones():
    prestamos = (
        Prestamo.query.filter_by(estado="activo")
        .join(Libro, Prestamo.libro_id == Libro.id)
        .join(UsuarioBiblioteca, Prestamo.usuario_id == UsuarioBiblioteca.id)
        .add_entity(Libro)
        .add_entity(UsuarioBiblioteca)
        .order_by(Prestamo.fecha_devolucion_esperada)
        .all()
    )
    config = get_config_map()
    return render_template(
        "devoluciones.html",
        prestamos=prestamos,
        config=config,
    )


@app.route("/devoluciones/procesar", methods=["POST"])
@login_required
def procesar_devolucion():
    prestamo_id = request.form.get("prestamo_id")
    estado_libro = request.form.get("estado_libro", "sin_dano")
    observaciones = request.form.get("observaciones", "").strip()
    usuario_id = request.form.get("usuario_id")

    prestamo = Prestamo.query.filter_by(id=prestamo_id, estado="activo").first()
    if not prestamo:
        flash("Préstamo no encontrado", "error")
        return redirect(url_for("devoluciones"))

    try:
        prestamo.estado = "devuelto"
        prestamo.fecha_devolucion_real = datetime.utcnow().date()
        prestamo.libro.disponibles += 1

        config = get_config_map()
        multa_total = 0.0
        dias_retraso = 0
        if prestamo.fecha_devolucion_real and prestamo.fecha_devolucion_esperada:
            dias_retraso = (prestamo.fecha_devolucion_real - prestamo.fecha_devolucion_esperada).days
        if dias_retraso > 0:
            multa_retraso = float(config.get("multa_retraso", 0) or 0)
            multa_total += dias_retraso * multa_retraso

        multa_dano = 0.0
        if estado_libro in {"leve", "moderado", "grave"}:
            clave = f"multa_{estado_libro}"
            multa_dano = float(config.get(clave, 0) or 0)
            multa_total += multa_dano

        if multa_total > 0:
            tipo = "retraso" if estado_libro == "sin_dano" else "daño"
            descripcion = observaciones
            detalles = []
            if dias_retraso > 0:
                detalles.append(f"Retraso de {dias_retraso} días")
            if multa_dano:
                detalles.append(f"Daño {estado_libro}")
            if detalles:
                descripcion = (observaciones + " | " if observaciones else "") + ", ".join(detalles)
            db.session.add(
                Multa(
                    prestamo_id=prestamo.id,
                    tipo=tipo,
                    monto=multa_total,
                    descripcion=descripcion,
                )
            )

        libro_costo = float(prestamo.libro.costo or 0)
        if usuario_id and libro_costo:
            garantia_libro = libro_costo * 0.20
            prestamo.usuario.garantia_dinero = max(
                0, prestamo.usuario.garantia_dinero - garantia_libro - multa_total
            )

        db.session.commit()
        flash("Devolución procesada", "success")
    except Exception as exc:  # pragma: no cover - safety net
        db.session.rollback()
        flash(f"Error al procesar devolución: {exc}", "error")

    return redirect(url_for("devoluciones"))


@app.route("/api/usuario/garantia")
@login_required
def api_usuario_garantia():
    usuario_id = request.args.get("id")
    libro_id = request.args.get("libro_id")
    if not usuario_id or not libro_id:
        return jsonify({"success": False, "error": "Parámetros inválidos"}), 400
    usuario = UsuarioBiblioteca.query.filter_by(id=usuario_id).first()
    libro = Libro.query.filter_by(id=libro_id).first()
    if not usuario or not libro:
        return jsonify({"success": False, "error": "Usuario o libro no encontrado"}), 404
    return jsonify(
        {
            "success": True,
            "garantia": float(usuario.garantia_dinero or 0),
            "libro_costo": float(libro.costo or 0),
        }
    )


@app.context_processor
def inject_globals():
    return {"es_admin": is_admin, "datetime": datetime}


# Garantiza que la base se cree al levantar con `flask run`.
with app.app_context():
    seed_data()


if __name__ == "__main__":
    with app.app_context():
        seed_data()
    app.run(debug=True)
