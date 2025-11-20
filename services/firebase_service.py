import os
import uuid
import time
import json
from firebase_admin import firestore
# No necesitamos importar mercadopago aquí, solo el cliente firestore

# ----------------------------------------------------
# A. LÓGICA DE LECTURA DE PRODUCTOS Y CONFIGURACIÓN
# ----------------------------------------------------

def ver_productos(db_client: firestore.client, email: str):
    """Obtiene todos los productos y configuraciones para renderizar la tienda."""
    try:
        if not email:
            return [], {}
            
        productos_ref = db_client.collection("usuarios").document(email).collection("productos")
        productos = [doc.to_dict() for doc in productos_ref.order_by("orden_time").stream()]

        config_ref = db_client.collection("usuarios").document(email).collection("config").document("general")
        config = config_ref.get().to_dict() if config_ref.exists else {}

        return productos, config
    except Exception as e:
        print(f"❌ Error al obtener productos/configuración para {email}: {e}")
        return [], {}

def get_mp_token(db_client: firestore.client, email: str):
    """Obtiene el token de Mercado Pago (public_key) desde variables de entorno."""
    # En esta versión simplificada, se lee directo de env, no de DB
    return {"public_key": os.getenv("MERCADO_PAGO_PUBLIC_KEY")}

# ----------------------------------------------------
# B. LÓGICA DE ESCRITURA DE PRODUCTOS Y ADMIN
# ----------------------------------------------------

def subir_a_firestore(db_client: firestore.client, producto: dict, email: str, repo_name: str) -> bool:
    """Sube un producto individual a la colección de Firestore del usuario."""
    custom_id = str(uuid.uuid4())
    orden_time = time.time()
    
    doc = {
        # ... (Definición del documento) ...
        "id_base": producto.get('id_base', custom_id),
        "repo_name": repo_name,
        "nombre": producto.get('nombre', 'Producto sin nombre'),
        "precio": float(producto.get('precio', 0.0)),
        "orden_time": orden_time
    }
    
    try:
        db_client.collection("usuarios").document(email).collection("productos").document(custom_id).set(doc)
        return True
    except Exception as e:
        # Esto es crucial para la depuración
        print(f"❌ ERROR EN FIRESTORE (subir_a_firestore): {e}") 
        return False

def crear_admin(db_client: firestore.client, usuario: str, clave: str) -> bool:
    """Crea la cuenta de administrador para el usuario en Firestore."""
    try:
        db_client.collection("usuarios").document(usuario).set({"clave_admin": clave})
        return True
    except Exception as e:
        print(f"❌ Error al crear admin {usuario}: {e}")
        return False

def login_admin(db_client: firestore.client, usuario: str, clave: str) -> bool:
    """Verifica las credenciales de administrador."""
    try:
        doc = db_client.collection("usuarios").document(usuario).get()
        if doc.exists:
            data = doc.to_dict()
            return data.get("clave_admin") == clave
        return False
    except Exception as e:
        print(f"❌ Error en login admin: {e}")
        return False

def actualizar_firestore(db_client: firestore.client, id_base: str, campos: dict, email: str) -> bool:
    """Actualiza campos específicos de un producto basado en id_base."""
    try:
        productos_ref = db_client.collection("usuarios").document(email).collection("productos")
        query = productos_ref.where("id_base", "==", id_base).limit(1).get()
        
        if not query:
            return False
            
        doc = query[0]
        doc.reference.update(campos)
        
        return True
    except Exception as e:
        print(f"❌ Error al actualizar producto {id_base}: {e}")
        return False
