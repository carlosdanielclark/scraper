import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, TypedDict, Literal
from dotenv import load_dotenv


load_dotenv()

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
        default_if_missing='N/S'  # Confirmado por Jaime
    )
}


# ── Selectores UI ───────────────────────────────────────────────────────

class Selectors:
    # Pipeline view (/opportunities/pipeline)
    DUE_DATE_HEADER = 'th[aria-sort]:has-text("Due Date")'
    DUE_DATE_SORT_DESC = 'th[aria-sort="descending"]:has-text("Due Date")'
    PROJECT_LINKS = 'tr.opportunity-row a[href*="/opportunities/"]:first-of-type'

    # Project Overview (/opportunities/{id}/info)
    PROJECT_NAME = 'h1[data-testid="opportunity-name"]'
    DUE_DATE = 'span:has-text("Due Date") + div, div:has-text("Due Date") + span'
    PROJECT_SIZE = 'span:has-text("Project Size") + div, div:has-text("Project Size") + span'
    LOCATION = 'span:has-text("Location") + div, div:has-text("Location") + span'
    CLIENT = 'span:has-text("Client") + div, div:has-text("Client") + span'
    PHONE = (
        'span:has-text("Phone") + div, div:has-text("Phone") + span, '
        'div[data-testid*="contact"], div:has-text("Contact")'
    )


# ── Normalización y validación ──────────────────────────────────────────

DATE_FORMAT_OUTPUT: Literal['%Y-%m-%d'] = '%Y-%m-%d'
MISSING_PHONE_PLACEHOLDER: Literal['N/S'] = 'N/S'


# ── Configuración principal (URLs, credenciales, rutas) ──────────────────

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
