import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from config.settings import GOOGLE_API_KEY

# Configuración Global
genai.configure(api_key=GOOGLE_API_KEY)

class ITAdvisorService:
    def __init__(self):
        # CONFIGURACIÓN TÉCNICA (Pilar de Precisión)
        # temperature=0.2: Baja creatividad, alta fidelidad a los datos. Ideal para manuales técnicos.
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=1024,
        )
        
        # CONFIGURACIÓN DE SEGURIDAD (Pilar de Privacidad)
        # Bloqueamos contenido peligroso o de odio, pero permitimos algo de flexibilidad para términos técnicos
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash-lite',
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )
    
    def _format_history_for_gemini(self, streamlit_history):
        """
        Convierte el historial de Streamlit (dict) al formato que espera Gemini.
        Streamlit: [{'role': 'user', 'content': 'hola'}]
        Gemini:    [{'role': 'user', 'parts': ['hola']}]
        """
        gemini_history = []
        for msg in streamlit_history:
            # Ignoramos mensajes de sistema o errores si los hubiera guardado
            if msg["role"] in ["user", "model", "assistant"]:
                role = "model" if msg["role"] == "assistant" else "user"
                gemini_history.append({
                    "role": role,
                    "parts": [msg["content"]]
                })
        return gemini_history

    def get_system_prompt(self, workload_context: str, rag_context: str) -> str:
        """
        Prompt de Ingeniería avanzado para roles técnicos.
        """
        base_prompt = f"""
        ACTÚA COMO: Un Arquitecto de Soluciones TI Senior y SysAdmin experto (Nivel 3).
        TONO: Profesional, técnico, conciso y orientado a la resolución de problemas.

        FUENTES DE CONOCIMIENTO (Prioridad Máxima):
        A continuación se presentan extractos de la DOCUMENTACIÓN OFICIAL de la empresa (RAG).
        Úsalos para responder. Si la respuesta está aquí, cítala explícitamente.
        --- INICIO DOCUMENTACIÓN RAG ---
        {rag_context}
        --- FIN DOCUMENTACIÓN RAG ---

        CONTEXTO OPERATIVO (Estado actual del equipo):
        {workload_context}

        REGLAS DE COMPORTAMIENTO (OBLIGATORIAS):
        1. HONESTIDAD RADICAL: Si la información no está en la documentación RAG ni en tu conocimiento general confiable, di: "No encuentro información específica en los protocolos sobre este tema". NO INVENTES COMANDOS NI PROCEDIMIENTOS.
        2. SEGURIDAD: Si el usuario pega credenciales, IPs privadas o PII, IGNÓRALAS en tu respuesta y advierte sobre seguridad.
        3. FORMATO: Usa Markdown. Pon el código o comandos siempre en bloques de código (```bash).
        4. CITA DE FUENTES: Si usas info del RAG, indica: "Según el protocolo [Nombre archivo]...".
        """

        return base_prompt

    def ask_advisor(self, user_question: str, workload_dict: dict, rag_context: str = "",  chat_history: list = []) -> str:
        try:
            # 1. Preparar contextos
            workload_str = "\n".join([f"- {k}: {v} tickets activos" for k, v in workload_dict.items()])
            
            # 2. Generar System Prompt Dinámico
            system_instruction = self.get_system_prompt(workload_str, rag_context)
            
            # 3. Preparar Historial (Memoria de corto plazo)
            # Nota: Gemini Pro no tiene un parámetro 'system_prompt' directo en start_chat en todas las versiones SDK,
            # pero podemos inyectarlo en el primer mensaje o usar la historia.
            # Estrategia Híbrida: Enviamos el system prompt como "instrucción oculta" junto con la pregunta actual
            # para no ensuciar el historial pasado o confundir al modelo con contextos viejos.
            
            formatted_history = self._format_history_for_gemini(chat_history)
            
            # Iniciamos chat con la historia previa
            chat = self.model.start_chat(history=formatted_history)
            
            # 4. Construir el mensaje final (Contexto + Pregunta)
            full_message = f"{system_instruction}\n\nPREGUNTA DEL OPERADOR: {user_question}"
            
            # 5. Enviar
            response = chat.send_message(full_message)
            return response.text

        except Exception as e:
            return f"⚠️ Error en el servicio cognitivo (LLM): {str(e)}"




