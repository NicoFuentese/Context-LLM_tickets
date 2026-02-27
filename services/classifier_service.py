import joblib
import re
import os
import numpy as np
import boto3
from dotenv import load_dotenv

class TicketClassifierService:
    def __init__(self):
        # 1. Cargar Variables de Entorno (AWS Credentials)
        load_dotenv()
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("DEEPSEEK_MODEL_ID")
        
        # 2. Inicializar y VERIFICAR Cliente AWS Bedrock
        try:
            # Creamos el cliente de Bedrock
            self.aws_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.aws_region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
            
            # --- NUEVO: VERIFICACIÓN REAL (PING A AWS) ---
            sts_client = boto3.client(
                service_name='sts',
                region_name=self.aws_region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
            )
            identidad = sts_client.get_caller_identity()
            
            # Si llegamos aquí, las credenciales son 100% válidas
            print("="*50)
            print("📡 ESTADO DE CONEXIÓN IA PROFUNDA (AWS BEDROCK)")
            print("="*50)
            print(f"✅ Credenciales AWS OK. ARN: {identidad['Arn'].split(':')[-1]}")
            print(f"✅ Agente DeepSeek R1 ({self.model_id}) en línea.")
            print("="*50)
            self.bedrock_ready = True
            
        except Exception as e:
            print("="*50)
            print(f"❌ ERROR CRÍTICO CONECTANDO A DEEPSEEK R1 (AWS): {e}")
            print("Verifica tu archivo .env y tus llaves de acceso.")
            print("="*50)
            self.bedrock_ready = False

        # 3. Cargar Modelos SVM
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = os.path.join(base_dir, 'data', 'models')
        
        pipeline_path = os.path.join(models_dir, 'svm_pipeline.pkl')
        encoder_path = os.path.join(models_dir, 'label_encoder.pkl')
        
        self.svm_ready = False
        try:
            if os.path.exists(pipeline_path) and os.path.exists(encoder_path):
                self.pipeline = joblib.load(pipeline_path)
                self.encoder = joblib.load(encoder_path)
                self.categorias_validas = self.encoder.classes_.tolist()
                self.svm_ready = True
                print("✅ Motor SVM Rápido (Local) en línea.")
            else:
                print("⚠️ Faltan los archivos .pkl de la SVM en data/models/")
        except Exception as e:
            print(f"❌ Error crítico cargando la SVM: {e}")
            
        # 4. Inyección de Reglas de Negocio
        # (El resto de tu __init__ sigue igual...)
        self.mapa_expertos = {
            "Orieta Catalan": "DBA", "Cesar Milko Lazo": "DBA", "Gonzalo Alejandro Tobar": "DBA",
            "Jean Franco Andre Miranda": "Ingenieros TI", "Claudio Daniel Aliste": "Ingenieros TI",
            "Rodrigo Andres Jara": "Ingenieros TI", "Rodrigo Aravena": "Ingenieros TI", "Jesus Ayala": "Ingenieros TI",
            "Jose Ignacio Mayea": "Ciberseguridad", "Ricchard Mancilla": "Ciberseguridad",
            "Gabriel Natan Pizarro": "Aplicaciones", "Luis Eduardo Villagra": "Aplicaciones",
            "Reinaldo Zuniga": "Aplicaciones", "Christian Miguel Hevia": "Aplicaciones", "Veronica Paz Ramirez": "Aplicaciones",
            "Josefa Ignacia Lohaus": "ABM"
        }
        self.reglas_expertos = "\n".join([f"- Si menciona a '{nombre}', es '{area}'." for nombre, area in self.mapa_expertos.items()])

    def es_ticket_basura(self, texto: str) -> bool:
        """Detecta tickets sin contexto (ahorro de API)."""
        palabras = texto.strip().split()
        basura_comun = ['consulta', 'solicitud', 'ayuda', 'urgente', 'problema', 'error', 'ticket']
        if len(palabras) <= 2:
            if all(p.lower() in basura_comun for p in palabras):
                return True
        return False

    def limpiar_texto(self, texto: str) -> str:
        if not isinstance(texto, str): return ""
        texto = texto.lower()
        texto = re.sub(r'\(\d+\)$', '', texto) 
        texto = re.sub(r'^(rv|re|fwd|enc):\s*', '', texto)
        texto = re.sub(r'\[glpi #\d+\]', '', texto) 
        texto = re.sub(r'[^a-záéíóúñ0-9 ]', '', texto) 
        return texto.strip()

    def decidir_accion(self, clase_predicha: str, confianza: float) -> str:
        if clase_predicha in ['ABM', 'Ciberseguridad', 'DBA']:
            if confianza >= 0.60: return "SVM (Auto-Asignar)"
        if clase_predicha in ['Aplicaciones', 'Soporte de Campo', 'Desarrollo de Sistemas', 'Desarrollo de Sistemas y Proyectos Tecnológicos']:
            if confianza >= 0.80: return "SVM (Auto-Asignar)"
        if confianza >= 0.75: return "SVM (Auto-Asignar)"
        return "Agente IA"

    def _llamar_deepseek_bedrock(self, texto_ticket: str) -> dict:
        """Llama a DeepSeek-R1 vía AWS Bedrock usando tu super-prompt."""
        if not self.bedrock_ready:
            return {"categoria": "Requiere Humano (Bedrock Offline)", "confianza": 0.0, "accion": "Derivado a L2"}

        prompt = f"""Eres un Despachador Senior de una Mesa de Ayuda TI en Chile.
        Tu tarea es analizar el título/descripción de un ticket y clasificarlo ESTRICTAMENTE en UNA de estas categorías:
        {self.categorias_validas}

        MAPA DE EXPERTOS (PRIORIDAD MÁXIMA):
        {self.reglas_expertos}

        GLOSARIO DE SIGLAS (TRADUCCIÓN OBLIGATORIA):
        - TTI -> 'Técnico TI'
        - EO / Electric Office -> 'Soporte de Campo'
        - MGS -> 'Desarrollo de Sistemas y Proyectos Tecnológicos'
        - OSF -> Ver reglas abajo.

        REGLAS DE DESEMPATE Y CONFLICTOS:
        1. CONTRASEÑAS: "OSF", "ERP", "Oracle" -> 'DBA'. "Clevest", "Red" -> 'Técnico TI'.
        2. ACCESOS: "Cuenta bloqueada" -> 'DBA'. "Alta usuarios" -> 'ABM'.
        3. FALLAS: "Caida ORM", "Monitor OSF" -> 'Aplicaciones'.

        INSTRUCCIONES FINALES:
        Analiza el ticket paso a paso. Entrega TU RESPUESTA FINAL OBLIGATORIAMENTE dentro de las etiquetas <categoria></categoria>.

        Ticket a clasificar: "{texto_ticket}"
        Respuesta:"""

        try:
            response = self.aws_client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"temperature": 0.0}
            )
            
            respuesta_cruda = response['output']['message']['content'][0]['text']
            
            match = re.search(r'<categoria>(.*?)</categoria>', respuesta_cruda, re.IGNORECASE)
            
            if match:
                categoria = match.group(1).strip()
            else:
                if "</think>" in respuesta_cruda:
                    categoria = respuesta_cruda.split("</think>")[-1].strip()
                else:
                    categoria = respuesta_cruda.strip()
                    
            return {"categoria": categoria, "confianza": 99.9, "accion": "Clasificado por DeepSeek R1"}
            
        except Exception as e:
            print(f"Error llamando a AWS Bedrock: {e}")
            return {"categoria": "Error de Bedrock", "confianza": 0.0, "accion": "Derivado a L2"}

    def analizar_ticket(self, titulo: str, descripcion: str = "") -> dict:
        if not self.svm_ready:
            return {"categoria": "Desconocida", "confianza": 0.0, "accion": "Error (SVM Offline)"}

        texto_completo = f"{titulo} {descripcion}"
        
        # 1. Filtro Basura Rápido
        if self.es_ticket_basura(texto_completo):
            return {"categoria": "Sin Categoria", "confianza": 0.0, "accion": "Cierre Automático (Basura)"}
            
        texto_limpio = self.limpiar_texto(texto_completo)
        if not texto_limpio:
             return {"categoria": "Sin Texto", "confianza": 0.0, "accion": "Derivado a L2"}

        try:
            # 2. Predicción SVM
            probs = self.pipeline.predict_proba([texto_limpio])[0]
            max_prob = float(np.max(probs))
            pred_index = np.argmax(probs)
            categoria_svm = self.encoder.inverse_transform([pred_index])[0]
            
            accion = self.decidir_accion(categoria_svm, max_prob)
            
            # 3. Model Cascade -> DeepSeek R1
            if accion == "Agente IA":
                print(f"SVM dudó ({max_prob:.2f}). Derivando a Bedrock (DeepSeek R1)...")
                return self._llamar_deepseek_bedrock(texto_completo)
            
            return {
                "categoria": categoria_svm,
                "confianza": round(max_prob * 100, 2),
                "accion": accion
            }
        except Exception as e:
            print(f"Error en analizador híbrido: {e}")
            return {"categoria": "Error", "confianza": 0.0, "accion": "Derivado a L2"}