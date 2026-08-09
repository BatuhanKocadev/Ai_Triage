import chromadb
from chromadb.utils import embedding_functions

from app.config.config import settings

# Ayarlar pydantic-settings üzerinden okunuyor: önce ortam değişkenleri
# (Docker Compose bunları veriyor), yoksa .env dosyası, o da yoksa varsayılan.

# Bağlantı tembel kuruluyor: import anında kurulursa ChromaDB kapalıyken
# uygulama hiç açılmıyordu (/health bile cevap vermiyordu). Desen
# rag_service.py içindeki get_reranker() ile aynı.
_collection = None


def _gomme_fonksiyonu():
    """Ayarlardaki çok dilli modelden gömme fonksiyonu kurar.

    Açıkça veriliyor çünkü ChromaDB'nin varsayılanı all-MiniLM-L6-v2 (İngilizce);
    Türkçe sorguda ayırt edici olmayan vektör üretip yanlış dokümanları getiriyor.
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model
    )


def get_collection():
    global _collection
    if _collection is None:
        chroma_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        _collection = chroma_client.get_or_create_collection(
            name="triage_documents",
            embedding_function=_gomme_fonksiyonu(),
        )
    return _collection
