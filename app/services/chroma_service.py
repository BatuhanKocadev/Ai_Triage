"""ChromaDB bağlantısı ve triyaj koleksiyonu.

Ayarlar pydantic-settings üzerinden okunuyor: önce ortam değişkenleri
(Docker Compose bunları veriyor), yoksa .env dosyası, o da yoksa varsayılan.
"""

from app.config.config import settings

# Bağlantı tembel kuruluyor: import anında kurulursa ChromaDB kapalıyken
# uygulama hiç açılmıyordu (/health bile cevap vermiyordu).
_collection = None


def _gomme_fonksiyonu():
    """Ayarlardaki çok dilli modelden gömme fonksiyonu kurar.

    Açıkça veriliyor çünkü ChromaDB'nin varsayılanı all-MiniLM-L6-v2 (İngilizce);
    Türkçe sorguda ayırt edici olmayan vektör üretip yanlış dokümanları getiriyor.
    """
    # chromadb BURADA import ediliyor, modül düzeyinde değil. Sebebi görünmez
    # olduğu için yazılıyor: chromadb hafif görünür ama `onnxruntime` ve
    # `tokenizers` çekiyor, ve modül düzeyinde import edilince `app.main`
    # açılışına da CI ortamına da o ağırlığı ekliyor (tasarım K2).
    from chromadb.utils import embedding_functions

    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model
    )


def get_collection():
    global _collection
    if _collection is None:
        # Yukarıdaki `_gomme_fonksiyonu` ile aynı sebep: chromadb hafif görünür
        # ama `onnxruntime`/`tokenizers` çekiyor. Modül düzeyine taşımayın
        # (tasarım K2); `tests/birim/test_import_agirligi.py` bunu bağlıyor.
        import chromadb

        chroma_client = chromadb.HttpClient(
            host=settings.chroma_host, port=settings.chroma_port
        )
        _collection = chroma_client.get_or_create_collection(
            name="triage_documents",
            embedding_function=_gomme_fonksiyonu(),
        )
    return _collection
