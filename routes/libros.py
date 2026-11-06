import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import db
from models import Libro, Reserva, registrar_log
from utils import login_required, is_admin, admin_required, to_int, to_float

libros_bp = Blueprint("libros", __name__)

MAX_EJEMPLARES_POR_LOTE = 100

@libros_bp.route("/inventario", methods=["GET"])
@login_required
def inventario():
    libros_db = Libro.query.filter_by(activo=True).order_by(Libro.titulo).all()
    
    grupos = {}
    for l in libros_db:
        key = (l.titulo.strip().lower(), (l.autor or "").strip().lower(), (l.isbn or "").strip())
        if key not in grupos:
            grupos[key] = {
                'id': l.id,
                'titulo': l.titulo,
                'autor': l.autor,
                'isbn': l.isbn,
                'genero': l.genero,
                'costo': l.costo,
                'tags': l.tags,
                'activo': l.activo,
                'cantidad': 0,
                'disponibles': 0,
                'danados': 0,
                'bajas': 0,
                'ids': [],
                'ejemplares': []
            }
        grupos[key]['cantidad'] += l.cantidad
        grupos[key]['disponibles'] += l.disponibles
        if l.estado == 'dañado':
            grupos[key]['danados'] += 1
        elif l.estado == 'dado_de_baja':
            grupos[key]['bajas'] += 1
            
        grupos[key]['ids'].append(l.id)
        grupos[key]['ejemplares'].append({
            'id': l.id,
            'titulo': l.titulo,
            'autor': l.autor,
            'isbn': l.isbn,
            'genero': l.genero,
            'costo': l.costo,
            'tags': l.tags,
            'cantidad': l.cantidad,
            'disponibles': l.disponibles,
            'estado': l.estado or 'disponible',
            'detalle_estado': l.detalle_estado,
            'activo': l.activo
        })
        
    libros_agrupados = list(grupos.values())

    reservas_pendientes = (
        db.session.query(Reserva.libro_id, db.func.count(Reserva.id))
        .filter(Reserva.estado == "pendiente")
        .group_by(Reserva.libro_id)
        .all()
    )
    reservas_map = {libro_id: count for libro_id, count in reservas_pendientes}
    return render_template("inventario.html", libros=libros_agrupados, reservas_map=reservas_map)

@libros_bp.route("/libros/agregar", methods=["POST"])
@login_required
def agregar_libro():
    if not is_admin():
        flash("Solo un administrador puede agregar libros", "error")
        return redirect(url_for("libros.inventario"))
    
    data = request.form
    titulo = (data.get("titulo") or "").strip()[:200]
    if not titulo:
        flash("El título del libro es obligatorio", "error")
        return redirect(url_for("libros.inventario"))
    cantidad = to_int(data.get("cantidad"), default=1, minimo=1, maximo=MAX_EJEMPLARES_POR_LOTE)
    costo_libro = to_float(data.get("costo"), default=0.0, minimo=0.0, maximo=1_000_000)
    
    try:
        prefijo = "QR"
        existentes = [
            int(libro.id.replace(prefijo, ""))
            for libro in Libro.query.filter(Libro.id.like(f"{prefijo}%")).all()
            if libro.id.replace(prefijo, "").isdigit()
        ]
        ultimo_num = max(existentes) if existentes else 0
        
        ids_creados = []
        for i in range(1, cantidad + 1):
            nuevo_num = ultimo_num + i
            nuevo_id = f"{prefijo}{nuevo_num:04d}"
            
            libro = Libro(
                id=nuevo_id,
                titulo=titulo,
                cantidad=1,
                disponibles=1,
                autor=(data.get("autor") or "").strip()[:200] or None,
                isbn=(data.get("isbn") or "").strip()[:80] or None,
                genero=(data.get("genero") or "").strip()[:120] or None,
                tags=(data.get("tags") or "").strip()[:400] or None,
                costo=costo_libro,
                estado="disponible",
                detalle_estado=None
            )
            db.session.add(libro)
            ids_creados.append(nuevo_id)
        
        registrar_log("Crear Lote", f"Se agregaron {cantidad} ejemplares de '{titulo}' (IDs: {ids_creados[0]} al {ids_creados[-1]})")
        db.session.commit()
        
        flash(f"Se han agregado {cantidad} ejemplares de '{titulo}' exitosamente.", "success")
        session['ultimos_ids_agregados'] = ids_creados
        
    except Exception as e:
        db.session.rollback()
        print(f"[AGREGAR LIBRO ERROR] {e}")
        flash("Error al agregar el lote de libros. Intenta de nuevo.", "error")
        
    return redirect(url_for("libros.inventario"))

@libros_bp.route("/admin/libros/imprimir-qr")
@login_required
def imprimir_qrs():
    ids = request.args.getlist('ids')
    if not ids:
        ids = session.get('ultimos_ids_agregados', [])
    
    if not ids:
        flash("No hay IDs seleccionados para imprimir.", "warning")
        return redirect(url_for("libros.inventario"))
        
    libros = Libro.query.filter(Libro.id.in_(ids)).all()
    return render_template("imprimir_qrs.html", libros=libros)

@libros_bp.route("/libros/<libro_id>/editar", methods=["POST"])
@admin_required
def editar_libro(libro_id: str):
    from models import Prestamo # circular import prevention
    libro = Libro.query.get(libro_id)
    if not libro:
        flash("Libro no encontrado", "error")
        return redirect(url_for("libros.inventario"))

    data = request.form
    prestados = Prestamo.query.filter_by(libro_id=libro_id, estado="activo").count()
    nueva_cantidad = to_int(data.get("cantidad"), default=libro.cantidad or 1, minimo=1, maximo=1)
    if nueva_cantidad < prestados:
        nueva_cantidad = prestados
    # Cada fila es UN ejemplar físico: su disponibilidad depende de su estado, no de lo que se teclee.
    # (Evita que un ejemplar dañado/prestado aparezca como disponible o uno sano quede "invisible").
    nuevos_disponibles = 1 if (libro.estado in (None, "", "disponible") and not prestados) else 0

    titulo = (data.get("titulo") or "").strip()
    if titulo:
        libro.titulo = titulo[:200]
    libro.autor = ((data.get("autor") or libro.autor or "").strip())[:200]
    libro.isbn = ((data.get("isbn") or libro.isbn or "").strip())[:80]
    libro.genero = (data.get("genero") or libro.genero or "")[:120]
    libro.tags = (data.get("tags") or libro.tags or "")[:400]
    libro.costo = to_float(data.get("costo"), default=libro.costo or 0.0, minimo=0.0, maximo=1_000_000)
    libro.cantidad = nueva_cantidad
    libro.disponibles = nuevos_disponibles
    nuevo_activo = bool(data.get("activo"))
    if not nuevo_activo and prestados:
        flash("No se puede desactivar un ejemplar que está prestado.", "error")
        return redirect(url_for("libros.inventario"))
    libro.activo = nuevo_activo

    registrar_log("Editar Libro", f"Libro {libro.titulo} (ID: {libro.id}) actualizado")
    db.session.commit()
    flash("Libro actualizado", "success")
    return redirect(url_for("libros.inventario"))

@libros_bp.route("/libros/<libro_id>/eliminar", methods=["POST"])
@admin_required
def eliminar_libro(libro_id: str):
    from models import Prestamo # circular import prevention
    libro = Libro.query.get(libro_id)
    if not libro:
        flash("Libro no encontrado", "error")
        return redirect(url_for("libros.inventario"))
    prestamos_activos = Prestamo.query.filter_by(libro_id=libro_id, estado="activo").count()
    if prestamos_activos > 0:
        flash("No se puede dar de baja un libro con préstamos activos", "error")
        return redirect(url_for("libros.inventario"))

    libro.activo = False
    libro.disponibles = 0
    registrar_log("Baja Libro", f"Libro {libro.titulo} (ID: {libro.id}) dado de baja")
    db.session.commit()
    flash("Libro dado de baja", "success")
    return redirect(url_for("libros.inventario"))

@libros_bp.route("/libros/<libro_id>/resolver-dano", methods=["POST"])
@login_required
def resolver_dano_libro(libro_id: str):
    from models import Prestamo  # circular import prevention
    libro = Libro.query.get(libro_id)
    if not libro:
        flash("Ejemplar no encontrado", "error")
        return redirect(url_for("libros.inventario"))

    # Solo un ejemplar DAÑADO y sin préstamo activo puede regresar a "disponible".
    # Antes se podía usar sobre un libro prestado o dado de baja -> doble renta del mismo ejemplar.
    if libro.estado != "dañado":
        flash(f"El ejemplar {libro.id} no está marcado como dañado.", "warning")
        return redirect(url_for("libros.inventario"))
    if Prestamo.query.filter_by(libro_id=libro.id, estado="activo").first():
        flash(f"El ejemplar {libro.id} tiene un préstamo activo; no se puede marcar como disponible.", "error")
        return redirect(url_for("libros.inventario"))
    
    libro.estado = "disponible"
    libro.disponibles = 1
    libro.detalle_estado = None
    
    registrar_log("Resolver Daño", f"Daño del ejemplar {libro.titulo} (ID: {libro.id}) resuelto")
    db.session.commit()
    flash(f"El ejemplar {libro.id} se ha marcado como disponible nuevamente.", "success")
    return redirect(url_for("libros.inventario"))
