# src/utils/naming.py

import re
from typing import Optional


def normalize_project_slug(raw: Optional[str], max_len: int = 60) -> str:
    """
    Normaliza el nombre del proyecto para usarlo en carpetas y archivos.

    Reglas:
    - Si el nombre está vacío → "project".
    - Reemplaza símbolos comunes (-_,:/\() por espacios.
    - Reduce múltiples espacios.
    - Toma solo las primeras 2 palabras.
    - Une con guion '-'.
    - Elimina caracteres no alfanuméricos en el slug final.
    - Recorta a max_len caracteres.
    """
    if not raw:
        return "project"

    # 1) Reemplazar símbolos por espacios
    cleaned = re.sub(r"[-_,:/\\()]+", " ", raw)

    # 2) Normalizar espacios
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return "project"

    # 3) Partir en palabras
    words = cleaned.split(" ")

    if len(words) == 1:
        base = words[0]
    elif len(words) == 2:
        base = f"{words[0]}-{words[1]}"
    else:
        base = f"{words[0]}-{words[1]}-{words[2]}"

    # 4) Eliminar caracteres raros del slug
    slug = re.sub(r"[^A-Za-z0-9_\-]", "", base)

    if not slug:
        slug = "project"

    # 5) Recortar
    if len(slug) > max_len:
        slug = slug[:max_len]

    return slug
