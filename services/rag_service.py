import os
import chromadb
import pypdf
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from config.settings import DATA_DIR

# Configurar ruta de persistencia
VECTOR_DB_PATH = DATA_DIR / "vector_store"
PROTOCOLS_DIR = DATA_DIR / "protocols"

class KnowledgeBaseService:
    def __init__(self):
        # Inicializar cliente de Chroma persistente
        self.client = chromadb.PersistentClient(
            path=str(VECTOR_DB_PATH),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 🟢 NUEVO: Motor de Embeddings 100% Local y Gratuito (HuggingFace)
        # La primera vez descargará un modelo muy ligero (~80MB) y luego volará en local.
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
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
        """Divide el texto respetando frases y manteniendo contexto (Overlap)."""
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            if end < text_len:
                last_period = text.rfind('.', start, end)
                if last_period != -1 and last_period > start + (chunk_size * 0.5):
                    end = last_period + 1 
                else:
                    last_newline = text.rfind('\n', start, end)
                    if last_newline != -1 and last_newline > start + (chunk_size * 0.5):
                        end = last_newline + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < text_len else end
            
        return chunks

    def ingest_protocols(self):
        if not PROTOCOLS_DIR.exists():
            os.makedirs(PROTOCOLS_DIR)
            return "Carpeta creada."

        files = [f for f in os.listdir(PROTOCOLS_DIR) if f.endswith(('.txt', '.md', '.pdf'))]
        
        if not files:
            return "⚠️ No hay archivos soportados."

        # ⚠️ CRÍTICO: Eliminamos la colección vieja para no mezclar vectores de Gemini con los de HuggingFace
        try:
            self.client.delete_collection("it_protocols")
        except:
            pass # Si no existe, ignorar
            
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

            chunks = self._smart_chunking(text, chunk_size=1000, overlap=200)
            ids = [f"{filename}_{i}" for i in range(len(chunks))]
            metadatas = [{"source": filename} for _ in range(len(chunks))]
            
            if chunks:
                self.collection.add(documents=chunks, ids=ids, metadatas=metadatas)
                total_chunks += len(chunks)
        
        return f"✅ Indexación Inteligente Local: {total_chunks} fragmentos generados."

    def search_context(self, query: str, n_results: int = 15) -> str:
        """Busca los fragmentos más relevantes para la pregunta."""
        if self.collection.count() == 0:
            return ""

        # Limitamos los resultados al máximo existente si hay menos de 15 chunks
        actual_results = min(n_results, self.collection.count())
        
        results = self.collection.query(
            query_texts=[query],
            n_results=actual_results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return ""

        context_parts = results['documents'][0]
        sources = [m['source'] for m in results['metadatas'][0]]
        
        formatted_context = "\n\n--- DOCUMENTACIÓN TÉCNICA (RAG) ---\n"
        for source, text in zip(sources, context_parts):
            formatted_context += f"[Fuente: {source}]\n{text}\n...\n"
            
        return formatted_context