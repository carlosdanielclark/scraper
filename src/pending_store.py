import json
from pathlib import Path
from typing import List, Dict, Any
from src.utils.logger import get_logger
from src.paths import PENDING_JSON

logger = get_logger("pending")


class PendingProjectStore:
    """
    Gestiona un JSON persistente con proyectos pendientes de extracción.

    Cada entrada del JSON tiene estructura:
    {
        "url": "...",
        "name": "...",
        "due_date": "YYYY-MM-DD",
        "estado": "pendiente" | "extraido"
    }
    """

    def __init__(self, json_path: str = PENDING_JSON) -> None:
        # Ruta donde se guarda el JSON de proyectos pendientes
        self.path = Path(json_path)
        self.projects: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """
        Carga el JSON si existe, si no deja la lista vacía.
        """
        if not self.path.exists():
            logger.info(f"[📁] Archivo JSON de pendientes no existe, se creará: {self.path}")
            self.projects = []
            return

        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.projects = data
                else:
                    logger.warning("[⚠️] Formato de JSON inesperado, se inicializa lista vacía")
                    self.projects = []
        except Exception as e:
            logger.error(f"[❌] Error leyendo JSON de pendientes: {e}")
            self.projects = []

    def _save(self) -> None:
        """
        Guarda la lista actual de proyectos al archivo JSON.
        """
        try:
            with self.path.open("w", encoding="utf-8") as f:
                json.dump(self.projects, f, ensure_ascii=False, indent=2)
            logger.info(f"[💾] JSON de proyectos pendientes actualizado: {self.path}")
        except Exception as e:
            logger.error(f"[❌] Error escribiendo JSON de pendientes: {e}")

    def add_or_update_projects(self, new_projects: List[Dict[str, Any]]) -> int:
        """
        Agrega proyectos nuevos evitando duplicados por URL.
        Actualiza nombre/fecha si la URL ya existe, preservando el estado.

        Args:
            new_projects: lista de dicts con keys al menos: url, name, due_date

        Returns:
            int: número de proyectos realmente nuevos agregados.
        """
        # Índice rápido por URL para búsquedas O(1)
        index_by_url = {p.get("url"): i for i, p in enumerate(self.projects) if p.get("url")}
        nuevos = 0

        for p in new_projects:
            url = p.get("url")
            if not url:
                continue

            if url in index_by_url:
                # Ya existe → solo actualizamos nombre/fecha si vinieron
                idx = index_by_url[url]
                existing = self.projects[idx]
                name = p.get("name")
                due_date = p.get("due_date")

                if name:
                    existing["name"] = name
                if due_date:
                    existing["due_date"] = due_date

                # NO tocamos "estado", se mantiene (pendiente/extraido)
            else:
                # Nuevo proyecto → lo registramos como pendiente
                project_entry = {
                    "url": url,
                    "name": p.get("name", ""),
                    "due_date": p.get("due_date", ""),
                    "estado": "pendiente",  # estado inicial
                }
                self.projects.append(project_entry)
                index_by_url[url] = len(self.projects) - 1
                nuevos += 1

        if nuevos > 0:
            self._save()

        return nuevos

    def get_pending_projects(self) -> List[Dict[str, Any]]:
        """
        Devuelve la lista de proyectos con estado 'pendiente'.
        (Esto será útil para Fase 3.)
        """
        return [p for p in self.projects if p.get("estado") == "pendiente"]
