from flask import Blueprint, render_template, request, session, redirect, jsonify, current_app, url_for
import os
import json
from concurrent.futures import ThreadPoolExecutor

# Importar las funciones de servicio (NO current_app, db, o sdk)
from services import github_service as ghs
from services import firebase_service as fbs

wizard_bp = Blueprint('wizard_bp', __name__)
executor = ThreadPoolExecutor(max_workers=5) # Definición local

# ----------------------------------------------------
# A. RUTAS DEL FLUJO Y PREVIEW
# ----------------------------------------------------

@wizard_bp.route('/', methods=['GET', 'POST'])
def step1():
    """Paso 1: Configuración inicial."""
    # ... (Lógica de step1) ...
    if request.method == 'POST':
        # ... (Guardar sesión y redirigir) ...
        return redirect('/step0')
    return render_template('step1.html')

@wizard_bp.route('/step0', methods=['GET'])
def step0():
    """Paso 0: Optimización de imágenes."""
    return render_template('step0.html')

@wizard_bp.route('/contenido', methods=['GET', 'POST'])
def step3():
    """Paso 3: Subida final de contenido."""
    db_client = current_app.config.get('DB_CLIENT') # Obtener el cliente
    email = session.get("email")
    
    if request.method == 'POST':
        # ... (Lógica de recolección de productos) ...
        productos = [] # Rellenar con datos de request.form

        # Lógica de Subida a DB
        repo_name = session.get("repo_nombre")
        def subir_con_resultado(producto):
            ok = fbs.subir_a_firestore(db_client, producto, email, repo_name)
            return ok
            
        future = executor.submit(lambda: [subir_con_resultado(p) for p in productos])
        future.result() # Esperar la subida
        
        # ... (Subir HTML a GitHub) ...
        
        session['repo_creado'] = True
        return redirect('/preview')

    return render_template('step3.html')


@wizard_bp.route('/preview', methods=['GET'])
def preview_site():
    """Ruta para ver la vista previa o la tienda final."""
    db_client = current_app.config.get('DB_CLIENT')
    email = session.get("email") 
    
    if not email:
        return redirect(url_for('wizard_bp.step1'))

    # 1. Obtener la data (Llama al servicio)
    productos, config = fbs.ver_productos(db_client, email)

    # 2. Preparar el contexto de Mercado Pago
    mp_tokens = fbs.get_mp_token(db_client, email)
    if mp_tokens:
        config['public_key'] = mp_tokens.get('public_key')
    
    # 3. Determinar Modo Admin
    modo_admin = session.get('logged_in', False) or request.args.get('admin', 'false') == 'true'

    # 4. Renderizar el template
    return render_template('preview.html', 
                           productos=productos, 
                           config=config, 
                           modoAdmin=modo_admin)

# ----------------------------------------------------
# B. RUTAS UTILITY
# ----------------------------------------------------

@wizard_bp.route('/upload-image', methods=['POST'])
def upload_image():
    # ... (Lógica de subida de imagen con ghs.subir_archivo) ...
    pass 

@wizard_bp.route('/crear-repo', methods=['POST'])
def crear_repo():
    # ... (Lógica de creación de repo con ghs.crear_repo_github) ...
    pass
# ... (otras utilidades) ...
