from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenAI artık zorunlu değil; analiz yerel LLM (Ollama) üzerinden yapılıyor.
    openai_api_key: Optional[str] = None

    # Yerel LLM (Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"

    # İlişkisel veritabanı (Gün 13'te devreye giriyor)
    database_url: str = "postgresql+psycopg2://triage:triage@localhost:5432/ai_triage"

    # Kimlik doğrulama
    jwt_secret_key: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    # Kapalı: açıkken model, getirilen protokol kriterini örneklere bakarak eziyordu
    # (izole deney ve gerekçe: Ek C, Gün 24).
    few_shot_aktif: bool = False

    # --- Güvenlik (Gün 21) ---
    # Üç sayaç da kayan pencerede ama ayrı kovalarda; ikisi IP'ye, biri kullanıcı adına.
    rate_limit_genel: int = 30
    # Kullanıcı adı başına, yalnızca BAŞARISIZ giriş denemeleri.
    rate_limit_giris: int = 5
    # /auth/login'in ikinci katmanı: IP başına toplam hacim (parola serpmeyi kapatır).
    rate_limit_giris_ip: int = 30
    rate_limit_pencere_sn: int = 60
    # Dosya yükleme sınırları; uzantı listesi virgülle ayrılır.
    max_upload_mb: int = 10
    izinli_uzantilar: str = "pdf,docx,txt"
    # CORS: varsayılan yalnızca yerel Streamlit. "*" bırakmak savunulamaz.
    cors_origins: str = "http://localhost:8501"

    # Vektör veritabanı
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # RAG / yeniden sıralama
    # Çok dilli olmak zorunda: bge-reranker-base Türkçede hiç ayrım üretmiyordu.
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    # Çok dilli olmak zorunda: ChromaDB varsayılanı (all-MiniLM-L6-v2) sadece İngilizce.
    embedding_model: str = "BAAI/bge-m3"
    # Ölçümle belirlendi; alakasız sorguların en yükseğinin 1,7 katı. Reranker, gömme
    # modeli ya da derleme değişirse scripts/kalibre_esik.py ile YENİDEN ÖLÇÜLMELİ.
    rerank_threshold: float = 0.005

    # Chroma'dan reranker'a giden aday sayısı; 10 iken doğru protokolü dışarı itiyordu.
    top_k_initial: int = 20

    # Ses tanıma (STT) — faster-whisper
    whisper_model_size: str = "medium"
    whisper_device: str = "auto"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
