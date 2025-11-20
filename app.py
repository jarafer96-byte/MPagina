import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, render_template, request, session, redirect, url_for
import mercadopago
from datetime import datetime

# Importar los Blueprints de Rutas
from routes.admin_routes import admin_bp
from routes.wizard_routes import wizard_bp
from routes.shop_routes import shop_bp 

app = Flask(__name__)

# --- Configuración y Inicialización de Clientes ---

# CLAVE para la sesión (reemplazar con valor seguro)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "CLAVE_ULTRA_SECRETA_DEV")
app.config['UPLOAD_FOLDER'] = 'static/img' # Carpeta local para subir imágenes

# Inicialización segura de Firebase
try:
    cred_dict = json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON"))
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    
    db_client = firestore.client()
    app.config['DB_CLIENT'] = db_client # Guardar el cliente en la configuración de la app
    
    print("✅ Firebase inicializado y cliente DB guardado.")
except Exception as e:
    # Este error detiene Gunicorn si la variable está mal/vacía
    print(f"❌ Error CRÍTICO al cargar JSON de Firebase: {e}") 

# Inicialización segura de Mercado Pago
access_token = os.getenv("MERCADO_PAGO_TOKEN")
if access_token and isinstance(access_token, str):
    sdk = mercadopago.SDK(access_token.strip())
    app.config['MP_SDK'] = sdk # Guardar el SDK en la configuración
    print("✅ SDK de Mercado Pago inicializado globalmente y guardado.")
else:
    app.config['MP_SDK'] = None
    print("⚠️ MERCADO_PAGO_TOKEN no configurado, SDK no inicializado.")
    
# --- Registro de Blueprints ---

app.register_blueprint(admin_bp, url_prefix='/admin') # Puedes usar un prefijo si lo deseas
app.register_blueprint(wizard_bp) # Montado en la raíz
app.register_blueprint(shop_bp) 

# --- Filtros y Handlers de bajo nivel ---

@app.template_filter('imgver')
def imgver_filter(name):
    """Filtro para añadir versión de caché a las imágenes locales."""
    try:
        # Usa el timestamp del archivo local para evitar caché
        return f"{name}?v={int(os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], name))) % 10_000}"
    except Exception:
        return name

@app.after_request
def cache(response):
    """Configura encabezados de caché para archivos estáticos."""
    if request.path.startswith("/static/img"):
        response.headers['Cache-Control'] = 'public, max-age=604800' # 1 semana
    return response

# --- Rutas de Manejo de Error/Fallback (Ejemplo) ---
@app.route('/test-db')
def test_db():
    if app.config.get('DB_CLIENT'):
        return "Conexión a Firestore OK", 200
    return "Fallo en conexión a Firestore", 500
