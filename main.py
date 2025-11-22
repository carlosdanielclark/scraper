from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config import PIPELINE_URL
from src.auth_manager import AuthManager
from src.data_extractor import DataExtractor
from src.pending_store import PendingProjectStore
from src.paths import PENDING_JSON
from src.utils.logger import get_logger

logger = get_logger("main")


def main() -> None:
    """
    Flujo principal para la FASE 2:
    1. Autenticación en BuildingConnected
    2. Navegación al Bid Board y extracción de TODOS los proyectos válidos
    3. Registro/actualización en JSON persistente
    """
    store = PendingProjectStore(PENDING_JSON)

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
                logger.warning(
                    "[⚠️]Timeout en networkidle, esperando selector 'Undecided'."
                )
                page.wait_for_selector('text=Undecided', timeout=20000)

            # -------------------- FASE 2 -------------------- #
            extractor = DataExtractor(page)

            if not extractor.ensure_descending_due_date_order():
                logger.error("[❌] No se pudo asegurar orden descendente en 'Due Date'.")
                return

            project_summaries = extractor.get_valid_project_summaries()

            if not project_summaries:
                logger.warning("[⚠️] No hay proyectos con fecha futura.")
                return

            logger.info(
                f"[📊] Total proyectos válidos encontrados: {len(project_summaries)}"
            )

            # 👉 **SOLO ESTA INSTANCIA — YA CON RUTA ABSOLUTA**
            nuevos = store.add_or_update_projects(project_summaries)

            logger.info(
                f"[📦] JSON actualizado. Nuevos agregados: {nuevos} | Total: {len(store.projects)}"
            )

            logger.info("[⏹️] Fase 2 completada.")

        except Exception as e:
            logger.exception(f"[🔥] Error crítico: {str(e)}")
        finally:
            browser.close()
            logger.info("[CloseOperation] Navegador cerrado correctamente")


if __name__ == "__main__":
    main()
