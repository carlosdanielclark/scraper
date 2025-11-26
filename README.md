# BuildingConnected Scraper

## Descripción
Automatización para extraer datos de proyectos y descargar documentos desde BuildingConnected. Desarrollado para apoyar el proceso de estimación de proyectos de construcción.

## Características Principales
- ✅ Autenticación automática con credenciales proporcionadas
- ✅ Extracción de metadatos de proyectos en estado "Undecided"
- ✅ Descarga de documentos como archivos .rar por proyecto
- ✅ Estructura organizada de carpetas numeradas por proyecto
- ✅ Registro persistente de descargas en store.csv
- ✅ Manejo de datos faltantes (ej: teléfono no disponible → "N/S")
- ✅ Confirmación entre proyectos para control manual del flujo

## Requisitos
- Python 3.10+
- Playwright
- dateparser
- python-dotenv

## Instalación

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd scraper

# 2. Crear entorno virtual
python -m venv scraper_env
scraper_env\Scripts\activate  # Windows
# source scraper_env/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Instalar navegador Chromium
playwright install chromium
```

## Configuración

1. **Crear archivo `.env`** en la raíz del proyecto:
```
BC_EMAIL=email@deprueba.com
BC_PASSWORD=mypassword*$-123
```

2. **Crear archivo `requirements.txt`**:
```
dateparser==1.2.2
pandas==2.3.3
pip==25.3
playwright==1.56.0
python-dotenv==1.2.1
```

## Estructura de Archivos
```
scraper/
├── .env                    # Variables de entorno (NO COMMITEAR)
├── .gitignore              # Archivos a ignorar en git
├── config.py               # Configuración global y variables
├── run_scraper.py          # Orquestador
├── bid_board_collector.py  # Fase 2: recolecta proyectos y actualiza pending_projects.json
├── project_processor.py    # Fase 3: procesa proyectos pendientes con metadatos y descargas
├── store                   # Registro de descargas (se crea automáticamente)
│   └── pending_projects.json
├── requirements.txt        # Dependencias del proyecto
├── data/                   # Almacenamiento de proyectos descargados
│   ├── 1-Fowler_Kia_Windsor/
│   │   ├── 1-Fowler_Kia_Windsor.rar
│   │   └── data_project.txt
│   └── 2-Bank_of_America_Broomfield_CO/
│       ├── 2-Bank_of_America_Broomfield_CO.rar
│       └── data_project.txt
├── logs/                   # Registros de ejecución y capturas de pantalla
├── src/
│   ├── __init__.py
│   ├── authentication_handler.py     # Gestión de autenticación
│   ├── bid_board_scraper.py   
│   ├── project_downloader.py         # Descarga de archivos
│   ├── project_metadata_extractor.py # Extracción de metadatos
│   ├── project_paths.py
│   ├── pending_store.py
│   ├── validation.py
│   ├── storage_manager.py  # Gestión de almacenamiento
│   └── utils/
│       ├── __init__.py
│       ├── naming.py
│       └── logger.py       # Sistema de logging
└── tests/                  # Pruebas unitarias (pendiente)
```

## Uso

```bash
python main.py        # ejecutar programa
python debug_paths.py # validar rutas
```

## Flujo de Ejecución
1. El programa se autentica en BuildingConnected
2. Navega a la sección "Undecided" en el Bid Board
3. Para cada proyecto:
   - Extrae metadatos (nombre, fecha, ubicación, cliente, teléfono)
   - Descarga todos los documentos como un único archivo .rar
   - Crea una carpeta numerada con el nombre del proyecto
   - Guarda los datos en `data_project.txt` dentro de la carpeta
   - Registra la descarga en `store.csv`
   - Pregunta si continuar con el siguiente proyecto

## Variables de Configuración
En `config.py` puedes modificar:
- Selectores CSS/XPath para adaptarse a cambios en la UI
- Campos a extraer en cada proyecto
- Formato de fecha
- Rutas de almacenamiento

## Buenas Prácticas
- **Nunca commitear `.env`**: Contiene credenciales sensibles
- **Verificar selectores periódicamente**: La UI de BuildingConnected puede cambiar
- **Usar tiempos de espera razonables**: Evitar bloqueos innecesarios
- **Mantener logs limpios**: Facilita el debugging y monitoreo

## Solución de Problemas Comunes

### Autenticación fallida
- Verificar credenciales en `.env`
- Actualizar selectores en `config.py` si la UI cambió
- Revisar capturas de pantalla en `logs/` para debugging

### Elementos no encontrados
- Inspeccionar manualmente la página y actualizar selectores
- Aumentar tiempos de espera en `main.py`
- Verificar que no haya popups o modales bloqueando la interacción

### Errores de permisos
- Asegurar que las carpetas `data/` y `logs/` existan y tengan permisos de escritura
- Ejecutar el script con privilegios adecuados

## Mantenimiento
- Para corregir errores en `store.csv`: editar manualmente o eliminar para reiniciar contador
- Para actualizar selectores: modificar únicamente `config.py`
- Para cambiar formato de salida: modificar `storage_manager.py` sin afectar lógica de scraping

## Próximos Pasos
- Añadir pruebas unitarias en la carpeta `tests/` [En proceso]
- Implementar logging mejorado para producción

## Licencia
Este proyecto es propiedad de Jaime y está destinado únicamente para uso interno.