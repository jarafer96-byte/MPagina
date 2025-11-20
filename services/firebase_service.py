import os
import re
import uuid
import time
import json
from firebase_admin import firestore
from firebase_admin.exceptions import FirebaseError

# ----------------------------------------------------
# A. LÓGICA DE LECTURA (CLAVE PARA EL PROBLEMA DE LAS TARJETAS)
# ----------------------------------------------------

def ver_productos(db_client: firestore.client, email: str):
    """Obtiene todos los productos y configuraciones para renderizar la tienda."""
    if not db_client:
        print("❌ Error: Cliente DB no inicializado.")
        return [], {}
        
    try:
        if not email:
            return [], {}
            
        productos_ref = db_client.collection("usuarios").document(email).collection("productos")
        
        # Obtener productos ordenados por 'orden_time' (o como se prefiera)
        productos = [doc.to_dict() for doc in productos_ref.order_by("orden_time").stream()]

        # Obtener la configuración general
        config_ref = db_client.collection("usuarios").document(email).collection("config").document("general")
        config = config_ref.get().to_dict() if config_ref.exists else {}

        print(f"✅ DB: {len(productos)} productos y {len(config)} items de config cargados para {email}.")

        return productos, config
    except FirebaseError as e:
        print(f"❌ Error de Firebase al obtener productos/configuración para {email}: {e}")
        return [], {}
    except Exception as e:
        print(f"❌ Error al obtener productos/configuración para {email}: {e}")
        return [], {}

def get_mp_token(db_client: firestore.client, email: str):
    """Obtiene el token público de Mercado Pago."""
    # En esta versión simplificada, se lee directo de env y solo comprueba si el usuario activó la tienda (opcional)
    return {"public_key": os.getenv("MERCADO_PAGO_PUBLIC_KEY")}


# ----------------------------------------------------
# B. LÓGICA DE ESCRITURA Y ADMIN
# ----------------------------------------------------

def subir_a_firestore(db_client: firestore.client, producto: dict, email: str, repo_name: str) -> bool:
    """Sube un producto individual a la colección de Firestore del usuario."""
    if not db_client: return False
    
    custom_id = str(uuid.uuid4())
    orden_time = time.time()
    
    # Asegurar el formato correcto de los campos, como en el app.py original
    doc = {
        "id_base": producto.get('id_base', custom_id),
        "repo_name": repo_name,
        "grupo": producto.get('grupo', ''),
        "subgrupo": producto.get('subgrupo', ''),
        "nombre": producto.get('nombre', 'Producto sin nombre'),
        "descripcion": producto.get('descripcion', 'Sin descripción'),
        "precio": float(producto.get('precio', 0.0)),
        "talles_stock": json.loads(producto.get('talles_stock', '{}')), # Se asume JSON string
        "imagen_github": producto.get('imagen_github', ''),
        "orden": int(producto.get('orden', 9999)),
        "orden_time": orden_time
    }
    
    try:
        db_client.collection("usuarios").document(email).collection("productos").document(custom_id).set(doc)
        return True
    except Exception as e:
        print(f"❌ Error al subir producto {producto.get('nombre')} a Firestore: {e}")
        return False

# ... (Incluir aquí las funciones login_admin, crear_admin y actualizar_firestore completas)
