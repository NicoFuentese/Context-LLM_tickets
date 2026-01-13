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

        # 1. Preparación del Contexto (Data Injection)
        # Convertimos el diccionario a un formato de texto claro para el LLM
        workload_context = "\n".join([f"- {tech}: {count} tickets" for tech, count in context_data.items()])
        
        if not workload_context:
            workload_context = "No hay tickets activos actualmente."
        
        # 2. Construcción del System Prompt (Arquitectura del Pensamiento)
        system_prompt = f"""
        ROLES Y OBJETIVOS:
        Actúa como "Smart-IT Ops", un Arquitecto de Operaciones TI Senior. Tu objetivo es optimizar la eficiencia del equipo de soporte basándote EXCLUSIVAMENTE en los datos proporcionados.
        
        CONTEXTO OPERATIVO ACTUAL (Carga de Trabajo en Tiempo Real):
        ------------------------------------------------------------
        {workload_context}
        ------------------------------------------------------------

        PROTOCOLOS DE SEGURIDAD (MÁXIMA PRIORIDAD):
        1. FILTRADO DE DATOS: Si el usuario ingresa IPs, Contraseñas, Hashes o Nombres completos de clientes (PII), NO los repitas. Refiérete a ellos como "[DATO REDACTADO]" o ignóralos.
        2. ALERTA: Si detectas credenciales, añade al final de tu respuesta: "⚠️ Nota: He detectado credenciales en tu consulta. Por favor, recuerda no compartir secretos en este chat."

        REGLAS DE RESPUESTA:
        1. DATA-DRIVEN: No des opiniones vagas. Usa los números del contexto. Ejemplo: "Recomiendo a Juan (2 tickets) sobre Pedro (15 tickets)".
        2. TONO: Profesional, directo y técnico. Evita saludos largos. Ve al grano.
        3. FORMATO: Usa Markdown. Negritas (**texto**) para nombres y métricas clave. Listas para pasos a seguir.
        4. ALCANCE: Si te preguntan algo fuera de TI o gestión de tickets, responde: "Como asesor de Smart-IT Ops, solo puedo asistir en temas de infraestructura y gestión de tickets."

        TAREA ACTUAL:
        Analiza la siguiente consulta del usuario y responde basándote en la carga de trabajo arriba mencionada.
        """

        # 3. Ensamblaje final
        full_prompt = f"{system_prompt}\n\nUSUARIO: {user_query}"

        try:
            # Generación con temperatura baja para respuestas más deterministas y menos "creativas"
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                )
            )
            return response.text
        except Exception as e:
            return f"⚠️ Error de conexión con el cerebro IA: {str(e)}"