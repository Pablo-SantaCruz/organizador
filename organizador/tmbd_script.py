import requests
import os
import re
import shutil
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
#prueba2
# Tu API Key de TMDB
API_KEY = '8eccf967757f87e14c687ed2a9361ad7'

# URL base de la API de TMDB
BASE_URL = 'https://api.themoviedb.org/3'

# Directorio donde están los archivos a procesar
DIRECTORIO_ARCHIVOS = '/srv/dev-disk-by-uuid-71ae3b67-0294-40c8-b26b-4e5047cd2666/kimchi/biblioteca/Procesador de peliculas'

# Directorio donde se crearán las carpetas de las películas
DIRECTORIO_MOVIES = '/srv/dev-disk-by-uuid-71ae3b67-0294-40c8-b26b-4e5047cd2666/kimchi/biblioteca/movies'

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
        'language': 'en-US'  # Cambiamos el idioma a inglés
    }
    # Si se proporciona el año, agregarlo a los parámetros de búsqueda
    if year:
        params['year'] = year
    
    # Hacer la solicitud GET
    response = requests.get(endpoint, params=params)
    # Verificar si la solicitud fue exitosa
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
        shutil.move(file_path, directory)
        print(f"File moved to: {directory}")
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
                move_file_to_directory(file_path, os.path.join(directory_path, os.path.basename(file_path)))
    else:
        print(f'No results found for movie: {movie_name}')

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            file_name = os.path.basename(file_path)
            print(f"\nNew file detected: {file_name}")
            movie_name, year = clean_movie_name(file_name)
            print(f"Extracted movie name: {movie_name}")
            print(f"Extracted year: {year}")
            process_movie(movie_name, year, file_path)

def process_existing_files():
    # Procesar todos los archivos existentes en el directorio
    for file_name in os.listdir(DIRECTORIO_ARCHIVOS):
        file_path = os.path.join(DIRECTORIO_ARCHIVOS, file_name)
        if os.path.isfile(file_path):
            print(f"\nProcessing existing file: {file_name}")
            movie_name, year = clean_movie_name(file_name)
            print(f"Extracted movie name: {movie_name}")
            print(f"Extracted year: {year}")
            process_movie(movie_name, year, file_path)

if __name__ == '__main__':
    # Verificar si el directorio de archivos existe
    if not os.path.exists(DIRECTORIO_ARCHIVOS):
        print(f"Directory {DIRECTORIO_ARCHIVOS} does not exist.")
        exit(1)

    # Verificar si el directorio de películas existe
    if not os.path.exists(DIRECTORIO_MOVIES):
        print(f"Directory {DIRECTORIO_MOVIES} does not exist.")
        exit(1)

    # Procesar archivos existentes antes de comenzar a monitorear
    process_existing_files()

    # Configurar el observador de archivos
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=DIRECTORIO_ARCHIVOS, recursive=False)
    observer.start()

    print(f"Monitoring directory: {DIRECTORIO_ARCHIVOS}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
