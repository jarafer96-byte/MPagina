import os
import requests
import base64
import re
import uuid
import time
from werkzeug.utils import secure_filename
from io import BytesIO

# --- Configuraciones (Basadas en app.py original) ---
# Usamos el mismo nombre de usuario codificado para la API
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME") or "jarafer96-byte" 
GITHUB_API_URL = "https://api.github.com"
# El token debe obtenerse de la variable de entorno
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ----------------------------------------------------
# 1. GENERACIÓN DE NOMBRES Y LIMPIEZA (Líneas 66-73 y 207-219 del app.py original)
# ----------------------------------------------------

def generar_nombre_repo(email: str) -> str:
    """Genera un nombre de repositorio único a partir del email."""
    # Líneas 66-73 del app.py original
    try:
        # Usa el email, elimina caracteres no válidos y limita a 30
        nombre = re.sub(r'[^a-zA-Z0-9-]', '-', email.split('@')[0].lower())
        unique_suffix = str(uuid.uuid4()).split('-')[0]
        return f"appweb-{nombre[:20]}-{unique_suffix}"
    except Exception:
        # Fallback de seguridad
        return f"appweb-user-{str(uuid.uuid4()).split('-')[0]}"


def limpiar_imagenes_usuario(upload_folder: str, email: str):
    """Limpia las imágenes temporales locales del usuario tras subir/descargar."""
    # Lógica de las Líneas 207-219 (dentro de limpiar_imagenes_usuario)
    if not email:
        return
        
    try:
        prefix = f"optimizado_{email}_"
        # Itera sobre todos los archivos en la carpeta de subida
        for filename in os.listdir(upload_folder):
            if filename.startswith(prefix) or filename == f"logo_{email}":
                try:
                    os.remove(os.path.join(upload_folder, filename))
                except Exception as e:
                    print(f"❌ Error al borrar archivo {filename}: {e}")
    except Exception as e:
        print(f"❌ Error general al limpiar imágenes para {email}: {e}")

# ----------------------------------------------------
# 2. CREACIÓN DE REPOSITORIO (Líneas 460-493 del app.py original)
# ----------------------------------------------------

def crear_repo_github(nombre_repo: str) -> dict:
    """Crea un repositorio vacío en GitHub."""
    
    if not GITHUB_TOKEN:
        return {"error": "Token de GitHub no configurado en variables de entorno."}

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": nombre_repo,
        "description": "Sitio de e-commerce estático generado por AppWeb.",
        "homepage": f"https://{GITHUB_USERNAME}.github.io/{nombre_repo}",
        "private": False, # Lo mantenemos público para GitHub Pages
        "has_issues": False,
        "has_projects": False,
        "has_wiki": False
    }
    
    response = requests.post(f"{GITHUB_API_URL}/user/repos", headers=headers, json=data)

    if response.status_code == 201:
        return {"url": response.json().get('html_url'), "status": 201}
    else:
        # Intenta subirlo de nuevo si falla por existencia
        return {"error": f"Error al crear repo ({response.status_code}): {response.text}", "status": response.status_code}

# ----------------------------------------------------
# 3. SUBIDA Y ACTUALIZACIÓN DE ARCHIVOS (Líneas 122-192 del app.py original)
# ----------------------------------------------------

def subir_archivo(repo_name: str, contenido_bytes: bytes, ruta_remota: str, branch="main") -> dict:
    """Sube o actualiza un archivo en el repositorio usando la API de contenidos."""
    
    if not GITHUB_TOKEN:
        return {"ok": False, "error": "Token de GitHub no disponible"}
        
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 1. Preparar el contenido
    # Codificación de Base64 del contenido.
    contenido_base64 = base64.b64encode(contenido_bytes).decode('utf-8')
    
    # 2. Verificar si el archivo ya existe (Líneas 142-160)
    sha = None
    url_contenido = f"{GITHUB_API_URL}/repos/{GITHUB_USERNAME}/{repo_name}/contents/{ruta_remota}"
    
    try:
        # Se agrega un timestamp para prevenir caché en la consulta de existencia
        response_check = requests.get(url_contenido + f"?ref={branch}&t={int(time.time())}", headers=headers)
        if response_check.status_code == 200:
            sha = response_check.json().get('sha')
            # print(f"-> Archivo existente: {ruta_remota}, SHA: {sha}")
        elif response_check.status_code != 404:
             # Solo loguear si no es un 404 esperado
            print(f"-> GitHub Check Error {response_check.status_code} en {ruta_remota}: {response_check.text[:100]}")
    except Exception as e:
        print(f"-> Excepción en check de GitHub: {e}")

    # 3. Datos de la transacción (Líneas 162-180)
    data = {
        "message": f"Actualización automática: {ruta_remota}",
        "content": contenido_base64,
        "branch": branch
    }
    if sha:
        data["sha"] = sha # Necesario para actualizar
        
    # 4. Enviar la transacción (Líneas 182-192)
    response_upload = requests.put(url_contenido, headers=headers, json=data)

    if response_upload.status_code in [200, 201]:
        return {"ok": True, "status": response_upload.status_code, "url": response_upload.json().get('content', {}).get('html_url')}
    else:
        return {"ok": False, "status": response_upload.status_code, "error": f"Error {response_upload.status_code}: {response_upload.text}"}

# ----------------------------------------------------
# 4. SUBIDA DE ICONOS FIJOS (Líneas 274-325 del app.py original)
# ----------------------------------------------------

def subir_iconos_png(repo_name: str, upload_folder: str):
    """Sube los iconos PNG y el logo por defecto al repositorio."""
    
    # Lista de archivos fijos que subimos
    archivos_fijos = ['whatsapp.png', 'logo_fallback.png']
    
    resultados = []
    
    for filename in archivos_fijos:
        path_local = os.path.join(upload_folder, filename)
        
        try:
            with open(path_local, 'rb') as f:
                contenido_bytes = f.read()
                ruta_remota = f"img/{filename}"
                
                # Usamos la función de subida ya definida
                resultado = subir_archivo(repo_name, contenido_bytes, ruta_remota)
                resultados.append(resultado)
        except FileNotFoundError:
            # Esto puede ocurrir si el archivo no existe localmente
            print(f"⚠️ Archivo fijo {filename} no encontrado localmente.")
            resultados.append({"ok": False, "error": f"Archivo {filename} no existe localmente."})
        except Exception as e:
            print(f"❌ Error al subir {filename}: {e}")
            resultados.append({"ok": False, "error": str(e)})

    return resultados
