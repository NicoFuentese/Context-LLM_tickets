import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from config.settings import GOOGLE_API_KEY, TECH_SPECIALTIES

# Configuración Global
genai.configure(api_key=GOOGLE_API_KEY)

class ITAdvisorService:
    def __init__(self):
        # CONFIGURACIÓN TÉCNICA (Pilar de Precisión)
        # temperature=0.2: Baja creatividad, alta fidelidad a los datos. Ideal para manuales técnicos.
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=2048, #aumento para respuesta mas detallada
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

        # Convertimos el diccionario de skills a texto legible
        skills_str = "\n".join([f"- {name}: {', '.join(skills)}" for name, skills in TECH_SPECIALTIES.items()])

        base_prompt = f"""
        ROL: Eres el Tech Lead y Arquitecto de 'Smart-IT Ops'.
        
        TU SUPERPODER: Asignar tickets inteligentemente buscando el equilibrio perfecto entre:
        1. **Especialidad:** ¿Quién sabe más del tema? (Prioridad Alta)
        2. **Carga Laboral:** ¿Quién está más libre? (Prioridad Media)
        
        --- MATRIZ DE EXPERTOS (Técnico: Habilidades) ---
        {skills_str}

        --- CARGA DE TRABAJO ACTUAL (Tickets Activos) ---
        {workload_context}
        
        --- CONOCIMIENTO TÉCNICO (RAG) ---
        {rag_context}

        INSTRUCCIONES PARA ASIGNACIÓN:
        Cuando el usuario pregunte por tickets sin asignar o pida recomendaciones:
        1. Analiza el "Título" y "Descripción" del ticket para detectar el tema (ej: Base de Datos, Redes).
        2. Busca en la Matriz de Expertos quién es el más apto.
        3. Verifica su Carga de Trabajo.
           - Si el experto está saturado (>5 tickets), busca al siguiente más apto o al que tenga menos carga (Generalista).
           - Si el experto está libre, asígnaselo sin dudar.
        4. **FORMATO DE RESPUESTA:**
           - 🎫 **Ticket [ID]:** [Título]
           - 👉 **Sugerencia:** Asignar a **[Nombre Técnico]**.
           - 💡 **Razón:** "[Nombre] es experto en [Skill] y tiene carga baja/media..." o "Aunque [Nombre] está ocupado, es el único experto en..."

        REGLAS DE SEGURIDAD:
        - No inventes nombres que no estén en la lista.
        - Si no hay información suficiente, sugiere "Investigar primero".
        """

        return base_prompt

    def ask_advisor(self, user_question: str, workload_dict: dict, rag_context: str = "", chat_history: list = [], unassigned_tickets: list = []) -> str:
        try:
            workload_str = "\n".join([f"- {k}: {v} tickets" for k, v in workload_dict.items()])
            
            # Si hay tickets sin asignar y la pregunta parece sobre asignación, los inyectamos en el contexto
            unassigned_context = ""
            if unassigned_tickets and ("asignar" in user_question.lower() or "pendientes" in user_question.lower()):
                unassigned_context = "\nTICKETS SIN ASIGNAR DETECTADOS:\n" + "\n".join(
                    [f"ID: {t['id']} | Título: {t['titulo']} | Desc: {t['descripcion']}" for t in unassigned_tickets]
                )
                # Añadimos esto a la pregunta del usuario para que el LLM lo vea
                user_question = f"{user_question}\n\n{unassigned_context}"

            system_instruction = self.get_system_prompt(workload_str, rag_context)
            formatted_history = self._format_history_for_gemini(chat_history)
            
            chat = self.model.start_chat(history=formatted_history)
            
            response = chat.send_message(f"{system_instruction}\n\nPREGUNTA USUARIO: {user_question}")
            return response.text

        except Exception as e:
            return f"⚠️ Error en LLM Service: {str(e)}"
