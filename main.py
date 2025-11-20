import json
from pathlib import Path
from typing import List

from playwright.sync_api import sync_playwright, BrowserContext, Page

from config import LOGIN_URL, PIPELINE_URL, PROJECT_FIELDS
from src.auth_manager import AuthManager
from src.data_extractor import DataExtractor
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main() -> None:
    """
    Flujo principal orquestado de extracción de metadatos.
    
    Pasos:
    1. Autenticación persistente
    2. Navegación a pipeline y extracción de metadatos
    3. Confirmación explícita antes de Fase 3 (descarga de archivos)
    4. Generación de muestra para testing
    
    Comportamiento:
    - headless=False para debugging visual (como requerido)
    - No descarga archivos aún (solo genera metadatos)
    - Detiene flujo si falla validación de campos obligatorios
    """
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    test_output_path = output_dir / "test_metadata.json"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Fase 1: Autenticación
            auth_manager = AuthManager(page)
            if not auth_manager.login():
                logger.critical("[❌] Autenticación fallida. Deteniendo ejecución.")
                return
            
            logger.info("[✅] Autenticación exitosa. Navegando a pipeline...")
            page.goto(PIPELINE_URL, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)
            
            # Fase 2: Extracción de metadatos
            extractor = DataExtractor(page)
            metadata_list = extractor.extract_all_metadata()
            
            if not metadata_list:
                logger.warning("[⚠️] No se extrajeron metadatos válidos. Verificar selectores.")
                return
            
            # Generar muestra para testing (máximo 3 proyectos)
            test_sample = metadata_list[:3]
            with open(test_output_path, "w", encoding="utf-8") as f:
                json.dump(test_sample, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[✅] Muestra guardada en: {test_output_path.absolute()}")
            logger.info(f"[📊] Total de proyectos procesados: {len(metadata_list)}")
            
            # Confirmación explícita antes de Fase 3
            proceed = input("\n¿Continuar con descarga de archivos (Fase 3)? [y/N]: ").strip().lower()
            if proceed not in ["y", "yes"]:
                logger.info("[⏹️] Ejecución detenida por usuario. Metadatos listos para Fase 3.")
                return
            
            logger.info("[⏭️] Continuando con Fase 3 (descarga de archivos)...")
            # Aquí se integraría FileDownloader en Fase 3
            
        except Exception as e:
            logger.exception(f"[🔥] Error crítico en flujo principal: {str(e)}")
        finally:
            browser.close()
            logger.info("[CloseOperation] Navegador cerrado correctamente")

if __name__ == "__main__":
    main()