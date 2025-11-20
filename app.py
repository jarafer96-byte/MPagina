from flask import Flask, request, redirect, url_for, send_file, current_app
import os
import json
from datetime import datetime

# Importación de servicios y librerías
import firebase_admin
from firebase_admin import credentials, firestore
import mercadopago

# Importación de Blueprints (las rutas que moveremos)
# Nota: Necesitarás crear los archivos routes/ para que esto funcione
from routes.admin_routes import admin_bp
from routes.wizard_routes import wizard_bp
from routes.shop_routes import shop_bp # Nuevo Blueprint para pagos

# ----------------------------------------------------
# 1. INICIALIZACIÓN DE COMPONENTES GLOBALES (Mantenido aquí por su complejidad)
# ----------------------------------------------------

# 🔐 Inicialización segura de Firebase (Líneas 25-34 del original)
try:
    cred_dict = json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON"))
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase inicializado")
except Exception as e:
    print("❌ Error al cargar JSON de Firebase:", e)
    
db = firestore.client() # Cliente Firestore

# 🔑 Inicialización segura de Mercado Pago (Líneas 37-43 del original)
access_token = os.getenv("MERCADO_PAGO_TOKEN")
sdk = mercadopago.SDK(access_token.strip()) if access_token and isinstance(access_token, str) else None
if sdk:
    print("✅ SDK de Mercado Pago inicializado globalmente")
else:
    print("⚠️ MERCADO_PAGO_TOKEN no configurado, SDK no inicializado")
    
# ----------------------------------------------------
# 2. CONFIGURACIÓN DE FLASK
# ----------------------------------------------------

app = Flask(__name__)

# 🔒 CORRECCIÓN DE SEGURIDAD (WASM + Servidor)
# Línea 59 original: REDUCIDA de 200MB a 5MB
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 
app.secret_key = os.getenv("FLASK_SECRET_KEY") or "clave-secreta-temporal"
app.config['SESSION_COOKIE_SECURE'] = not app.debug

UPLOAD_FOLDER = 'static/img'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 💡 CLAVE: GUARDAR LOS CLIENTES GLOBALES EN LA CONFIGURACIÓN DEL APP
app.config['DB_CLIENT'] = db
app.config['MP_SDK'] = sdk

# ----------------------------------------------------
# 3. REGISTRO DE RUTAS (BLUEPRINTS)
# ----------------------------------------------------

# El orden no es crucial, pero es buena práctica agrupar funcionalidades.
app.register_blueprint(admin_bp)
app.register_blueprint(wizard_bp)
app.register_blueprint(shop_bp) # Registrar el nuevo Blueprint de pagos

# ----------------------------------------------------
# 4. FUNCIONES ÚNICAS DE HOOKS Y FILTROS
# ----------------------------------------------------

# Filtro imgver (Líneas 801-805 del original)
@app.template_filter('imgver')
def imgver_filter(name):
    # Necesita current_app para acceder a UPLOAD_FOLDER
    try:
        return int(os.path.getmtime(os.path.join(current_app.config['UPLOAD_FOLDER'], name))) % 10_000
    except Exception:
        return 0
        
# Handler after_request (Líneas 806-final del original)
@app.after_request
def cache(response):
    if request.path.startswith("/static/img"):
        # Establece la caché de un año para imágenes (Línea 808 original)
        one_year_seconds = 31536000
        response.headers['Cache-Control'] = f'public, max-age={one_year_seconds}, immutable'
        response.headers['Expires'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    # Previene que navegadores y proxies almacenen en caché el HTML (Líneas 811-814 original)
    if not request.path.startswith("/static/"):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
    return response

# ----------------------------------------------------
# 5. INICIO DE LA APLICACIÓN
# ----------------------------------------------------

if __name__ == '__main__':
    # Usar host='0.0.0.0' para que Render/Heroku pueda servir la aplicación
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
