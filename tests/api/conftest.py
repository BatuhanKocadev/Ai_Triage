"""tests/api/ altındaki tüm uç testlerinin gördüğü ortak fixture'lar."""

import pytest

from app.api import ai as ai_modulu


@pytest.fixture
def esik_alti(monkeypatch):
    """RAG'i eşiğin altında kalmış gibi ayarlar; LLM hiç çağrılmamalı.

    DİKKAT — yalnızca doğrulama/yetki kontrol eden testler de bu fixture'ı alır,
    gereksiz görünse bile SİLMEYİN. O testler bugün uç gövdesine hiç girmiyor
    (401/422 daha önce dönüyor), ama tam da korudukları kural gevşerse (min_length,
    le=120, Literal) istek gövdeye giriyor ve gerçek get_collection() çağrılıyor.
    Geliştirici makinesinde `docker compose up` ile ChromaDB ayakta olduğundan
    çağrı başarılı olabiliyor, eşiği geçip gerçek Ollama'ya gidiyor: temiz bir
    kırmızı yerine dakikalarca süren takılma. Bu fixture o yolu kapatır.
    """
    monkeypatch.setattr(ai_modulu, "get_collection", lambda: object())
    monkeypatch.setattr(ai_modulu, "retrieve_and_rerank", lambda **kwargs: [])
