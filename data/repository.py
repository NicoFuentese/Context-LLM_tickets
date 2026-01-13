import pandas as pd
import os
import datetime
from config.settings import DATA_FILE_PATH

class TicketRepository:
    def __init__(self):
        self.file_path = DATA_FILE_PATH
        self._validate_file()

    def _validate_file(self):
        """Valida la existencia física del archivo CSV."""
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"CRÍTICO: No se encuentra el archivo de datos en: {self.file_path}. "
                "Por favor exporte los tickets de GLPi y colóquelos en la carpeta /data."
            )

    def load_data(self) -> pd.DataFrame:
        """Lee el CSV con la codificación y separador típicos de GLPi."""
        try:
            df = pd.read_csv(
                self.file_path,
                sep=';',           # Separador estándar GLPi
            )
            # Normalización básica de nombres de columnas (strip whitespace)
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            raise RuntimeError(f"Error al leer el CSV: {str(e)}")

    def get_last_update_time(self) -> str:
        """Retorna la fecha de modificación del archivo formateada."""
        try:
            timestamp = os.path.getmtime(self.file_path)
            dt_object = datetime.datetime.fromtimestamp(timestamp)
            return dt_object.strftime("%d/%m/%Y a las %H:%M")
        except Exception:
            return "Desconocida"

    def get_team_workload(self) -> dict:
        """Calcula la carga laboral de técnicos activos."""
        df = self.load_data()
        
        # Columnas esperadas (ajustar según tu export exacto de GLPi)
        col_status = 'Estado'
        col_tech = 'Asignado a - Técnico'

        # Verificar columnas
        if col_status not in df.columns or col_tech not in df.columns:
            return {"Error": "Columnas de GLPi no encontradas en el CSV"}

        # 1. Filtrar tickets NO cerrados (Ajustar strings según tu GLPi)
        estados_cerrados = ['Cerrado', 'Solucionado', 'Closed', 'Solved']
        active_tickets = df[~df[col_status].isin(estados_cerrados)]

        # 2. Manejar Nulos
        active_tickets[col_tech] = active_tickets[col_tech].fillna("Sin Asignar")

        # 3. Contar ocurrencias
        workload = active_tickets[col_tech].value_counts().to_dict()
        
        return workload