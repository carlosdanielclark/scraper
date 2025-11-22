# src/paths.py
from pathlib import Path

# Ruta raíz del proyecto (carpeta donde está el repo)
# __file__ = .../src/paths.py → parent = /src → parent.parent = root del proyecto
ROOT_DIR = Path(__file__).resolve().parent.parent

# Carpeta de datos persistentes
DATA_DIR = ROOT_DIR / "data"

# Te aseguras de que la carpeta exista
DATA_DIR.mkdir(exist_ok=True)

# Ruta absoluta al JSON de proyectos pendientes
PENDING_JSON = DATA_DIR / "pending_projects.json"
