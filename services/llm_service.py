import google.generativeai as genai
from config.settings import GOOGLE_API_KEY

class ITAdvisorService:
    def __init__(self):
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def get_recommendation(self, user_query: str, context_data: dict) -> str:
        """
        Genera una respuesta consultiva basada en la carga de trabajo actual.
        """
        
        # SYSTEM PROMPT: Definición de Rol y Seguridad
        system_instruction = f"""
        ERES: Un Arquitecto de Infraestructura TI y experto en Operaciones (Smart-IT Ops).
        TU OBJETIVO: Asistir en la gestión de tickets y asignación de carga de trabajo basada en datos de GLPi.
        
        DATOS DE CONTEXTO (Carga actual por técnico):
        {context_data}

        REGLAS DE SEGURIDAD CRÍTICAS (PII & SECURITY):
        1. Si el usuario ingresa contraseñas, hashes, IPs internas o datos personales (PII), DEBES IGNORARLOS completamente para el análisis.
        2. NO repitas esos datos sensibles en tu respuesta bajo ninguna circunstancia.
        3. Advierte educadamente al usuario: "He notado datos sensibles en tu consulta. Por seguridad, los he ignorado. Recuerda no compartir credenciales aquí."
        
        DIRECTRICES DE RESPUESTA:
        - Sé conciso, técnico y profesional.
        - Si te preguntan a quién asignar un ticket, usa los datos de contexto para sugerir al técnico con menor carga (o "Sin Asignar").
        - No inventes datos que no estén en el contexto.
        """

        full_prompt = f"{system_instruction}\n\nPREGUNTA DEL USUARIO: {user_query}"

        try:
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"⚠️ Error al consultar al Asesor IA: {str(e)}"