import os
import boto3
from dotenv import load_dotenv

class ITAdvisorService:
    def __init__(self):
        # Cargamos las credenciales de AWS desde tu .env
        load_dotenv()
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("DEEPSEEK_MODEL_ID") 
        
        try:
            self.aws_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.aws_region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
            print("✅ LLM Service Principal: Conectado a AWS Bedrock (DeepSeek R1).")
        except Exception as e:
            print(f"❌ Error conectando LLM a AWS Bedrock: {e}")

        # Matriz de expertos (copiada de tu lógica de negocio)
        self.mapa_expertos = {
            "DBA": ["Orieta Catalan", "Cesar Milko Lazo", "Gonzalo Alejandro Tobar"],
            "Ingenieros TI": ["Jean Franco Andre Miranda", "Claudio Daniel Aliste", "Rodrigo Andres Jara", "Rodrigo Aravena", "Jesus Ayala"],
            "Ciberseguridad": ["Jose Ignacio Mayea", "Ricchard Mancilla"],
            "Aplicaciones": ["Gabriel Natan Pizarro", "Luis Eduardo Villagra", "Reinaldo Zuniga", "Christian Miguel Hevia", "Veronica Paz Ramirez"],
            "ABM": ["Josefa Ignacia Lohaus"]
        }

    def get_system_prompt(self, workload_context: str) -> str:
        # Convertimos el diccionario a un texto que la IA entienda
        skills_str = "\n".join([f"- {area}: {', '.join(nombres)}" for area, nombres in self.mapa_expertos.items()])
        
        return f"""
        ROL: Eres el Tech Lead y Arquitecto de la Mesa de Ayuda 'Smart-IT Ops'.
        
        TU SUPERPODER: Asignar tickets inteligentemente buscando el equilibrio perfecto entre Especialidad y Carga Laboral.
        
        --- MATRIZ DE EXPERTOS (Área: Nombres) ---
        {skills_str}

        --- CARGA DE TRABAJO ACTUAL (Tickets Activos) ---
        {workload_context}

        INSTRUCCIONES PARA ASIGNACIÓN:
        1. Lee los detalles del ticket. Fíjate especialmente en el "[ANÁLISIS SVM]" que viene adjunto.
        2. Si la sugerencia del Motor es "SVM (Auto-Asignar)" o "Clasificado por DeepSeek", CONFÍA ciegamente en esa categoría.
        3. Busca en la Matriz de Expertos quién pertenece a esa categoría.
        4. Revisa la Carga de Trabajo Actual y elige al experto de esa área que tenga MENOS tickets asignados.
        5. Justifica tu decisión brevemente.

        FORMATO DE RESPUESTA REQUERIDO:
        - 🎫 **Ticket:** [Título]
        - 🏷️ **Categoría Final:** [Categoría detectada]
        - 👉 **Asignar a:** **[Nombre del Técnico]**
        - 💡 **Razón:** "[Nombre] es del área [Área] y actualmente tiene una carga baja de [X] tickets."
        """

    def get_recommendation(self, user_query: str, workload_data: dict, specific_ticket_info: str = "", rag_context: str = "") -> str:
        try:
            # 1. Preparar texto de carga laboral actual
            workload_str = "\n".join([f"- {tecnico}: {cantidad} tickets activos" for tecnico, cantidad in workload_data.items()])
            
            # 2. Generar instrucciones del sistema
            system_instruction = self.get_system_prompt(workload_str)

            # 3. Construir el mensaje del usuario (Pregunta + Datos del Ticket)
            full_query = user_query
            if specific_ticket_info:
                full_query += f"\n\n--- DETALLES DEL TICKET A ANALIZAR ---\n{specific_ticket_info}"

            #Inyectamos el conocimiento del manual para que DeepSeek lo lea
            if rag_context:
                full_query += f"\n{rag_context}"

            # 4. Llamada a AWS Bedrock (DeepSeek R1)
            response = self.aws_client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": full_query}]}],
                system=[{"text": system_instruction}],
                inferenceConfig={
                    "temperature": 0.1 # Muy bajo para evitar alucinaciones en la asignación
                }
            )
            
            respuesta_cruda = response['output']['message']['content'][0]['text']
            
            # 5. Limpieza especial para DeepSeek R1 (Reasoner)
            # El modelo R1 suele incluir sus pensamientos entre <think>...</think>
            if "</think>" in respuesta_cruda:
                respuesta_limpia = respuesta_cruda.split("</think>")[-1].strip()
                return respuesta_limpia
                
            return respuesta_cruda.strip()

        except Exception as e:
            return f"⚠️ Error en el Agente Principal (AWS Bedrock): {str(e)}"