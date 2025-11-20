import os
import requests
import base64
import re
import uuid
import time
from werkzeug.utils import secure_filename

# --- Configuraciones ---
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME") or "jarafer96-byte" 
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ----------------------------------------------------
# A. UTILIDADES (Usadas en step1)
# ----------------------------------------------------

def generar_nombre_repo(email: str) -> str:
    """Genera un nombre de repositorio único a partir del email."""
    try:
        nombre = re.sub(r'[^a-zA-Z0-9-]', '-', email.split('@')[0].lower())
        unique_suffix = str(uuid.uuid4()).split('-')[0]
        return f"appweb-{nombre[:20]}-{unique_suffix}"
    except Exception:
        return f"appweb-user-{str(uuid.uuid4()).split('-')[0]}"


def limpiar_imagenes_usuario(upload_folder: str, email: str):
    """Limpia las imágenes temporales locales del usuario."""
    if not email: return
        
    try:
        prefix = f"optimizado_{email}_"
        for filename in os.listdir(upload_folder):
            # Limpia archivos optimizados y el logo
            if filename.startswith(prefix) or filename == f"logo_{email}": 
                try:
                    os.remove(os.path.join(upload_folder, filename))
                except Exception as e:
                    print(f"❌ Error al borrar archivo {filename}: {e}")
    except Exception as e:
        print(f"❌ Error general al limpiar imágenes para {email}: {e}")

# ----------------------------------------------------
# B. API DE GITHUB
# ----------------------------------------------------

def crear_repo_github(nombre_repo: str) -> dict:
    """Crea un repositorio vacío en GitHub."""
    if not GITHUB_TOKEN: return {"error": "Token de GitHub no configurado.", "status": 500}
    # ... (Lógica completa para hacer el POST a la API de GitHub) ...
    return {"url": f"https://github.com/{GITHUB_USERNAME}/{nombre_repo}", "status": 201}


def subir_archivo(repo_name: str, contenido_bytes: bytes, ruta_remota: str, branch="main") -> dict:
    """Sube o actualiza un archivo en el repositorio."""
    if not GITHUB_TOKEN: return {"ok": False, "error": "Token de GitHub no disponible"}
    # ... (Lógica completa para subir el archivo con SHA check) ...
    return {"ok": True, "status": 200, "url": "URL_DE_GITHUB"}

def subir_iconos_png(repo_name: str, upload_folder: str):
    """Sube los iconos PNG y el logo por defecto al repositorio."""
    # ... (Lógica completa para subir archivos fijos) ...
    pass
