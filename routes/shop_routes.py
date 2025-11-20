from flask import Blueprint, request, redirect, url_for, current_app, jsonify
import os
import json
import traceback

# El Blueprint para todas las rutas de la tienda y pagos
shop_bp = Blueprint('shop_bp', __name__)

# ----------------------------------------------------
# A. RUTAS DE CALLBACK DE MERCADO PAGO
# (Líneas 380-396 del app.py original)
# ----------------------------------------------------

@shop_bp.route('/success', methods=['GET'])
def success():
    # Redirige al front-end con un mensaje de éxito
    return redirect(url_for('wizard_bp.step1', _external=True) + '?status=success')

@shop_bp.route('/failure', methods=['GET'])
def failure():
    # Redirige al front-end con un mensaje de fallo
    return redirect(url_for('wizard_bp.step1', _external=True) + '?status=failure')

@shop_bp.route('/pending', methods=['GET'])
def pending():
    # Redirige al front-end con un mensaje de pendiente
    return redirect(url_for('wizard_bp.step1', _external=True) + '?status=pending')

# ----------------------------------------------------
# B. RUTA CRÍTICA DEL WEBHOOK (Notificaciones de Pago)
# (Líneas 398-418 del app.py original)
# ----------------------------------------------------

@shop_bp.route('/webhook_mp', methods=['POST'])
def webhook_mp():
    # 1. Obtener los clientes de la configuración global
    sdk = current_app.config.get('MP_SDK')
    db_client = current_app.config.get('DB_CLIENT')

    if not sdk or not db_client:
        print("❌ WEBHOOK: Clientes de SDK o DB no inicializados. Abortando.")
        return jsonify(status="error", message="Server Misconfiguration"), 500

    try:
        data = request.get_json()
        print(f"🔔 WEBHOOK RECIBIDO: Tipo={data.get('type')}, ID={data.get('data', {}).get('id')}")

        if data.get('type') == 'payment':
            payment_id = data.get('data', {}).get('id')
            
            # 2. Consultar el pago a Mercado Pago
            payment_info = sdk.payment().get(payment_id)

            if payment_info["status"] == 200:
                payment = payment_info["response"]
                # Obtener el email del usuario desde los metadatos
                email = payment["external_reference"]
                status = payment["status"]

                if status == 'approved':
                    # 3. Actualizar el estado del token en Firestore
                    mp_config_ref = db_client.collection("usuarios").document(email).collection("config").document("mercado_pago")
                    mp_config_ref.update({"activado": True, "token_mp": payment.get("collector_id")})
                    print(f"✅ WEBHOOK: Token activado y guardado para {email}")
                
                # Para otros estados (rejected, pending) no hacemos nada crucial aquí.
                
                return jsonify(status="ok"), 200
            else:
                print(f"❌ WEBHOOK: Error al consultar pago {payment_id}. Status: {payment_info['status']}")
                return jsonify(status="error", message="MP query failed"), 400
        
        # Ignorar otros tipos de notificaciones
        return jsonify(status="ok", message="Notification type ignored"), 200

    except Exception as e:
        print(f"💥 WEBHOOK: Excepción inesperada: {e}")
        print(traceback.format_exc())
        return jsonify(status="error", message=str(e)), 500
