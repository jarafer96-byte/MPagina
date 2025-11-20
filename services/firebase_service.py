import os
import re
import uuid
import time
import json
from firebase_admin import firestore
import mercadopago # Necesario para inicializar el SDK si se moviera, aunque aquí solo se usa el cliente db

# ----------------------------------------------------
# 1. LÓGICA DE SUBIDA DE PRODUCTOS (Líneas 76-118 del app.py original)
# ----------------------------------------------------

def subir_a_firestore(db_client: firestore.client, producto: dict, email: str, repo_name: str) -> bool:
    """Sube un producto individual a la colección de Firestore del usuario."""
    custom_id = str(uuid.uuid4())
    orden_time = time.time()
    
    doc = {
        "id_base": producto.get('id_base', custom_id),
        "repo_name": repo_name,
        "grupo": producto.get('grupo', ''),
        "subgrupo": producto.get('subgrupo', ''),
        "nombre": producto.get('nombre', 'Producto sin nombre'),
        "descripcion": producto.get('descripcion', 'Sin descripción'),
        "precio": float(producto.get('precio', 0.0)),
        "talles_stock": json.loads(producto.get('talles_stock', '{}')),
        "imagen_github": producto.get('imagen_github', ''),
        "orden": int(producto.get('orden', 9999)),
        "orden_time": orden_time
    }
    
    try:
        # Usa el cliente recibido para la transacción
        db_client.collection("usuarios").document(email).collection("productos").document(custom_id).set(doc)
        return True
    except Exception as e:
        print(f"❌ Error al subir producto {producto.get('nombre')} a Firestore: {e}")
        return False

# ----------------------------------------------------
# 2. LÓGICA DE ADMINISTRACIÓN (Líneas 400-456 del app.py original)
# ----------------------------------------------------

def crear_admin(db_client: firestore.client, usuario: str, clave: str) -> bool:
    """Crea la cuenta de administrador para el usuario en Firestore."""
    try:
        # Crea el documento en la colección 'usuarios'
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
            # Asume que la clave_admin se almacena en texto plano (como en el original)
            return data.get("clave_admin") == clave
        return False
    except Exception as e:
        print(f"❌ Error en login admin: {e}")
        return False

# ----------------------------------------------------
# 3. LÓGICA DE MERCADO PAGO (Líneas 340-377 del app.py original)
# ----------------------------------------------------

def get_mp_token(db_client: firestore.client, email: str):
    """Obtiene el token de Mercado Pago (public_key, access_token) desde Firestore."""
    try:
        if not email:
            print("⚠️ Email no disponible en sesión para buscar token MP.")
            return None

        doc_ref = db_client.collection("usuarios").document(email).collection("config").document("mercado_pago")
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            if data.get("activado"):
                return {
                    "public_key": os.getenv("MERCADO_PAGO_PUBLIC_KEY"), # O lo obtienes de donde esté configurado
                    "access_token": os.getenv("MERCADO_PAGO_TOKEN") # Usas el token de la App (Serverless)
                }
        
        # Fallback: Si no está activado, retorna solo la public_key
        return {"public_key": os.getenv("MERCADO_PAGO_PUBLIC_KEY")}

    except Exception as e:
        print("❌ Error al leer token de MP de Firestore:", e)
        # Fallback de seguridad
        return {"public_key": os.getenv("MERCADO_PAGO_PUBLIC_KEY")}

# ----------------------------------------------------
# 4. LÓGICA DE ACTUALIZACIÓN GENÉRICA (Líneas 527-543 del app.py original)
# ----------------------------------------------------

def actualizar_firestore(db_client: firestore.client, id_base: str, campos: dict, email: str) -> bool:
    """Actualiza campos específicos de un producto basado en id_base."""
    try:
        productos_ref = db_client.collection("usuarios").document(email).collection("productos")
        
        # Buscar por id_base
        query = productos_ref.where("id_base", "==", id_base).limit(1).get()
        
        if not query:
            print(f"❌ Producto con id_base {id_base} no encontrado.")
            return False
            
        # Actualizar el documento encontrado
        doc = query[0]
        doc.reference.update(campos)
        
        return True
    except Exception as e:
        print(f"❌ Error al actualizar producto {id_base}: {e}")
        return False
        
# ... (Mover aquí cualquier otra función que use db_client, como ver_productos, etc.) ...
