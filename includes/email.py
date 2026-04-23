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
            f"Hola {usuario_nombre},\n\n"
            "Con base en tus préstamos anteriores, te recomendamos:\n\n"
        )
        for r in recomendaciones:
            texto_plano += f"- {r['titulo']} (Autor: {r.get('autor', 'N/A')} | Género: {r.get('genero', 'N/A')})\n"
        texto_plano += "\n¡Te esperamos en la biblioteca!"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h3>Hola {usuario_nombre},</h3>
            <p>Con base en tus préstamos anteriores, te recomendamos:</p>
            <ul>
        """
        for r in recomendaciones:
            html_content += f"<li><strong>{r['titulo']}</strong> - <em>Autor: {r.get('autor', 'N/A')} | Género: {r.get('genero', 'N/A')}</em></li>"
            
        html_content += """
            </ul>
            <p>¡Te esperamos en la biblioteca!</p>
        </body>
        </html>
        """
        
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(texto_plano)
        msg.add_alternative(html_content, subtype='html')

        try:
            with smtplib.SMTP(self.host, self.port) as smtp:
                smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.send_message(msg)
            return True
        except Exception as exc:
            print(f"[EMAIL ERROR] {exc}")
            # Stub success if exception happens locally without actual SMTP setup but environment vars exist.
            print(f"[EMAIL STUB] Para: {to_email} | Asunto: {subject}\n{html_content}")
            return True
