# src/project_downloader.py
from pathlib import Path
from typing import Any, Dict
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.utils.logger import get_logger

logger = get_logger("download")


class DownloadCanceledError(Exception):
    """
    Error específico para indicar que la descarga fue cancelada
    (por ejemplo: Download.save_as: canceled).
    """
    pass


class DiskFullError(Exception):
    """
    Error específico para indicar que no hay espacio en disco (errno 28).
    Se usa para:
    - marcar el proyecto como 'error'
    - detener Fase 3 con un mensaje claro
    """
    pass


class BuildingConnectedProjectDownloader:
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
        hasta max_retries veces.

        - Si tras los reintentos sigue fallando por cancelación:
            → lanza DownloadCanceledError.
        - Si detecta error de disco lleno (errno 28):
            → lanza DiskFullError (NO reintenta).
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
                    logger.info(
                        f"[⬇️] Intento de descarga (Download All) "
                        f"#{attempt}/{max_retries}..."
                    )
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

                except DownloadCanceledError:
                    if attempt < max_retries:
                        logger.warning(
                            "[🔁] Descarga cancelada (Download.save_as: canceled). "
                            f"Reintentando (intento {attempt + 1}/{max_retries})..."
                        )
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

        except DiskFullError:
            # Se deja que Fase 3 decida si parar completamente
            raise

        except Exception as e:
            logger.exception(f"[🔥] Error crítico en descarga para proyecto: {e}")
            return False

    def _build_files_url(self, project_url: str) -> str:
        """
        Construye la URL de 'Files' a partir de la URL base del proyecto.
        """
        if project_url.endswith("/files"):
            return project_url
        if project_url.endswith("/info"):
            return project_url[:-5] + "files"
        if project_url.endswith("/"):
            return project_url + "files"
        return project_url + "/files"

    # ------------------------------------------------------------------ #
    #                 MÉTODOS PRIVADOS DE APOYO
    # ------------------------------------------------------------------ #

    def _ensure_files_view(self) -> bool:
        """
        Intenta asegurar que estamos realmente en la vista 'Files'.
        """
        try:
            files_tab = self.page.locator("text=Files")
            if files_tab.first.is_visible():
                logger.info("[📁] Pestaña 'Files' visible, intentando activarla...")
                try:
                    files_tab.first.click(timeout=5000)
                except Exception:
                    logger.warning("[⚠️] No se pudo hacer click en la pestaña 'Files'.")
        except Exception:
            logger.debug(
                "[DEBUG] No se pudo verificar/clickear la pestaña 'Files', "
                "se continuará igualmente."
            )

        try:
            download_btn = self.page.locator("text=Download All")
            self.page.wait_for_timeout(1000)
            if download_btn.first.is_visible():
                logger.info("[📥] Botón 'Download All' localizado en la vista Files.")
                return True
            else:
                logger.warning(
                    "[⚠️] Botón 'Download All' no visible aunque la página cargó."
                )
                return False
        except Exception as e:
            logger.warning(
                f"[⚠️] No se pudo confirmar la presencia de 'Download All': {e}"
            )
            return False

    def _perform_download_all(self, project_dir: Path) -> bool:
        """
        Ejecuta el click en 'Download All' y maneja la descarga.

        - Si todo va bien → True.
        - Si timeout u otro fallo “normal” → False.
        - Si detecta:
            * Download.save_as: canceled → DownloadCanceledError
            * errno 28 (No space left on device) → DiskFullError
        """
        import os

        project_dir.mkdir(parents=True, exist_ok=True)

        download_button = self.page.locator("text=Download All")

        if not download_button.first.is_visible():
            logger.error(
                "[❌] Botón 'Download All' no visible, no se puede iniciar la descarga."
            )
            return False

        try:
            with self.page.expect_download(timeout=120000) as download_info:
                download_button.first.click()

            download = download_info.value
            suggested_name = download.suggested_filename or "project_files.zip"
            destination = project_dir / suggested_name

            logger.info(f"[💾] Guardando descarga en: {destination}")

            try:
                download.save_as(str(destination))
            except Exception as e:
                msg = str(e)

                # Caso 1: cancelación explícita
                if "Download.save_as: canceled" in msg:
                    logger.warning(
                        "[⚠️] Download.save_as: canceled detectado "
                        "(posible cierre del navegador o cancelación del usuario)."
                    )
                    raise DownloadCanceledError(msg) from e

                # Caso 2: disco lleno (errno 28) u mensaje similar
                if isinstance(e, OSError):
                    errno = getattr(e, "errno", None)
                    if errno == 28 or "No space left on device" in msg:
                        logger.error(
                            "[❌] Error de espacio en disco (errno 28: "
                            "No space left on device)."
                        )
                        raise DiskFullError(msg) from e

                logger.exception(
                    "[🔥] Error inesperado en download.save_as (no es cancelación / "
                    "ni disco lleno): %s", e
                )
                return False

            logger.info("[✅] Descarga guardada correctamente.")
            return True

        except TimeoutError:
            logger.error(
                "[❌] Timeout esperando la descarga al hacer click en 'Download All'."
            )
            return False

        except DownloadCanceledError:
            raise

        except DiskFullError:
            raise

        except Exception as e:
            msg = str(e)
            # Extra protección por si el errno 28 se cuela aquí
            if isinstance(e, OSError):
                errno = getattr(e, "errno", None)
                if errno == 28 or "No space left on device" in msg:
                    logger.error(
                        "[❌] Error de espacio en disco detectado en bloque general "
                        "(errno 28)."
                    )
                    raise DiskFullError(msg) from e

            logger.exception(
                f"[🔥] Error inesperado durante 'Download All': {e}"
            )
            return False
