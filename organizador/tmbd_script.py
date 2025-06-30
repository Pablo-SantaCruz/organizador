import requests
import os
import re
import shutil
import sys

# Configuración
API_KEY = '8eccf967757f87e14c687ed2a9361ad7'
BASE_URL = 'https://api.themoviedb.org/3'
DIRECTORIO_DESTINO = '/srv/dev-disk-by-uuid-71ae3b67-0294-40c8-b26b-4e5047cd2666/kimchi/Biblioteca/movies'
DIRECTORIO_PERMANENTE = '/home/pablo/nextcloud'  # Directorio que siempre se escanea
EXTENSIONES_VIDEO = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.m4v')

def verificar_directorio(directorio):
    """Verifica que un directorio exista"""
    if not os.path.isdir(directorio):
        print(f"ERROR: Directorio no encontrado: {directorio}")
        return False
    return True

def buscar_archivos_video(directorio):
    """Busca archivos de video en un directorio y sus subdirectorios"""
    archivos_video = []
    try:
        for root, _, files in os.walk(directorio):
            for file in files:
                if file.lower().endswith(EXTENSIONES_VIDEO):
                    archivos_video.append(os.path.join(root, file))
    except Exception as e:
        print(f"Error al escanear {directorio}: {str(e)}")
    return archivos_video

def procesar_directorios(directorios):
    """Procesa todos los directorios especificados"""
    todos_archivos = []
    
    for directorio in directorios:
        if not verificar_directorio(directorio):
            continue
            
        print(f"\nEscaneando directorio: {directorio}")
        archivos = buscar_archivos_video(directorio)
        
        if not archivos:
            print(f"No se encontraron archivos de video en {directorio}")
            continue
            
        print(f"Encontrados {len(archivos)} archivos de video")
        todos_archivos.extend(archivos)
    
    return todos_archivos

# [Tus funciones existentes: clean_movie_name, search_movie, etc...]

def main():
    # Verificar directorio destino primero
    if not verificar_directorio(DIRECTORIO_DESTINO):
        return
    
    # Directorios a procesar (siempre el permanente + opcionalmente el argumento)
    directorios_a_procesar = [DIRECTORIO_PERMANENTE]
    
    # Si se proporciona un argumento, añadirlo a la lista
    if len(sys.argv) > 1:
        directorio_adicional = sys.argv[1]
        directorios_a_procesar.append(directorio_adicional)
    
    # Obtener todos los archivos de video
    archivos_video = procesar_directorios(directorios_a_procesar)
    
    if not archivos_video:
        print("\nNo se encontraron archivos de video para procesar")
        return
    
    print(f"\nTotal de archivos a procesar: {len(archivos_video)}")
    
    # Procesar cada archivo
    for file_path in archivos_video:
        print(f"\nProcesando: {os.path.basename(file_path)}")
        movie_name, year = clean_movie_name(os.path.basename(file_path))
        process_movie(movie_name, year, file_path)

if __name__ == '__main__':
    main()
