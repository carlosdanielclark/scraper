import argparse
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from src.auth_manager import AuthManager
from src.metadata_extractor import ProjectMetadataExtractor
from src.download import ProjectFilesDownloader, DownloadCanceledError
from src.pending_store import PendingProjectStore
from src.paths import DATA_DIR
from src.utils.logger import get_logger
from src.utils.naming import normalize_project_slug

logger = get_logger("phase3")


# ------------------------- HELPERS SELECCIÓN ------------------------- #

def select_next_project(
    store: PendingProjectStore,
    preferred_id: Optional[int],
) -> Optional[Dict[str, Any]]:
    """
    Selecciona el próximo proyecto a procesar:

    - Si 'preferred_id' está definido (solo la primera iteración), busca ese ID.
    - Si no, toma el primer proyecto con estado 'pendiente'.

    Si no hay proyectos pendientes, devuelve None.
    """
    if preferred_id is not None:
        project = store.get_project_by_id(preferred_id)
        if not project:
            logger.error(
                f"[❌] No se encontró proyecto con id={preferred_id} "
                f"en pending_projects.json"
            )
            return None
        if project.get("estado") != "pendiente":
            logger.warning(
                f"[⚠️] Proyecto id={preferred_id} no está en estado 'pendiente' "
                f"(estado actual: {project.get('estado')})."
            )
            return None
        logger.info(f"[🎯] Proyecto seleccionado por ID: {preferred_id}")
        return project

    pending = store.get_pending_projects()
    if not pending:
        logger.info(
            "[ℹ️] No hay proyectos con estado 'pendiente' en pending_projects.json"
        )
        return None

    project = pending[0]
    logger.info(
        f"[🎯] Proyecto seleccionado (primer pendiente): {project.get('name')}"
    )
    return project


def build_info_url(project_url: str) -> str:
    """
    Construye la URL de 'info' del proyecto a partir de la URL base.
    """
    if project_url.endswith("/info"):
        return project_url
    if project_url.endswith("/files"):
        return project_url[:-5] + "info"
    if project_url.endswith("/"):
        return project_url + "info"
    return project_url + "/info"


def build_project_paths(project: Dict[str, Any]) -> tuple[Path, Path]:
    """
    Construye:
      - Carpeta del proyecto: data/projects/{id_padded}_{slug}
      - Archivo txt:         {id_padded}_{slug}.txt

    El slug usa como máximo las 2 primeras palabras del nombre del proyecto.
    """
    project_id = project.get("id")
    if not isinstance(project_id, int):
        project_id = 0  # fallback, pero idealmente siempre habrá id

    id_padded = f"{project_id:03d}"
    name = project.get("name") or "UnnamedProject"
    slug = normalize_project_slug(name)

    folder_name = f"{id_padded}_{slug}"
    projects_base_dir = DATA_DIR / "projects"
    projects_base_dir.mkdir(parents=True, exist_ok=True)

    project_dir = projects_base_dir / folder_name
    project_dir.mkdir(parents=True, exist_ok=True)

    txt_path = project_dir / f"{folder_name}.txt"

    logger.debug(f"[🗂️] Carpeta de proyecto: {project_dir}")
    logger.debug(f"[📄] Archivo txt: {txt_path}")

    return project_dir, txt_path


def cleanup_project_dir(project_dir: Path) -> None:
    """
    Elimina por completo la carpeta del proyecto si existe.
    """
    try:
        if project_dir.exists():
            shutil.rmtree(project_dir)
            logger.info(
                f"[🧹] Carpeta de proyecto eliminada por fallo en Fase 3: {project_dir}"
            )
    except Exception as e:
        logger.warning(
            f"[⚠️] No se pudo eliminar la carpeta del proyecto {project_dir}: {e}"
        )


# ------------------------- TXT DE METADATOS ------------------------- #

def format_metadata_txt(project: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    """
    Construye el contenido del archivo .txt para el proyecto.
    """
    project_id = project.get("id", "")
    url = project.get("url", "")
    project_display_name = project.get("name", "")

    client = metadata.get("client") or {}
    name = client.get("name") or ""
    email = client.get("email") or ""
    phone = client.get("phone") or ""

    date_due = metadata.get("date_due") or ""
    project_name = metadata.get("project_name") or ""
    location = metadata.get("location") or ""
    project_size = metadata.get("project_size") or ""
    project_info = metadata.get("project_information") or ""

    lines: list[str] = []
    lines.append(f"ID: {project_id}")
    lines.append(f"Project URL: {url}")
    lines.append(f"Project (Bid Board Name): {project_display_name}")
    lines.append("")
    lines.append("{")
    lines.append("  Client: {")
    lines.append(f"    Name:  {name}")
    lines.append(f"    Email: {email}")
    lines.append(f"    Phone: {phone}")
    lines.append("  }")
    lines.append(f"  Date Due:           {date_due}")
    lines.append(f"  Project Name:       {project_name}")
    lines.append(f"  Location:           {location}")
    lines.append(f"  Project Size:       {project_size}")
    lines.append(
        f"  Project Information:{(' ' + project_info) if project_info else ''}"
    )
    lines.append("}")

    return "\n".join(lines)


# --------------------- PROCESO DE UN PROYECTO ---------------------- #

def process_single_project(
    page,
    store: PendingProjectStore,
    project: Dict[str, Any],
) -> bool:
    """
    Procesa COMPLETAMENTE un proyecto en Fase 3:

    - Cambia estado a 'en-proceso' al inicio.
    - Extrae metadatos y genera .txt.
    - Descarga archivos (Download All) en la carpeta del proyecto.
    - Si todo sale bien:
        - Estado → 'descargado'
        - Se conserva la carpeta.
    - Si falla por descarga cancelada (DownloadCanceledError) después de reintentos:
        - Estado → 'error'
        - Se elimina la carpeta.
        - Devuelve False, pero el lazo principal continuará con el siguiente proyecto.
    - Si falla por otro motivo (metadatos vacíos, descarga False, excepción general):
        - Estado → 'pendiente'
        - Se elimina la carpeta.
        - Devuelve False y el lazo principal se detendrá.
    """
    project_id = project.get("id")
    if not isinstance(project_id, int):
        logger.warning(
            "[⚠️] Proyecto sin 'id' numérico. Esto no debería pasar."
        )
        project_id = 0

    # ---- Estado: EN PROCESO ----
    store.update_project_state(project_id, "en-proceso")

    project_dir, txt_path = build_project_paths(project)

    project_url = project.get("url") or ""
    if not project_url:
        logger.error("[❌] Proyecto sin URL, no se puede procesar Fase 3.")
        store.update_project_state(project_id, "pendiente")
        cleanup_project_dir(project_dir)
        return False

    info_url = build_info_url(project_url)
    logger.info(f"[🌐] URL de info del proyecto: {info_url}")

    try:
        # --- METADATOS ---
        logger.info(
            f"[🌐] Navegando a página de info del proyecto: {info_url}"
        )
        page.goto(info_url, timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except PlaywrightTimeoutError:
            logger.warning(
                "[[WARN]] Timeout en networkidle al cargar 'info', "
                "continuando con el DOM actual."
            )

        metadata_extractor = ProjectMetadataExtractor(page)
        metadata = metadata_extractor.extract()

        txt_content = format_metadata_txt(project, metadata)
        txt_path.write_text(txt_content, encoding="utf-8")
        logger.info(f"[💾] Archivo de metadatos guardado en: {txt_path}")

        metadata_ok = bool(metadata.get("project_name"))

        # --- DESCARGA ---
        downloader = ProjectFilesDownloader(page)

        try:
            download_ok = downloader.download_all_for_project(project, project_dir)
        except DownloadCanceledError:
            # Política especial: cancelación repetida tras reintentos
            logger.warning(
                "[⚠️] Descarga cancelada para este proyecto "
                "(Download.save_as: canceled tras reintentos). "
                "Se marcará como 'error' y se limpiará la carpeta, "
                "luego se continuará con el siguiente."
            )
            store.update_project_state(project_id, "error")
            cleanup_project_dir(project_dir)
            return False

        if metadata_ok and download_ok:
            # ---- Estado: DESCARGADO ----
            store.update_project_state(project_id, "descargado")
            logger.info(
                "[✅] Fase 3 completada para este proyecto: "
                "metadatos + descarga OK. "
                "Proyecto marcado como 'descargado'."
            )
            return True

        # Otros fallos (ej: descarga False sin ser cancelada, metadatos vacíos, etc.)
        logger.warning(
            "[⚠️] Fase 3 NO completó todos los pasos para este proyecto "
            f"(metadata_ok={metadata_ok}, download_ok={download_ok}). "
            "Se revertirá el estado a 'pendiente' y se limpiará la carpeta."
        )
        store.update_project_state(project_id, "pendiente")
        cleanup_project_dir(project_dir)
        return False

    except Exception as e:
        logger.exception(
            f"[🔥] Error crítico procesando proyecto id={project_id}: {e}"
        )
        store.update_project_state(project_id, "pendiente")
        cleanup_project_dir(project_dir)
        return False


# ----------------------------- ENTRY POINT ------------------------------ #

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fase 3 continua: metadatos + descarga para todos los proyectos "
            "pendientes, uno por uno, en modo automático."
        )
    )
    parser.add_argument(
        "--project-id",
        type=int,
        default=None,
        help=(
            "ID del primer proyecto a procesar en pending_projects.json. "
            "Luego continúa con el resto de 'pendiente'."
        ),
    )
    args = parser.parse_args()

    store = PendingProjectStore()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            auth_manager = AuthManager(page)
            if not auth_manager.login():
                logger.critical("[❌] Autenticación fallida. Deteniendo Fase 3.")
                return

            logger.info(
                "[✅] Autenticación exitosa. Iniciando procesamiento automático de proyectos..."
            )

            preferred_id: Optional[int] = args.project_id

            while True:
                project = select_next_project(store, preferred_id)
                preferred_id = None  # solo se usa en la primera iteración

                if not project:
                    logger.info(
                        "[✅] No hay más proyectos 'pendiente' para procesar. "
                        "Fase 3 finalizada."
                    )
                    break

                project_id = project.get("id")
                logger.info(
                    f"[▶️] Iniciando Fase 3 para proyecto id={project_id}: "
                    f"{project.get('name')}"
                )

                success = process_single_project(page, store, project)

                remaining = store.get_pending_projects()
                remaining_count = len(remaining)

                if success:
                    logger.info(
                        f"[✅] Proyecto id={project_id} completado. "
                        f"Proyectos pendientes restantes: {remaining_count}"
                    )
                    continue

                # Si NO tuvo éxito, diferenciamos por estado actual
                refreshed = store.get_project_by_id(project_id)
                estado_actual = refreshed.get("estado") if refreshed else None

                if estado_actual == "error":
                    # Política: casos 'error' (descarga cancelada repetida)
                    # se saltan y se continúa con el siguiente.
                    logger.warning(
                        f"[⚠️] Proyecto id={project_id} marcado como 'error' "
                        f"(descarga cancelada). Se continuará con el siguiente. "
                        f"Proyectos pendientes restantes: {remaining_count}"
                    )
                    continue

                # Cualquier otro fallo se toma como crítico: detenemos Fase 3
                logger.warning(
                    f"[⚠️] Proyecto id={project_id} NO se completó correctamente "
                    f"(estado actual: {estado_actual}). "
                    f"Se detiene Fase 3 para evitar bucles de error. "
                    f"Proyectos pendientes restantes: {remaining_count}"
                )
                break

        finally:
            browser.close()
            logger.info("[CloseOperation] Navegador cerrado correctamente")


if __name__ == "__main__":
    main()
