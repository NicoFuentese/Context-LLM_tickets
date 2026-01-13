import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Rutas Base (Pathlib maneja automáticamente las barras invertidas de Windows)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Configuración de Archivos
CSV_FILENAME = os.getenv("GLPI_CSV_FILENAME", "tickets.csv")
DATA_FILE_PATH = DATA_DIR / CSV_FILENAME

# Configuración API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("❌ CRÍTICO: No se encontró GOOGLE_API_KEY en el archivo .env")