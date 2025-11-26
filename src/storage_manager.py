# src/storage_manager.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Tuple

from .utils.logger import get_logger
from .utils.naming import normalize_project_slug

# Intentamos usar tu módulo de rutas actual
try:
    from . import project_paths as paths
except ImportError:  # fallback por si el nombre cambia
    paths = None

logger = get_logger("storage")


class StorageManager:
    """
    Responsable de TODA la gestión de almacenamiento del scraper:

    - Dónde están los directorios base (root, data, store, logs).
    - Dónde vive pending_projects.json.
    - Cómo se nombran las carpetas de proyecto: {id}-{slug}.
    - Dónde se guarda el archivo de metadatos (data_project.txt).
    - Limpieza/borrado seguro de carpetas de proyecto.

    La idea es que:
      - bid_board_collector.py NO tenga que preocuparse por rutas.
      - project_processor.py solo diga: “dame carpeta y txt de este proyecto”.
      - pending_store.py use StorageManager para ubicar el JSON.
    """

    # Nombre de archivo estándar para metadatos del proyecto
    METADATA_FILENAME = "data_project.txt"

    def __init__(self, ensure_dirs: bool = True) -> None:
        # ----- Resolver rutas base desde project_paths.py (si existe) -----
        if paths is not None:
            self.root_dir: Path = getattr(
                paths, "ROOT_DIR", Path(__file__).resolve().parents[1]
            )
            self.data_dir: Path = getattr(
                paths, "DATA_DIR", self.root_dir / "data"
            )
            # Nuevo: carpeta de estado (cola, etc.)
            self.store_dir: Path = getattr(
                paths, "STORE_DIR", self.root_dir / "store"
            )
            # Opcional: logs dir, por si ya lo tienes en project_paths
            self.logs_dir: Path = getattr(
                paths, "LOGS_DIR", self.root_dir / "logs"
            )
        else:
            # Fallback muy defensivo
            self.root_dir = Path(__file__).resolve().parents[1]
            self.data_dir = self.root_dir / "data"
            self.store_dir = self.root_dir / "store"
            self.logs_dir = self.root_dir / "logs"

        if ensure_dirs:
            self._ensure_base_directories()

        logger.debug(f"[📁] ROOT_DIR:  {self.root_dir}")
        logger.debug(f"[📁] DATA_DIR:  {self.data_dir}")
        logger.debug(f"[📁] STORE_DIR: {self.store_dir}")
        logger.debug(f"[📁] LOGS_DIR:  {self.logs_dir}")

    # ------------------------------------------------------------------ #
    #     BASE DIRECTORIES & PENDING STORE
    # ------------------------------------------------------------------ #

    def _ensure_base_directories(self) -> None:
        """
        Asegura que las carpetas base existan:
        - data/
        - store/
        - logs/
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def pending_store_path(self) -> Path:
        """
        Ruta absoluta a store/pending_projects.json
        """
        return self.store_dir / "pending_projects.json"

    # ------------------------------------------------------------------ #
    #                       PROYECTOS INDIVIDUALES
    # ------------------------------------------------------------------ #

    def get_project_folder_name(self, project: Dict[str, Any]) -> str:
        """
        Devuelve el nombre de carpeta para un proyecto, con el formato:

            {id}-{slug}

        Ejemplo:
            id = 5, name = "Fowler Kia Windsor"
            → "5-Fowler_Kia_Windsor"
        """
        pid = project.get("id")
        try:
            pid_int = int(pid) if pid is not None else 0
        except (TypeError, ValueError):
            pid_int = 0

        raw_name = project.get("name") or "UnnamedProject"
        slug = normalize_project_slug(raw_name)
        return f"{pid_int}-{slug}"

    def get_project_dir(self, project: Dict[str, Any], create: bool = True) -> Path:
        """
        Devuelve la carpeta física del proyecto dentro de data/.

        Ejemplo:
            data/5-Fowler_Kia_Windsor/
        """
        folder_name = self.get_project_folder_name(project)
        project_dir = self.data_dir / folder_name

        if create:
            project_dir.mkdir(parents=True, exist_ok=True)

        return project_dir

    def get_project_metadata_path(self, project: Dict[str, Any]) -> Path:
        """
        Devuelve la ruta del archivo de metadatos para el proyecto:

            data/{id}-{slug}/data_project.txt
        """
        project_dir = self.get_project_dir(project, create=True)
        return project_dir / self.METADATA_FILENAME

    def get_project_paths(self, project: Dict[str, Any]) -> Tuple[Path, Path]:
        """
        Atajo conveniente: devuelve (project_dir, metadata_txt_path)

        - project_dir: data/{id}-{slug}/
        - metadata_txt_path: data/{id}-{slug}/data_project.txt
        """
        project_dir = self.get_project_dir(project, create=True)
        metadata_txt = project_dir / self.METADATA_FILENAME
        return project_dir, metadata_txt

    # ------------------------------------------------------------------ #
    #                       LIMPIEZA / UTILIDADES
    # ------------------------------------------------------------------ #

    def cleanup_project_dir(self, project: Dict[str, Any]) -> None:
        """
        Elimina COMPLETAMENTE la carpeta de un proyecto:

            data/{id}-{slug}/

        Se usa cuando:
        - Falla Fase 3 y quieres rollback (borrar lo descargado).
        - Hay datos corruptos y necesitas limpiar antes de reintentar.
        """
        import shutil

        project_dir = self.get_project_dir(project, create=False)

        if not project_dir.exists():
            logger.info(
                f"[🧹] No se encontró carpeta para el proyecto al intentar limpiarla: "
                f"{project_dir}"
            )
            return

        try:
            shutil.rmtree(project_dir)
            logger.info(
                f"[🧹] Carpeta de proyecto eliminada: {project_dir}"
            )
        except Exception as e:
            logger.warning(
                f"[⚠️] No se pudo eliminar la carpeta del proyecto {project_dir}: {e}"
            )

    def cleanup_project_dir_by_path(self, project_dir: Path) -> None:
        """
        Versión por Path directo (por si ya tienes el Path de la carpeta).
        Útil en código legado donde el directorio ya se ha construido.
        """
        import shutil

        if not project_dir.exists():
            logger.info(
                f"[🧹] No se encontró carpeta para limpiar: {project_dir}"
            )
            return

        try:
            shutil.rmtree(project_dir)
            logger.info(
                f"[🧹] Carpeta de proyecto eliminada: {project_dir}"
            )
        except Exception as e:
            logger.warning(
                f"[⚠️] No se pudo eliminar la carpeta del proyecto {project_dir}: {e}"
            )

    # ------------------------------------------------------------------ #
    #                  UTILIDADES VARIAS (OPCIONALES)
    # ------------------------------------------------------------------ #

    def list_project_dirs(self) -> list[Path]:
        """
        Devuelve una lista de todas las carpetas de proyecto en data/
        (útil para diagnósticos, scripts de mantenimiento, etc.).
        """
        if not self.data_dir.exists():
            return []

        return [
            p for p in self.data_dir.iterdir()
            if p.is_dir()
        ]

    def ensure_for_project(self, project: Dict[str, Any]) -> Tuple[Path, Path]:
        """
        Alias explícito para 'get_project_paths' que deja claro que:

        - Asegura que exista la carpeta del proyecto.
        - Devuelve (project_dir, metadata_txt_path).
        """
        return self.get_project_paths(project)
