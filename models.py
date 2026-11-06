from datetime import datetime, timezone
from werkzeug.security import check_password_hash
from flask import session, request
from extensions import db

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="bibliotecario")
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
    tipo_usuario = db.Column(db.String(20), default="interno")
    numero_cuenta = db.Column(db.String(30))
    garantia_dinero = db.Column(db.Float, default=0)
    fecha_registro = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    activo = db.Column(db.Boolean, default=True)
    estado = db.Column(db.String(30), default="activo")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


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
    estado = db.Column(db.String(30), default="disponible")
    detalle_estado = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Prestamo(db.Model):
    __tablename__ = "prestamos"
    id = db.Column(db.Integer, primary_key=True)
    libro_id = db.Column(db.String, db.ForeignKey("libros.id"), nullable=False)
    usuario_id = db.Column(db.String, db.ForeignKey("usuarios_biblioteca.id"), nullable=False)
    fecha_salida = db.Column(db.Date, nullable=False)
    fecha_devolucion_esperada = db.Column(db.Date, nullable=False)
    fecha_devolucion_real = db.Column(db.Date)
    estado = db.Column(db.String(40), default="activo")
    condicion_entrega = db.Column(db.String(50), default="Excelente")
    condicion_devolucion = db.Column(db.String(50), default="Excelente")

    libro = db.relationship("Libro")
    usuario = db.relationship("UsuarioBiblioteca")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Configuracion(db.Model):
    __tablename__ = "configuracion"
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(120), unique=True, nullable=False)
    valor = db.Column(db.String(255), nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Multa(db.Model):
    __tablename__ = "multas"
    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey("prestamos.id"), nullable=False)
    tipo = db.Column(db.String(40), default="retraso")
    monto = db.Column(db.Float, default=0)
    descripcion = db.Column(db.Text)
    pagado = db.Column(db.Boolean, default=False)

    prestamo = db.relationship("Prestamo")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class LogAuditoria(db.Model):
    __tablename__ = "log_auditoria"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    accion = db.Column(db.String(100), nullable=False)
    detalle = db.Column(db.Text)
    ip = db.Column(db.String(45))
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    usuario_admin = db.relationship("Usuario")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


def registrar_log(accion, detalle=""):
    """Registra una acción en el log de auditoría.

    NO hace commit: el log se guarda junto con la operación que lo origina
    (todo-o-nada). Si la operación falla y se hace rollback, el log tampoco queda.
    El llamador es responsable de hacer db.session.commit().
    """
    try:
        log = LogAuditoria(
            usuario_id=session.get("user_id"),
            accion=accion,
            detalle=detalle,
            ip=request.remote_addr
        )
        db.session.add(log)
    except Exception as e:
        print(f"Error al registrar log: {e}")


class Recomendacion(db.Model):
    __tablename__ = "recomendaciones"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.String, db.ForeignKey("usuarios_biblioteca.id"), nullable=False)
    libros_base = db.Column(db.Text)
    libros_recomendados = db.Column(db.Text)
    scores = db.Column(db.Text)
    email_enviado = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = db.relationship("UsuarioBiblioteca")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Reserva(db.Model):
    __tablename__ = "reservas"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.String, db.ForeignKey("usuarios_biblioteca.id"), nullable=False)
    libro_id = db.Column(db.String, db.ForeignKey("libros.id"), nullable=False)
    fecha_reserva = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    estado = db.Column(db.String(20), default="pendiente") # pendiente, activa, cancelada, completada

    usuario = db.relationship("UsuarioBiblioteca")
    libro = db.relationship("Libro")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

