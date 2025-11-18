import logging
from pathlib import Path
import sys
import io

def get_logger(name: str) -> logging.Logger:
    """Configura y devuelve un logger robusto que evita errores de encoding en Windows"""
    
    # Forzar UTF-8 en la consola de Windows
    if sys.platform.startswith('win'):
        try:
            # Reconfigurar stdout/stderr para usar UTF-8
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
        except Exception as e:
            pass  # Si falla, continuar sin reconfigurar
    
    # Crear logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Limpiar handlers existentes
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Formato SIN caracteres Unicode problemáticos en Windows
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para archivo (con encoding UTF-8 explícito)
    log_file = Path("logs") / f"{name}.log"
    log_file.parent.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(
        str(log_file),
        encoding='utf-8',  # Forzar UTF-8 para archivos
        errors='replace'   # Reemplazar caracteres problemáticos
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Handler para consola (evitar caracteres problemáticos en Windows)
    class SafeStreamHandler(logging.StreamHandler):
        """Handler que evita caracteres Unicode problemáticos en Windows"""
        def emit(self, record):
            try:
                # Reemplazar caracteres problemáticos solo para Windows
                if sys.platform.startswith('win'):
                    record.msg = str(record.msg).replace('✓', '[OK]').replace('✗', '[FAIL]').replace('⚠️', '[WARN]')
                super().emit(record)
            except Exception:
                self.handleError(record)
    
    console_handler = SafeStreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Añadir handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger