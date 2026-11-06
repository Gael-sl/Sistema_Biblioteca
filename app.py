import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for as flask_url_for, flash, request
from flask_wtf.csrf import CSRFError
from apscheduler.schedulers.background import BackgroundScheduler

from extensions import db, migrate, csrf
from models import Usuario, Configuracion, Libro, UsuarioBiblioteca, Prestamo, Multa, LogAuditoria, Reserva, Recomendacion
from routes import init_app
from includes.email import EmailNotificaciones

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "biblioteca.sqlite")

app = Flask(__name__)

# Security configuration
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    raise RuntimeError(
        "SECRET_KEY no está definida en el archivo .env.\n"
        "Genera una con: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
app.config["SECRET_KEY"] = _secret_key
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Sesión: cookie no accesible desde JS, protegida contra envíos cross-site,
# expira tras 8 h y se cierra sola tras IDLE_TIMEOUT_MINUTES sin actividad.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE") == "1"  # activar con HTTPS
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["IDLE_TIMEOUT_MINUTES"] = int(os.environ.get("IDLE_TIMEOUT_MINUTES", 30))
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB por petición

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
csrf.init_app(app)

# Initialize blueprints
init_app(app)

# Smart url_for for backward compatibility with templates
def smart_url_for(endpoint, **values):
    if '.' not in endpoint:
        for ep in app.view_functions:
            if ep.endswith('.' + endpoint):
                return flask_url_for(ep, **values)
    return flask_url_for(endpoint, **values)

# Global variables inject processor
@app.context_processor
def inject_globals():
    from utils import is_admin
    return {
        "es_admin": is_admin, 
        "datetime": datetime, 
        "timezone": timezone,
        "url_for": smart_url_for
    }

# Cabeceras de seguridad en todas las respuestas
@app.after_request
def security_headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    # Páginas con datos personales no deben quedar en caché del navegador
    if request.endpoint and not request.endpoint.startswith("static"):
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp

# CSRF error handler
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash("La sesión expiró o el formulario no es válido. Por favor intenta de nuevo.", "error")
    return redirect(smart_url_for("menu"))

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    try:
        db.session.rollback()
    except Exception:
        pass
    return render_template("500.html"), 500

def seed_data() -> None:
    from werkzeug.security import generate_password_hash
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
            "zona_horaria": "-7",
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
        ultimo_num = 0
        for data in libros_seed:
            cant = data.pop("cantidad", 1)
            data.pop("disponibles", 1)
            for _ in range(cant):
                ultimo_num += 1
                new_id = f"QR{ultimo_num:04d}"
                libro_data = data.copy()
                libro_data["id"] = new_id
                libro_data["cantidad"] = 1
                libro_data["disponibles"] = 1
                libro_data["estado"] = "disponible"
                libro_data["detalle_estado"] = None
                db.session.add(Libro(**libro_data))

    if UsuarioBiblioteca.query.count() == 0:
        usuarios_seed = [
            {
                "id": "USR001",
                "nombre": "Juan Pérez",
                "correo": "juan@email.com",
                "telefono": "555-1234",
                "facultad": "Ingeniería",
                "carrera": "Sistemas",
                "estado": "activo",
            },
            {
                "id": "USR002",
                "nombre": "María García",
                "correo": "maria@email.com",
                "telefono": "555-5678",
                "facultad": "Ciencias",
                "carrera": "Biología",
                "estado": "activo",
            },
            {
                "id": "USR003",
                "nombre": "Carlos López",
                "correo": "carlos@email.com",
                "telefono": "555-9012",
                "facultad": "Humanidades",
                "carrera": "Derecho",
                "estado": "activo",
            },
        ]
        for data in usuarios_seed:
            db.session.add(UsuarioBiblioteca(**data))

    db.session.commit()

def verificar_vencimientos():
    """Tarea programada para verificar vencimientos y enviar correos."""
    with app.app_context():
        try:
            print("[CRON] Iniciando verificación de vencimientos...")
            from utils import hoy as hoy_local
            hoy = hoy_local()
            limite = hoy + timedelta(days=2)

            prestamos = Prestamo.query.filter(
                Prestamo.estado == 'activo',
                Prestamo.fecha_devolucion_esperada <= limite
            ).all()

            if not prestamos:
                print("[CRON] No hay vencimientos próximos.")
                return

            por_usuario = {}
            for p in prestamos:
                if not p.usuario.correo:
                    continue
                if p.usuario_id not in por_usuario:
                    por_usuario[p.usuario_id] = {
                        "usuario": p.usuario,
                        "libros": []
                    }
                por_usuario[p.usuario_id]["libros"].append({
                    "titulo": p.libro.titulo,
                    "fecha": p.fecha_devolucion_esperada
                })

            if not por_usuario:
                return

            host = os.environ.get("SMTP_HOST")
            port = int(os.environ.get("SMTP_PORT", 587))
            user = os.environ.get("SMTP_USER")
            password = os.environ.get("SMTP_PASSWORD")
            sender = os.environ.get("SMTP_FROM") or os.environ.get("SMTP_SENDER") or user

            email_notif = EmailNotificaciones(host, port, user, password, sender)
            for uid, data in por_usuario.items():
                email_notif.enviar_aviso_vencimiento(data["usuario"].correo, data["usuario"].nombre, data["libros"])
            print(f"[CRON] Verificación de vencimientos completada. Correos enviados a {len(por_usuario)} usuarios.")
        except Exception as e:
            print(f"[CRON ERROR] Falló la verificación de vencimientos: {e}")

# Create database and seed when starting via Flask directly
with app.app_context():
    seed_data()

if __name__ == "__main__":
    with app.app_context():
        seed_data()
        
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(verificar_vencimientos, 'cron', hour=8, minute=0)
    scheduler.start()
    
    # Nunca dejes debug=True en producción: expone una consola que ejecuta código.
    # Para desarrollo local pon FLASK_DEBUG=1 en el .env
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
