import os
import time
import chromadb
import pypdf
from chromadb.utils import embedding_functions
from chromadb.config import Settings
import google.generativeai as genai
from config.settings import DATA_DIR, GOOGLE_API_KEY

# Configurar ruta de persistencia
VECTOR_DB_PATH = DATA_DIR / "vector_store"
PROTOCOLS_DIR = DATA_DIR / "protocols"

class GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    Wrapper con 'Freno de Mano' para el Tier Gratuito de Gemini.
    """
    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings = []
        for text in input:
            try:
                response = genai.embed_content(
                    model="models/embedding-001",
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(response["embedding"])
                
                # 🛑 FRENO: Esperar 2 segundos entre cada petición
                # Esto reduce la velocidad a máx 30 peticiones por minuto, 
                # manteniéndonos seguros en el Free Tier.
                time.sleep(2) 
                
            except Exception as e:
                print(f"⚠️ Error vectorizando chunk (saltando): {e}")
                # En caso de error, devolvemos un vector vacío o ceros para no romper la lista
                # (Opcional: podrías reintentar, pero por ahora simplificamos)
                embeddings.append([0.0] * 768) 
                
        return embeddings

class KnowledgeBaseService:
    def __init__(self):
        # Inicializar cliente de Chroma persistente
        self.client = chromadb.PersistentClient(
            path=str(VECTOR_DB_PATH),
            settings=Settings(anonymized_telemetry=False))
        self.embedding_fn = GeminiEmbeddingFunction()
        
        # Crear o recuperar la colección "protocols"
        self.collection = self.client.get_or_create_collection(
            name="it_protocols",
            embedding_function=self.embedding_fn
        )

    def _extract_text_from_pdf(self, file_path):
        text = ""
        try:
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text
        except Exception as e:
            print(f"Error leyendo PDF {file_path}: {e}")
            return ""

    def _smart_chunking(self, text, chunk_size=1000, overlap=200):
        """
        Divide el texto respetando frases y manteniendo contexto (Overlap).
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            
            # Si no estamos al final, intentamos buscar el último punto o salto de línea
            # para no cortar una frase a la mitad.
            if end < text_len:
                # Buscar el último punto '.' en el rango del chunk
                last_period = text.rfind('.', start, end)
                if last_period != -1 and last_period > start + (chunk_size * 0.5):
                    end = last_period + 1 # Cortar después del punto
                else:
                    # Si no hay punto, buscar salto de línea
                    last_newline = text.rfind('\n', start, end)
                    if last_newline != -1 and last_newline > start + (chunk_size * 0.5):
                        end = last_newline + 1
            
            # Extraer el chunk y limpiar espacios extra
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Avanzar, pero retrocediendo el 'overlap' para mantener contexto
            # (Solo si no hemos llegado al final)
            start = end - overlap if end < text_len else end
            
        return chunks

    def ingest_protocols(self):
        if not PROTOCOLS_DIR.exists():
            os.makedirs(PROTOCOLS_DIR)
            return "Carpeta creada."

        files = [f for f in os.listdir(PROTOCOLS_DIR) if f.endswith(('.txt', '.md', '.pdf'))]
        
        if not files:
            return "⚠️ No hay archivos soportados."

        self.client.delete_collection("it_protocols")
        self.collection = self.client.get_or_create_collection(
            name="it_protocols", 
            embedding_function=self.embedding_fn
        )

        total_chunks = 0
        
        for filename in files:
            file_path = PROTOCOLS_DIR / filename
            text = ""
            
            if filename.endswith('.pdf'):
                text = self._extract_text_from_pdf(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            
            if not text.strip():
                continue

            # --- USO DEL NUEVO CHUNKING INTELIGENTE ---
            chunks = self._smart_chunking(text, chunk_size=1000, overlap=200)
            # ------------------------------------------
            
            ids = [f"{filename}_{i}" for i in range(len(chunks))]
            metadatas = [{"source": filename} for _ in range(len(chunks))]
            
            if chunks:
                self.collection.add(documents=chunks, ids=ids, metadatas=metadatas)
                total_chunks += len(chunks)
        
        return f"✅ Indexación Inteligente: {total_chunks} fragmentos generados (con Overlap)."

    def search_context(self, query: str, n_results: int = 25) -> str:
        """Busca los fragmentos más relevantes para la pregunta."""
        if self.collection.count() == 0:
            return ""

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Concatenar los documentos encontrados
        context_parts = results['documents'][0]
        sources = [m['source'] for m in results['metadatas'][0]]
        
        # Formatear para el LLM
        formatted_context = "\n\n--- DOCUMENTACIÓN INTERNA ENCONTRADA ---\n"
        for source, text in zip(sources, context_parts):
            formatted_context += f"[Fuente: {source}]\n{text}\n...\n"
            
        return formatted_context