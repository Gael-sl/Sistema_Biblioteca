import os
import sys

# Add current directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import app
from extensions import db
from models import Libro, Prestamo

def migrate():
    with app.app_context():
        print("Iniciando migración de libros...")
        
        # Obtener el número máximo actual de código QR para continuar la numeración
        libros_todos = Libro.query.all()
        prefijo = "QR"
        existentes = []
        for l in libros_todos:
            num_part = l.id.replace(prefijo, "")
            if num_part.isdigit():
                existentes.append(int(num_part))
        
        ultimo_num = max(existentes) if existentes else 0
        
        libros_para_separar = Libro.query.filter(Libro.cantidad > 1).all()
        if not libros_para_separar:
            print("No se encontraron libros con cantidad > 1. La base de datos ya está al día.")
            return
            
        print(f"Se encontraron {len(libros_para_separar)} libros que requieren separación.")
        
        for l in libros_para_separar:
            cant_original = l.cantidad
            disp_original = l.disponibles
            prestados = cant_original - disp_original
            
            print(f"Procesando '{l.titulo}' (ID: {l.id}) - Cantidad: {cant_original}, Prestados: {prestados}")
            
            # 1. Modificar el libro original a cantidad = 1
            l.cantidad = 1
            if prestados > 0:
                l.disponibles = 0
                prestados -= 1
            else:
                l.disponibles = 1
                
            db.session.add(l)
            
            # 2. Encontrar préstamos activos para este libro
            prestamos_activos = Prestamo.query.filter_by(libro_id=l.id, estado="activo").all()
            
            # 3. Crear las copias restantes
            for i in range(1, cant_original):
                ultimo_num += 1
                nuevo_id = f"{prefijo}{ultimo_num:04d}"
                
                # Determinar si esta copia está prestada
                if prestados > 0:
                    disp = 0
                    prestados -= 1
                    
                    # Reasignar uno de los préstamos activos al nuevo ID
                    if prestamos_activos:
                        p_rebotar = prestamos_activos.pop(0)
                        p_rebotar.libro_id = nuevo_id
                        db.session.add(p_rebotar)
                        print(f"  -> Reasignando préstamo activo {p_rebotar.id} al nuevo ejemplar {nuevo_id}")
                else:
                    disp = 1
                    
                nueva_copia = Libro(
                    id=nuevo_id,
                    titulo=l.titulo,
                    autor=l.autor,
                    isbn=l.isbn,
                    genero=l.genero,
                    tags=l.tags,
                    costo=l.costo,
                    cantidad=1,
                    disponibles=disp,
                    veces_rentado=0,
                    activo=l.activo,
                    created_at=l.created_at
                )
                db.session.add(nueva_copia)
                print(f"  -> Creado ejemplar '{l.titulo}' con ID {nuevo_id} (Disponible: {disp})")
                
        db.session.commit()
        print("¡Migración completada exitosamente!")

if __name__ == "__main__":
    migrate()
