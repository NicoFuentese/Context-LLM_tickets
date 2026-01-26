import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Rutas Base (Pathlib maneja automáticamente las barras invertidas de Windows)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TICKETS_FILE = DATA_DIR / "tickets.csv"

# Configuración de Archivos
CSV_FILENAME = os.getenv("GLPI_CSV_FILENAME", "tickets.csv")
DATA_FILE_PATH = DATA_DIR / CSV_FILENAME

# Configuración API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("❌ CRÍTICO: No se encontró GOOGLE_API_KEY en el archivo .env")

# fortalezas de cada técnico para que la IA sepa a quién elegir.
TECH_SPECIALTIES = {
    "Eduardo Francisco Zamora Gonzalez": ["Redes", "Cisco", "Hardware", "Cableado"],
    "Jose Manuel Carrasco Gonzalez": ["Bases de Datos", "SQL", "Oracle", "SAP Nivel 1"],
    "Fernando Adrian Silva Leon": ["Soporte Usuario", "Office 365", "Impresoras", "Windows"],
    "Italo Joshua Toro Sepulveda": ["Servidores", "Linux", "Virtualización", "VMware"],
    "Gonzalo Alejandro Tobar Ramirez": ["Ciberseguridad", "Firewall", "VPN", "Auditoría"],
    # Fallback para nombres nuevos
    "Sin Asignar": ["N/A"]
}