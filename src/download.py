# src/download.py

from pathlib import Path
from typing import Any, Dict

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.utils.logger import get_logger

logger = get_logger("download")


class DownloadCanceledError(Exception):
    """
    Error específico para indicar que la descarga fue cancelada
    (por ejemplo: Download.save_as: canceled).
    Se usa para aplicar una política distinta en Fase 3.
    """
    pass


class ProjectFilesDownloader:
    def __init__(self, page: Page) -> None:
        self.page = page

    def download_all_for_project(
        self,
        project: Dict[str, Any],
        project_dir: Path,
        max_retries: int = 2,   # al menos 1 reintento (2 intentos total)
    ) -> bool:
        """
        Flujo completo de descarga para un proyecto (vista Files + Download All).

        Reintenta automáticamente en caso de Download.save_as: canceled
        hasta max_retries veces. Si tras los reintentos sigue fallando por
        cancelación, se vuelve a lanzar DownloadCanceledError para que la
        Fase 3 aplique su política (rollback, marcar 'pendiente', etc.).
        """
        project_url = project.get("url") or ""
        if not project_url:
            logger.error("[❌] Proyecto sin URL, no se puede descargar.")
            return False

        files_url = self._build_files_url(project_url)
        logger.info(f"[🌐] Vista 'Files' del proyecto: {files_url}")

        try:
            self.page.goto(files_url, timeout=60000)
            try:
                self.page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                logger.warning(
                    "[[WARN]] Timeout en networkidle al cargar 'Files', "
                    "continuando con el DOM actual."
                )

            files_ok = self._ensure_files_view()
            if not files_ok:
                logger.warning(
                    "[⚠️] No se pudo confirmar completamente la vista Files. "
                    "Se intentará igualmente localizar 'Download All'."
                )

            # ---------- Bloque con reintento específico para cancelación ---------- #
            attempt = 0
            while attempt < max_retries:
                attempt += 1
                try:
                    logger.info(f"[⬇️] Intento de descarga (Download All) #{attempt}/{max_retries}...")
                    success = self._perform_download_all(project_dir)

                    if success:
                        logger.info(
                            "[✅] Descarga (Download All) completada con éxito "
                            f"en el intento #{attempt}."
                        )
                        return True

                    # Si _perform_download_all devuelve False sin lanzar excepción,
                    # no hay motivo claro para reintentar automáticamente.
                    logger.warning(
                        "[[WARN]] _perform_download_all devolvió False sin excepción. "
                        "No se reintentará de forma automática."
                    )
                    return False

                except DownloadCanceledError as e:
                    if attempt < max_retries:
                        logger.warning(
                            "[🔁] Descarga cancelada (Download.save_as: canceled). "
                            f"Reintentando (intento {attempt + 1}/{max_retries})..."
                        )
                        # Pequeña pausa opcional entre reintentos
                        self.page.wait_for_timeout(2000)
                        continue
                    else:
                        logger.error(
                            "[❌] Descarga cancelada repetidamente. "
                            "Se han agotado los reintentos."
                        )
                        # Repropagamos para que la Fase 3 aplique política especial.
                        raise

        except DownloadCanceledError:
            # Se deja que Fase 3 maneje la cancelación definitiva (rollback, etc.)
            raise

        except Exception as e:
            logger.exception(f"[🔥] Error crítico en descarga para proyecto: {e}")
            return False