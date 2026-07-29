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

    # Vektör veritabanı
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # RAG / yeniden sıralama
    # bge-reranker-base yalnızca İngilizce+Çince eğitimli olduğu için Türkçe
    # sorgularda hiç ayrım üretmiyordu (tüm skorlar ~0.50). v2-m3 çok dillidir.
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    # Eşik scripts/kalibre_esik.py ile ölçülerek seçildi: alakasız sorgular
    # tam 0.5000 alıyor, ilgili sorgular 0.502-0.664 aralığında. 0.52 eşiği
    # ilgili sorguların 7/8'ini geçiriyor, alakasızların hiçbirini geçirmiyor.
    rerank_threshold: float = 0.52

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
