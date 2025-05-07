import requests
import os
import re
import shutil
import sys
# este es el branch prueba
# Tu API Key de TMDB
API_KEY = '8eccf967757f87e14c687ed2a9361ad7'

# URL base de la API de TMDB
BASE_URL = 'https://api.themoviedb.org/3'

# Directorio donde se crearán las carpetas de las películas
DIRECTORIO_MOVIES = '/srv/dev-disk-by-uuid-71ae3b67-0294-40c8-b26b-4e5047cd2666/kimchi/biblioteca/movies'

def clean_movie_name(filename):
    # Nuevo regex que maneja paréntesis y títulos complejos
    pattern = r'^(.*?)[ ._(](\d{4})[ ._)]'
    match = re.match(pattern, filename, re.IGNORECASE)
    
    if match:
        title = match.group(1)
        year = match.group(2)
        # Limpieza más robusta:
        title = re.sub(r'[._-]', ' ', title)  # Reemplaza puntos/guiones por espacios
        title = re.sub(r'\s+', ' ', title)    # Elimita espacios múltiples
        return title.strip(), year
    else:
        return os.path.splitext(filename)[0], None

def search_movie(query, year=None):
    endpoint = f'{BASE_URL}/search/movie'
    params = {
        'api_key': API_KEY,
        'query': query,
        'language': 'es-ES',  # Prioriza español (cambiable a 'en-US' si no hay resultados)
        'include_adult': True  # Incluye películas no infantiles
    }
    if year:
        params['primary_release_year'] = year  # Más preciso que 'year'
    
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error: {response.status_code}')
        return None

def get_movie_credits(movie_id):
    # Endpoint para obtener los créditos de una película (incluyendo el director)
    endpoint = f'{BASE_URL}/movie/{movie_id}/credits'
    # Parámetros de la solicitud
    params = {
        'api_key': API_KEY,
        'language': 'en-US'  # Cambiamos el idioma a inglés
    }
    # Hacer la solicitud GET
    response = requests.get(endpoint, params=params)
    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error: {response.status_code}')
        return None

def get_movie_details(movie_id):
    # Endpoint para obtener detalles de una película
    endpoint = f'{BASE_URL}/movie/{movie_id}'
    # Parámetros de la solicitud
    params = {
        'api_key': API_KEY,
        'language': 'en-US'  # Cambiamos el idioma a inglés
    }
    # Hacer la solicitud GET
    response = requests.get(endpoint, params=params)
    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error: {response.status_code}')
        return None

def get_director(credits):
    # Buscar al director en la lista de créditos
    for crew_member in credits['crew']:
        if crew_member['job'] == 'Director':
            return crew_member['name']
    return 'Director not found'

def get_production_countries(movie_details):
    # Obtener los países de producción de la película
    if 'production_countries' in movie_details:
        countries = [country['name'] for country in movie_details['production_countries']]
        return ', '.join(countries)  # Devolver una cadena con los países separados por comas
    return 'Country not found'

def create_movie_directory(title, year, director, countries):
    # Crear el nombre del directorio
    directory_name = f"{title} ({year}) - {director} - {countries}"
    # Eliminar caracteres no válidos para nombres de directorios
    directory_name = "".join(c for c in directory_name if c.isalnum() or c in " ()-_,")
    # Ruta completa del directorio
    full_path = os.path.join(DIRECTORIO_MOVIES, directory_name)
    # Crear el directorio
    try:
        os.makedirs(full_path, exist_ok=True)
        print(f"Directory created: {full_path}")
        return full_path  # Devolver la ruta completa del directorio creado
    except Exception as e:
        print(f"Error creating directory: {e}")
        return None

def move_file_to_directory(file_path, directory):
    # Mover el archivo al directorio correspondiente
    try:
        destination = os.path.join(directory, os.path.basename(file_path))
        shutil.move(file_path, destination)
        print(f"File moved to: {destination}")
    except Exception as e:
        print(f"Error moving file: {e}")

def process_movie(movie_name, year, file_path):
    # Buscar la película
    search_results = search_movie(movie_name, year)
    
    if search_results and search_results['results']:
        # Obtener el ID de la primera película encontrada
        first_result = search_results['results'][0]
        movie_id = first_result['id']
        print(f'Movie found: {first_result["title"]} (ID: {movie_id})')

        # Obtener detalles de la película (año de estreno y países de producción)
        movie_details = get_movie_details(movie_id)
        if movie_details:
            release_year = movie_details['release_date'].split('-')[0]  # Extraer el año
            print(f'Release year: {release_year}')

            # Obtener los países de producción
            countries = get_production_countries(movie_details)
            print(f'Production countries: {countries}')

        # Obtener los créditos de la película (director)
        credits = get_movie_credits(movie_id)
        if credits:
            director = get_director(credits)
            print(f'Director: {director}')

        # Crear el directorio con la información de la película
        if movie_details and credits:
            directory_path = create_movie_directory(first_result['title'], release_year, director, countries)
            if directory_path:
                # Mover el archivo al directorio creado
                move_file_to_directory(file_path, directory_path)
    else:
        print(f'No results found for movie: {movie_name}')

def process_single_file(file_path):
    if os.path.isfile(file_path):
        file_name = os.path.basename(file_path)
        print(f"\nProcessing file: {file_name}")
        movie_name, year = clean_movie_name(file_name)
        print(f"Extracted movie name: {movie_name}")
        print(f"Extracted year: {year}")
        process_movie(movie_name, year, file_path)
    else:
        print(f"Error: {file_path} is not a valid file.")

if __name__ == '__main__':
    # Verificar si se proporcionó un argumento
    if len(sys.argv) != 2:
        print("Usage: python script.py <file_path>")
        exit(1)
    
    file_path = sys.argv[1]
    
    # Verificar si el directorio de películas existe
    if not os.path.exists(DIRECTORIO_MOVIES):
        print(f"Directory {DIRECTORIO_MOVIES} does not exist.")
        exit(1)
    
    # Procesar el archivo
    process_single_file(file_path)
