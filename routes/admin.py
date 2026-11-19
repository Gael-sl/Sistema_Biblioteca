import os
import re
import json
import io
import openpyxl
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from sqlalchemy import desc, func
from extensions import db
from models import Usuario, UsuarioBiblioteca, Prestamo, Multa, Libro, Recomendacion, LogAuditoria, Configuracion, registrar_log
from utils import admin_required, login_required, hoy as hoy_local, ZONAS_HORARIAS_PERMITIDAS

admin_bp = Blueprint("admin", __name__)

def get_config_map() -> dict:
    rows = Configuracion.query.all()
    return {row.clave: row.valor for row in rows}

@admin_bp.route("/")
@admin_required
def admin_panel():
    config = get_config_map()
    hoy = hoy_local()
    
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


@admin_bp.route("/usuarios", methods=["POST"])
@admin_required
def crear_usuario_sistema():
    from werkzeug.security import generate_password_hash # circular prevention
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    role = request.form.get("role") or "bibliotecario"

    if not username or not password:
        flash("Usuario y contraseña son obligatorios", "error")
        return redirect(url_for("admin.admin_panel"))

    error = _validar_empleado(username, password, role)
    if error:
        flash(error, "error")
        return redirect(url_for("admin.admin_panel"))

    if Usuario.query.filter(Usuario.username.ilike(username)).first():
        flash("El nombre de usuario ya existe", "error")
        return redirect(url_for("admin.admin_panel"))

    user = Usuario(username=username, password=generate_password_hash(password), role=role)
    db.session.add(user)
    registrar_log("Crear Empleado", f"Empleado '{username}' creado con rol {role}")
    db.session.commit()
    flash("Usuario creado", "success")
    return redirect(url_for("admin.admin_panel"))


ROLES_VALIDOS = {"admin", "bibliotecario"}
MIN_PASSWORD = 8


def _validar_empleado(username, password, role):
    """Devuelve un mensaje de error o None si los datos son válidos."""
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,40}", username or ""):
        return "El usuario debe tener 3-40 caracteres (letras, números, punto, guion o guion bajo)."
    if role not in ROLES_VALIDOS:
        return "Rol inválido."
    if password is not None and len(password) < MIN_PASSWORD:
        return f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres."
    return None


@admin_bp.route("/usuarios/<int:user_id>/editar", methods=["POST"])
@admin_required
def editar_usuario_sistema(user_id: int):
    from werkzeug.security import generate_password_hash
    user = Usuario.query.get(user_id)
    if not user:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("admin.admin_panel"))

    nuevo_username = (request.form.get("username") or user.username).strip()
    nuevo_role = request.form.get("role") or user.role
    nueva_clave = request.form.get("password") or None

    error = _validar_empleado(nuevo_username, nueva_clave, nuevo_role)
    if error:
        flash(error, "error")
        return redirect(url_for("admin.admin_panel"))

    # No dejar el sistema sin administradores
    if user.role == "admin" and nuevo_role != "admin":
        if Usuario.query.filter_by(role="admin", activo=True).count() <= 1:
            flash("Debe quedar al menos un administrador activo", "error")
            return redirect(url_for("admin.admin_panel"))

    existente = Usuario.query.filter(Usuario.username.ilike(nuevo_username)).first()
    if existente and existente.id != user.id:
        flash("Ya existe otro usuario con ese nombre", "error")
        return redirect(url_for("admin.admin_panel"))

    cambios = []
    if user.username != nuevo_username:
        cambios.append(f"usuario {user.username}->{nuevo_username}")
    if user.role != nuevo_role:
        cambios.append(f"rol {user.role}->{nuevo_role}")
    if nueva_clave:
        cambios.append("contraseña cambiada")

    user.username = nuevo_username
    user.role = nuevo_role
    if nueva_clave:
        user.password = generate_password_hash(nueva_clave)

    registrar_log("Editar Empleado", f"Empleado #{user.id}: " + (", ".join(cambios) or "sin cambios"))
    db.session.commit()
    flash("Usuario actualizado", "success")
    return redirect(url_for("admin.admin_panel"))


@admin_bp.route("/usuarios/<int:user_id>/eliminar", methods=["POST"])
@admin_required
def eliminar_usuario_sistema(user_id: int):
    if session.get("user_id") == user_id:
        flash("No puedes eliminar tu propio usuario", "error")
        return redirect(url_for("admin.admin_panel"))

    user = Usuario.query.get(user_id)
    if not user:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("admin.admin_panel"))

    if user.role == "admin":
        admins = Usuario.query.filter_by(role="admin").count()
        if admins <= 1:
            flash("Debe quedar al menos un administrador", "error")
            return redirect(url_for("admin.admin_panel"))

    registrar_log("Eliminar Empleado", f"Empleado '{user.username}' (rol {user.role}) eliminado")
    db.session.delete(user)
    db.session.commit()
    flash("Usuario eliminado", "success")
    return redirect(url_for("admin.admin_panel"))


# Reglas de validación de la configuración: (tipo, mínimo, máximo, etiqueta)
REGLAS_CONFIG = {
    "dias_prestamo": (int, 1, 90, "Días de préstamo"),
    "limite_libros": (int, 1, 20, "Límite de libros por usuario"),
    "multa_retraso": (float, 0, 10000, "Multa por día de retraso"),
    "multa_leve": (float, 0, 10000, "Multa por daño leve"),
    "multa_moderado": (float, 0, 10000, "Multa por daño moderado"),
    "multa_grave": (float, 0, 10000, "Multa por daño grave"),
}


@admin_bp.route("/configuracion", methods=["POST"])
@admin_required
def guardar_configuracion():
    nuevos = {}
    for param, (tipo, minimo, maximo, etiqueta) in REGLAS_CONFIG.items():
        valor = request.form.get(param)
        if valor is None:
            continue
        try:
            numero = float(str(valor).strip().replace(",", ""))
            if tipo is int:
                if numero != int(numero):
                    raise ValueError
                numero = int(numero)
        except (ValueError, OverflowError):
            flash(f"{etiqueta}: '{valor}' no es un número válido. No se guardaron cambios.", "error")
            return redirect(url_for("admin.admin_panel"))
        if numero != numero or not (minimo <= numero <= maximo):
            flash(f"{etiqueta} debe estar entre {minimo} y {maximo}. No se guardaron cambios.", "error")
            return redirect(url_for("admin.admin_panel"))
        nuevos[param] = f"{numero:.2f}" if tipo is float else str(numero)

    zona = request.form.get("zona_horaria")
    if zona is not None:
        zona = str(zona).strip()
        if zona not in ZONAS_HORARIAS_PERMITIDAS:
            flash("Zona horaria inválida. No se guardaron cambios.", "error")
            return redirect(url_for("admin.admin_panel"))
        nuevos["zona_horaria"] = zona

    try:
        for param, valor in nuevos.items():
            config_row = Configuracion.query.filter_by(clave=param).first()
            if config_row:
                config_row.valor = valor
            else:
                db.session.add(Configuracion(clave=param, valor=valor))
        registrar_log("Configuración", ", ".join(f"{k}={v}" for k, v in nuevos.items()))
        db.session.commit()
        flash("Configuración actualizada correctamente", "success")
    except Exception as e:
        db.session.rollback()
        print(f"[CONFIG ERROR] {e}")
        flash("Error al actualizar configuración", "error")
    
    return redirect(url_for("admin.admin_panel"))


@admin_bp.route("/exportar/prestamos")
@admin_required
def exportar_prestamos():
    return _generar_reporte_excel("prestamos")


@admin_bp.route("/exportar/multas")
@admin_required
def exportar_multas():
    return _generar_reporte_excel("multas")


@admin_bp.route("/exportar/inventario")
@admin_required
def exportar_inventario():
    return _generar_reporte_excel("inventario")


@admin_bp.route("/exportar/reporte")
@admin_required
def exportar_reporte():
    tipo = (request.args.get("tipo") or "completo").strip().lower()
    if tipo not in {"completo", "prestamos", "multas", "inventario"}:
        flash("Tipo de reporte inválido.", "error")
        return redirect(url_for("admin.admin_panel"))
    return _generar_reporte_excel(tipo)


def _parse_fecha_arg(valor: str | None):
    raw = (valor or "").strip()
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _autoajustar_hoja(ws):
    from openpyxl.styles import Font, PatternFill

    header_fill = PatternFill(start_color="141413", end_color="141413", fill_type="solid")
    header_font = Font(bold=True, color="FAF9F5")
    title_font = Font(bold=True, size=11, color="C6613F")

    if ws.max_row >= 1:
        ws.cell(row=1, column=1).font = title_font
    if ws.max_row >= 2:
        for cell in ws[2]:
            cell.fill = header_fill
            cell.font = header_font

    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.row == 1:
                continue
            val = str(cell.value or "")
            if len(val) > max_len:
                max_len = len(val)
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 14), 45)


def _llenar_hoja_prestamos(ws, prestamos, etiqueta_periodo: str):
    ws.append([f"Reporte de Préstamos — {etiqueta_periodo}"])
    ws.append(["ID Préstamo", "Lector", "ID Lector", "Libro", "ID Ejemplar", "Fecha Salida", "Fecha Límite", "Fecha Devolución Real", "Estado"])
    for p in prestamos:
        ws.append([
            p.id,
            p.usuario.nombre if p.usuario else "N/A",
            p.usuario_id,
            p.libro.titulo if p.libro else "N/A",
            p.libro_id,
            p.fecha_salida.strftime("%Y-%m-%d") if p.fecha_salida else "",
            p.fecha_devolucion_esperada.strftime("%Y-%m-%d") if p.fecha_devolucion_esperada else "",
            p.fecha_devolucion_real.strftime("%Y-%m-%d") if p.fecha_devolucion_real else "Pendiente",
            p.estado,
        ])
    _autoajustar_hoja(ws)


def _llenar_hoja_multas(ws, multas, etiqueta_periodo: str):
    ws.append([f"Reporte de Multas — {etiqueta_periodo}"])
    ws.append(["ID Multa", "Lector", "Libro", "Fecha Préstamo", "Tipo", "Monto ($)", "Motivo", "Estado"])
    for m in multas:
        p = m.prestamo
        ws.append([
            m.id,
            p.usuario.nombre if p and p.usuario else "N/A",
            p.libro.titulo if p and p.libro else "N/A",
            p.fecha_salida.strftime("%Y-%m-%d") if p and p.fecha_salida else "",
            m.tipo or "",
            float(m.monto or 0),
            m.descripcion or "",
            "Pagado" if m.pagado else "Pendiente",
        ])
    _autoajustar_hoja(ws)


def _llenar_hoja_inventario(ws, libros, rentas_periodo: dict, etiqueta_periodo: str):
    ws.append([f"Inventario y Movimientos — {etiqueta_periodo}"])
    ws.append(["ID", "Título", "Autor", "ISBN", "Género", "Cantidad", "Disponibles", "Costo ($)", "Rentas en Periodo", "Rentas Históricas", "Estado"])
    for l in libros:
        ws.append([
            l.id,
            l.titulo,
            l.autor,
            l.isbn or "",
            l.genero or "",
            l.cantidad,
            l.disponibles,
            float(l.costo or 0),
            rentas_periodo.get(l.id, 0),
            l.veces_rentado or 0,
            l.estado,
        ])
    _autoajustar_hoja(ws)


def _generar_reporte_excel(tipo: str):
    try:
        fecha_inicio = _parse_fecha_arg(request.args.get("fecha_inicio"))
        fecha_fin = _parse_fecha_arg(request.args.get("fecha_fin"))
    except ValueError:
        flash("Formato de fecha inválido. Usa AAAA-MM-DD.", "error")
        return redirect(url_for("admin.admin_panel"))

    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        flash("La fecha de inicio no puede ser posterior a la fecha final.", "error")
        return redirect(url_for("admin.admin_panel"))

    if fecha_inicio and fecha_fin:
        etiqueta_periodo = f"Del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"
        sufijo = f"{fecha_inicio.strftime('%Y-%m-%d')}_a_{fecha_fin.strftime('%Y-%m-%d')}"
    elif fecha_inicio:
        etiqueta_periodo = f"Desde el {fecha_inicio.strftime('%d/%m/%Y')}"
        sufijo = f"desde_{fecha_inicio.strftime('%Y-%m-%d')}"
    elif fecha_fin:
        etiqueta_periodo = f"Hasta el {fecha_fin.strftime('%d/%m/%Y')}"
        sufijo = f"hasta_{fecha_fin.strftime('%Y-%m-%d')}"
    else:
        etiqueta_periodo = "Todo el historial"
        sufijo = "completo"

    q_prestamos = Prestamo.query.order_by(desc(Prestamo.fecha_salida), desc(Prestamo.id))
    q_multas = Multa.query.join(Prestamo, Multa.prestamo_id == Prestamo.id).order_by(desc(Multa.id))
    q_conteo = db.session.query(Prestamo.libro_id, func.count(Prestamo.id))

    if fecha_inicio:
        q_prestamos = q_prestamos.filter(Prestamo.fecha_salida >= fecha_inicio)
        q_multas = q_multas.filter(Prestamo.fecha_salida >= fecha_inicio)
        q_conteo = q_conteo.filter(Prestamo.fecha_salida >= fecha_inicio)
    if fecha_fin:
        q_prestamos = q_prestamos.filter(Prestamo.fecha_salida <= fecha_fin)
        q_multas = q_multas.filter(Prestamo.fecha_salida <= fecha_fin)
        q_conteo = q_conteo.filter(Prestamo.fecha_salida <= fecha_fin)

    wb = openpyxl.Workbook()
    ws = wb.active

    if tipo == "prestamos":
        ws.title = "Préstamos"
        _llenar_hoja_prestamos(ws, q_prestamos.all(), etiqueta_periodo)
        filename = f"prestamos_{sufijo}.xlsx"
    elif tipo == "multas":
        ws.title = "Multas"
        _llenar_hoja_multas(ws, q_multas.all(), etiqueta_periodo)
        filename = f"multas_{sufijo}.xlsx"
    elif tipo == "inventario":
        ws.title = "Inventario"
        rentas_periodo = {lid: int(cnt) for lid, cnt in q_conteo.group_by(Prestamo.libro_id).all()}
        _llenar_hoja_inventario(ws, Libro.query.order_by(Libro.titulo).all(), rentas_periodo, etiqueta_periodo)
        filename = f"inventario_{sufijo}.xlsx"
    else:
        prestamos_list = q_prestamos.all()
        multas_list = q_multas.all()
        libros_list = Libro.query.order_by(Libro.titulo).all()
        rentas_periodo = {lid: int(cnt) for lid, cnt in q_conteo.group_by(Prestamo.libro_id).all()}

        ws.title = "Resumen"
        ws.append([f"Resumen Estadístico — {etiqueta_periodo}"])
        ws.append(["Indicador", "Valor"])
        ws.append(["Periodo consultado", etiqueta_periodo])
        ws.append(["Total de préstamos en periodo", len(prestamos_list)])
        ws.append(["Préstamos activos del periodo", sum(1 for p in prestamos_list if p.estado == "activo")])
        ws.append(["Préstamos devueltos del periodo", sum(1 for p in prestamos_list if p.estado == "devuelto")])
        ws.append(["Multas generadas en periodo", len(multas_list)])
        ws.append(["Monto total en multas ($)", round(sum(float(m.monto or 0) for m in multas_list), 2)])
        ws.append(["Ejemplares registrados en catálogo", len(libros_list)])
        _autoajustar_hoja(ws)

        ws_p = wb.create_sheet("Préstamos")
        _llenar_hoja_prestamos(ws_p, prestamos_list, etiqueta_periodo)

        ws_m = wb.create_sheet("Multas")
        _llenar_hoja_multas(ws_m, multas_list, etiqueta_periodo)

        ws_i = wb.create_sheet("Inventario")
        _llenar_hoja_inventario(ws_i, libros_list, rentas_periodo, etiqueta_periodo)
        filename = f"reporte_biblioteca_{sufijo}.xlsx"

    registrar_log("Exportar Reporte", f"Reporte '{tipo}' ({etiqueta_periodo})")
    db.session.commit()

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, download_name=filename, as_attachment=True)


@admin_bp.route("/logs")
@admin_required
def admin_logs():
    logs = (
        db.session.query(LogAuditoria, Usuario)
        .outerjoin(Usuario, LogAuditoria.usuario_id == Usuario.id)
        .order_by(desc(LogAuditoria.fecha))
        .limit(200)
        .all()
    )
    return render_template("admin_logs.html", logs=logs)
