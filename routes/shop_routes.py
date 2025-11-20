from flask import Blueprint, request, jsonify, redirect, url_for, current_app
import os

# shop_bp no necesita importar servicios si solo maneja redirecciones/webhooks
shop_bp = Blueprint('shop_bp', __name__)

@shop_bp.route('/success', methods=['GET'])
def mp_success():
    """Callback de éxito de Mercado Pago."""
    # Redirige a la preview con un mensaje de pago OK
    return redirect('/preview?pago=ok')

@shop_bp.route('/failure', methods=['GET'])
def mp_failure():
    """Callback de fallo de Mercado Pago."""
    return redirect('/preview?pago=fail')

@shop_bp.route('/pending', methods=['GET'])
def mp_pending():
    """Callback de pago pendiente de Mercado Pago."""
    return redirect('/preview?pago=pending')

@shop_bp.route('/webhook_mp', methods=['POST'])
def webhook_mp():
    """Manejo de notificaciones de Mercado Pago."""
    # En el código original, esta lógica usaba el SDK (sdk.payment().get).
    # Aquí accedemos al SDK desde la configuración de la app.
    sdk = current_app.config.get('MP_SDK')
    # ... (Lógica para procesar el webhook y actualizar el estado de pago) ...
    
    # Debe devolver un 200 OK para que Mercado Pago no reintente.
    return jsonify({'status': 'ok'}), 200
