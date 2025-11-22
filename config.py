import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, TypedDict, Literal
from dotenv import load_dotenv


load_dotenv()

MISSING_PHONE_PLACEHOLDER = "N/S"

# ── Esquema de metadatos ───────────────────────────────────────────────

class ProjectMetadata(TypedDict):
    """Estructura tipada de salida (para serialización JSON)."""
    project_name: str
    due_date: str          # YYYY-MM-DD
    project_size: str      # texto crudo (ej: "1,611 sq. ft."), vacío si no existe
    location: str
    client: str
    phone: str             # Siempre str; "N/S" si ausente


# ── Configuración de campos ─────────────────────────────────────────────

@dataclass(frozen=True)
class FieldConfig:
    key: str
    label: str
    required: bool
    default_if_missing: str


PROJECT_FIELDS: Dict[str, FieldConfig] = {
    'project_name': FieldConfig(
        key='project_name',
        label='Project Name',
        required=True,
        default_if_missing=''
    ),
    'due_date': FieldConfig(
        key='due_date',
        label='Due Date',
        required=True,
        default_if_missing=''
    ),
    'project_size': FieldConfig(
        key='project_size',
        label='Project Size',
        required=False,
        default_if_missing=''
    ),
    'location': FieldConfig(
        key='location',
        label='Location',
        required=True,
        default_if_missing=''
    ),
    'client': FieldConfig(
        key='client',
        label='Client',
        required=True,
        default_if_missing=''
    ),
    'phone': FieldConfig(
        key='phone',
        label='Phone number',
        required=False,
        default_if_missing='N/S'
    )
}


# ── Selectores UI actualizados ───────────────────────────────────────────

class Selectors:
    # Pipeline view (/opportunities/pipeline) - ACTUALIZADOS
    DUE_DATE_HEADER = 'div[role="columnheader"][aria-label="Due Date"]'
    PROJECT_ROWS = 'div.ReactVirtualized__Table__row[role="row"]'
    PROJECT_CELLS = 'div.ReactVirtualized__Table__rowColumn'
    PROJECT_LINK = 'div.ReactVirtualized__Table__rowColumn:nth-child(2) a[href*="/opportunities/"]'
    PAGINATION_NEXT = 'button[data-id="caret-right"]:not([disabled])'
    
    # Project Overview (/opportunities/{id}/info) - ACTUALIZADOS
    PROJECT_NAME = 'h1, div.header-0-1-10'  # Fallback para diferentes estilos
    DUE_DATE = 'div:has-text("Due Date") + div, div:has-text("Due Date") ~ div'
    PROJECT_SIZE = 'div:has-text("Project Size") + div, div:has-text("Project Size") ~ div'
    LOCATION = 'div:has-text("Location") + div, div:has-text("Location") ~ div'
    CLIENT = 'div:has-text("Client") + div, div:has-text("Client") ~ div'
    PHONE = (
        'div:has-text("Phone") + div, div:has-text("Phone") ~ div, '
        'div:has-text("Contact") + div, div:has-text("Contact") ~ div, '
        'div[data-testid*="contact"], div:has-text("Phone number")'
    )


# ── Normalización y validación ──────────────────────────────────────────

DATE_FORMAT_OUTPUT: Literal['%Y-%m-%d'] = '%Y-%m-%d'
MISSING_PHONE_PLACEHOLDER: Literal['N/S'] = 'N/S'


# ── Configuración principal (URLs, credenciales, rutas) ──────────────────
SELECTORS = {
    "email": 'input[type="email"], input[name="email"], input#email',  # Ajusta según el HTML real
    "password": 'input[type="password"], input[name="password"], input#password',  # Igual
    # Puedes agregar otros selectores para uso en otras partes del scraping aquí si quieres centralizar
}

@dataclass
class Config:
    # URLs
    LOGIN_URL: str = "https://app.buildingconnected.com/login"
    PIPELINE_URL: str = "https://app.buildingconnected.com/opportunities/pipeline"

    # Credenciales
    BC_EMAIL: str = field(default_factory=lambda: os.getenv("BC_EMAIL", ""))
    BC_PASSWORD: str = field(default_factory=lambda: os.getenv("BC_PASSWORD", ""))

    # Paths
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    STORE_CSV: Path = BASE_DIR / "store.csv"

    def __post_init__(self) -> None:
        if not self.BC_EMAIL or not self.BC_PASSWORD:
            raise ValueError("❌ Faltan credenciales: BC_EMAIL y BC_PASSWORD deben estar en .env")

        self.DATA_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)


# Inicializar configuración global
config = Config()

# ── Exportar constantes globales para importación directa ─────────────────
LOGIN_URL: str = config.LOGIN_URL
PIPELINE_URL: str = config.PIPELINE_URL
BC_EMAIL: str = config.BC_EMAIL
BC_PASSWORD: str = config.BC_PASSWORD
BASE_DIR: Path = config.BASE_DIR
DATA_DIR: Path = config.DATA_DIR
LOGS_DIR: Path = config.LOGS_DIR
STORE_CSV: Path = config.STORE_CSV
