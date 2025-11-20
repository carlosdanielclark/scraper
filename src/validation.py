import re
from typing import Dict, Optional, Tuple, Union
from datetime import datetime
import dateparser
from config import DATE_FORMAT_OUTPUT, FieldConfig, MISSING_PHONE_PLACEHOLDER, PROJECT_FIELDS

def normalize_date(date_str: str) -> str:
    """
    Normaliza formato de fecha humana a YYYY-MM-DD.
    """
    parsed = dateparser.parse(date_str, settings={'DATE_ORDER': 'MDY'})
    if not parsed:
        raise ValueError(f"Fecha no válida: {date_str}")
    return parsed.strftime(DATE_FORMAT_OUTPUT)

def extract_phone_from_text(text: Optional[str]) -> str:
    """
    Extrae el primer número de teléfono razonable.
    """
    if not text or not isinstance(text, str):
        return MISSING_PHONE_PLACEHOLDER
    # Busca el primer patrón de teléfono razonable
    phone_pattern = (
        r'(\+?\d{1,3}[-.\s]*)?'        # Código país opcional
        r'(\(?\d{3}\)?[-.\s]*)'        # Área
        r'(\d{3}[-.\s]*)'              # Prefijo
        r'(\d{4})'                     # Línea
    )
    match = re.search(phone_pattern, text)
    if not match:
        return MISSING_PHONE_PLACEHOLDER
    # Une y limpia solo los dígitos y "+"
    raw_phone = ''.join(match.groups(default=''))
    digits = re.sub(r'[^\d+]', '', raw_phone)
    # Estandarización básica
    if digits.startswith('+'):
        # Delejamos formato internacional simple
        return digits
    if len(digits) == 10:
        return "+1 " + digits[:3] + "-" + digits[3:6] + "-" + digits[6:]
    return digits or MISSING_PHONE_PLACEHOLDER

def validate_project_data(
    data: Dict[str, str], 
    field_configs: Dict[str, FieldConfig]
) -> Tuple[bool, str]:
    """
    Valida datos proyecto contra FieldConfig; normaliza fechas.
    No debe mutar data original.
    """
    data = data.copy()
    for key, config in field_configs.items():
        value = data.get(key, '').strip()
        if key == 'phone' and not value:
            data[key] = MISSING_PHONE_PLACEHOLDER
            continue
        if config.required and not value:
            return False, f"Campo obligatorio ausente: {config.label} (clave: {key})"
        if key == 'due_date' and value:
            try:
                data[key] = normalize_date(value)
            except ValueError as e:
                return False, str(e)
    return True, ""

def safe_strip(value: Union[str, None]) -> str:
    """
    Wrapper seguro para .strip(), tolerante a None/tipos no-string.
    """
    return value.strip() if isinstance(value, str) else ''
