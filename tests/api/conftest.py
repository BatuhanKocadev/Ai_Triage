"""tests/api/ altındaki tüm uç testlerinin gördüğü ortak fixture'lar."""

import pytest

from app.api import ai as ai_modulu
from app.api import document as document_modulu


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


class _YazmayiReddedenKoleksiyon:
    """upsert çağrılırsa testi patlatır — gerçek koleksiyona yazılmadığını kanıtlar."""

    def upsert(self, **kwargs):
        raise AssertionError(
            "ChromaDB'ye yazma girişimi: yetki kapısı testi uç gövdesine ilerledi. "
            "Bu bir regresyondur — gerçek koleksiyona doküman yazılacaktı."
        )


@pytest.fixture
def dokuman_yazmayi_engelle(monkeypatch):
    """/document/upload testlerinin gerçek ChromaDB koleksiyonuna yazmasını önler.

    DİKKAT — gereksiz görünse bile SİLMEYİN, `esik_alti` ile aynı sebepten.
    `/document/upload` testleri bugün uç gövdesine hiç girmiyor (401/403 daha
    önce dönüyor), ama tam da korudukları kural gevşerse (require_admin_role)
    istek gövdeye ilerliyor ve `document.py:125` `get_collection().upsert(...)`
    çalıştırıyor. `esik_alti`'ndan farkı şu: orada risk gerçek servisten
    OKUMAKTI, burada gerçek `triage_documents` koleksiyonuna YAZMAK — yani her
    hasta sorgusunun tarandığı vektör veritabanının kirlenmesi.

    Bu tehlike ölçüldü: Görev 9'un `auth_service.py:78` mutasyonu
    `assert 500 == 403` verdi; 500, isteğin gövdeye ilerleyip ChromaDB'ye
    ulaşamamasından geliyordu. Chroma o an ayakta olsaydı test kırmızı olmak
    yerine koleksiyona yazacaktı.
    """
    monkeypatch.setattr(
        document_modulu, "get_collection", lambda: _YazmayiReddedenKoleksiyon()
    )
