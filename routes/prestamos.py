import os
import json
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from sqlalchemy import desc
from extensions import db
from models import Libro, UsuarioBiblioteca, Prestamo, Multa, Recomendacion, Reserva, registrar_log
from utils import login_required, admin_required, hoy as hoy_local, to_int

prestamos_bp = Blueprint("prestamos", __name__)

def get_config_map() -> dict:
    from models import Configuracion # circular import prevention
    rows = Configuracion.query.all()
    return {row.clave: row.valor for row in rows}

def generar_recomendaciones(usuario_id: str, limite: int = 3, enviar_correo: bool = False):
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
            try:
                email_sistema = EmailRecomendaciones(host, port, user, password, sender)
                enviado = email_sistema.enviar_recomendaciones(usuario.correo, usuario.nombre, recomendaciones)
                if enviado:
                    nueva_rec.email_enviado = True
            except Exception as email_exc:
                print(f"[RECOMENDACION EMAIL ERROR] {email_exc}")

        db.session.commit()

    return recomendaciones


@prestamos_bp.route("/renta", methods=["GET", "POST"])
@login_required
def renta():
    config = get_config_map()
    libros = (
        Libro.query.filter_by(activo=True)
        .filter(Libro.disponibles > 0, Libro.estado == "disponible")
        .order_by(Libro.titulo)
        .all()
    )
    show_ticket = False
    prestamo = None
    prestamos_creados = []
    usuario_data = None
    libro_data = None
    error = None

    if request.method == "POST" and request.form.get("confirmar_prestamo"):
        usuario_id = (request.form.get("usuario_id") or "").strip()
        libro_ids = request.form.getlist("libro_id")
        if not libro_ids:
            libro_id_real = request.form.get("libro_id_real")
            if libro_id_real:
                libro_ids = [libro_id_real]
                
        usuario_data = UsuarioBiblioteca.query.filter_by(id=usuario_id, activo=True).first()
        
        if not usuario_data or not libro_ids:
            error = "Usuario o libros no seleccionados."
        else:
            if usuario_data.estado == "suspendido":
                error = "El usuario se encuentra suspendido. No se permiten nuevos préstamos."
            else:
                multas_pendientes = (
                    db.session.query(Multa)
                    .join(Prestamo, Multa.prestamo_id == Prestamo.id)
                    .filter(Prestamo.usuario_id == usuario_id, Multa.pagado == False)
                    .count()
                )
                if multas_pendientes > 0:
                    error = "El usuario tiene multas pendientes de pago. No se permiten nuevos préstamos."
                else:
                    limite = to_int(config.get("limite_libros"), default=3, minimo=1)
                    prestamos_activos = Prestamo.query.filter_by(usuario_id=usuario_id, estado="activo").count()
                    
                    if prestamos_activos + len(libro_ids) > limite:
                        error = f"El usuario excedería el límite de {limite} libros. (Tiene {prestamos_activos}, intenta rentar {len(libro_ids)})"
                    else:
                        try:
                            dias_prestamo = to_int(config.get("dias_prestamo"), default=7, minimo=1)
                            fecha_salida = hoy_local()
                            fecha_devolucion = fecha_salida + timedelta(days=dias_prestamo)
                            
                            for l_id in libro_ids:
                                l_id = l_id.strip()
                                if not l_id: continue
                                
                                libro_data = Libro.query.filter_by(id=l_id, activo=True).filter(Libro.disponibles > 0, Libro.estado == "disponible").first()
                                if not libro_data:
                                    raise Exception(f"Libro {l_id} no disponible o no existe.")
                                    
                                prestamo_duplicado = Prestamo.query.filter_by(usuario_id=usuario_id, libro_id=l_id, estado="activo").first()
                                if prestamo_duplicado:
                                    raise Exception(f"El usuario ya tiene un préstamo activo del libro {libro_data.titulo}.")

                                garantia = libro_data.costo * 0.20
                                
                                prestamo = Prestamo(
                                    libro_id=l_id,
                                    usuario_id=usuario_id,
                                    fecha_salida=fecha_salida,
                                    fecha_devolucion_esperada=fecha_devolucion,
                                    estado="activo",
                                    condicion_entrega=libro_data.detalle_estado or "Excelente"
                                )
                                libro_data.disponibles = 0
                                libro_data.estado = "prestado"
                                libro_data.veces_rentado += 1
                                usuario_data.garantia_dinero += garantia
                                
                                db.session.add(prestamo)
                                prestamos_creados.append(prestamo)
                                registrar_log("Préstamo", f"Libro {libro_data.titulo} rentado a {usuario_data.nombre}")

                            db.session.flush()
                            db.session.commit()
                            
                            if prestamos_creados:
                                prestamo = prestamos_creados[0]
                                libro_data = prestamo.libro
                                show_ticket = True

                            try:
                                generar_recomendaciones(usuario_id, enviar_correo=True)
                            except Exception as rec_exc:
                                print(f"[RECOMENDACIONES ERROR] {rec_exc}")

                        except Exception as exc:
                            db.session.rollback()
                            error = f"Error al procesar préstamo: {exc}"

    return render_template(
        "renta.html",
        libros=libros,
        config=config,
        show_ticket=show_ticket,
        prestamo=prestamo,
        prestamos=prestamos_creados,
        usuario=usuario_data,
        libro=libro_data,
        error=error,
    )


@prestamos_bp.route("/admin/recomendaciones", methods=["GET", "POST"])
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


@prestamos_bp.route("/devoluciones", methods=["GET"])
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


@prestamos_bp.route("/devoluciones/procesar", methods=["POST"])
@login_required
def procesar_devolucion():
    prestamo_id = request.form.get("prestamo_id")
    estado_libro = request.form.get("estado_libro", "sin_dano")
    observaciones = request.form.get("observaciones", "").strip()[:250]
    usuario_id = request.form.get("usuario_id")

    if estado_libro not in {"sin_dano", "leve", "moderado", "grave"}:
        flash("Estado del libro inválido", "error")
        return redirect(url_for("prestamos.devoluciones"))

    prestamo = Prestamo.query.filter_by(id=prestamo_id, estado="activo").first()
    if not prestamo:
        flash("Préstamo no encontrado", "error")
        return redirect(url_for("prestamos.devoluciones"))

    try:
        fecha_real = hoy_local()
        prestamo.estado = "devuelto"
        prestamo.fecha_devolucion_real = fecha_real

        config = get_config_map()
        multa_total = 0.0
        dias_retraso = 0
        if prestamo.fecha_devolucion_esperada:
            dias_retraso = (fecha_real - prestamo.fecha_devolucion_esperada).days
        if dias_retraso > 0:
            multa_retraso = float(config.get("multa_retraso", 0) or 0)
            multa_total += dias_retraso * multa_retraso

        multa_dano = 0.0
        if estado_libro in {"leve", "moderado", "grave"}:
            clave = f"multa_{estado_libro}"
            multa_dano = float(config.get(clave, 0) or 0)
            if estado_libro == "grave":
                libro_costo = float(prestamo.libro.costo or 0)
                multa_dano += libro_costo
            multa_total += multa_dano

        if multa_total > 0:
            tipo = "retraso" if estado_libro == "sin_dano" else "daño"
            detalles = []
            if dias_retraso > 0:
                detalles.append(f"Retraso de {dias_retraso} días")
            if multa_dano:
                detalles.append(f"Daño {estado_libro}")
            descripcion = (observaciones + " | " if observaciones else "") + ", ".join(detalles)
            db.session.add(
                Multa(
                    prestamo_id=prestamo.id,
                    tipo=tipo,
                    monto=multa_total,
                    descripcion=descripcion,
                    pagado=False
                )
            )

        libro_costo = float(prestamo.libro.costo or 0)
        if prestamo.usuario and libro_costo:
            garantia_libro = libro_costo * 0.20
            prestamo.usuario.garantia_dinero = max(
                0, prestamo.usuario.garantia_dinero - garantia_libro
            )

        # ILS Damage State Machine
        if estado_libro == "sin_dano":
            prestamo.libro.estado = "disponible"
            prestamo.libro.detalle_estado = None
            prestamo.libro.disponibles = 1
            prestamo.condicion_devolucion = "Excelente"

            # Check and trigger pending reservations only if returned without damage
            reserva = Reserva.query.filter_by(libro_id=prestamo.libro.id, estado="pendiente").order_by(Reserva.fecha_reserva).first()
            if reserva:
                reserva.estado = "activa"
                prestamo.libro.disponibles = 0
                registrar_log("Reserva Activada", f"Libro {prestamo.libro.titulo} asignado a reserva de usuario {reserva.usuario.nombre}")
                flash(f"¡Atención! Este libro tiene una reserva pendiente para: {reserva.usuario.nombre}", "info")
        else:
            prestamo.libro.disponibles = 0
            prestamo.usuario.estado = "suspendido"
            if estado_libro in {"leve", "moderado"}:
                prestamo.libro.estado = "dañado"
                prestamo.libro.detalle_estado = observaciones or f"Daño {estado_libro}"
                prestamo.condicion_devolucion = "Dañado Parcial"
            else: # grave
                prestamo.libro.estado = "dado_de_baja"
                prestamo.libro.detalle_estado = observaciones or "Dado de baja por daño grave"
                prestamo.condicion_devolucion = "Dañado Total"

        db.session.flush()
        db.session.commit()
        flash("Devolución procesada", "success")
    except Exception as exc:
        db.session.rollback()
        print(f"[DEVOLUCION ERROR] {exc}")
        flash("Error al procesar la devolución. No se guardó ningún cambio.", "error")

    return redirect(url_for("prestamos.devoluciones"))


@prestamos_bp.route("/api/usuario/garantia")
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


@prestamos_bp.route("/api/libros/<libro_id>")
@login_required
def api_libro_info(libro_id: str):
    libro_id = (libro_id or "").strip()
    if not libro_id:
        return jsonify({"success": False, "error": "Código inválido"}), 400
    libro = Libro.query.filter_by(id=libro_id).first()
    if not libro or not libro.activo:
        return jsonify({"success": False, "error": "Libro no encontrado"}), 404

    # Check if this specific copy has an active loan
    en_prestamo = Prestamo.query.filter_by(
        libro_id=libro.id, estado="activo"
    ).first() is not None

    estado = libro.estado or "disponible"
    puede_rentar = (estado == "disponible") and not en_prestamo

    return jsonify(
        {
            "success": True,
            "libro": {
                "id": libro.id,
                "titulo": libro.titulo,
                "autor": libro.autor,
                "isbn": libro.isbn,
                "genero": libro.genero,
                "disponibles": int(libro.disponibles or 0),
                "cantidad": int(libro.cantidad or 0),
                "estado": estado,
                "detalle_estado": libro.detalle_estado or "",
                "en_prestamo_activo": en_prestamo,
                "puede_rentar": puede_rentar,
            },
        }
    )


@prestamos_bp.route("/api/usuarios/buscar")
@login_required
def api_usuarios_buscar():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    resultados = (
        UsuarioBiblioteca.query
        .filter(
            UsuarioBiblioteca.activo == True,
            (UsuarioBiblioteca.nombre.ilike(f"%{q}%")) |
            (UsuarioBiblioteca.id.ilike(f"%{q}%"))
        )
        .order_by(UsuarioBiblioteca.nombre)
        .limit(8)
        .all()
    )
    return jsonify([
        {
            "id": u.id,
            "nombre": u.nombre,
            "facultad": u.facultad or "",
            "carrera": u.carrera or "",
            "estado": u.estado or "activo",
            "multas_pendientes": (
                db.session.query(Multa)
                .join(Prestamo, Multa.prestamo_id == Prestamo.id)
                .filter(Prestamo.usuario_id == u.id, Multa.pagado == False)
                .count()
            ),
            "prestamos_activos": Prestamo.query.filter_by(usuario_id=u.id, estado="activo").count(),
        }
        for u in resultados
    ])


@prestamos_bp.route("/usuarios-biblioteca/<usuario_id>/historial")
@login_required
def historial_usuario(usuario_id):
    usuario = UsuarioBiblioteca.query.get_or_404(usuario_id)
    prestamos = (
        db.session.query(Prestamo, Libro)
        .join(Libro, Prestamo.libro_id == Libro.id)
        .filter(Prestamo.usuario_id == usuario_id)
        .order_by(desc(Prestamo.fecha_salida))
        .all()
    )
    
    prestamos_ids = [p[0].id for p in prestamos]
    multas = Multa.query.filter(Multa.prestamo_id.in_(prestamos_ids)).all() if prestamos_ids else []
    
    multas_map = {}
    for m in multas:
        if m.prestamo_id not in multas_map:
            multas_map[m.prestamo_id] = []
        multas_map[m.prestamo_id].append(m)
        
    return render_template("historial_usuario.html", 
                           usuario=usuario, 
                           prestamos=prestamos, 
                           multas_map=multas_map)


@prestamos_bp.route("/multas/<int:multa_id>/pagar", methods=["POST"])
@login_required
def pagar_multa(multa_id):
    multa = Multa.query.get_or_404(multa_id)
    if multa.pagado:
        flash("Esta multa ya ha sido pagada.", "warning")
    else:
        multa.pagado = True
        registrar_log("Pago Multa", f"Multa #{multa.id} de ${multa.monto:.2f} pagada")
        
        # Check if user has other unpaid fines and reactive user if they were suspended
        usuario = multa.prestamo.usuario
        multas_pendientes = (
            db.session.query(Multa)
            .join(Prestamo, Multa.prestamo_id == Prestamo.id)
            .filter(Prestamo.usuario_id == usuario.id, Multa.pagado == False)
            .count()
        )
        if multas_pendientes == 0 and usuario.estado == "suspendido":
            usuario.estado = "activo"
            registrar_log("Usuario Reactivado", f"Usuario {usuario.nombre} reactivado automáticamente al liquidar todas sus multas")
            flash(f"El usuario {usuario.nombre} ha sido reactivado automáticamente al no contar con adeudos.", "info")
            
        db.session.commit()
        flash(f"Pago de multa ${multa.monto:.2f} registrado con éxito.", "success")
    
    return redirect(request.referrer or url_for("public.menu"))


@prestamos_bp.route("/api/libros/<libro_id>/prestamo-actual")
@login_required
def api_libro_prestamo_actual(libro_id):
    prestamos_activos = (
        db.session.query(Prestamo, UsuarioBiblioteca)
        .join(UsuarioBiblioteca, Prestamo.usuario_id == UsuarioBiblioteca.id)
        .filter(Prestamo.libro_id == libro_id, Prestamo.estado == "activo")
        .all()
    )
    
    if not prestamos_activos:
        return jsonify({"success": True, "prestamos": []})
        
    return jsonify({
        "success": True,
        "prestamos": [
            {
                "usuario_id": u.id,
                "usuario_nombre": u.nombre,
                "fecha_salida": p.fecha_salida.strftime("%d/%m/%Y"),
                "fecha_esperada": p.fecha_devolucion_esperada.strftime("%d/%m/%Y"),
                "vencido": p.fecha_devolucion_esperada < hoy_local()
            }
            for p, u in prestamos_activos
        ]
    })


@prestamos_bp.route("/prestamos/<int:prestamo_id>/renovar", methods=["POST"])
@login_required
def renovar_prestamo(prestamo_id):
    prestamo = Prestamo.query.get_or_404(prestamo_id)
    
    if prestamo.estado != "activo":
        flash("Solo se pueden renovar préstamos activos.", "error")
        return redirect(request.referrer or url_for("public.menu"))
        
    # 1. Validar mermas: Si hay reservas pendientes de este libro, bloquear renovación
    reserva = Reserva.query.filter_by(libro_id=prestamo.libro_id, estado="pendiente").first()
    if reserva:
        flash("No se puede renovar este libro porque está reservado por otro estudiante.", "error")
        return redirect(request.referrer or url_for("public.menu"))

    # 2. Validar mermas: Si el usuario tiene multas pendientes de pago, bloquear renovación
    multas_pendientes = (
        db.session.query(Multa)
        .join(Prestamo, Multa.prestamo_id == Prestamo.id)
        .filter(Prestamo.usuario_id == prestamo.usuario_id, Multa.pagado == False)
        .count()
    )
    if multas_pendientes > 0:
        flash("No se puede renovar. El usuario tiene multas pendientes de pago.", "error")
        return redirect(request.referrer or url_for("public.menu"))

    # 2.5 Validar si el usuario está suspendido
    if prestamo.usuario.estado == "suspendido":
        flash("No se puede renovar. El usuario se encuentra suspendido.", "error")
        return redirect(request.referrer or url_for("public.menu"))

    hoy = hoy_local()
    
    # 3. Validar mermas: Si el préstamo ya está vencido, cobrar los días de retraso hasta hoy
    if prestamo.fecha_devolucion_esperada < hoy:
        dias_retraso = (hoy - prestamo.fecha_devolucion_esperada).days
        if dias_retraso > 0:
            config = get_config_map()
            multa_retraso = float(config.get("multa_retraso", 0) or 0)
            monto_multa = dias_retraso * multa_retraso
            if monto_multa > 0:
                # Registrar multa por el retraso acumulado hasta hoy
                db.session.add(
                    Multa(
                        prestamo_id=prestamo.id,
                        tipo="retraso",
                        monto=monto_multa,
                        descripcion=f"Recargo por retraso de {dias_retraso} días previo a la renovación",
                    )
                )
                # Descontar de la garantía del usuario
                prestamo.usuario.garantia_dinero = max(0, prestamo.usuario.garantia_dinero - monto_multa)
                flash(f"Se ha registrado una multa de ${monto_multa:.2f} por los {dias_retraso} días de retraso acumulados antes de la renovación.", "warning")

    # 4. Calcular nueva fecha de devolución esperada (7 días extra)
    dias_extra = 7
    base_fecha = max(prestamo.fecha_devolucion_esperada, hoy)
    nueva_fecha = base_fecha + timedelta(days=dias_extra)
    
    prestamo.fecha_devolucion_esperada = nueva_fecha
    
    registrar_log("Renovación", f"Préstamo #{prestamo.id} renovado hasta {nueva_fecha.strftime('%d/%m/%Y')}")
    db.session.commit()
    
    # 5. Enviar correo de confirmación de renovación de forma asíncrona
    if prestamo.usuario.correo:
        from includes.email import EmailNotificaciones
        host = os.environ.get("SMTP_HOST")
        user = os.environ.get("SMTP_USER")
        password = os.environ.get("SMTP_PASSWORD")
        port = int(os.environ.get("SMTP_PORT", 587))
        sender = os.environ.get("SMTP_FROM", user or "noreply@biblioteca.local")
        
        if host and user and password:
            try:
                email_notif = EmailNotificaciones(host, port, user, password, sender)
                email_notif.enviar_confirmacion_renovacion(
                    prestamo.usuario.correo,
                    prestamo.usuario.nombre,
                    prestamo.libro.titulo,
                    nueva_fecha
                )
            except Exception as e:
                print(f"[RENEWAL EMAIL ERROR] {e}")

    flash(f"Préstamo renovado con éxito. Nueva fecha: {nueva_fecha.strftime('%d/%m/%Y')}", "success")
    return redirect(request.referrer or url_for("public.menu"))


@prestamos_bp.route("/reservas")
@login_required
def listar_reservas():
    reservas = (
        db.session.query(Reserva, UsuarioBiblioteca, Libro)
        .join(UsuarioBiblioteca, Reserva.usuario_id == UsuarioBiblioteca.id)
        .join(Libro, Reserva.libro_id == Libro.id)
        .order_by(desc(Reserva.fecha_reserva))
        .all()
    )
    return render_template("reservas.html", reservas=reservas)


@prestamos_bp.route("/api/reservas/crear", methods=["POST"])
@login_required
def crear_reserva():
    try:
        data = request.get_json()
        usuario_id = data.get("usuario_id")
        libro_id = data.get("libro_id")
        
        if not usuario_id or not libro_id:
            return jsonify({"success": False, "message": "Datos incompletos"}), 400
            
        libro = Libro.query.get(libro_id)
        if not libro:
            return jsonify({"success": False, "message": "Libro no encontrado"}), 404
            
        if libro.disponibles > 0:
            return jsonify({"success": False, "message": "El libro está disponible, puedes rentarlo directamente."}), 400
            
        usuario = UsuarioBiblioteca.query.get(usuario_id)
        if not usuario:
            return jsonify({"success": False, "message": "Usuario no encontrado"}), 404
            
        reserva_existente = Reserva.query.filter_by(usuario_id=usuario_id, libro_id=libro_id, estado="pendiente").first()
        if reserva_existente:
            return jsonify({"success": False, "message": "El usuario ya tiene una reserva pendiente para este libro."}), 400
            
        nueva_reserva = Reserva(usuario_id=usuario_id, libro_id=libro_id)
        db.session.add(nueva_reserva)
        registrar_log("Reserva", f"Usuario {usuario.nombre} reservó {libro.titulo}")
        db.session.commit()
        return jsonify({"success": True, "message": "Reserva creada exitosamente"})
    except Exception as e:
        db.session.rollback()
        print(f"[RESERVA ERROR] {e}")
        return jsonify({"success": False, "message": "No se pudo crear la reserva."}), 500


@prestamos_bp.route("/reservas/<int:reserva_id>/cancelar", methods=["POST"])
@login_required
def cancelar_reserva(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    if reserva.estado in ['pendiente', 'activa']:
        estaba_activa = reserva.estado == 'activa'
        reserva.estado = "cancelada"
        if estaba_activa and reserva.libro and reserva.libro.estado == "disponible":
            # El ejemplar estaba apartado: vuelve a quedar libre para renta
            reserva.libro.disponibles = 1
        registrar_log("Cancelar Reserva", f"Reserva #{reserva.id} cancelada")
        db.session.commit()
        flash("Reserva cancelada", "success")
    return redirect(url_for('prestamos.listar_reservas'))
