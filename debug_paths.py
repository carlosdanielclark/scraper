from src.paths import ROOT_DIR, DATA_DIR, PENDING_JSON
from pathlib import Path

print("ROOT_DIR     :", ROOT_DIR)
print("DATA_DIR     :", DATA_DIR, "exists?", DATA_DIR.exists(), "is_dir?", DATA_DIR.is_dir())
print("PENDING_JSON :", PENDING_JSON, "exists?", PENDING_JSON.exists())

# Además, mostrar el cwd actual para ver desde dónde estás ejecutando
print("CWD          :", Path().resolve())
