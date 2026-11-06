from flask import Blueprint

def init_app(app):
    from .auth import auth_bp
    from .admin import admin_bp
    from .libros import libros_bp
    from .prestamos import prestamos_bp
    from .public import public_bp
    from .usuarios import usuarios_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(libros_bp)
    app.register_blueprint(prestamos_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(usuarios_bp)
