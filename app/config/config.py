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
    # 9 Ağustos 2026'da ölçüldü (scripts/kalibre_esik.py, 15 protokol / 48 chunk,
    # 18 ilgili + 10 alakasız sorgu). Ölçülen dağılım:
    #   ilgili   -> 0.0005 ... 0.7381
    #   alakasız -> 0.0000 ... 0.0030
    # 0.005 seçildi: alakasız sorguların en yükseğinin 1.7 katı, bir sonraki net
    # ilgili skora (0.0089) kadar olan boşlukta duruyor. 18 ilgiliden 16'sı
    # geçiyor, 10 alakasızın hiçbiri geçmiyor.
    # Sayının küçük olması bir hata değil: reranker olasılık döndürüyor ve bu
    # derlemede alakasız eşleşmeler sıfıra yapışıyor. Önemli olan mutlak değer
    # değil, iki sınıf arasındaki ayrım — düzeltmeden önce sınıflar iç içeydi
    # (ilgili min 0.5001 < alakasız max 0.5004) ve hiçbir eşik işe yaramıyordu.
    # Eşiğin altında kalan iki ilgili sorgu (yanık 0.0005, karaktersiz inme
    # 0.0031) Ek C'de Gün 22 borcu olarak kayıtlı.
    # Reranker modeli, gömme modeli ya da derleme değişirse YENİDEN ÖLÇÜLMELİ.
    rerank_threshold: float = 0.005

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
