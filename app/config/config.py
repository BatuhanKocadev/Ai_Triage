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
    # Gömme modeli çok dilli olmalı: ChromaDB'nin varsayılanı (all-MiniLM-L6-v2)
    # yalnızca İngilizce üzerinde eğitilmiştir ve Türkçe sorguda anlamsız
    # vektör üretiyor.
    embedding_model: str = "BAAI/bge-m3"
    # GEÇİCİ DEĞER — GÜVENİLMEZ. Bu 0.52, reranker skorlarının ikinci kez
    # sigmoid'den geçirildiği BOZUK ölçekte ölçülmüştü: o ölçekte tüm skorlar
    # 0.500-0.731 aralığına sıkışıyordu. Çift sigmoid kaldırıldığı için ölçek
    # tamamen değişti ve bu sayıyı gerekçelendiren ölçüm artık geçersiz.
    # Değer, gömme modeli de değiştiği için bilgi tabanı bge-m3 ile yeniden
    # kurulduktan SONRA scripts/kalibre_esik.py yeniden koşulup ondan
    # türetilecek. O ana kadar buradaki sayı bir kalibrasyon sonucu değil,
    # yalnızca yer tutucudur.
    rerank_threshold: float = 0.52

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
