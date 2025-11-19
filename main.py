import sys
import time
from pathlib import Path
import traceback

# Añadir el directorio raíz al path de Python
sys.path.append(str(Path(__file__).parent))

from src.auth_manager import AuthManager
from src.utils.logger import get_logger
from config import config
from playwright.sync_api import sync_playwright

logger = get_logger("main")

def main():
    """Punto de entrada para la Fase 1: Autenticación y Navegación"""
    try:
        logger.info("="*50)
        logger.info("INICIO DE AUTENTICACION Y NAVEGACION (FASE 1)")
        logger.info("="*50)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=100,
                args=["--start-maximized", "--disable-infobars"]
            )
            context = browser.new_context(
                viewport={"width": 800, "height": 600},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            success = False
            
            try:
                auth = AuthManager(page)
                success = auth.login()
                if success:
                    logger.info("[✅] Autenticación completada exitosamente")
                    logger.info(f"Navegando a: {config.PIPELINE_URL}")
                    page.goto(config.PIPELINE_URL, timeout=45000)
                    page.wait_for_selector('text="Undecided"', timeout=20000)
                    logger.info("[✅] Página de pipeline cargada correctamente")
                else:
                    logger.error("[❌] Autenticación fallida")
            except Exception as e:
                logger.error(f"[❌] Error crítico: {str(e)}")
                logger.debug(f"Detalles: {traceback.format_exc()}")
            
            # ✅ CORRECCIÓN CLAVE: Cerrar recursos ANTES de salir del bloque `with`
            try:
                if success:
                    try:
                        input("\n[✅] Todo listo. Presiona Enter para cerrar el navegador...")
                    except Exception as e:
                        logger.warning("No se pudo leer la entrada. Esperando 3 segundos antes de cerrar...")
                        time.sleep(3)
                else:
                    # Si hubo error, solo esperar unos segundos sin input
                    logger.info("Cerrando navegador en 3 segundos por error...")
                    time.sleep(3)
                
                # ✅ CERRAR NAVEGADOR DENTRO DEL BLOQUE `with`
                browser.close()
                logger.info("[✅] Navegador cerrado correctamente.")
                
            except Exception as e:
                logger.error(f"[❌] Error al cerrar navegador: {str(e)}")
    
    finally:
        logger.info("[✅] Fase 1 completada.")


if __name__ == "__main__":
    main()