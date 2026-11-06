# 📚 Sistema Inteligente de Gestión de Biblioteca

¡Bienvenido al **Sistema de Gestión de Biblioteca**! Una aplicación web de última generación diseñada con una estética de **vidrio líquido (Liquid Glass UI)**, pensada para ofrecer una experiencia de usuario premium, fluida e interactiva.

Este sistema implementa un robusto backend modular con **Flask Blueprints**, bases de datos transaccionales, colas de tareas asíncronas para el envío de correos electrónicos y algoritmos avanzados de recomendación de libros basados en IA.

---

## ✨ Características Principales

### 💎 Interfaz de Usuario Premium (Liquid Glass UI)
- **Estética Ultra-Moderna**: Bordes redondeados suavizados (12px - 24px), sombras difusas tridimensionales, efectos de desenfoque de fondo (`backdrop-filter`) y paleta de colores curada y armónica (Dark Mode elegante).
- **Animaciones Sutiles**: Micro-interacciones y transiciones fluidas en botones, tarjetas y menús que hacen sentir la aplicación viva y responsiva.

### ⚡ Rendimiento y Arquitectura
- **Modularidad Completa**: Arquitectura desacoplada mediante **Flask Blueprints** dividida en dominios lógicos de negocio (`auth`, `admin`, `libros`, `prestamos`, `usuarios`, `public`).
- **Emails Asíncronos**: Envío de correos de credenciales, sugerencias de libros y notificaciones en segundo plano mediante hilos independientes (`threading.Thread`). ¡Cero esperas en el navegador!
- **Transaccionalidad Atómica**: Toda operación de préstamo y devolución se ejecuta en bloques atómicos controlados. Si un paso falla, la base de datos se revierte automáticamente a su estado original (sin inconsistencias de stock).

### 🔍 Gestión Inteligente
- **Préstamo de Múltiples Libros**: Selección masiva de libros mediante interfaz dinámica tipo check-list con cálculos automáticos de depósitos en garantía (20% del costo total).
- **Recomendaciones con Inteligencia Artificial**: Algoritmo que analiza los géneros y autores más leídos por el usuario para predecir y sugerir nuevos ejemplares personalizados.
- **Recordatorios Automáticos**: Tareas programadas en background con `APScheduler` que corren diariamente a las 8:00 AM para enviar alertas de vencimiento por correo electrónico.
- **Reportería Masiva en un Clic**: Exportación instantánea de bases de datos completas de Inventario, Multas y Préstamos directamente a archivos formateados de **Microsoft Excel** usando `openpyxl`.

---

## 🛠️ Requisitos del Sistema

Para ejecutar este proyecto de forma local, asegúrate de tener instalado:
* **Python 3.10** o superior.
* **SQLite 3** (manejado automáticamente por SQLAlchemy).

---

## 🚀 Instalación y Primer Arranque

Sigue estos sencillos pasos para levantar el servidor local en menos de 3 minutos:

### 1. Clonar el repositorio y acceder a la carpeta
```bash
git clone <url-del-repositorio>
cd Sistema_Biblioteca
```

### 2. Configurar el Entorno Virtual (`virtualenv`)
Es altamente recomendable aislar las dependencias:
```bash
# Crear el entorno virtual
python -m venv .venv

# Activar el entorno virtual (Windows Powershell)
.\.venv\Scripts\Activate.ps1

# Activar el entorno virtual (Windows CMD)
.\.venv\Scripts\activate.bat

# Activar el entorno virtual (Linux/macOS)
source .venv/bin/activate
```

### 3. Instalar Dependencias
Instala todas las librerías oficiales con sus versiones exactas y validadas:
```bash
pip install -r requirements.txt
```

### 4. Configurar el Archivo `.env`
Crea un archivo llamado `.env` en la raíz del proyecto y define los siguientes parámetros:

```env
# Clave secreta para la encriptación de cookies y sesiones Flask
SECRET_KEY=clave_secreta_super_segura_de_tu_eleccion

# Configuración del servidor de correo SMTP (Ejemplo con Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=tu_contraseña_de_aplicacion
SMTP_FROM=tu_correo@gmail.com
SMTP_SENDER="Biblioteca Universitaria"
```

> 💡 **Nota:** Si las credenciales SMTP no están definidas o son incorrectas, el sistema no se detendrá; imprimirá de manera segura las credenciales de prueba y los correos simulados en la consola del servidor (modo Fallback).

---

## 🚦 Ejecución del Servidor

Para iniciar la aplicación, ejecuta el siguiente comando con el entorno virtual activo:

```bash
python app.py
```

El servidor web se iniciará en modo de desarrollo en la dirección:  
👉 **`http://127.0.0.1:5000`**

Al iniciarse por primera vez, el sistema creará automáticamente la base de datos `biblioteca.sqlite` e inyectará semillas de datos de prueba completos (libros de muestra, alumnos pre-registrados y cuentas del personal).

---

## 🔑 Credenciales de Acceso (Semillas de Prueba)

Usa estas cuentas de demostración generadas automáticamente al arrancar la app:

| Rol | Usuario | Contraseña | Permisos |
|---|---|---|---|
| **Administrador** | `admin` | `admin123` | Control total del sistema, logs, configuraciones y exportaciones. |
| **Bibliotecario** | `bibliotecario` | `biblio123` | Registro de rentas, devoluciones, usuarios e inventario. |

---

## 📂 Arquitectura de Directorios

El código está estructurado bajo las mejores prácticas de la ingeniería de software:

```text
Sistema_Biblioteca/
│
├── app.py                  # Punto de entrada principal y configuración base del servidor
├── extensions.py           # Declaración y puente de base de datos y token CSRF
├── models.py               # Modelos relacionales SQLAlchemy (Base de datos transaccional)
├── utils.py                # Decoradores de autenticación y funciones globales auxiliares
├── requirements.txt        # Dependencias oficiales validadas del proyecto
│
├── routes/                 # Lógica modular del negocio (Flask Blueprints)
│   ├── __init__.py         # Inicializador y registro de los blueprints
│   ├── auth.py             # Módulo de sesión de usuarios del personal
│   ├── public.py           # Módulo de catálogo público y menú principal
│   ├── libros.py           # Módulo de inventario y etiquetas QR
│   ├── usuarios.py         # Módulo de registro de alumnos y credenciales digitales
│   ├── prestamos.py        # Módulo de control de préstamos, multas y recomendaciones
│   └── admin.py            # Módulo del panel de control de administración y reportes
│
├── includes/               # Componentes auxiliares de lógica compleja
│   ├── recomendaciones.py  # Algoritmo heurístico de IA para emparejamiento de libros
│   └── email.py            # Plantillas Liquid Glass y conectores para correos
│
├── static/                 # Recursos web frontend
│   ├── css/                # Diseño Liquid Glass exclusivo (biblioteca.css)
│   └── js/                 # Interactividad de gráficos Chart.js y autocompletes
│
└── templates/              # Vistas HTML con inyección dinámica Jinja2
```

---

## 🛡️ Seguridad e Integridad del Código
* **Protección CSRF**: Todos los formularios y transacciones asíncronas vía AJAX cuentan con tokens de seguridad dinámicos para evitar ataques de falsificación de petición en sitios cruzados.
* **Encriptación Hashing**: Ninguna contraseña se almacena en texto plano; se utiliza encriptación de grado militar mediante el algoritmo `scrypt` provisto por `Werkzeug`.
* **Auditoría Interna**: Toda acción crítica realizada por el personal (dar de baja un libro, realizar préstamos, registrar cobros de multas) queda registrada permanentemente en la base de datos de auditoría con fecha y firma de usuario para transparencia operativa.

---
Elaborado con dedicación y enfoque en la excelencia operativa. 📖✨
