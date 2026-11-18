"""Script idempotente para dejar biblioteca.sqlite lista para el experimento con 12 participantes."""

from datetime import timedelta
from werkzeug.security import generate_password_hash

from app import app
from extensions import db
from models import (
    Libro,
    LogAuditoria,
    Multa,
    Prestamo,
    Recomendacion,
    Reserva,
    Usuario,
    UsuarioBiblioteca,
)
from utils import hoy as hoy_local


PASSWORD_EXPERIMENTO = "Prueba123*"

CUENTAS_EXPERIMENTO = [
    # Perfil 1: Bibliotecarios de mostrador (6)
    ("biblio1", "bibliotecario"),
    ("biblio2", "bibliotecario"),
    ("biblio3", "bibliotecario"),
    ("biblio4", "bibliotecario"),
    ("biblio5", "bibliotecario"),
    ("biblio6", "bibliotecario"),
    # Perfil 2: Administradores de acervo (3)
    ("admin1", "admin"),
    ("admin2", "admin"),
    ("admin3", "admin"),
    # Perfil 3: Flujo integral (3)
    ("biblio7", "bibliotecario"),
    ("biblio8", "bibliotecario"),
    ("admin4", "admin"),
]

LECTORES_EXPERIMENTO = [
    {
        "id": "USR001",
        "nombre": "Juan Pérez",
        "correo": "juan.perez@lector.com",
        "telefono": "555-0101",
        "facultad": "Área de Tecnología",
        "carrera": "Desarrollador",
        "tipo_usuario": "interno",
        "numero_cuenta": "AFI-2026-001",
    },
    {
        "id": "USR002",
        "nombre": "María García",
        "correo": "maria.garcia@lector.com",
        "telefono": "555-0102",
        "facultad": "Ciencias Naturales",
        "carrera": "Investigadora",
        "tipo_usuario": "interno",
        "numero_cuenta": "AFI-2026-002",
    },
    {
        "id": "USR003",
        "nombre": "Carlos López",
        "correo": "carlos.lopez@lector.com",
        "telefono": "555-0103",
        "facultad": "Humanidades y Letras",
        "carrera": "Docente",
        "tipo_usuario": "interno",
        "numero_cuenta": "AFI-2026-003",
    },
    {
        "id": "USR004",
        "nombre": "Ana Martínez",
        "correo": "ana.martinez@lector.com",
        "telefono": "555-0104",
        "facultad": "Artes y Diseño",
        "carrera": "Diseñadora Editorial",
        "tipo_usuario": "interno",
        "numero_cuenta": "AFI-2026-004",
    },
    {
        "id": "USR005",
        "nombre": "Luis Rodríguez",
        "correo": "luis.rodriguez@lector.com",
        "telefono": "555-0105",
        "facultad": "Público General",
        "carrera": "Consultor Independiente",
        "tipo_usuario": "externo",
        "numero_cuenta": "EXT-2026-005",
    },
    {
        "id": "USR006",
        "nombre": "Sofía Hernández",
        "correo": "sofia.hernandez@lector.com",
        "telefono": "555-0106",
        "facultad": "Ciencias Sociales",
        "carrera": "Analista",
        "tipo_usuario": "interno",
        "numero_cuenta": "AFI-2026-006",
    },
    {
        "id": "USR007",
        "nombre": "Diego Sánchez",
        "correo": "diego.sanchez@lector.com",
        "telefono": "555-0107",
        "facultad": "Ingeniería y Datos",
        "carrera": "Estudiante",
        "tipo_usuario": "interno",
        "numero_cuenta": "AFI-2026-007",
    },
    {
        "id": "USR008",
        "nombre": "Valeria Gómez",
        "correo": "valeria.gomez@lector.com",
        "telefono": "555-0108",
        "facultad": "Literatura Clásica",
        "carrera": "Editora",
        "tipo_usuario": "interno",
        "numero_cuenta": "AFI-2026-008",
    },
    {
        "id": "USR009",
        "nombre": "Miguel Torres",
        "correo": "miguel.torres@lector.com",
        "telefono": "555-0109",
        "facultad": "Público General",
        "carrera": "Lector Visitante",
        "tipo_usuario": "externo",
        "numero_cuenta": "EXT-2026-009",
    },
    {
        "id": "USR010",
        "nombre": "Elena Ramírez",
        "correo": "elena.ramirez@lector.com",
        "telefono": "555-0110",
        "facultad": "Educación",
        "carrera": "Coordinadora",
        "tipo_usuario": "interno",
        "numero_cuenta": "AFI-2026-010",
    },
    {
        "id": "USR011",
        "nombre": "Fernando Morales",
        "correo": "fernando.morales@lector.com",
        "telefono": "555-0111",
        "facultad": "Arquitectura",
        "carrera": "Proyectista",
        "tipo_usuario": "interno",
        "numero_cuenta": "AFI-2026-011",
    },
    {
        "id": "USR012",
        "nombre": "Gabriela Castro",
        "correo": "gabriela.castro@lector.com",
        "telefono": "555-0112",
        "facultad": "Comunicación",
        "carrera": "Periodista",
        "tipo_usuario": "externo",
        "numero_cuenta": "EXT-2026-012",
    },
]


def limpiar_residuos_qa() -> None:
    """Elimina libros Spam/Test, cuentas qa_* y préstamos/reservas de QA."""
    # 1. Libros basura de qa_tests.py (QR0029..QR0230 o títulos Spam/Test)
    basura = Libro.query.filter(
        db.or_(Libro.titulo.in_(["Spam", "Test"]), Libro.id >= "QR0029")
    ).all()
    if basura:
        basura_ids = [b.id for b in basura]
        Reserva.query.filter(Reserva.libro_id.in_(basura_ids)).delete(synchronize_session=False)
        Prestamo.query.filter(Prestamo.libro_id.in_(basura_ids)).delete(synchronize_session=False)
        for b in basura:
            db.session.delete(b)
        print(f"[LIMPIEZA] Eliminados {len(basura)} libros basura (Spam/Test).")

    # 2. Cuentas temporales qa_* y sus logs
    qa_users = Usuario.query.filter(
        Usuario.username.in_(["qa_admin", "qa_biblio", "qa_victim", "qa_hacker"])
    ).all()
    if qa_users:
        qa_ids = [u.id for u in qa_users]
        logs_del = LogAuditoria.query.filter(LogAuditoria.usuario_id.in_(qa_ids)).delete(
            synchronize_session=False
        )
        for u in qa_users:
            db.session.delete(u)
        print(f"[LIMPIEZA] Eliminadas {len(qa_users)} cuentas QA y {logs_del} logs asociados.")

    # 3. Reservas canceladas de prueba sobre QR0001
    res_qa = Reserva.query.filter_by(libro_id="QR0001", estado="cancelada").delete(
        synchronize_session=False
    )
    if res_qa:
        print(f"[LIMPIEZA] Eliminadas {res_qa} reservas canceladas de prueba en QR0001.")

    # 4. Préstamo activo de QA en QR0004 hacia USR001
    prestamo_qa = Prestamo.query.filter_by(
        libro_id="QR0004", usuario_id="USR001", estado="activo"
    ).all()
    if prestamo_qa:
        p_ids = [p.id for p in prestamo_qa]
        Multa.query.filter(Multa.prestamo_id.in_(p_ids)).delete(synchronize_session=False)
        for p in prestamo_qa:
            db.session.delete(p)
        print(f"[LIMPIEZA] Eliminado préstamo activo de QA sobre QR0004 ({len(prestamo_qa)}).")


def restaurar_ejemplares_base() -> None:
    """Restaura QR0001..QR0028 dejando QR0003 prestado (real) y QR0008/QR0009 dañados."""
    libros = Libro.query.order_by(Libro.id).all()
    restaurados = 0
    for libro in libros:
        if libro.id in {"QR0008", "QR0009"}:
            # Conservar estado dañado realista para pruebas de mantenimiento
            libro.activo = True
            libro.estado = "dañado"
            libro.disponibles = 0
            continue
        if libro.id == "QR0003":
            # Conservar préstamo activo existente (Prestamo #12) si sigue activo
            tiene_activo = Prestamo.query.filter_by(libro_id="QR0003", estado="activo").first()
            if tiene_activo:
                libro.activo = True
                libro.estado = "prestado"
                libro.disponibles = 0
                continue

        libro.activo = True
        libro.estado = "disponible"
        libro.disponibles = 1
        libro.detalle_estado = None
        restaurados += 1
    print(f"[ACERVO] {restaurados} ejemplares base disponibles (total catálogo: {len(libros)}).")


def asegurar_cuentas_sistema() -> None:
    """Crea o actualiza las 12 cuentas del experimento con contraseña Prueba123*."""
    password_hash = generate_password_hash(PASSWORD_EXPERIMENTO)
    creadas = 0
    actualizadas = 0
    for username, role in CUENTAS_EXPERIMENTO:
        user = Usuario.query.filter_by(username=username).first()
        if user:
            user.role = role
            user.activo = True
            user.password = password_hash
            actualizadas += 1
        else:
            db.session.add(
                Usuario(username=username, password=password_hash, role=role, activo=True)
            )
            creadas += 1
    print(f"[CUENTAS] {creadas} creadas, {actualizadas} actualizadas (contraseña: {PASSWORD_EXPERIMENTO}).")


def asegurar_lectores_experimento() -> None:
    """Crea o actualiza USR001..USR012 activos, con datos genéricos y sin bloqueos."""
    lector_ids = [d["id"] for d in LECTORES_EXPERIMENTO]

    # Limpiar multas impagas o préstamos activos residuales en USR001..USR012
    prestamos_lectores = Prestamo.query.filter(Prestamo.usuario_id.in_(lector_ids)).all()
    for p in prestamos_lectores:
        if p.estado == "activo":
            p.estado = "devuelto"
            p.fecha_devolucion_real = hoy_local()
        Multa.query.filter_by(prestamo_id=p.id, pagado=False).delete(synchronize_session=False)

    creados = 0
    actualizados = 0
    for data in LECTORES_EXPERIMENTO:
        lector = UsuarioBiblioteca.query.get(data["id"])
        if lector:
            for k, v in data.items():
                setattr(lector, k, v)
            lector.activo = True
            lector.estado = "activo"
            lector.garantia_dinero = 0.0
            actualizados += 1
        else:
            db.session.add(
                UsuarioBiblioteca(
                    **data,
                    activo=True,
                    estado="activo",
                    garantia_dinero=0.0,
                )
            )
            creados += 1
    print(f"[LECTORES] {creados} creados, {actualizados} actualizados (USR001..USR012 libres de adeudos).")


def sembrar_historial_devuelto() -> None:
    """Inserta historial devuelto para USR001..USR003 (gráficas Admin + CBF+SAW)."""
    hoy = hoy_local()
    # (usuario_id, libro_id, dias_atras_salida, dias_atras_devolucion)
    plan_historial = [
        ("USR001", "QR0011", 5, 2),  # Cien años de soledad
        ("USR001", "QR0019", 4, 1),  # Rayuela
        ("USR002", "QR0015", 5, 2),  # El principito
        ("USR002", "QR0020", 3, 1),  # La Biblioteca de la Medianoche
        ("USR003", "QR0013", 4, 2),  # Don Quijote de la Mancha
        ("USR003", "QR0018", 2, 0),  # 1984
    ]

    insertados = 0
    for uid, lid, d_sal, d_dev in plan_historial:
        existe = Prestamo.query.filter_by(
            usuario_id=uid, libro_id=lid, estado="devuelto"
        ).first()
        if existe:
            continue
        libro = Libro.query.get(lid)
        if not libro:
            continue
        salida = hoy - timedelta(days=d_sal)
        esperada = salida + timedelta(days=7)
        real = hoy - timedelta(days=d_dev)
        db.session.add(
            Prestamo(
                libro_id=lid,
                usuario_id=uid,
                fecha_salida=salida,
                fecha_devolucion_esperada=esperada,
                fecha_devolucion_real=real,
                estado="devuelto",
                condicion_entrega="Excelente",
                condicion_devolucion="Excelente",
            )
        )
        libro.veces_rentado = (libro.veces_rentado or 0) + 1
        insertados += 1
    print(f"[HISTORIAL] {insertados} préstamos históricos devueltos registrados para métricas y CBF+SAW.")


def main() -> None:
    with app.app_context():
        limpiar_residuos_qa()
        db.session.flush()
        asegurar_cuentas_sistema()
        asegurar_lectores_experimento()
        restaurar_ejemplares_base()
        sembrar_historial_devuelto()
        db.session.commit()
        print("[OK] Base de datos preparada para el experimento con 12 participantes.")


if __name__ == "__main__":
    main()
