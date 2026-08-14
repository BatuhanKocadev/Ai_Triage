"""Koleksiyonun ayarlardaki çok dilli gömme modeliyle açıldığını dondurur."""

import chromadb
import pytest
from chromadb.utils import embedding_functions

from app.config.config import settings
from app.services import chroma_service


class _SahteGomme:
    """SentenceTransformerEmbeddingFunction yerine geçer; model adını kaydeder."""

    def __init__(self, model_name):
        self.model_name = model_name


class _SahteIstemci:
    """chromadb.HttpClient yerine geçer; koleksiyon çağrısının kwargs'ını tutar."""

    def __init__(self, **kwargs):
        self.kurulum = kwargs
        self.koleksiyon_kwargs = None

    def get_or_create_collection(self, **kwargs):
        self.koleksiyon_kwargs = kwargs
        return object()


@pytest.fixture
def sahte_chromadb(monkeypatch):
    """Gerçek ChromaDB'ye ve gerçek modele hiç dokunmadan get_collection'ı izler."""
    olusan = {}

    def _istemci_uret(**kwargs):
        olusan["istemci"] = _SahteIstemci(**kwargs)
        return olusan["istemci"]

    # Yama KAYNAĞIN kendisine uygulanıyor, uç modülün takma adına değil:
    # chroma_service bu iki adı artık modül düzeyinde tutmuyor, get_collection()
    monkeypatch.setattr(chromadb, "HttpClient", _istemci_uret)
    monkeypatch.setattr(
        embedding_functions,
        "SentenceTransformerEmbeddingFunction",
        _SahteGomme,
    )
    # Modül düzeyindeki tekil önceki testten dolu kalmış olabilir.
    monkeypatch.setattr(chroma_service, "_collection", None)
    return olusan


def test_gomme_modeli_ayarlardan_okunur(sahte_chromadb, monkeypatch):
    # Varsayılandan FARKLI bir değer zorlanıyor: kod sabit yazılmış olsaydı
    # (örn. "BAAI/bge-m3") bu mutasyon testi kırmızıya çevirirdi.
    monkeypatch.setattr(settings, "embedding_model", "test-gomme-modeli-xyz")

    chroma_service.get_collection()

    kwargs = sahte_chromadb["istemci"].koleksiyon_kwargs
    gomme = kwargs["embedding_function"]
    assert isinstance(gomme, _SahteGomme)
    assert gomme.model_name == "test-gomme-modeli-xyz"
