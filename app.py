from flask import Flask, request, redirect, url_for, send_file, current_app, render_template
import os
import json
from datetime import datetime

# Importación de servicios y librerías
import firebase_admin
from firebase_admin import credentials, firestore
import mercadopago

# Importación de Blueprints (Rutas)
from routes.admin_routes import admin_bp
from routes.wizard_routes import wizard_bp
from routes.shop_routes import shop_bp 

# ----------------------------------------------------
# 1. INICIALIZACIÓN DE COMPONENTES GLOBALES
# ----------------------------------------------------

# 🔐 Inicialización segura de Firebase
try:
    cred_dict = json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON"))
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db_client = firestore.client()
    print("✅ Firebase inicializado")
except Exception as e:
    db_client = None
    print(f"❌ Error CRÍTICO al cargar JSON de Firebase: {e}") 
    
# 🔑 Inicialización segura de Mercado Pago
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

# Configuración de seguridad y directorios
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 
app.secret_key = os.getenv("FLASK_SECRET_KEY") or "clave-secreta-temporal"
app.config['SESSION_COOKIE_SECURE'] = not app.debug
app.config['UPLOAD_FOLDER'] = 'static/img'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 💡 CLAVE: GUARDAR LOS CLIENTES GLOBALES
app.config['DB_CLIENT'] = db_client
app.config['MP_SDK'] = sdk

# ----------------------------------------------------
# 3. REGISTRO DE RUTAS (BLUEPRINTS)
# ----------------------------------------------------

app.register_blueprint(admin_bp)
app.register_blueprint(wizard_bp)
app.register_blueprint(shop_bp) 

# ----------------------------------------------------
# 4. FUNCIONES ÚNICAS DE HOOKS Y FILTROS
# ----------------------------------------------------

# Filtro imgver
@app.template_filter('imgver')
def imgver_filter(name):
    # Usa current_app para acceder a UPLOAD_FOLDER
    try:
        return int(os.path.getmtime(os.path.join(current_app.config['UPLOAD_FOLDER'], name))) % 10_000
    except Exception:
        return 0
        
# Handler after_request
@app.after_request
def cache(response):
    if request.path.startswith("/static/img"):
        one_year_seconds = 31536000
        response.headers['Cache-Control'] = f'public, max-age={one_year_seconds}, immutable'
        response.headers['Expires'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    if not request.path.startswith("/static/"):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
    return response

# ----------------------------------------------------
# 5. INICIO DE LA APLICACIÓN
# ----------------------------------------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
