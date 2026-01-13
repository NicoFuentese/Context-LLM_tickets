import google.generativeai as genai
from config.settings import GOOGLE_API_KEY

class ITAdvisorService:
    def __init__(self):
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')

    def get_recommendation(self, user_query: str, 
                           workload_data: dict,
                           specific_ticket_info: str = "") -> str:
        """
        Genera una respuesta consultiva basada en la carga de trabajo actual.
        """

        # CONTEXTO 1
        # Convertimos el diccionario a un formato de texto claro para el LLM
        workload_data = "\n".join([f"- {tech}: {count} tickets" for tech, count in workload_data.items()])
        
        if not workload_data:
            workload_data = "No hay tickets activos actualmente."
        
        # CONTEXTO 2
        ticket_context_section = ""
        if specific_ticket_info:
            ticket_context_section = f"""
            NFORMACIÓN ESPECÍFICA DE LOS TICKETS RELEVANTES:
            ------------------------------------------------------------
            {specific_ticket_info}
            ------------------------------------------------------------
            """
        
        # Construcción del System Prompt (Arquitectura del Pensamiento)
        system_prompt = f"""
        ERES: Smart-IT Ops, Tech Lead virtual.
        OBJETIVO: Ayudar a asignar tickets y gestionar infraestructura.
        CONTEXTO OPERATIVO ACTUAL (Carga de Trabajo en Tiempo Real):
        ------------------------------------------------------------
        CONEXTO DE CARGA DE TRABAJO: 
        {workload_data}

        {ticket_context_section}
        ------------------------------------------------------------

        INSTRUCCIONES:
        1. Si hay información de un ticket específico ("INFORMACIÓN ESPECÍFICA"), úsala para recomendar al mejor técnico basándote en la descripción del problema y quién tiene menos carga.
        2. Si el ticket trata de redes, sugieres al experto en redes (si lo deduces) o al que tenga menos tickets.
        3. Mantén la seguridad: CENSURA IPs o PASSWORDS detectados.
        4. Sé breve y directivo. Ejemplo: "Asigna el ticket #505 a Ana, ya que es un problema de impresión y ella tiene baja carga (2 tickets)."

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