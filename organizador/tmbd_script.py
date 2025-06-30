import requests
import os
import re
import shutil

# Tu API Key de TMDB
API_KEY = '8eccf967757f87e14c687ed2a9361ad7'

# URL base de la API de TMDB
BASE_URL = 'https://api.themoviedb.org/3'

# Directorio donde se crearán las carpetas de las películas
DIRECTORIO_DESTINO = '/srv/dev-disk-by-uuid-71ae3b67-0294-40c8-b26b-4e5047cd2666/kimchi/Biblioteca/movies'

# Directorio a escanear (ahora fijo)
DIRECTORIO_FUENTE = '/home/pablo/nextcloud'

# Extensiones de archivo de video reconocidas
EXTENSIONES_VIDEO = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v')

def clean_movie_name(filename):
    # Expresión regular para extraer el título y el año de la película
    pattern = r'^(.*?)[ ._-](\d{4})[ ._-]'
    match = re.match(pattern, filename, re.IGNORECASE)
    
    if match:
        # Extraer el título y el año de la película
        title = match.group(1)
        year = match.group(2)
        
        # Limpiar el título: reemplazar puntos, guiones bajos y otros símbolos por espacios
        title = re.sub(r'[._-]', ' ', title)
        title = ' '.join(title.split())  # Eliminar espacios adicionales
        
        return title.strip(), year  # Devolver el título y el año
    else:
        # Si no se encuentra un patrón, devolver el nombre original sin extensión y año vacío
        return os.path.splitext(filename)[0], None

def search_movie(query, year=None):
    # Endpoint para buscar películas
    endpoint = f'{BASE_URL}/search/movie'
    # Parámetros de la solicitud
    params = {
        'api_key': API_KEY,
        'query': query,
        'language': 'en-US'
    }
    if year:
        params['year'] = year
    
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error: {response.status_code}')
        return None

def get_movie_credits(movie_id):
    endpoint = f'{BASE_URL}/movie/{movie_id}/credits'
    params = {
        'api_key': API_KEY,
        'language': 'en-US'
    }
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error: {response.status_code}')
        return None

def get_movie_details(movie_id):
    endpoint = f'{BASE_URL}/movie/{movie_id}'
    params = {
        'api_key': API_KEY,
        'language': 'en-US'
    }
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error: {response.status_code}')
        return None

def get_director(credits):
    for crew_member in credits['crew']:
        if crew_member['job'] == 'Director':
            return crew_member['name']
    return 'Director not found'

def get_production_countries(movie_details):
    if 'production_countries' in movie_details:
        countries = [country['name'] for country in movie_details['production_countries']]
        return ', '.join(countries)
    return 'Country not found'

def create_movie_directory(title, year, director, countries):
    directory_name = f"{title} ({year}) - {director} - {countries}"
    directory_name = "".join(c for c in directory_name if c.isalnum() or c in " ()-_,")
    full_path = os.path.join(DIRECTORIO_DESTINO, directory_name)
    try:
        os.makedirs(full_path, exist_ok=True)
        print(f"Directory created: {full_path}")
        return full_path
    except Exception as e:
        print(f"Error creating directory: {e}")
        return None

def move_file_to_directory(file_path, directory):
    try:
        destination = os.path.join(directory, os.path.basename(file_path))
        shutil.move(file_path, destination)
        print(f"File moved to: {destination}")
    except Exception as e:
        print(f"Error moving file: {e}")

def process_movie(movie_name, year, file_path):
    search_results = search_movie(movie_name, year)
    
    if search_results and search_results['results']:
        first_result = search_results['results'][0]
        movie_id = first_result['id']
        print(f'Movie found: {first_result["title"]} (ID: {movie_id})')

        movie_details = get_movie_details(movie_id)
        if movie_details:
            release_year = movie_details['release_date'].split('-')[0]
            print(f'Release year: {release_year}')

            countries = get_production_countries(movie_details)
            print(f'Production countries: {countries}')

        credits = get_movie_credits(movie_id)
        if credits:
            director = get_director(credits)
            print(f'Director: {director}')

        if movie_details and credits:
            directory_path = create_movie_directory(first_result['title'], release_year, director, countries)
            if directory_path:
                move_file_to_directory(file_path, directory_path)
    else:
        print(f'No results found for movie: {movie_name}')

def process_directory():
    # Verificar si el directorio fuente existe
    if not os.path.isdir(DIRECTORIO_FUENTE):
        print(f"Error: {DIRECTORIO_FUENTE} is not a valid directory.")
        return
    
    # Verificar si el directorio destino existe
    if not os.path.exists(DIRECTORIO_DESTINO):
        print(f"Error: {DIRECTORIO_DESTINO} does not exist.")
        return
    
    print(f"\nProcessing directory: {DIRECTORIO_FUENTE}")
    
    # Recorrer todos los archivos en el directorio fuente
    for filename in os.listdir(DIRECTORIO_FUENTE):
        file_path = os.path.join(DIRECTORIO_FUENTE, filename)
        
        # Procesar solo archivos (no directorios) con extensiones de video
        if os.path.isfile(file_path) and filename.lower().endswith(EXTENSIONES_VIDEO):
            print(f"\nProcessing file: {filename}")
            movie_name, year = clean_movie_name(filename)
            print(f"Extracted movie name: {movie_name}")
            print(f"Extracted year: {year}")
            process_movie(movie_name, year, file_path)

if __name__ == '__main__':
    process_directory()
