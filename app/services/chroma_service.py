import chromadb

from app.config.config import settings

# Ayarlar pydantic-settings üzerinden okunuyor: önce ortam değişkenleri
# (Docker Compose bunları veriyor), yoksa .env dosyası, o da yoksa varsayılan.
# Doğrudan os.getenv kullanıldığında .env dosyası hiç devreye girmiyordu.

# Bağlantı tembel kuruluyor: import anında kurulursa ChromaDB kapalıyken
# uygulama hiç açılmıyordu (/health bile cevap vermiyordu). Desen
# rag_service.py içindeki get_reranker() ile aynı.
_collection = None


def get_collection():
    global _collection
    if _collection is None:
        chroma_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        _collection = chroma_client.get_or_create_collection(name="triage_documents")
    return _collection
