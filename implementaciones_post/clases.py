import google.generativeai as genai
import chromadb

class GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    """
    Wrapper para usar los Embeddings de Google dentro de ChromaDB.
    """ 
    def __call__(self, input: list[str]) -> list[list[float]]:
        # model="models/embedding-001" es el estándar de Gemini para esto
        return [
            genai.embed_content(
                model="models/embedding-001",
                content=text,
                task_type="retrieval_document"
            )["embedding"]
            for text in input
        ]