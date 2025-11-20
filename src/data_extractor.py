from datetime import datetime
from typing import Dict, List, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config import MISSING_PHONE_PLACEHOLDER, PROJECT_FIELDS, Selectors
from src.validation import extract_phone_from_text, normalize_date, safe_strip, validate_project_data
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DataExtractor:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.today = datetime.today().date()
        self.base_url = "https://app.buildingconnected.com"  # Mejor leer desde config

    def ensure_descending_due_date_order(self) -> bool:
        try:
            header = self.page.locator(Selectors.DUE_DATE_HEADER)
            if not header.is_visible(timeout=5000):
                logger.error("[❌] Columna 'Due Date' no visible en pipeline")
                return False

            sort_state = header.get_attribute("aria-sort")
            if sort_state == "ascending":
                header.click()
                self.page.wait_for_timeout(1000)
                logger.info("[🔄] Orden de fechas invertido a descendente")
                return True

            if sort_state == "descending":
                logger.debug("[✓] Orden de fechas ya es descendente")
                return True

            logger.warning("[⚠️] Estado de orden desconocido para Due Date")
            return False

        except PlaywrightTimeoutError:
            logger.error("[❌] Timeout esperando columna 'Due Date'")
            return False

    def get_valid_project_links(self) -> List[str]:
        if not self.ensure_descending_due_date_order():
            logger.error("[❌] No se pudo garantizar orden descendente de fechas")
            return []

        project_links = []
        rows = self.page.locator("tr.opportunity-row")
        row_count = rows.count()

        logger.info(f"[🔍] Analizando {row_count} proyectos en pipeline")

        for i in range(row_count):
            row = rows.nth(i)
            due_date_cell = row.locator("td:nth-child(3)")

            try:
                due_date_text = safe_strip(due_date_cell.text_content())
                if not due_date_text:
                    logger.warning(f"[⚠️] Fila {i+1} sin fecha, saltando o deteniendo")
                    continue  # o break si quieres detener

                normalized_date = normalize_date(due_date_text)
                due_date_obj = datetime.strptime(normalized_date, "%Y-%m-%d").date()

                if due_date_obj <= self.today:
                    logger.debug(f"[⏭️] Fecha antigua {normalized_date}, cortando iteración")
                    break

                link = row.locator(Selectors.PROJECT_LINKS).get_attribute("href")
                if link:
                    full_url = f"{self.base_url}{link}"
                    project_links.append(full_url)
                    logger.debug(f"[➕] Proyecto válido encontrado: {full_url}")

            except (ValueError, PlaywrightTimeoutError) as e:
                logger.warning(f"[⚠️] Error en fila {i+1}: {str(e)}")
                continue

        logger.info(f"[✅] {len(project_links)} proyectos válidos identificados")
        return project_links

    def extract_metadata_from_project(self, project_url: str) -> Optional[Dict[str, str]]:
        try:
            self.page.goto(project_url, timeout=10000)
            self.page.wait_for_selector(Selectors.PROJECT_NAME, timeout=5000)

            metadata = {
                "project_name": safe_strip(self.page.locator(Selectors.PROJECT_NAME).text_content()),
                "due_date": safe_strip(self.page.locator(Selectors.DUE_DATE).text_content()),
                "project_size": safe_strip(self.page.locator(Selectors.PROJECT_SIZE).text_content()),
                "location": safe_strip(self.page.locator(Selectors.LOCATION).text_content()),
                "client": safe_strip(self.page.locator(Selectors.CLIENT).text_content()),
                "phone": ""
            }

            phone_element = self.page.locator(Selectors.PHONE)
            if phone_element.count() > 0:
                phone_text = safe_strip(phone_element.text_content() or "")
                metadata["phone"] = extract_phone_from_text(phone_text)
            else:
                metadata["phone"] = MISSING_PHONE_PLACEHOLDER
                logger.warning(f"[⚠️] Teléfono no encontrado en: {metadata['project_name']}")

            is_valid, error_msg = validate_project_data(metadata, PROJECT_FIELDS)
            if not is_valid:
                logger.error(f"[❌] Validación fallida para {project_url}: {error_msg}")
                return None

            logger.info(f"[✅] Proyecto procesado: {metadata['project_name']} - {metadata['due_date']}")
            return metadata

        except PlaywrightTimeoutError:
            logger.error(f"[❌] Timeout al acceder a proyecto: {project_url}")
            return None
        except Exception as e:
            logger.exception(f"[🔥] Error inesperado en {project_url}: {str(e)}")
            return None

    def extract_all_metadata(self) -> List[Dict[str, str]]:
        valid_projects = self.get_valid_project_links()
        results = []

        for url in valid_projects:
            metadata = self.extract_metadata_from_project(url)
            if metadata:
                results.append(metadata)

        logger.info(f"[📊] Extracción completada: {len(results)}/{len(valid_projects)} proyectos válidos")
        return results
