import requests
import os
import re
import shutil
import sys
import subprocess

# Configuración
API_KEY = '8eccf967757f87e14c687ed2a9361ad7'
BASE_URL = 'https://api.themoviedb.org/3'
DIRECTORIO_DESTINO = '/srv/dev-disk-by-uuid-71ae3b67-0294-40c8-b26b-4e5047cd2666/kimchi/Biblioteca/movies'
# Lista de directorios fijos a escanear siempre
DIRECTORIOS_PERMANENTES = (
    '/home/pablo/transmission_downloads',
    '/mnt/mint_downloads',
    '/mnt/mac_downloads'
)
EXTENSIONES_VIDEO = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v')

# ----------------------------
# FUNCIONES AUXILIARES
# ----------------------------

def verificar_directorio(directorio):
    if not os.path.isdir(directorio):
        print(f"ERROR: Directorio no encontrado: {directorio}")
        return False
    return True

def buscar_archivos_video(directorio):
    archivos_video = []
    try:
        for root, _, files in os.walk(directorio):
            for file in files:
                if file.lower().endswith(EXTENSIONES_VIDEO):
                    archivos_video.append(os.path.join(root, file))
    except Exception as e:
        print(f"Error al escanear {directorio}: {str(e)}")
    return archivos_video

def clean_movie_name(filename):
    # Primero, quitamos la extensión del archivo para trabajar solo con el nombre.
    name_without_ext = os.path.splitext(filename)[0]

    # Patrón 1: Busca el año entre paréntesis o corchetes. Ej: "Movie (2023)" o "Movie [2023]"
    # Esta es la forma más fiable de encontrar el año.
    match = re.search(r'^(.*?)[\[\(](\d{4})[\]\)]', name_without_ext)
    if match:
        # El título es todo lo que viene ANTES del año.
        title = match.group(1)
        year = match.group(2)
        # Limpiamos el título de caracteres como '.' o '_' y espacios extra.
        return re.sub(r'[._]', ' ', title).strip(), year

    # Patrón 2 (si el primero falla): Busca un año separado por punto, espacio o guion.
    # Ej: "Movie.2023.1080p"
    match = re.search(r'^(.*?)[. _-](\d{4})', name_without_ext)
    if match:
        potential_year = int(match.group(2))
        # Nos aseguramos de que sea un año de película plausible y no "1080p".
        if 1900 < potential_year < 2050:
            title = match.group(1)
            return re.sub(r'[._]', ' ', title).strip(), str(potential_year)

    # Si ningún patrón funcionó, devolvemos el nombre limpio sin año.
    return re.sub(r'[._]', ' ', name_without_ext).strip(), None

# ----------------------------
# FUNCIONES TMDB
# ----------------------------

def search_movie(query, year=None):
    params = {'api_key': API_KEY, 'query': query, 'language': 'en-US'}
    if year:
        params['year'] = year
    try:
        r = requests.get(f'{BASE_URL}/search/movie', params=params)
        if r.status_code == 200:
            return r.json()
        else:
            print(f'Error buscando película: {r.status_code}')
    except Exception as e:
        print(f"Error en search_movie: {e}")
    return None

def get_movie_details(movie_id):
    params = {'api_key': API_KEY, 'language': 'en-US'}
    try:
        r = requests.get(f'{BASE_URL}/movie/{movie_id}', params=params)
        if r.status_code == 200:
            return r.json()
        else:
            print(f'Error obteniendo detalles: {r.status_code}')
    except Exception as e:
        print(f"Error en get_movie_details: {e}")
    return None

def get_movie_credits(movie_id):
    params = {'api_key': API_KEY, 'language': 'en-US'}
    try:
        r = requests.get(f'{BASE_URL}/movie/{movie_id}/credits', params=params)
        if r.status_code == 200:
            return r.json()
        else:
            print(f'Error obteniendo créditos: {r.status_code}')
    except Exception as e:
        print(f"Error en get_movie_credits: {e}")
    return None

def get_director(credits):
    if credits and 'crew' in credits:
        for c in credits['crew']:
            if c['job'] == 'Director':
                return c['name']
    return 'Director not found'

def get_production_countries(details):
    if details and 'production_countries' in details:
        return ', '.join([c['name'] for c in details['production_countries']])
    return 'Unknown country'

# ----------------------------
# FUNCIONES DE PROCESO
# ----------------------------

def create_movie_directory(title, year, director, countries):
    # Crear nombre seguro de carpeta
    name = f"{title} ({year}) - {director} - {countries}"
    name = "".join(c for c in name if c.isalnum() or c in " ()-_,")
    path = os.path.join(DIRECTORIO_DESTINO, name)
    try:
        os.makedirs(path, exist_ok=True)
        print(f"Carpeta creada: {path}")
        return path
    except Exception as e:
        print(f"Error creando carpeta: {e}")
    return None

def move_file_to_directory(file_path, target_dir):
    try:
        shutil.move(file_path, os.path.join(target_dir, os.path.basename(file_path)))
        print(f"Archivo movido a: {target_dir}")
    except Exception as e:
        print(f"Error moviendo archivo: {e}")

def process_movie(movie_name, year, file_path):
    print(f"Buscando metadata para: {movie_name} ({year})")
    search = search_movie(movie_name, year)
    if not search or not search['results']:
        print("No se encontró la película.")
        return
    movie = search['results'][0]
    movie_id = movie['id']
    details = get_movie_details(movie_id)
    credits = get_movie_credits(movie_id)
    if details and credits:
        release_year = details.get('release_date', '0000').split('-')[0]
        director = get_director(credits)
        countries = get_production_countries(details)
        dir_path = create_movie_directory(movie['title'], release_year, director, countries)
        if dir_path:
            move_file_to_directory(file_path, dir_path)
    else:
        print("No se pudo obtener metadata completa.")

def intentar_montar_recurso(mount_point):
    """Intenta montar un recurso de red si no está montado, usando fstab."""
    nombre_recurso = os.path.basename(mount_point).replace('_', ' ')
    if not os.path.ismount(mount_point):
        print(f"Intentando montar el recurso de red en {mount_point}...")
        mount_command = ['mount', mount_point]
        try:
            subprocess.run(mount_command, check=True, capture_output=True, timeout=15)
            print(f"Recurso '{nombre_recurso}' montado con éxito.")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            print(f"{nombre_recurso} desconectado")
    else:
        print(f"{mount_point} ya se encuentra montado.")

# ----------------------------
# PROCESO PRINCIPAL
# ----------------------------

def main():
    # Lista de recursos de red que el script debe intentar montar.
    # Deben tener una entrada en /etc/fstab con la opción 'user'.
    recursos_de_red = ('/mnt/mint_downloads', '/mnt/mac_downloads')

    for recurso in recursos_de_red:
        intentar_montar_recurso(recurso)

    if not verificar_directorio(DIRECTORIO_DESTINO):
        return

    directorios_a_escanear = list(DIRECTORIOS_PERMANENTES)
    archivos_a_procesar = []

    # Procesar argumentos de línea de comandos (pueden ser archivos o directorios)
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.isdir(arg):
                print(f"Argumento detectado como directorio: {arg}")
                directorios_a_escanear.append(arg)
            elif os.path.isfile(arg):
                if arg.lower().endswith(EXTENSIONES_VIDEO):
                    print(f"Argumento detectado como archivo de vídeo: {arg}")
                    archivos_a_procesar.append(arg)
                else:
                    print(f"AVISO: El archivo '{os.path.basename(arg)}' no tiene una extensión de vídeo válida y será ignorado.")
            else:
                print(f"AVISO: El argumento '{arg}' no es un archivo o directorio válido y será ignorado.")

    # Buscar vídeos en los directorios configurados
    for d in directorios_a_escanear:
        if verificar_directorio(d):
            encontrados = buscar_archivos_video(d)
            print(f"Encontrados {len(encontrados)} archivos en {d}")
            archivos_a_procesar.extend(encontrados)

    if not archivos_a_procesar:
        print("\nNo se encontraron archivos para procesar.")
        return

    print(f"\nTotal de archivos a procesar: {len(archivos_a_procesar)}")
    for f in archivos_a_procesar:
        print(f"\nProcesando archivo: {os.path.basename(f)}")
        name, year = clean_movie_name(os.path.basename(f))
        print(f"Título detectado: {name} | Año detectado: {year}")
        process_movie(name, year, f)

if __name__ == '__main__':
    main()
