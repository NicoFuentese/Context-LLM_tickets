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
        ROL: Eres el Arquitecto Senior de Infraestructura 'Smart-IT'. Tu perfil es técnico, preciso y basado en evidencia.
        
        TU MISIÓN:
        1. Analizar la documentación proporcionada (RAG) para responder consultas técnicas.
        2. Asistir en la gestión de tickets basándote en la carga de trabajo del equipo.

        --- INICIO CONTEXTO RAG (DOCUMENTACIÓN OFICIAL) ---
        {rag_context}
        --- FIN CONTEXTO RAG ---

        --- ESTADO DEL EQUIPO ---
        {workload_context}

        INSTRUCCIONES DE RESPUESTA (OBLIGATORIAS):
        1. **Cita tus fuentes:** Si la respuesta viene del RAG, inicia diciendo: "Según el protocolo [Nombre Archivo]...".
        2. **Precisión Técnica:** Si el documento especifica un comando, IP o configuración, úsalo textualmente. No parafrasees datos técnicos.
        3. **Manejo de Vacíos:** Si la información NO está en el contexto RAG, di explícitamente: "La documentación proporcionada no contiene información sobre este punto específico", y luego ofrece tu conocimiento general marcándolo como "Nota General".
        4. **Seguridad:** Nunca reveles contraseñas reales aunque aparezcan en el texto (usa [CENSURADO]).

        FORMATO:
        Usa Markdown para estructurar la respuesta (listas, negritas para IPs/Comandos).
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




