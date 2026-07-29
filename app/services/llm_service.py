"""Yerel LLM (Ollama) servisi.

Bulut tabanlı `openai_client.py`'nin yerine geçer. Tüm analiz artık
kendi makinemizde çalışan bir modelle yapılır; dışarıya istek gitmez.
"""

import json

import ollama

from app.config.config import settings
from app.utils.logger import logger

_client = ollama.Client(host=settings.ollama_base_url)


class LLMError(Exception):
    """LLM'den geçerli bir yanıt alınamadığında fırlatılır."""


def get_structured_completion(
    system_prompt: str,
    user_prompt: str,
    retries: int = 1,
    temperature: float = 0.2,
    keep_alive: str = "30m",
) -> dict:
    """Modelden JSON yanıt ister ve dict olarak döndürür.

    `format="json"` Ollama'ya gramer kısıtı uygulattığı için çıktı büyük
    ölçüde geçerli JSON olur; yine de küçük modellerde kayma olabildiğinden
    `retries` kadar yeniden denenir.

    `keep_alive` modeli VRAM'de tutar. Varsayılan 5 dakikada model bellekten
    düşüyor ve sonraki ilk istek ~90 saniye sürüyor; 30 dakika demo/kullanım
    sırasındaki bu donmayı engelliyor.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_raw = ""
    for attempt in range(retries + 1):
        try:
            response = _client.chat(
                model=settings.ollama_model,
                format="json",
                messages=messages,
                options={"temperature": temperature},
                keep_alive=keep_alive,
            )
        except Exception as exc:
            logger.error(f"Ollama bağlantı hatası (deneme {attempt + 1}): {exc}")
            raise LLMError("Yerel LLM servisine ulaşılamadı") from exc

        last_raw = response["message"]["content"]
        try:
            parsed = json.loads(last_raw)
        except json.JSONDecodeError:
            logger.error(
                f"JSON parse hatası (deneme {attempt + 1}): {last_raw[:200]}"
            )
            continue

        if isinstance(parsed, dict):
            return parsed

        logger.error(f"LLM dict yerine {type(parsed).__name__} döndürdü")

    raise LLMError(f"LLM geçerli JSON döndürmedi. Son yanıt: {last_raw[:200]}")


def check_health() -> bool:
    """Ollama sunucusu ayakta ve hedef model yüklü mü?"""
    try:
        models = _client.list().get("models", [])
    except Exception as exc:
        logger.error(f"Ollama erişilemiyor: {exc}")
        return False

    available = {m.get("model") or m.get("name") for m in models}
    return settings.ollama_model in available
