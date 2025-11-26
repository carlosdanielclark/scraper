import re
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.utils.logger import get_logger

logger = get_logger("data")


def safe_strip(text: Optional[str]) -> str:
    return text.strip() if text else ""


def safe_click(locator, timeout: int = 3000, retries: int = 3) -> bool:
    for attempt in range(1, retries + 1):
        try:
            locator.click(timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"[⏳] Error al hacer click (intento {attempt}/{retries}): {str(e)}")
            time.sleep(0.5)
    return False


def normalize_date(date_str: str) -> str:
    date_str = safe_strip(date_str)
    if not date_str:
        raise ValueError("Fecha vacía")

    for fmt in ("%m/%d/%Y", "%m/%-d/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    m = re.search(r"([A-Za-z]+ \d{1,2}, \d{4})", date_str)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    raise ValueError(f"Fecha no válida o formato no soportado: {date_str}")


class BuildingConnectedBidBoardScraper:
    """
    Encapsula la lógica de extracción de datos desde el Bid Board.
    """

    _CHECKBOX_COL_INDEX = 0
    _ASSIGN_COL_INDEX = 1
    _NAME_COL_INDEX = 2
    _DUE_DATE_COL_INDEX = 3

    def __init__(self, page: Page) -> None:
        self.page = page
        self.today = datetime.today().date()

    def ensure_descending_due_date_order(self) -> bool:
        try:
            header = self.page.locator('div[role="columnheader"][aria-label="Due Date"]')
            if not header.is_visible(timeout=8000):
                logger.error("[❌] Columna 'Due Date' no visible en el DOM")
                return False

            sort_icon = header.locator('div.root-0-1-122.sorted-0-1-126')
            is_descending = sort_icon.locator(
                'span.ReactVirtualized__Table__headerTruncatedText[title="Due Date"]'
            ).count() > 0

            if is_descending:
                logger.info("[✅] Columna 'Due Date' ya está ordenada de forma descendente")
                return True

            for attempt in range(3):
                logger.info(f"[🔁] Ajustando orden de 'Due Date' (intento {attempt + 1}/3)")
                header.click()
                self.page.wait_for_timeout(1500)

                sort_icon = header.locator('div.root-0-1-122.sorted-0-1-126')
                is_descending = sort_icon.locator(
                    'span.ReactVirtualized__Table__headerTruncatedText[title="Due Date"]'
                ).count() > 0

                if is_descending:
                    logger.info("[✅] Columna 'Due Date' ajustada a orden descendente")
                    return True

            logger.warning("[⚠️] No se pudo asegurar orden descendente en 'Due Date'")
            return False

        except PlaywrightTimeoutError:
            logger.error("[❌] Timeout al intentar ajustar orden de 'Due Date'")
            return False
        except Exception as e:
            logger.error(f"[❌] Error inesperado al ajustar orden de 'Due Date': {str(e)}")
            return False

    def _get_table_container(self):
        """
        Localiza la tabla principal de ReactVirtualized en el Bid Board.
        """
        try:
            container = self.page.locator('div.ReactVirtualized__Table[role="grid"]').first
            if not container or container.count() == 0:
                logger.error("[❌] Contenedor de tabla ReactVirtualized__Table no encontrado")
                return None

            logger.debug("[✅] Contenedor de tabla ReactVirtualized localizado correctamente")
            return container
        except Exception as e:
            logger.error(f"[❌] Error localizando contenedor de tabla: {str(e)}")
            return None

    def _extract_clean_date_from_cell(self, date_cell) -> str:
        """
        Extrae la fecha limpia desde la celda de Due Date.
        """
        try:
            highlight_spans = date_cell.locator('[class*="highlightDate"] span')
            if highlight_spans.count() > 0:
                first_span = highlight_spans.nth(0)
                title_attr = first_span.get_attribute("title")
                date_text = safe_strip(first_span.text_content())
                logger.debug(
                    f"[📅] Fecha extraída de highlight span - title: {title_attr}, text: {date_text}"
                )
                return date_text

            date_text = safe_strip(date_cell.text_content())
            logger.debug(f"[📅] Texto crudo de celda de fecha: {date_text}")

            date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", date_text)
            if date_match:
                return date_match.group(1)

            return date_text

        except Exception as e:
            logger.debug(f"[⚠️] Error extrayendo fecha: {str(e)}")
            return ""

    def _scroll_to_bottom(self, scroll_container) -> None:
        try:
            self.page.evaluate(
                """
                (element) => {
                    element.scrollTop = element.scrollHeight;
                }
                """,
                scroll_container,
            )
            self.page.wait_for_timeout(1500)
        except Exception as e:
            logger.debug(f"[⚠️] Error al hacer scroll en contenedor: {str(e)}")

    # --------------------- FASE 2: RESUMEN DE BID BOARD --------------------- #

    def get_valid_project_summaries(self) -> List[Dict[str, Any]]:
        """
        Recorre todas las páginas del Bid Board (Undecided) y devuelve
        una lista de proyectos con:
            - name
            - due_date (YYYY-MM-DD)
            - url

        Solo incluye proyectos con fecha > hoy.
        NO entra a cada proyecto (Fase 3).
        """
        project_data: List[Dict[str, Any]] = []
        page_num = 1

        def wait_for_page_load():
            self.page.wait_for_timeout(1500)
            try:
                self.page.wait_for_selector(
                    'div.ReactVirtualized__Table[role="grid"]',
                    state="visible",
                    timeout=7000,
                )
                logger.debug("[✅] Tabla cargada correctamente")
            except PlaywrightTimeoutError:
                logger.warning(f"[⚠️] Timeout esperando tabla después de paginación")

        while True:
            logger.info(f"[🔍] Analizando página {page_num}...")

            table_container = self._get_table_container()
            if not table_container:
                logger.error("[❌] Contenedor de tabla no encontrado. Deteniendo extracción.")
                break

            rows = table_container.locator('div.ReactVirtualized__Table__row[role="row"]')
            row_count = rows.count()

            if row_count == 0:
                logger.warning(f"[⚠️] No se encontraron filas en la página {page_num}")
                if page_num == 1:
                    logger.info("[🔄] Intentando recargar página para cargar filas")
                    self.page.reload()
                    self.page.wait_for_timeout(3000)
                    continue
                else:
                    break

            logger.info(f"[📊] Encontradas {row_count} filas en página {page_num}")

            for i in range(row_count):
                row = rows.nth(i)
                try:
                    cells = row.locator(
                        'div.ReactVirtualized__Table__rowColumn[role="gridcell"]'
                    )
                    cell_count = cells.count()

                    if cell_count < 3:
                        logger.debug(
                            f"[⏭️] Fila {i + 1} tiene menos de 3 celdas ({cell_count}), omitiendo"
                        )
                        continue

                    date_cell = None
                    name_cell = None

                    # Detectamos columnas por contenido, no por índice
                    for j in range(cell_count):
                        cell = cells.nth(j)

                        if name_cell is None and cell.locator(
                            'a[href*="/opportunities/"]'
                        ).count() > 0:
                            name_cell = cell
                            continue

                        if date_cell is None and cell.locator(
                            '[class*="highlightDate"], [class*="two-row-cell__RootContainer"]'
                        ).count() > 0:
                            date_cell = cell
                            continue

                    if not date_cell or not name_cell:
                        logger.debug(
                            f"[⏭️] No se encontraron celdas de nombre o fecha en fila {i + 1}"
                        )
                        continue

                    project_name = safe_strip(name_cell.text_content())
                    logger.debug(f"[🔍] Nombre del proyecto en fila {i + 1}: {project_name}")

                    project_link = None
                    link_element = name_cell.locator('a[href*="/opportunities/"]')
                    if link_element.count() > 0:
                        href = link_element.first.get_attribute("href")
                        if href:
                            project_link = f"https://app.buildingconnected.com{href}"
                            logger.debug(
                                f"[🔗] Enlace encontrado para {project_name}: {project_link}"
                            )

                    raw_date_text = self._extract_clean_date_from_cell(date_cell)
                    logger.debug(f"[📅] Texto crudo de fecha en fila {i + 1}: '{raw_date_text}'")

                    if i < 3:
                        logger.debug(
                            f"[🔎 TEST] Fila {i + 1} -> project_name='{project_name}' | "
                            f"raw_date_text='{raw_date_text}'"
                        )

                    if not raw_date_text:
                        logger.debug(f"[⏭️] No se encontró texto de fecha en fila {i + 1}")
                        continue

                    try:
                        normalized_date = normalize_date(raw_date_text)
                        due_date_obj = datetime.strptime(normalized_date, "%Y-%m-%d").date()

                        logger.debug(
                            f"[🧮] Fila {i + 1} - Fecha normalizada: {normalized_date}, "
                            f"objeto fecha: {due_date_obj}, hoy: {self.today}"
                        )

                        if due_date_obj > self.today and project_link:
                            project_info = {
                                "name": project_name,
                                "due_date": normalized_date,
                                "url": project_link,
                            }
                            project_data.append(project_info)
                            logger.info(
                                f"[✅] Proyecto válido encontrado: {project_name} "
                                f"- Fecha: {normalized_date}"
                            )
                        else:
                            logger.debug(
                                f"[⏭️] Proyecto con fecha antigua o sin URL ({due_date_obj}), omitiendo"
                            )

                    except ValueError as ve:
                        logger.warning(
                            f"[⚠️] Error al procesar fecha '{raw_date_text}' en fila {i + 1}: {str(ve)}"
                        )
                except Exception as e:
                    logger.error(f"[❌] Error procesando fila {i + 1}: {str(e)}")

            # --------- PAGINACIÓN NUEVA (page-navigation / caret-right) --------- #
            navigation = self.page.locator('div[data-id="page-navigation"]')
            if navigation.count() == 0:
                logger.info("[ℹ️] Controles de paginación no encontrados, terminando recorrido.")
                break

            page_info_el = navigation.locator('div[data-id="page-count"]')
            if page_info_el.count() > 0:
                page_info_text = safe_strip(page_info_el.first.text_content())
                logger.debug(f"[ℹ️] Página actual según contador: '{page_info_text}'")

            next_button = navigation.locator('button[data-id="caret-right"]')
            if next_button.count() == 0:
                logger.info("[ℹ️] Botón 'caret-right' no encontrado, fin del recorrido.")
                break

            is_disabled = next_button.get_attribute("disabled")
            if is_disabled is not None:
                logger.info("[ℹ️] Ya estamos en la última página, fin del recorrido.")
                break

            logger.info("[➡️] Navegando a la siguiente página de Bid Board...")
            safe_click(next_button)
            page_num += 1
            wait_for_page_load()

        logger.info(f"[📈] Total de proyectos válidos encontrados: {len(project_data)}")
        return project_data

    # -------------------- MÉTODOS PARA FASES FUTURAS (3/4) -------------------- #

    def get_valid_project_links(self) -> List[str]:
        """
        Versión auxiliar que devuelve solo las URLs,
        utilizando la lógica de Fase 2.
        """
        summaries = self.get_valid_project_summaries()
        return [p["url"] for p in summaries if p.get("url")]

    def extract_metadata_from_project(self, project_url: str) -> Optional[Dict[str, Any]]:
        """
        FASE 3 (futuro): abrir cada proyecto y extraer metadatos detallados.
        Ahora mismo se mantiene para compatibilidad, pero no se usa en Fase 2.
        """
        try:
            logger.info(f"[🔗] Abriendo proyecto: {project_url}")
            self.page.goto(project_url)
            self.page.wait_for_timeout(3000)

            self.page.wait_for_selector('div[data-id="opportunity-details"]', timeout=10000)

            metadata: Dict[str, Any] = {
                "url": project_url,
                "name": "",
                "client": "",
                "location": "",
                "due_date": "",
                "scope": "",
            }

            try:
                title_el = self.page.locator('h1[data-id="opportunity-title"]')
                if title_el.count() > 0:
                    metadata["name"] = safe_strip(title_el.first.text_content())
            except Exception as e:
                logger.debug(f"[⚠️] No se pudo extraer título de proyecto: {str(e)}")

            logger.info(f"[✅] Metadatos extraídos para proyecto: {metadata['name']}")
            return metadata

        except PlaywrightTimeoutError:
            logger.error(f"[❌] Timeout cargando proyecto: {project_url}")
            return None
        except Exception as e:
            logger.error(
                f"[❌] Error inesperado extrayendo metadatos de proyecto {project_url}: {str(e)}"
            )
            return None

    def extract_all_projects_metadata(self) -> List[Dict[str, Any]]:
        """
        FASE 3 (futuro): usar get_valid_project_links y luego
        abrir cada proyecto. Por ahora, no se usa en Fase 2.
        """
        if not self.ensure_descending_due_date_order():
            logger.error("[❌] No se pudo asegurar orden descendente en 'Due Date', abortando pipeline.")
            return []

        valid_links = self.get_valid_project_links()
        results: List[Dict[str, Any]] = []

        if not valid_links:
            logger.warning("[⚠️] No se encontraron proyectos válidos para procesar")
            return results

        logger.info(f"[🚀] Iniciando extracción de metadatos para {len(valid_links)} proyectos")

        for url in valid_links:
            metadata = self.extract_metadata_from_project(url)
            if metadata:
                results.append(metadata)

        logger.info(f"[📊] Extracción completada: {len(results)}/{len(valid_links)} proyectos válidos")
        return results

    def extract_all_metadata(self) -> List[Dict[str, Any]]:
        """
        Wrapper de compatibilidad para código legado.
        Delegará en extract_all_projects_metadata (Fase 3).
        """
        return self.extract_all_projects_metadata()
