"""RAG eşik kapısının davranışını dondurur: LLM ne zaman çağrılır, ne zaman çağrılmaz.

Bu kapı bilinçli bir maliyet/güvenlik kontrolüdür (CLAUDE.md); bug değildir.
"""

import pytest
import torch

from app.services import rag_service
from tests.yardimcilar.sahte_rag import SahteKoleksiyon, sahte_reranker_uret


def test_koleksiyon_yoksa_bos_liste_doner():
    # collection None ise reranker hiç yüklenmemeli.
    assert rag_service.retrieve_and_rerank(query="karın ağrısı", collection=None) == []


def test_esik_altinda_bos_liste_doner(monkeypatch):
    # 0.10 olasılığı 0.52 eşiğinin altında. Değer bilerek seçildi: eski çift
    # sigmoidli kodda sigmoid(0.10)=0.525 çıkıp eşiği GEÇİYORDU, yani bu test
    # düzeltmenin bağlayıcı kanıtı.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.10]))
    koleksiyon = SahteKoleksiyon(["Apandisit protokolü"])
    sonuc = rag_service.retrieve_and_rerank(query="alakasiz sorgu", collection=koleksiyon)
    assert sonuc == []


def test_esik_ustunde_dokuman_doner(monkeypatch):
    # 0.90 olasılığı 0.52 eşiğini rahatça geçer.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.90]))
    koleksiyon = SahteKoleksiyon(["Apandisit protokolü"])
    sonuc = rag_service.retrieve_and_rerank(query="karın ağrısı", collection=koleksiyon)
    assert len(sonuc) == 1
    assert "Apandisit protokolü" in sonuc[0]


def test_tam_esik_degeri_dahil_edilir(monkeypatch):
    # Skor eşiğe tam eşit; karşılaştırma >= olduğu için dahil edilmeli.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.52]))
    koleksiyon = SahteKoleksiyon(["Sınırdaki doküman"])
    sonuc = rag_service.retrieve_and_rerank(
        query="sinir", collection=koleksiyon, threshold=0.52
    )
    assert len(sonuc) == 1


def test_dokuman_kaynagi_ciktiya_eklenir(monkeypatch):
    # Çıktı "[Kaynak: dosya] metin" biçiminde olmalı; doktor kaynağı görebilmeli.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.90]))
    koleksiyon = SahteKoleksiyon(["Metin"], kaynaklar=["gogus_agrisi.pdf"])
    sonuc = rag_service.retrieve_and_rerank(query="q", collection=koleksiyon)
    assert sonuc[0].startswith("[Kaynak: gogus_agrisi.pdf]")


def test_dokumanlar_skora_gore_siralanir(monkeypatch):
    # İkinci doküman daha yüksek olasılık alıyor; çıktıda önce o gelmeli.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.60, 0.95]))
    koleksiyon = SahteKoleksiyon(["Dusuk skorlu", "Yuksek skorlu"])
    sonuc = rag_service.retrieve_and_rerank(query="q", collection=koleksiyon)
    assert "Yuksek skorlu" in sonuc[0]


def test_metadata_filtresi_koleksiyona_gecirilir(monkeypatch):
    # source_document verildiğinde Chroma sorgusuna "where" olarak gitmeli.
    # 0.90 olasılık ölçeğinde geçerli bir skor; 10.0 logit ölçeğinden kalmıştı ve
    # gerçek predict() böyle bir değer asla döndürmez.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.90]))
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


def test_reranker_skoru_ikinci_kez_ezilmez(monkeypatch):
    # CrossEncoder.predict() modelin Sigmoid aktivasyonunu zaten uyguluyor.
    # Kod bunu ikinci kez sigmoid'den geçirirse 0.90 skoru 0.711'e düşer ve
    # 0.80 eşiğini geçemez — dokuman sessizce elenir. Bu test o davranışı
    # dondurur: skor ne verildiyse o sayılmalı.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.90]))
    koleksiyon = SahteKoleksiyon(["Yanık protokolü"])

    sonuc = rag_service.retrieve_and_rerank(
        query="kaynar su döküldü", collection=koleksiyon, threshold=0.80
    )

    assert len(sonuc) == 1


def test_reranker_aktivasyonu_acikca_kuruluyor(monkeypatch):
    # Skor ölçeğinin tamamı predict()'in olasılık döndürmesine bağlı; bu da
    # CrossEncoder'a açıkça verilen Sigmoid aktivasyonundan geliyor. Argüman
    # silinirse predict() modelin config dosyasındaki varsayılana düşer ve ham
    # logit döndürebilir — o an bütün eşikler sessizce anlamsızlaşır. Diğer
    # testler get_reranker()'ı sahteyle değiştirdiği için yapıcıyı hiç görmüyor;
    # aktivasyonu donduran tek test budur.
    yakalanan = {}

    def sahte_cross_encoder(*args, **kwargs):
        yakalanan["args"] = args
        yakalanan["kwargs"] = kwargs
        return object()

    # Modül tekili önceki testlerden dolu kalmış olabilir; None'a çekilmezse
    # get_reranker() yapıcıyı hiç çağırmaz ve test yanlışlıkla yeşil kalır.
    monkeypatch.setattr(rag_service, "_reranker", None)
    monkeypatch.setattr(rag_service, "CrossEncoder", sahte_cross_encoder)

    rag_service.get_reranker()

    assert isinstance(yakalanan["kwargs"].get("activation_fn"), torch.nn.Sigmoid)
