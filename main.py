import sys
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
    browser = None
    page = None
    
    try:
        logger.info("="*50)
        logger.info("INICIO DE AUTENTICACION Y NAVEGACION (FASE 1)")
        logger.info("="*50)
        
        with sync_playwright() as p:
            # Lanzar navegador
            browser = p.chromium.launch(
                headless=False,
                slow_mo=100,
                args=["--start-maximized", "--disable-infobars"]
            )
            
            # Crear contexto y página
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            # Autenticación
            auth = AuthManager(page)
            success = auth.login()
            
            if success:
                logger.info("[✅] Autenticación completada exitosamente")
                logger.info(f"Navegando a: {config.PIPELINE_URL}")
                page.goto(config.PIPELINE_URL, timeout=45000)
                
                # Verificar elementos de pipeline
                try:
                    page.wait_for_selector('text="Undecided"', timeout=20000)
                    logger.info("[✅] Página de pipeline cargada correctamente")
                except Exception as e:
                    logger.warning(f"[⚠️] La página cargó pero no se encontró 'Undecided': {str(e)}")
            else:
                logger.error("[❌] Autenticación fallida")
            
            # ✅ ESTO ES LO IMPORTANTE: Mantener navegador abierto hasta que el usuario presione Enter
            input("\n[✅] Autenticación completada. Presiona Enter para cerrar el navegador...")
            
    except Exception as e:
        logger.error(f"[❌] Error crítico: {str(e)}")
        logger.debug(f"Detalles: {traceback.format_exc()}")
        
        # Si hay error, aún así esperar a que el usuario presione Enter
        try:
            input("\n[❌] Ocurrió un error. Presiona Enter para cerrar el navegador...")
        except:
            # Si stdin está cerrado, esperar 3 segundos
            import time
            logger.warning("No se puede esperar entrada. Esperando 3 segundos antes de cerrar...")
            time.sleep(3)
    finally:
        # Cerrar recursos
        try:
            if page and not page.is_closed():
                page.close()
            if browser and browser.is_connected():
                browser.close()
            logger.info("[✅] Navegador cerrado correctamente. Fase 1 completada.")
        except Exception as e:
            logger.error(f"[❌] Error al cerrar recursos: {str(e)}")

if __name__ == "__main__":
    main()