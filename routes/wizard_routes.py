from flask import Blueprint, render_template, request, session, redirect, jsonify, current_app, url_for
from werkzeug.utils import secure_filename
import os
import json
import pandas as pd
from io import BytesIO
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import shortuuid
import time
import traceback

# Importar las funciones de servicio (CLAVE)
from services import github_service as ghs
from services import firebase_service as fbs

wizard_bp = Blueprint('wizard_bp', __name__)
executor = ThreadPoolExecutor(max_workers=5)


# ----------------------------------------------------
# A. RUTAS DEL FLUJO DE PASOS (CON LÓGICA COMPLETA)
# ----------------------------------------------------

@wizard_bp.route('/', methods=['GET', 'POST'])
def step1():
    """Paso 1: Configuración inicial del sitio y subida de logo."""
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    email_session = session.get('email')
    
    if request.method == 'GET':
        # Limpiar imágenes de la sesión anterior (si existía)
        if email_session:
            ghs.limpiar_imagenes_usuario(upload_folder, email_session)

        status_pago = request.args.get('status')
        return render_template('step1.html', status_pago=status_pago)

    if request.method == 'POST':
        # 1. Recolección y guardado de datos
        email = request.form.get("email").strip().lower() # CLAVE: Email de usuario
        session['titulo'] = request.form.get("titulo") or "Mi Sitio Web"
        session['descripcion'] = request.form.get("descripcion") or "Sitio de venta"
        session['email'] = email
        
        # 2. Subida de logo
        logo = request.files.get('logo')
        if logo and logo.filename:
            filename = f"logo_{email}"
            logo.save(os.path.join(upload_folder, filename))
            session['logo'] = filename
        else:
            session['logo'] = None
            
        # 3. Generar nombre del repositorio
        session['repo_nombre'] = ghs.generar_nombre_repo(email)
        
        # 4. Redirigir al siguiente paso
        return redirect(url_for('wizard_bp.step0')) # Asumiendo step0 está definido

@wizard_bp.route('/step0', methods=['GET'])
def step0():
    return render_template('step0.html')

@wizard_bp.route('/step2', methods=['GET'])
def step2():
    return render_template('step2.html')

@wizard_bp.route('/step2-5', methods=['GET'])
def step2_5():
    return render_template('step2-5.html')

@wizard_bp.route('/contenido', methods=['GET', 'POST'])
def step3():
    """Paso 3: Subida final de contenido."""
    db_client = current_app.config.get('DB_CLIENT') 
    email = session.get("email")
    
    if not email:
        return redirect(url_for('wizard_bp.step1'))
    
    if request.method == 'POST':
        # 1. Recolección de datos (SIMPLIFICADO - DEBE COINCIDIR CON step3.html)
        productos = []
        for key in request.form:
            if key.startswith('nombre_'):
                index = key.split('_')[1]
                # Crea el diccionario de producto completo a partir de request.form
                producto = {
                    'nombre': request.form.get(f'nombre_{index}'),
                    'grupo': request.form.get(f'grupo_{index}'),
                    'subgrupo': request.form.get(f'subgrupo_{index}'),
                    'precio': request.form.get(f'precio_{index}'),
                    'talles_stock': request.form.get(f'talles_{index}'), 
                    'imagen_github': request.form.get(f'imagen_github_{index}'),
                    'id_base': request.form.get(f'id_base_{index}'),
                    'orden': request.form.get(f'orden_{index}', 9999)
                }
                productos.append(producto)

        # 2. Lógica de Subida a DB en segundo plano
        repo_name = session.get("repo_nombre")
        def subir_con_resultado(producto):
            ok = fbs.subir_a_firestore(db_client, producto, email, repo_name)
            return ok
            
        # Ejecutar y esperar la subida para asegurar que la data esté para /preview
        future = executor.submit(lambda: [subir_con_resultado(p) for p in productos])
        future.result() 
        
        # 3. Renderizar y subir el HTML a GitHub
        
        # 3.1 Cargar productos recién subidos para el renderizado (Opcional, pero más seguro)
        productos_finales, config_data = fbs.ver_productos(db_client, email)
        
        # 3.2 Renderizar el template preview.html
        html = render_template('preview.html', config=config_data, productos=productos_finales)
        
        # 3.3 Subir HTML
        ghs.subir_archivo(repo_name, html.encode('utf-8'), 'index.html')
        
        # 3.4 Subir iconos (asumiendo existen localmente)
        ghs.subir_iconos_png(repo_name, current_app.config.get('UPLOAD_FOLDER'))
        
        session['repo_creado'] = True
        return redirect('/preview')

    return render_template('step3.html')

@wizard_bp.route('/preview', methods=['GET'])
def preview_site():
    """Ruta para ver la vista previa o la tienda final (CLAVE para el problema de las tarjetas)."""
    db_client = current_app.config.get('DB_CLIENT')
    email = session.get("email") 
    
    if not email:
        return redirect(url_for('wizard_bp.step1'))

    # 1. Obtener la data
    productos, config = fbs.ver_productos(db_client, email)

    # 2. Preparar el contexto de Mercado Pago
    mp_tokens = fbs.get_mp_token(db_client, email)
    if mp_tokens:
        config['public_key'] = mp_tokens.get('public_key')
    
    # 3. Determinar Modo Admin
    modo_admin = session.get('logged_in', False) or request.args.get('admin', 'false') == 'true'

    # 4. Renderizar el template
    return render_template('preview.html', 
                           productos=productos, # Si esta lista está vacía, no se verán tarjetas
                           config=config, 
                           modoAdmin=modo_admin)

# ----------------------------------------------------
# B. RUTAS UTILITY (LÓGICA COMPLETA)
# ----------------------------------------------------

@wizard_bp.route('/upload-image', methods=['POST'])
def upload_image():
    """Ruta para subir y optimizar imágenes."""
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    repo_name = session.get("repo_nombre")
    email = session.get("email")

    if not all([repo_name, email]):
        return jsonify({"ok": False, "error": "Sesión no válida"}), 400
        
    imagen_file = request.files.get('imagen')
    if not imagen_file or not imagen_file.filename:
        return jsonify({"ok": False, "error": "No se recibió archivo"}), 400
        
    # Lógica de optimización y guardado local
    filename = secure_filename(imagen_file.filename)
    path_local = os.path.join(upload_folder, filename)
    imagen_file.save(path_local)

    # Lógica de subida a GitHub (usando el servicio)
    with open(path_local, 'rb') as f:
        contenido_bytes = f.read()
    
    resultado = ghs.subir_archivo(repo_name, contenido_bytes, f"img/{filename}")
    
    if resultado.get("ok"):
        return jsonify({"ok": True, "url": filename}) # Devuelve SÓLO el nombre del archivo
    else:
        return jsonify({"ok": False, "error": resultado.get("error")}), 500

# ... (Incluir aquí descargar_sitio y crear_repo completas)
