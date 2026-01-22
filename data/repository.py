import pandas as pd
import os
import datetime
from config.settings import DATA_FILE_PATH, TICKETS_FILE

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

            if 'ID' in df.columns:
                df['ID'] = df['ID'].astype(str).str.strip()

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
        col_status = 'Estado'
        col_tech = 'Asignado a - Técnico'

        # Verificar columnas
        if col_status not in df.columns or col_tech not in df.columns:
            return {"Error": "Columnas de GLPi no encontradas en el CSV"}

        # 1. Filtrar tickets NO cerrados (Ajustar strings según tu GLPi)
        estados_cerrados = ['Cerrado', 'Solucionado', 'Closed', 'Solved']
        active_tickets = df[~df[col_status].isin(estados_cerrados)].copy()

        # 2. Manejar Nulos
        active_tickets[col_tech] = active_tickets[col_tech].fillna("Sin Asignar")

        # 3. Contar ocurrencias
        workload = active_tickets[col_tech].value_counts().to_dict()
        
        return workload

    def get_unassigned_tickets(self, limit=5) -> str:
        """Devuelve una lista formateada de los tickets abiertos sin técnico."""
        df = self.load_data()
        col_status = 'Estado'
        col_tech = 'Asignado a - Técnico'
        
        cerrados = ['Cerrado', 'Solucionado', 'Closed', 'Solved']
        
        # Filtros: No cerrados Y (Técnico es Null O Técnico es vacío)
        mask_active = ~df[col_status].isin(cerrados)
        mask_unassigned = (df[col_tech].isna()) | (df[col_tech] == '') | (df[col_tech] == 'Sin Asignar')
        
        pending = df[mask_active & mask_unassigned].head(limit)
        
        if pending.empty:
            return "No hay tickets pendientes de asignación."
            
        # Formatear para el LLM
        report = []
        for _, row in pending.iterrows():
            report.append(f"- ID {row['ID']}: {row['Título']} (Estado: {row['Estado']})")
        
        return "\n".join(report)

    def get_ticket_details(self, ticket_id: str) -> str:
        """Busca un ticket específico por ID y devuelve sus detalles."""
        df = self.load_data()
        
        # Buscar ID exacto
        target_id = str(ticket_id).strip()
        ticket = df[df['ID'] == target_id].fillna("Sin Asignar")
        
        if ticket.empty:
            # DEBUG: Si falla, mostramos qué IDs existen realmente (los primeros 3)
            available_ids = df['ID'].head(3).tolist()
            return f"❌ No encontré el ticket ID '{target_id}'. IDs visibles en el sistema (ejemplos): {available_ids}"
        
        row = ticket.iloc[0]
        # Construimos una ficha técnica del ticket
        details = f"""
        DETALLES DEL TICKET #{ticket_id}:
        - Título: {row.get('Título', 'Sin título')}
        - Estado: {row.get('Estado', 'Desconocido')}
        - Técnico Actual: {row.get('Asignado a - Técnico', 'Sin Asignar')}
        - Solicitante: {row.get('Solicitante', 'Desconocido')}
        - Fecha: {row.get('Fecha de apertura', 'Desconocida')}
        - Descripción/Contenido: {str(row.get('Descripción', 'Sin contenido'))[:500]}... (truncado)
        """
        return details
    
class GlpiRepository:
    def __init__(self):
        self.file_path = TICKETS_FILE

    def _check_file_exists(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"❌ El archivo de datos no existe en: {self.file_path}")

    def get_last_update_time(self) -> str:
        """Retorna la fecha de modificación del archivo CSV formateada."""
        try:
            self._check_file_exists()
            timestamp = os.path.getmtime(self.file_path)
            dt_object = datetime.datetime.fromtimestamp(timestamp)
            return dt_object.strftime("%d/%m/%Y %H:%M:%S")
        except Exception as e:
            return "Desconocida"

    def get_dataframe(self) -> pd.DataFrame:
        """Lee el CSV crudo de GLPi y realiza la limpieza base."""
        self._check_file_exists()
        try:
            # 1. Leer CSV (GLPi suele exportar en Latin-1 y separado por punto y coma)
            df = pd.read_csv(self.file_path, sep=';', encoding='latin-1')
            
            # 2. Normalizar nombres de columnas (quitar espacios extra)
            df.columns = df.columns.str.strip()
            
            # --- CORRECCIÓN CRÍTICA AQUÍ ---
            # Rellenamos los NaN de la columna de técnicos INMEDIATAMENTE al cargar
            if 'Asignado a - Técnico' in df.columns:
                df['Asignado a - Técnico'] = df['Asignado a - Técnico'].fillna("Sin Asignar")
            
            return df
        except Exception as e:
            raise RuntimeError(f"Error al leer el CSV de GLPi: {e}")

    def get_team_workload(self) -> dict:
        """Calcula la carga de trabajo por técnico (tickets activos)."""
        # Ahora llamamos a get_dataframe que ya nos trae los datos limpios
        df = self.get_dataframe()
        
        required_cols = ['ID', 'Estado', 'Asignado a - Técnico']
        if not all(col in df.columns for col in required_cols):
            missing = [c for c in required_cols if c not in df.columns]
            raise ValueError(f"El CSV no tiene las columnas esperadas de GLPi. Faltan: {missing}")

        # Filtrar tickets activos
        estados_inactivos = ['Cerrado', 'Solucionado', 'Closed', 'Solved']
        active_tickets = df[~df['Estado'].isin(estados_inactivos)]

        # Contar ocurrencias
        workload_series = active_tickets['Asignado a - Técnico'].value_counts()
        
        # Convertir a diccionario
        return workload_series.to_dict()

    def get_ticket_details(self, ticket_id: str) -> str:
        """
        Método auxiliar para buscar un ticket específico.
        Útil si quieres pasarle el contexto de un ticket específico al LLM.
        """
        df = self.get_dataframe()
        # Convertir a string para asegurar comparación
        ticket = df[df['ID'].astype(str) == str(ticket_id)]
        
        if ticket.empty:
            return "Ticket no encontrado."
            
        # Convertir la fila a texto legible
        row = ticket.iloc[0]
        return f"ID: {row['ID']}, Título: {row.get('Título', 'Sin título')}, Estado: {row['Estado']}, Técnico: {row['Asignado a - Técnico']}"