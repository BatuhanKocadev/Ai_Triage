"""tests/api/ altındaki tüm uç testlerinin gördüğü ortak fixture'lar."""

import pytest

from app.api import ai as ai_modulu
from app.api import document as document_modulu
from app.api import speech as speech_modulu


@pytest.fixture
def esik_alti(monkeypatch):
    """RAG'i eşiğin altında kalmış gibi ayarlar; LLM hiç çağrılmamalı."""
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
    """/document/upload testlerinin gerçek ChromaDB koleksiyonuna yazmasını önler."""
    monkeypatch.setattr(
        document_modulu, "get_collection", lambda: _YazmayiReddedenKoleksiyon()
    )


@pytest.fixture
def transkript_engelle(monkeypatch):
    """Yetki/doğrulama testlerinin gerçek faster-whisper modeline ulaşmasını önler."""

    def _asla_cagrilmamali(dosya_yolu: str) -> str:
        """Gerçek `transcribe`'ın yerine geçer; çağrılırsa modeli yüklemek yerine testi patlatır."""
        raise AssertionError(
            "Gerçek transcribe çağrıldı — uçtaki koruma gevşemiş demektir. "
            "Bu testin gerçek modeli yüklemesi beklenmiyor."
        )

    monkeypatch.setattr(speech_modulu, "transcribe", _asla_cagrilmamali)
