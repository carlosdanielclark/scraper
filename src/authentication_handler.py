from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config import config, SELECTORS
from src.utils.logger import get_logger

logger = get_logger("auth")


class BuildingConnectedAuthenticator:
    """Gestiona la autenticación en BuildingConnected con timeouts razonables"""

    def __init__(self, page: Page):
        self.page = page
        self.url = config.LOGIN_URL
        self.email = config.BC_EMAIL
        self.password = config.BC_PASSWORD

    def login(self) -> bool:
        """Realiza el proceso de autenticación completo con timeouts razonables"""
        try:
            logger.info("Iniciando autenticacion en BuildingConnected...")
            # Evitar timeout agresivo: usamos domcontentloaded en login
            self.page.goto(self.url, timeout=60000, wait_until="domcontentloaded")
            self.page.wait_for_selector('input[type="email"]', timeout=30000)

            # Paso 1: Introducir email
            if not self._fill_email():
                return False

            # Paso 2: Introducir password
            if not self._fill_password():
                return False

            # Paso 3: Verificar autenticación exitosa
            return self._verify_authentication()

        except PlaywrightTimeoutError as e:
            logger.error(f"[⏱️] Timeout durante autenticación: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[❌] Error inesperado durante autenticación: {str(e)}")
            return False

    def _fill_email(self) -> bool:
        """Rellena el campo de email y hace clic en NEXT"""
        try:
            logger.debug("[📧] Paso 1: Rellenando campo de email")
            self.page.wait_for_selector(SELECTORS["email"], timeout=15000)
            self.page.fill(SELECTORS["email"], self.email)
            logger.debug(f"Email rellenado: {self.email}")

            # Selectores para el botón NEXT (ordenados por prioridad)
            next_selectors = [
                'button[aria-label="NEXT"]',
                'button:has-text("NEXT")',
                'button:has-text("Next")',
                'button[data-test="next-btn"]',
                'button[type="button"]:has-text("NEXT")',
            ]

            for selector in next_selectors:
                try:
                    logger.debug(f"[⏭️] Intentando selector NEXT: {selector}")
                    self.page.wait_for_selector(selector, timeout=8000)
                    self.page.click(selector)
                    logger.debug("[✅] Clic realizado en botón NEXT")

                    # Verificar transición a página de contraseña
                    if self._verify_password_page():
                        return True
                except PlaywrightTimeoutError:
                    continue

            logger.error("[❌] No se encontró botón NEXT funcional")
            return False

        except Exception as e:
            logger.error(f"[❌] Error en _fill_email: {str(e)}")
            return False

    def _verify_password_page(self) -> bool:
        """Verifica que estamos en la página de contraseña"""
        try:
            logger.debug("[🔍] Verificando página de contraseña...")

            # Método 1: Verificar URL
            try:
                self.page.wait_for_url("**/login?next=true", timeout=10000)
                logger.info("[✅] URL de página de contraseña verificada")
                return True
            except PlaywrightTimeoutError:
                pass

            # Método 2: Buscar campo de contraseña
            password_selectors = [
                SELECTORS["password"],
                'input[aria-label="Password"]',
                'input[name="password"]',
                'input[type="password"]',
                'input[aria-label*="password" i]',
            ]

            for selector in password_selectors:
                try:
                    self.page.wait_for_selector(selector, timeout=10000)
                    logger.info(f"[✅] Campo de contraseña encontrado: {selector}")
                    return True
                except PlaywrightTimeoutError:
                    continue

            logger.error("[❌] No se pudo verificar la página de contraseña")
            return False

        except Exception as e:
            logger.error(f"[❌] Error verificando página de contraseña: {str(e)}")
            return False

    def _fill_password(self) -> bool:
        """Rellena el campo de password y hace clic en SIGN IN"""
        try:
            logger.debug("[🔑] Paso 2: Rellenando campo de contraseña")

            password_selectors = [
                SELECTORS["password"],
                'input[aria-label="Password"]',
                'input[name="password"]',
                'input[type="password"]',
            ]
            password_field = None

            for selector in password_selectors:
                try:
                    self.page.wait_for_selector(selector, timeout=10000)
                    password_field = selector
                    logger.debug(f"[✅] Campo de contraseña encontrado: {selector}")
                    break
                except PlaywrightTimeoutError:
                    continue

            if not password_field:
                logger.error("[❌] No se encontró campo de contraseña")
                return False

            # Rellenar contraseña
            self.page.fill(password_field, self.password)
            logger.debug("[✅] Contraseña rellenada")

            # Selectores para botón SIGN IN
            signin_selectors = [
                'button[aria-label="SIGN IN"]',
                'button:has-text("SIGN IN")',
                'button:has-text("Sign In")',
                'button[data-test="sign-in-btn"]',
                'button[type="submit"]',
            ]

            for selector in signin_selectors:
                try:
                    logger.debug(f"[✅] Intentando selector SIGN IN: {selector}")
                    self.page.wait_for_selector(selector, timeout=8000)
                    self.page.click(selector)
                    logger.debug("[✅] Clic realizado en botón SIGN IN")
                    self.page.wait_for_timeout(2000)
                    return True
                except PlaywrightTimeoutError:
                    continue

            logger.error("[❌] No se encontró botón SIGN IN funcional")
            return False

        except Exception as e:
            logger.error(f"[❌] Error en _fill_password: {str(e)}")
            return False

    def _verify_authentication(self) -> bool:
        """Verifica que la autenticación fue exitosa"""
        try:
            logger.debug("[🔍] Paso 3: Verificando autenticación exitosa...")

            url_patterns = [
                "**/opportunities/pipeline**",
                "**/opportunities/**",
                "**/dashboard**",
            ]
            current_url = ""

            # Método 1: verificar URL del portal
            for pattern in url_patterns:
                try:
                    logger.debug(f"[🌐] Esperando URL con patrón: {pattern}")
                    self.page.wait_for_url(pattern, timeout=15000)
                    current_url = self.page.url
                    logger.info(f"[✅] URL del portal verificada: {pattern}")
                    break
                except PlaywrightTimeoutError:
                    continue
            else:
                logger.error("[❌] Timeout esperando URL del portal")
                return False

            # Método 2: Buscar elementos críticos del dashboard
            logger.debug("[🔍] Buscando elementos críticos del dashboard...")
            critical_elements = [
                ('text="Bid Board"', "Interfaz principal - Bid Board"),
                ('text="Pipeline"', "Pestaña Pipeline"),
                ('[aria-label="Opportunities table"]', "Tabla de oportunidades (ARIA)"),
                (".bc-opportunity-table", "Tabla de oportunidades (clase CSS)"),
                ('[data-testid="opportunity-table"]', "Tabla de oportunidades (data-testid)"),
                ('text="Undecided"', "Pestaña Undecided"),
                ('nav >> text="Opportunities"', "Menú de navegación"),
            ]

            for selector, description in critical_elements:
                try:
                    logger.debug(f"[🔍] Buscando: {description}")
                    self.page.wait_for_selector(selector, timeout=10000, state="visible")
                    logger.info(f"[✅] Elemento crítico encontrado: {description}")
                    return True
                except PlaywrightTimeoutError:
                    continue

            # Método 3: Fallback solo con URL
            if current_url and "login" not in current_url.lower() and "signin" not in current_url.lower():
                logger.warning("[⚠️] Autenticación posible pero sin elementos críticos visibles")
                return True

            logger.error("[❌] No se pudo verificar autenticación completa")
            return False

        except Exception as e:
            logger.error(f"[❌] Error verificando autenticación: {str(e)}")
            return False
