import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "biblioteca.sqlite")

def run_migration():
    print(f"Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Helper to safely add column if it doesn't exist
    def add_column_if_not_exists(table, column, definition):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [info[1] for info in cursor.fetchall()]
        if column not in columns:
            print(f"Adding column '{column}' to table '{table}'...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            conn.commit()
        else:
            print(f"Column '{column}' in table '{table}' already exists.")

    try:
        # Add columns to 'libros'
        add_column_if_not_exists("libros", "estado", "TEXT DEFAULT 'disponible'")
        add_column_if_not_exists("libros", "detalle_estado", "TEXT")
        
        # Add column to 'usuarios_biblioteca'
        add_column_if_not_exists("usuarios_biblioteca", "estado", "TEXT DEFAULT 'activo'")
        
        # Add columns to 'prestamos'
        add_column_if_not_exists("prestamos", "condicion_entrega", "TEXT DEFAULT 'Excelente'")
        add_column_if_not_exists("prestamos", "condicion_devolucion", "TEXT DEFAULT 'Excelente'")
        
        # Set existing libro copy statuses based on current loans
        print("Syncing copy states based on active loans...")
        
        # Reset all libro states to disponible first
        cursor.execute("UPDATE libros SET estado = 'disponible' WHERE estado IS NULL OR estado = ''")
        conn.commit()
        
        # Find all active loans and set those books to 'prestado'
        cursor.execute("SELECT libro_id FROM prestamos WHERE estado = 'activo'")
        active_loans = cursor.fetchall()
        for (libro_id,) in active_loans:
            print(f"Setting copy {libro_id} state to 'prestado' due to active loan.")
            cursor.execute("UPDATE libros SET estado = 'prestado', disponibles = 0 WHERE id = ?", (libro_id,))
            
        # Ensure default values are filled for any nulls
        cursor.execute("UPDATE usuarios_biblioteca SET estado = 'activo' WHERE estado IS NULL OR estado = ''")
        cursor.execute("UPDATE prestamos SET condicion_entrega = 'Excelente' WHERE condicion_entrega IS NULL OR condicion_entrega = ''")
        cursor.execute("UPDATE prestamos SET condicion_devolucion = 'Excelente' WHERE condicion_devolucion IS NULL OR condicion_devolucion = ''")
        
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
