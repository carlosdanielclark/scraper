# src/project_paths.py
from pathlib import Path
import os

# Ruta raíz del proyecto (carpeta donde está el repo "scraper")
ROOT_DIR = Path(__file__).resolve().parent.parent

# Carpeta padre del proyecto (para poner scraper_data al lado)
PARENT_DIR = ROOT_DIR.parent

# 1) Intenta usar variable de entorno SCRAPER_DATA_DIR
env_data_dir = os.getenv("SCRAPER_DATA_DIR")

if env_data_dir:
    DATA_DIR = Path(env_data_dir).expanduser().resolve()
else:
    # 2) Si no hay env, por defecto: <carpeta_padre>/scraper_data
    # Ejemplo:
    #   C:\Users\...\TRABAJO\Jaime\scraper\        → ROOT_DIR
    #   C:\Users\...\TRABAJO\Jaime\scraper_data\  → DATA_DIR
    DATA_DIR = (PARENT_DIR / "scraper_data").resolve()

# Carpeta de estado (cola, JSON, etc.)
STORE_DIR = ROOT_DIR / "store"

# Carpeta de logs
LOGS_DIR = ROOT_DIR / "logs"

# Crear directorios base (el resto lo hace StorageManager)
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)