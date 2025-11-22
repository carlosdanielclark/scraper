import json
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config import PIPELINE_URL
from src.auth_manager import AuthManager
from src.data_extractor import DataExtractor
from src.pending_store import PendingProjectStore
from src.utils.logger import get_logger

logger = get_logger("main")


def main() -> None:
    """
    Flujo principal orquestado para la FASE 2 del proyecto.

    Fases manejadas aquí:
    1. Autenticación persistente en BuildingConnected.
    2. Navegación al Bid Board (pipeline) y listado de TODOS los proyectos
       visibles (todas las páginas de la paginación) con:
          - nombre
          - due_date normalizada (YYYY-MM-DD)
          - url absoluta
       Solo se consideran proyectos con fecha de entrega > hoy.
    3. Registro/actualización en un JSON persistente de proyectos pendientes
       (pending_projects.json) sin entrar todavía a cada proyecto.

    Importante:
    - NO se realiza aún la Fase 3 (extracción detallada ni descarga de archivos).
    - El JSON almacena los proyectos con un campo "estado" = "pendiente" | "extraido".
    - Para Fase 3 se leerán los proyectos con estado "pendiente" desde este JSON.
    """
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context()
        page = context.new_page()

        try:
            # -------------------- FASE 1: AUTENTICACIÓN -------------------- #
            auth_manager = AuthManager(page)
            if not auth_manager.login():
                logger.critical("[❌] Autenticación fallida. Deteniendo ejecución.")
                return

            logger.info("[✅] Autenticación exitosa. Navegando a pipeline...")
            page.goto(PIPELINE_URL, timeout=30000)

            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                logger.warning("[⚠️]"
                    "Timeout en wait_for_load_state('networkidle'), "
                    "intentando esperar selector visible 'Undecided'"
                )
                # Elemento clave para confirmar que cargó el Bid Board
                page.wait_for_selector('text=Undecided', timeout=20000)

            # -------------------- FASE 2: LISTADO + JSON -------------------- #
            extractor = DataExtractor(page)

            # 1) Asegurar que la columna "Due Date" esté en orden descendente
            if not extractor.ensure_descending_due_date_order():
                logger.error(
                    "[❌] No se pudo asegurar orden descendente en 'Due Date'. "
                    "Abandonando Fase 2."
                )
                return

            # 2) Obtener resumen de TODOS los proyectos válidos (todas las páginas)
            project_summaries = extractor.get_valid_project_summaries()

            if not project_summaries:
                logger.warning(
                    "[⚠️] No se encontraron proyectos con fecha futura en el Bid Board. "
                    "Nada que registrar en JSON."
                )
                return

            logger.info(f"[📊] Total de proyectos válidos encontrados en Bid Board: "
                        f"{len(project_summaries)}")

            # 3) Registrar/actualizar proyectos en el JSON persistente
            store = PendingProjectStore("pending_projects.json")
            nuevos = store.add_or_update_projects(project_summaries)

            logger.info(
                f"[📦] JSON actualizado. Proyectos encontrados en esta ejecución: "
                f"{len(project_summaries)} | Nuevos agregados: {nuevos} | "
                f"Total en JSON: {len(store.projects)}"
            )

            logger.info(
                "[⏹️] Fase 2 completada. Los proyectos 'pendientes' quedarán listos para "
                "la futura Fase 3 (extracción detallada y descargas)."
            )

        except Exception as e:
            logger.exception(f"[🔥] Error crítico en flujo principal: {str(e)}")
        finally:
            browser.close()
            logger.info("[CloseOperation] Navegador cerrado correctamente")


if __name__ == "__main__":
    main()
