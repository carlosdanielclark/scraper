import json
from pathlib import Path
from typing import Optional, Dict, Any, List
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
        Actualiza nombre/fecha si la URL ya existe.

        Reglas:
        - Buscar siempre por URL.
        - Si la URL ya existe:
            - Actualizar name y due_date si vienen en new_projects.
            - Verificar que tenga 'id'; si no, asignar uno nuevo.
            - No tocar 'estado'.
        - Si la URL NO existe:
            - Asignar nuevo id incremental.
            - Guardar url, name, due_date.
            - Poner estado="pendiente".
        """
        # Índice rápido por URL
        index_by_url = {p.get("url"): i for i, p in enumerate(self.projects) if p.get("url")}

        # Obtener el máximo ID existente (para nuevos ids o legacy sin id)
        max_id = 0
        for p in self.projects:
            pid = p.get("id")
            if isinstance(pid, int) and pid > max_id:
                max_id = pid

        nuevos = 0
        cambios_en_existentes = False

        for p in new_projects:
            url = p.get("url")
            if not url:
                continue

            name = p.get("name")
            due_date = p.get("due_date")

            if url in index_by_url:
                # Ya existe → actualizamos nombre/fecha y aseguramos que tenga id
                idx = index_by_url[url]
                existing = self.projects[idx]

                if name:
                    existing["name"] = name
                if due_date:
                    existing["due_date"] = due_date

                # Si el proyecto legacy no tenía id, se lo asignamos ahora
                if not isinstance(existing.get("id"), int):
                    max_id += 1
                    existing["id"] = max_id
                    logger.info(
                        f"[🆔] Proyecto con URL existente pero sin id, asignando id={max_id}"
                    )

                cambios_en_existentes = True
            else:
                # Proyecto NUEVO
                max_id += 1  # Nuevo ID secuencial

                project_entry = {
                    "id": max_id,
                    "url": url,
                    "name": name or "",
                    "due_date": due_date or "",
                    "estado": "pendiente",
                }

                self.projects.append(project_entry)
                index_by_url[url] = len(self.projects) - 1
                nuevos += 1

        # Guardar si hay nuevos o cambios en existentes
        if nuevos > 0 or cambios_en_existentes:
            self._save()

        return nuevos


    def get_pending_projects(self) -> List[Dict[str, Any]]:
        """
        Devuelve la lista de proyectos con estado 'pendiente'.
        (Esto será útil para Fase 3.)
        """
        return [p for p in self.projects if p.get("estado") == "pendiente"]

    def get_project_by_id(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Devuelve el proyecto cuyo campo 'id' coincide con project_id.
        Si no existe, devuelve None.
        """
        for project in self.projects:
            pid = project.get("id")
            if isinstance(pid, int) and pid == project_id:
                return project
        return None

    def update_project_state(self, project_id: int, new_state: str) -> bool:
        """
        Actualiza el campo 'estado' de un proyecto por id y guarda el JSON.
        Devuelve True si se encontró y actualizó, False si no.
        """
        for p in self.projects:
            pid = p.get("id")
            if isinstance(pid, int) and pid == project_id:
                p["estado"] = new_state
                self._save()
                logger.info(
                    f"[🔖] Proyecto id={project_id} actualizado a estado='{new_state}'"
                )
                return True

        logger.warning(
            f"[⚠️] No se encontró proyecto con id={project_id} para actualizar estado."
        )
        return False

    # Alias para no romper código viejo
    def update_project_status(self, project_id: int, new_status: str) -> bool:
        """
        Alias de compatibilidad. Delegamos en update_project_state.
        """
        return self.update_project_state(project_id, new_status)
