"""tests/api/ altındaki tüm uç testlerinin gördüğü ortak fixture'lar."""

import pytest

from app.api import ai as ai_modulu
from app.api import document as document_modulu
from app.api import speech as speech_modulu


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


_YAZMA_UYARISI = (
    "ChromaDB'ye yazma girişimi: yetki kapısı testi uç gövdesine ilerledi. "
    "Bu bir regresyondur — gerçek koleksiyona doküman yazılacaktı."
)


class _YazmayiReddedenKoleksiyon:
    """upsert/delete çağrılırsa testi patlatır — gerçek koleksiyona yazılmadığını kanıtlar."""

    def get(self, **kwargs):
        """Okuma zararsız olduğu için boş sonuç döndürür; akış yazma adımına ilerlesin."""
        return {"ids": [], "metadatas": [], "documents": []}

    def upsert(self, **kwargs):
        raise AssertionError(_YAZMA_UYARISI)

    def delete(self, **kwargs):
        """Silme de bir yazma işlemidir; upsert ile aynı uyarıyı fırlatır."""
        raise AssertionError(_YAZMA_UYARISI)


@pytest.fixture
def dokuman_yazmayi_engelle(monkeypatch):
    """/document/upload testlerinin gerçek ChromaDB koleksiyonuna yazmasını önler.

    DİKKAT — gereksiz görünse bile SİLMEYİN, `esik_alti` ile aynı sebepten.
    `/document/upload` testleri bugün uç gövdesine hiç girmiyor (401/403 daha
    önce dönüyor), ama tam da korudukları kural gevşerse (require_admin_role)
    istek gövdeye ilerliyor ve upload'ın yazma adımını, yani
    `get_collection().upsert(...)`'i çalıştırıyor.
    `esik_alti`'ndan farkı şu: orada risk gerçek servisten
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


@pytest.fixture
def transkript_engelle(monkeypatch):
    """Yetki/doğrulama testlerinin gerçek faster-whisper modeline ulaşmasını önler.

    DİKKAT — gereksiz görünse bile SİLMEYİN, `dokuman_yazmayi_engelle` ile aynı
    sebepten. Bu testler bugün uç gövdesine hiç girmiyor (401/400 daha önce
    dönüyor), ama tam da korudukları kural gevşerse istek gövdeye ilerliyor ve
    `transcribe` çağrılıyor — yani faster-whisper `medium` modeli indirilip
    yükleniyor: yüzlerce MB indirme, dakikalarca CPU. CI'da bu, testleri on
    dakikanın üstüne çıkaran bilinen tuzağın ta kendisidir.

    Yamalama uç modülünün ad alanına uygulanıyor (`app.api.speech.transcribe`),
    servis modülüne değil: `speech.py` adı kendi ad alanına almış durumda.
    """

    def _asla_cagrilmamali(dosya_yolu: str) -> str:
        """Gerçek `transcribe`'ın yerine geçer; çağrılırsa modeli yüklemek yerine testi patlatır."""
        raise AssertionError(
            "Gerçek transcribe çağrıldı — uçtaki koruma gevşemiş demektir. "
            "Bu testin gerçek modeli yüklemesi beklenmiyor."
        )

    monkeypatch.setattr(speech_modulu, "transcribe", _asla_cagrilmamali)
