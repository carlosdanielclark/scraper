import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # URLs
    LOGIN_URL: str = "https://app.buildingconnected.com/login"
    PIPELINE_URL: str = "https://app.buildingconnected.com/opportunities/pipeline"
    
    # Credenciales (cargadas desde .env o variables de entorno)
    BC_EMAIL: str = field(default_factory=lambda: os.getenv("BC_EMAIL", ""))
    BC_PASSWORD: str = field(default_factory=lambda: os.getenv("BC_PASSWORD", ""))
    
    # Selectores CSS (como campo de dataclass)
    SELECTORS: Dict[str, str] = field(default_factory=lambda: {
        "email": 'input[name="email"]',
        "next_btn": 'button[aria-label="NEXT"]',
        "password": 'input[name="password"]',
        "signin_btn": 'button[aria-label="SIGN IN"]',
        "undecided_tab": 'text="Undecided"',
        "project_rows": '.bc-table-row',
        "project_name": '.opportunity-title',
        "due_date": '.due-date',
        "location": '.location-address',
        "client_info": '.client-info',
        "phone": '.phone-number',
        "files_tab": 'text="Files"',
        "download_all": 'button:has-text("Download All")'
    })
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    STORE_CSV: Path = BASE_DIR / "store.csv"

    def __post_init__(self):
        # Validación crítica
        if not self.BC_EMAIL or not self.BC_PASSWORD:
            raise ValueError("❌ Faltan credenciales: BC_EMAIL y BC_PASSWORD deben estar en .env")
        
        # Crear directorios
        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)

# Inicializar
config = Config()