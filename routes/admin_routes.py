from flask import Blueprint, request, jsonify, session, current_app, redirect, url_for, render_template
import os
import json
import functools # ¡IMPORTANTE! Lo añadimos aquí

# Importar las funciones de servicio (ya modificadas para recibir db_client)
from services import firebase_service as fbs

# Inicializamos el Blueprint
admin_bp = Blueprint('admin_bp', __name__)

# ----------------------------------------------------
# A. DECORADOR CORREGIDO
# ----------------------------------------------------

def requiere_admin(f):
    """
    Decorador para asegurar que solo los admins logueados puedan usar la ruta.
    
    CLAVE: Usamos @functools.wraps(f) para preservar el nombre de la función
    original (y, por lo tanto, el nombre único del endpoint).
    """
    @functools.wraps(f) # <-- ¡Esto soluciona el AssertionError!
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            # Redireccionar al login si no está autorizado
            return redirect(url_for('admin_bp.login_admin')) 
        return f(*args, **kwargs)
    return decorated

# ----------------------------------------------------
# B. RUTAS DE AUTENTICACIÓN
# ----------------------------------------------------

@admin_bp.route('/crear-admin', methods=['POST'])
def crear_admin():
    """Ruta API para crear la clave de administrador inicial."""
    db_client = current_app.config.get('DB_CLIENT')
    data = request.get_json()
    usuario = data.get("usuario").strip().lower()
    clave = data.get("clave").strip()
    
    if not usuario or not clave:
        return jsonify({'status': 'error', 'message': 'Faltan datos de usuario/clave'}), 400
        
    if fbs.crear_admin(db_client, usuario, clave):
        return jsonify({'status': 'ok'}), 201
    else:
        return jsonify({'status': 'error', 'message': 'Error al guardar en DB'}), 500

@admin_bp.route('/login-admin', methods=['POST', 'GET']) # Permito GET para que la redirección funcione si el decorador lo pide.
def login_admin():
    """Ruta para autenticación y establecer la sesión (GET para la redirección, POST para el login)."""
    if request.method == 'GET':
        # Esta ruta puede ser llamada por el decorador si el usuario no está logueado
        # En una aplicación real, se renderizaría un formulario de login aquí.
        # Por ahora, simplemente redirige al inicio, donde está el formulario.
        return redirect(url_for('wizard_bp.step1', error='Necesita iniciar sesión'))

    if request.method == 'POST':
        db_client = current_app.config.get('DB_CLIENT')
        
        # Asumiendo que el login POST viene del formulario en step1 (con campos correctos)
        # Nota: La ruta original usaba request.form, ajusto para que funcione
        usuario = request.form.get("usuario_admin").strip().lower()
        clave = request.form.get("clave_admin").strip()
        
        if fbs.login_admin(db_client, usuario, clave):
            session['logged_in'] = True
            session['email'] = usuario
            return redirect(url_for('wizard_bp.preview_site', admin='true')) # Redirijo a la vista previa en modo admin
        else:
            return redirect(url_for('wizard_bp.step1', error='login')) # Fallo: retorna al inicio con error

@admin_bp.route('/logout-admin', methods=['GET'])
@requiere_admin # Uso el decorador para forzar la sesión
def logout_admin():
    """Cierra la sesión de administrador."""
    session.pop('logged_in', None)
    session.pop('email', None)
    return redirect(url_for('wizard_bp.preview_site')) # Redirijo a la vista previa normal

# ----------------------------------------------------
# C. RUTAS DE ACTUALIZACIÓN DE PRODUCTOS
# ----------------------------------------------------

@admin_bp.route('/actualizar-precio', methods=['POST'])
@requiere_admin
def actualizar_precio():
    """API para actualizar precio o stock (desde el modo admin de preview.html)."""
    db_client = current_app.config.get('DB_CLIENT')
    email = session.get("email")

    data = request.get_json()
    id_base = data.get("id")
    nuevo_precio_raw = data.get("nuevoPrecio")
    
    campos_a_actualizar = {}

    # Lógica de precio
    if nuevo_precio_raw is not None:
        try:
            # Asegurar que el precio es un float
            campos_a_actualizar['precio'] = float(nuevo_precio_raw) 
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Precio inválido'}), 400

    # Lógica de stock
    nuevo_stock = data.get("nuevoStock")
    if nuevo_stock is not None:
        # Se espera un JSON de talles/stock (e.g., {"S": 10, "M": 5})
        try:
             campos_a_actualizar['talles_stock'] = json.loads(nuevo_stock) 
        except json.JSONDecodeError:
             return jsonify({'status': 'error', 'message': 'Formato de stock JSON inválido'}), 400
        
    if not campos_a_actualizar:
        return jsonify({'status': 'ok', 'message': 'Nada que actualizar'}), 200

    # Llama al servicio
    if fbs.actualizar_firestore(db_client, id_base, campos_a_actualizar, email):
        return jsonify({'status': 'ok'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Error al actualizar producto'}), 500


@admin_bp.route('/actualizar-talle', methods=['POST'])
@requiere_admin
def actualizar_talle():
    """API para actualizar talles/stock específicos."""
    db_client = current_app.config.get('DB_CLIENT')
    email = session.get("email")
    data = request.get_json()

    id_base = data.get("id")
    # Los datos de talle y stock ya deberían estar dentro del campo 'nuevoStock' 
    # de actualizar_precio, pero mantengo esta ruta si se usa independientemente.
    nuevo_stock_json = data.get("nuevoStock") 
    
    if not all([id_base, nuevo_stock_json]):
         return jsonify({'status': 'error', 'message': 'Faltan datos (id, nuevoStock)'}), 400

    try:
        stock_data = json.loads(nuevo_stock_json)
    except json.JSONDecodeError:
        return jsonify({'status': 'error', 'message': 'Formato de stock JSON inválido'}), 400

    # Se asume que el cliente envía el objeto talles_stock completo y actualizado
    if fbs.actualizar_firestore(db_client, id_base, {'talles_stock': stock_data}, email):
         return jsonify({'status': 'ok'}), 200
    else:
         return jsonify({'status': 'error', 'message': 'Error al actualizar talles'}), 500
