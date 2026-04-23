import re
import os
import sys

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

match = re.search(r"def generar_recomendaciones.*?return recomendaciones", content, re.DOTALL)
if match:
    old_code = match.group(0)
    new_code = """def generar_recomendaciones(usuario_id: str, limite: int = 5, enviar_correo: bool = False):
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

    return recomendaciones"""
    
    content = content.replace(old_code, new_code)
    
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Code replaced successfully.")
else:
    print("Could not find the function to replace.")