# run_scraper.py
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Directorio raíz del proyecto (donde está este archivo)
ROOT_DIR = Path(__file__).resolve().parent

# Carpeta de logs SIEMPRE relativa al proyecto, no al cwd
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def run_command(cmd, name: str) -> bool:
    """
    Ejecuta un comando (lista o string) y loguea el resultado.
    Devuelve True si exit code = 0, False en caso contrario.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [▶️] Ejecutando {name}: {cmd}")

    log_file = LOGS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"\n\n[{ts}] ===== Inicio {name} =====\n")

        # ⬇⬇⬇ AQUÍ EL CAMBIO IMPORTANTE DE ENCODING ⬇⬇⬇
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",   # forzamos UTF-8
            errors="replace",   # cualquier carácter raro lo reemplaza, NO revienta
            cwd=ROOT_DIR,       # ejecuta siempre en la carpeta del proyecto
        )

        f.write(result.stdout)
        f.write(
            f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"===== Fin {name} (exit_code={result.returncode}) =====\n"
        )

    if result.returncode != 0:
        print(
            f"[❌] {name} terminó con error (exit code {result.returncode}). "
            f"Revisa el log: {log_file}"
        )
        return False

    print(f"[✅] {name} terminó correctamente.")
    return True


def main() -> None:
    """
    Orquestador del scraping:
    1) Ejecuta Fase 2 (bid_board_collector.py) para actualizar pending_projects.json
    2) Si Fase 2 fue bien, ejecuta Fase 3 (project_processor.py) para procesar pendientes
    """
    python_exe = sys.executable  # usa el Python con el que se lanzó este script

    # 1) FASE 2: actualizar pending_projects.json
    fase2_cmd = [python_exe, "bid_board_collector.py"]
    ok_fase2 = run_command(fase2_cmd, "fase2_bid_board")

    if not ok_fase2:
        print("[⏹️] Abortando Fase 3 porque Fase 2 falló.")
        return

    # 2) FASE 3: metadatos + descargas para todos los 'pendiente'
    fase3_cmd = [python_exe, "project_processor.py"]
    ok_fase3 = run_command(fase3_cmd, "fase3_project_processor")

    if not ok_fase3:
        print("[⚠️] Fase 3 terminó con errores. Revisa logs en carpeta 'logs'.")

    print("[🟢] Ciclo completo Fase2 + Fase3 finalizado.")


if __name__ == "__main__":
    main()
