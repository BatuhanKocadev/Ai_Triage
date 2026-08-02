"""RAG eşik kapısının davranışını dondurur: LLM ne zaman çağrılır, ne zaman çağrılmaz.

Bu kapı bilinçli bir maliyet/güvenlik kontrolüdür (CLAUDE.md); bug değildir.
"""

import pytest

from app.services import rag_service
from tests.yardimcilar.sahte_rag import SahteKoleksiyon, sahte_reranker_uret


def test_koleksiyon_yoksa_bos_liste_doner():
    # collection None ise reranker hiç yüklenmemeli.
    assert rag_service.retrieve_and_rerank(query="karın ağrısı", collection=None) == []


def test_esik_altinda_bos_liste_doner(monkeypatch):
    # Ham -10 skoru sigmoid'den ~0.00005 çıkar; 0.52 eşiğinin çok altında.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([-10.0]))
    koleksiyon = SahteKoleksiyon(["Apandisit protokolü"])
    sonuc = rag_service.retrieve_and_rerank(query="alakasiz sorgu", collection=koleksiyon)
    assert sonuc == []


def test_esik_ustunde_dokuman_doner(monkeypatch):
    # Ham 10.0 skoru sigmoid'den ~0.99995 çıkar; eşiği rahat geçer.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([10.0]))
    koleksiyon = SahteKoleksiyon(["Apandisit protokolü"])
    sonuc = rag_service.retrieve_and_rerank(query="karın ağrısı", collection=koleksiyon)
    assert len(sonuc) == 1
    assert "Apandisit protokolü" in sonuc[0]


def test_tam_esik_degeri_dahil_edilir(monkeypatch):
    # SINIR DAVRANIŞI: ham 0.0 -> sigmoid tam 0.5. Kod "< threshold" ile eleme
    # yaptığı için tam eşiğe eşit skor ELENMEZ, dokümana dahil edilir.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.0]))
    koleksiyon = SahteKoleksiyon(["Sınırdaki doküman"])
    sonuc = rag_service.retrieve_and_rerank(
        query="sinir", collection=koleksiyon, threshold=0.5
    )
    assert len(sonuc) == 1


def test_dokuman_kaynagi_ciktiya_eklenir(monkeypatch):
    # Çıktı "[Kaynak: dosya] metin" biçiminde olmalı; doktor kaynağı görebilmeli.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([10.0]))
    koleksiyon = SahteKoleksiyon(["Metin"], kaynaklar=["gogus_agrisi.pdf"])
    sonuc = rag_service.retrieve_and_rerank(query="q", collection=koleksiyon)
    assert sonuc[0].startswith("[Kaynak: gogus_agrisi.pdf]")


def test_dokumanlar_skora_gore_siralanir(monkeypatch):
    # En yüksek skorlu doküman başa gelmeli.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([1.0, 9.0]))
    koleksiyon = SahteKoleksiyon(["Dusuk skorlu", "Yuksek skorlu"])
    sonuc = rag_service.retrieve_and_rerank(query="q", collection=koleksiyon)
    assert "Yuksek skorlu" in sonuc[0]


def test_metadata_filtresi_koleksiyona_gecirilir(monkeypatch):
    # source_document verildiğinde Chroma sorgusuna "where" olarak gitmeli.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([10.0]))
    koleksiyon = SahteKoleksiyon(["Metin"])
    rag_service.retrieve_and_rerank(
        query="q", collection=koleksiyon, metadata_filter={"source": "a.pdf"}
    )
    assert koleksiyon.son_cagri["where"] == {"source": "a.pdf"}


def test_bos_koleksiyon_sonucu_bos_liste_doner(monkeypatch):
    # Chroma hiç doküman döndürmezse reranker çağrılmadan boş dönmeli.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([]))
    koleksiyon = SahteKoleksiyon([])
    assert rag_service.retrieve_and_rerank(query="q", collection=koleksiyon) == []
