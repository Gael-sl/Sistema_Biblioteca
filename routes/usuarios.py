import os
import re
import smtplib
from email.message import EmailMessage
from urllib.parse import quote
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db, csrf
from models import UsuarioBiblioteca, registrar_log
from utils import login_required

usuarios_bp = Blueprint("usuarios", __name__)

def enviar_credencial_email(usuario: UsuarioBiblioteca):
    """Envía la credencial del usuario por correo electrónico"""
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    sender = os.environ.get("SMTP_FROM", smtp_user or "noreply@biblioteca.local")

    if not all([smtp_host, smtp_user, smtp_password]):
        print("Configuración SMTP no encontrada, no se enviará correo")
        return
    
    from html import escape as _esc
    u_correo = usuario.correo
    u_nombre = _esc(usuario.nombre or "")
    u_tipo = usuario.tipo_usuario
    u_cuenta = _esc(usuario.numero_cuenta or "")
    u_id = usuario.id
    u_facultad = _esc(usuario.facultad or "")
    u_carrera = _esc(usuario.carrera or "")

    import threading
    def _send_thread():
        msg = EmailMessage()
        msg["Subject"] = "Tu Credencial de Biblioteca"
        msg["From"] = sender
        msg["To"] = u_correo

        tipo_texto = "Usuario externo" if u_tipo == "externo" else f"No. cuenta: {u_cuenta or 'N/A'}"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=140x140&data={quote(u_id)}"
        fecha_registro = datetime.now().strftime("%d/%m/%Y")
        
        html = f"""
            <html>
                <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; background-color: #f0f2f5;">
                    <p style="text-align: center; color: #666; margin-bottom: 25px;">Hola <strong>{u_nombre}</strong>, tu credencial ha sido generada exitosamente. Aquí la tienes:</p>
                    
                    <div style="max-width: 420px; margin: 0 auto; background-color: #1c212d; border-radius: 11px; overflow: hidden; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2); color: #ffffff;">
                        <!-- Header -->
                        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #242936; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding: 12px 16px;">
                            <tr>
                                <td align="left" valign="middle">
                                    <div style="font-size: 16px; font-weight: bold; color: #ffffff;">&#128214; Sistema de Biblioteca</div>
                                    <div style="font-size: 11px; color: #a9b2c3; margin-top: 2px;">Universidad</div>
                                </td>
                                <td align="right" valign="top">
                                    <div style="font-size: 8px; color: #a9b2c3; letter-spacing: 0.5px;">ESCANEAR PARA</div>
                                    <div style="font-size: 10px; font-weight: bold; color: #ffffff; letter-spacing: 0.5px;">RENTAR LIBROS</div>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Body -->
                        <div style="padding: 16px;">
                            <!-- Badge -->
                            <span style="background-color: rgba(255, 255, 255, 0.12); padding: 4px 12px; border-radius: 20px; font-size: 10px; font-weight: 600; color: #e9edf5; display: inline-block; margin-bottom: 12px;">
                                {tipo_texto}
                            </span>
                            
                            <table width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td valign="top" style="padding-right: 15px;">
                                        <h2 style="margin: 0 0 12px 0; font-size: 18px; color: #ffffff;">{u_nombre}</h2>
                                        
                                        <table width="100%" cellpadding="0" cellspacing="0" style="font-size: 11px; line-height: 1.5;">
                                            <tr>
                                                <td style="color: #a9b2c3; padding-bottom: 6px; width: 60px;">Facultad:</td>
                                                <td style="color: #ffffff; font-weight: 600; padding-bottom: 6px;">{u_facultad or 'N/A'}</td>
                                            </tr>
                                            <tr>
                                                <td style="color: #a9b2c3; padding-bottom: 6px;">Carrera:</td>
                                                <td style="color: #ffffff; font-weight: 600; padding-bottom: 6px;">{u_carrera or 'N/A'}</td>
                                            </tr>
                                            <tr>
                                                <td style="color: #a9b2c3; padding-bottom: 6px;">Email:</td>
                                                <td style="color: #ffffff; font-weight: 600; padding-bottom: 6px;">{u_correo or 'N/A'}</td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td width="110" align="center" valign="middle">
                                        <div style="background-color: #f7f7f7; padding: 6px; border-radius: 8px; display: inline-block;">
                                            <img src="{qr_url}" width="95" height="95" style="display: block; border: 0;" alt="Código QR">
                                        </div>
                                    </td>
                                </tr>
                            </table>
                            
                            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 15px; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 12px;">
                                <tr>
                                    <td align="left" valign="bottom">
                                        <div style="font-size: 8px; color: #a9b2c3; letter-spacing: 0.5px; margin-bottom: 4px;">ID DE USUARIO</div>
                                        <div style="font-size: 16px; font-weight: bold; color: #ffffff; letter-spacing: 1px;">{u_id}</div>
                                    </td>
                                    <td align="right" valign="bottom">
                                        <div style="font-size: 8px; color: #a9b2c3; letter-spacing: 0.5px; margin-bottom: 4px;">REGISTRO</div>
                                        <div style="font-size: 11px; font-weight: bold; color: #ffffff;">{fecha_registro}</div>
                                    </td>
                                </tr>
                            </table>
                        </div>
                        
                        <!-- Gold line at bottom -->
                        <table width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                                <td height="5" style="background-color: #c9b27f;"></td>
                            </tr>
                        </table>
                    </div>
                    
                    <p style="text-align: center; color: #666; font-size: 12px; margin-top: 30px;">
                        Presenta esta credencial en la biblioteca para solicitar préstamos.<br><br>
                        Este es un correo automático, por favor no respondas.
                    </p>
                </body>
            </html>
            """

        msg.set_content(
            f"Tu credencial de biblioteca\n\n"
            f"ID: {u_id}\n"
            f"Nombre: {u_nombre}\n"
            f"{tipo_texto}\n"
            f"Facultad: {u_facultad or 'No especificado'}\n"
            f"Carrera: {u_carrera or 'No especificado'}"
        )
        msg.add_alternative(html, subtype="html")

        try:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            print(f"[EMAIL CREDENCIAL SUCCESS] Enviado a {u_correo}")
        except Exception as e:
            print(f"[EMAIL CREDENCIAL ERROR] {e}")

    threading.Thread(target=_send_thread).start()


@usuarios_bp.route("/usuarios-biblioteca")
@login_required
def listar_usuarios_biblioteca():
    usuarios = UsuarioBiblioteca.query.order_by(UsuarioBiblioteca.nombre).all()
    return render_template("listar_usuarios.html", usuarios=usuarios)

@usuarios_bp.route("/usuarios-biblioteca/nuevo")
@login_required
def agregar_usuario_biblioteca():
    return render_template("agregar_usuario.html")

@usuarios_bp.route("/usuarios-biblioteca/crear", methods=["POST"])
@login_required
def crear_usuario_biblioteca():
    try:
        data = request.get_json(silent=True) or {}
        nuevo_id = (data.get("id") or "").strip()[:20]
        nombre = (data.get("nombre") or "").strip()[:120]
        correo = (data.get("correo") or "").strip()[:120]
        tipo_usuario = (data.get("tipo_usuario") or "interno").strip().lower()
        numero_cuenta = (data.get("numero_cuenta") or "").strip()
        
        if not nuevo_id or not nombre or not correo:
            return jsonify({"success": False, "message": "Faltan datos obligatorios"}), 400
        
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
            return jsonify({"success": False, "message": "El formato del correo parece inválido"}), 400
        
        if UsuarioBiblioteca.query.filter_by(id=nuevo_id).first():
            return jsonify({"success": False, "message": "Ya existe un usuario con ese ID"}), 400

        if tipo_usuario not in {"interno", "externo"}:
            return jsonify({"success": False, "message": "Tipo de usuario inválido"}), 400

        if tipo_usuario == "interno":
            if not numero_cuenta:
                return jsonify({"success": False, "message": "Número de cuenta requerido"}), 400
            if not re.match(r"^\d+(-\d)?$", numero_cuenta):
                return jsonify({"success": False, "message": "Formato de número de cuenta inválido"}), 400
        else:
            numero_cuenta = None
        
        usuario = UsuarioBiblioteca(
            id=nuevo_id,
            nombre=nombre,
            correo=correo,
            telefono=(data.get("telefono") or "").strip()[:40] or None,
            facultad=(data.get("facultad") or "").strip()[:120] or None,
            carrera=(data.get("carrera") or "").strip()[:120] or None,
            tipo_usuario=tipo_usuario,
            numero_cuenta=numero_cuenta,
            activo=True,
            estado="activo"
        )
        db.session.add(usuario)
        registrar_log("Crear Usuario", f"Usuario {usuario.nombre} (ID: {usuario.id}) registrado")
        db.session.commit()
        
        try:
            enviar_credencial_email(usuario)
        except Exception as e:
            print(f"Error al enviar correo: {e}")
        
        return jsonify({"success": True, "message": "Usuario creado exitosamente"})
    
    except Exception as e:
        db.session.rollback()
        print(f"[CREAR USUARIO ERROR] {e}")
        return jsonify({"success": False, "message": "No se pudo registrar el usuario. Intenta de nuevo."}), 500

@usuarios_bp.route("/usuarios-biblioteca/<usuario_id>/editar", methods=["POST"])
@login_required
def editar_usuario_biblioteca(usuario_id: str):
    usuario = UsuarioBiblioteca.query.get(usuario_id)
    if not usuario:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("usuarios.listar_usuarios_biblioteca"))

    data = request.form
    nuevo_correo = (data.get("correo") or "").strip()
    if nuevo_correo and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", nuevo_correo):
        flash("El formato del correo es inválido", "error")
        return redirect(url_for("usuarios.listar_usuarios_biblioteca"))
    nuevo_estado = data.get("estado") or usuario.estado or "activo"
    if nuevo_estado not in {"activo", "suspendido"}:
        flash("Estado inválido", "error")
        return redirect(url_for("usuarios.listar_usuarios_biblioteca"))

    usuario.nombre = (data.get("nombre") or usuario.nombre).strip()[:120]
    usuario.correo = nuevo_correo or usuario.correo
    usuario.telefono = (data.get("telefono") or usuario.telefono or "")[:40]
    usuario.facultad = (data.get("facultad") or usuario.facultad or "")[:120]
    usuario.carrera = (data.get("carrera") or usuario.carrera or "")[:120]
    usuario.activo = data.get("activo") == "1"
    usuario.estado = nuevo_estado
    registrar_log("Editar Usuario", f"Usuario {usuario.nombre} (ID: {usuario.id}) actualizado")
    db.session.commit()
    flash("Usuario actualizado", "success")
    return redirect(url_for("usuarios.listar_usuarios_biblioteca"))

@usuarios_bp.route("/usuarios-biblioteca/<usuario_id>/eliminar", methods=["POST"])
@login_required
def eliminar_usuario_biblioteca(usuario_id: str):
    usuario = UsuarioBiblioteca.query.get(usuario_id)
    if not usuario:
        flash("Usuario no encontrado", "error")
        return redirect(url_for("usuarios.listar_usuarios_biblioteca"))
    usuario.activo = False
    registrar_log("Baja Usuario", f"Usuario {usuario.nombre} (ID: {usuario.id}) dado de baja")
    db.session.commit()
    flash("Usuario dado de baja", "success")
    return redirect(url_for("usuarios.listar_usuarios_biblioteca"))
