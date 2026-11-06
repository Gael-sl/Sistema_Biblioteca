import smtplib
from email.message import EmailMessage

class EmailRecomendaciones:
    def __init__(self, host, port, user, password, sender):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender or user or "noreply@biblioteca.local"

    def enviar_recomendaciones(self, to_email, usuario_nombre, recomendaciones):
        if not to_email or not recomendaciones:
            return False

        subject = "Nuevas recomendaciones de libros para ti"
        
        texto_plano = (
            f"Recomendaciones personalizadas\nSugerencias basadas en tus préstamos recientes\n\n"
            f"Hola {usuario_nombre}, aquí tienes algunas lecturas que podrían gustarte:\n\n"
        )
        for r in recomendaciones:
            score_val = r.get('score', 0)
            score_display = f"{int(score_val)}%" if score_val else "Alta"
            texto_plano += f"- {r['titulo']} por {r.get('autor', 'N/A')} ({r.get('genero', 'N/A')} - {score_display} match)\n"
            
        texto_plano += "\nPasa por la biblioteca para llevarte estos libros!\nSistema de Biblioteca"
        
        # Generar las tarjetas de libros para el HTML
        libros_html = ""
        for r in recomendaciones:
            score_val = r.get('score', 0)
            score_display = f"{int(score_val)}%" if score_val else "Alta"
            libros_html += f"""
            <div style="background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <h3 style="margin: 0 0 4px 0; color: #111827; font-size: 17px;">{r['titulo']}</h3>
                        <p style="margin: 0; color: #4b5563; font-size: 14px;">por {r.get('autor', 'N/A')}</p>
                    </div>
                    <span style="background: #e0f2fe; color: #1e40af; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap;">
                        {score_display} Match
                    </span>
                </div>
                <div style="margin-top: 10px;">
                    <span style="font-size: 13px; color: #6b7280;">Género: {r.get('genero', 'N/A')}</span>
                </div>
            </div>
            """

        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f9fafb; padding: 20px; line-height: 1.6; color: #1f2937;">
            <div style="max-width: 500px; margin: 0 auto; background: transparent;">
                <div style="text-align: center; margin-bottom: 24px;">
                    <h2 style="margin: 0; color: #111827; font-size: 22px;">Recomendaciones personalizadas</h2>
                    <p style="margin: 4px 0 0 0; color: #6b7280; font-size: 14px;">Sugerencias basadas en tus préstamos recientes</p>
                </div>
                
                <p style="margin-bottom: 20px; font-size: 15px;">Hola <strong>{usuario_nombre}</strong>, aquí tienes algunas lecturas que podrían gustarte:</p>
                
                {libros_html}
                
                <div style="text-align: center; margin-top: 32px; padding-top: 20px; border-top: 2px solid #e5e7eb;">
                    <p style="margin: 0 0 8px 0; font-weight: 600; color: #374151;">Pasa por la biblioteca para llevarte estos libros &#128516;</p>
                    <p style="margin: 0 0 4px 0; color: #111827; font-weight: bold; font-size: 14px;">Sistema de Biblioteca</p>
                    <p style="margin: 0; color: #9ca3af; font-size: 11px;">Este email fue generado automáticamente por nuestro sistema de recomendaciones</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(texto_plano)
        msg.add_alternative(html_content, subtype='html')

        import threading
        def _send_thread(host, port, user, password, msg_to_send, sub, html_fallback):
            try:
                with smtplib.SMTP(host, port) as smtp:
                    smtp.starttls()
                    smtp.login(user, password)
                    smtp.send_message(msg_to_send)
                print(f"[EMAIL SUCCESS] Enviado a {msg_to_send['To']}")
            except Exception as exc:
                print(f"[EMAIL ERROR] {exc}")
                print(f"[EMAIL STUB] Para: {msg_to_send['To']} | Asunto: {sub}\n{html_fallback}")

        threading.Thread(
            target=_send_thread,
            args=(self.host, self.port, self.user, self.password, msg, subject, html_content)
        ).start()
        return True



class EmailNotificaciones:
    def __init__(self, host, port, user, password, sender):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.sender = sender or user or "noreply@biblioteca.local"

    def enviar_aviso_vencimiento(self, to_email, usuario_nombre, libros):
        if not to_email or not libros:
            return False

        subject = "Aviso: Préstamos por vencer en la biblioteca"
        
        texto_plano = f"Hola {usuario_nombre}, te recordamos que tienes libros que están a punto de vencer o ya vencieron:\n\n"
        for libro in libros:
            texto_plano += f"- {libro['titulo']} (Fecha de devolución: {libro['fecha'].strftime('%d/%m/%Y')})\n"
        
        texto_plano += "\nPor favor devuelve o renueva tus préstamos para evitar multas.\nSistema de Biblioteca"

        libros_html = ""
        for libro in libros:
            libros_html += f"""
            <div style="background: #ffffff; border: 1px solid #fee2e2; border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                <h3 style="margin: 0 0 4px 0; color: #111827; font-size: 16px;">{libro['titulo']}</h3>
                <p style="margin: 0; color: #dc2626; font-size: 14px; font-weight: 600;">Fecha límite: {libro['fecha'].strftime('%d/%m/%Y')}</p>
            </div>
            """

        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f9fafb; padding: 20px; line-height: 1.6; color: #1f2937;">
            <div style="max-width: 500px; margin: 0 auto;">
                <div style="text-align: center; margin-bottom: 24px;">
                    <h2 style="margin: 0; color: #dc2626; font-size: 22px;">Aviso de Vencimiento</h2>
                </div>
                <p>Hola <strong>{usuario_nombre}</strong>, te recordamos que los siguientes préstamos están próximos a vencer o ya han vencido:</p>
                {libros_html}
                <p style="margin-top: 20px;">Por favor, devuelve o renueva los ejemplares lo antes posible para evitar recargos o la pérdida de tu garantía.</p>
                <div style="text-align: center; margin-top: 32px; padding-top: 20px; border-top: 2px solid #e5e7eb;">
                    <p style="margin: 0 0 4px 0; color: #111827; font-weight: bold; font-size: 14px;">Sistema de Biblioteca</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(texto_plano)
        msg.add_alternative(html_content, subtype='html')

        import threading
        def _send_thread(host, port, user, password, msg_to_send, sub, html_fallback):
            try:
                with smtplib.SMTP(host, port) as smtp:
                    smtp.starttls()
                    smtp.login(user, password)
                    smtp.send_message(msg_to_send)
                print(f"[EMAIL SUCCESS VENCIMIENTO] Enviado a {msg_to_send['To']}")
            except Exception as exc:
                print(f"[EMAIL ERROR VENCIMIENTO] {exc}")
                print(f"[EMAIL STUB VENCIMIENTO] Para: {msg_to_send['To']} | Asunto: {sub}\n{html_fallback}")

        threading.Thread(
            target=_send_thread,
            args=(self.host, self.port, self.user, self.password, msg, subject, html_content)
        ).start()
        return True

    def enviar_confirmacion_renovacion(self, to_email, usuario_nombre, libro_titulo, nueva_fecha_esperada):
        if not to_email:
            return False

        subject = "Confirmación: Renovación de libro exitosa 📚"
        
        texto_plano = (
            f"Hola {usuario_nombre},\n\n"
            f"Te confirmamos que has renovado con éxito el préstamo del libro:\n"
            f"- Título: {libro_titulo}\n"
            f"- Nueva fecha límite de devolución: {nueva_fecha_esperada.strftime('%d/%m/%Y')}\n\n"
            f"Gracias por usar nuestro servicio de biblioteca.\n\n"
            f"Sistema de Biblioteca"
        )

        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f9fafb; padding: 20px; line-height: 1.6; color: #1f2937;">
            <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div style="text-align: center; margin-bottom: 24px; border-bottom: 2px solid #3b82f6; padding-bottom: 16px;">
                    <h2 style="margin: 0; color: #2563eb; font-size: 22px;">¡Renovación Exitosa! 🎉</h2>
                </div>
                <p>Hola <strong>{usuario_nombre}</strong>,</p>
                <p>Te confirmamos que el plazo de tu préstamo ha sido extendido con éxito.</p>
                
                <div style="background: #f3f4f6; border-left: 4px solid #2563eb; border-radius: 8px; padding: 16px; margin: 20px 0;">
                    <h3 style="margin: 0 0 8px 0; color: #111827; font-size: 16px;">Detalles del Libro</h3>
                    <p style="margin: 0; color: #4b5563; font-size: 14px;"><strong>Título:</strong> {libro_titulo}</p>
                    <p style="margin: 8px 0 0 0; color: #059669; font-size: 15px; font-weight: bold;">
                        📅 Nueva Fecha Límite: {nueva_fecha_esperada.strftime('%d/%m/%Y')}
                    </p>
                </div>
                
                <p>Recuerda entregar o renovar el libro antes de la nueva fecha límite para evitar recargos en tu cuenta.</p>
                <div style="text-align: center; margin-top: 32px; padding-top: 20px; border-top: 2px solid #e5e7eb;">
                    <p style="margin: 0 0 4px 0; color: #111827; font-weight: bold; font-size: 14px;">Sistema de Biblioteca</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(texto_plano)
        msg.add_alternative(html_content, subtype='html')

        import threading
        def _send_thread(host, port, user, password, msg_to_send, sub, html_fallback):
            try:
                with smtplib.SMTP(host, port) as smtp:
                    smtp.starttls()
                    smtp.login(user, password)
                    smtp.send_message(msg_to_send)
                print(f"[EMAIL SUCCESS RENOVACION] Enviado a {msg_to_send['To']}")
            except Exception as exc:
                print(f"[EMAIL ERROR RENOVACION] {exc}")
                print(f"[EMAIL STUB RENOVACION] Para: {msg_to_send['To']} | Asunto: {sub}\n{html_fallback}")

        threading.Thread(
            target=_send_thread,
            args=(self.host, self.port, self.user, self.password, msg, subject, html_content)
        ).start()
        return True

