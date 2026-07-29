import chromadb

from app.config.config import settings

# Ayarlar pydantic-settings üzerinden okunuyor: önce ortam değişkenleri
# (Docker Compose bunları veriyor), yoksa .env dosyası, o da yoksa varsayılan.
# Doğrudan os.getenv kullanıldığında .env dosyası hiç devreye girmiyordu.
chroma_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
triage_collection = chroma_client.get_or_create_collection(name="triage_documents")
