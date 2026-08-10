"""Yanık şikayetinin reranker eşiğini geçtiğini gerçek modellerle sınar.

Mevcut `test_turkce_retrieval.py` BİRİNCİ AŞAMAYI (gömme) ölçüyor ve bugün
geçiyor — doğru protokol getiriliyor. Kırık olan ikinci aşama: reranker
`yanik.txt`'ye 0.0005 veriyor, eşik ise 0.005. Sonuç, yanık hastasına
"Belirsiz" denmesi.

Bağlayıcılık üretim yolunun kendisinden geliyor: `retrieve_and_rerank` eşiğin
altında kalınca BOŞ LİSTE döndürüyor. Yani skor yetersizse test doğal olarak
kırmızı olur, ayrıca eşik karşılaştırması yazmaya gerek yok.

`yavas` + `entegrasyon`: gerçek bge-m3 ve bge-reranker-v2-m3 modellerini yükler,
ayakta bir ChromaDB ister.
"""

import uuid
from pathlib import Path

import chromadb
import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.config import settings
from app.services.chroma_service import _gomme_fonksiyonu
from app.services.rag_service import retrieve_and_rerank

DERLEME = Path(__file__).resolve().parent.parent.parent / "ornek_dokumanlar" / "protokoller"

# app/api/document.py'deki upload ucuyla birebir aynı ayarlar.
BOLUCU = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""],
)


@pytest.fixture(scope="module")
def derleme_koleksiyonu():
    """Derlemenin tamamını üretimle aynı biçimde chunk'layıp geçici koleksiyona gömer."""
    istemci = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    ad = f"test_yanik_reranker_{uuid.uuid4().hex[:8]}"
    koleksiyon = istemci.create_collection(name=ad, embedding_function=_gomme_fonksiyonu())

    belgeler, ustveriler, kimlikler = [], [], []
    for yol in sorted(DERLEME.glob("*.txt")):
        if yol.name.startswith("_"):
            continue  # şablon dosyası derlemeye girmez
        # HAM BAYT okunup decode ediliyor: /document/upload da böyle yapıyor.
        # read_text() Windows'ta CRLF'i LF'e çevirir ve test üretimden FARKLI
        # metin gömer; chunk sınırları kayar (tasarım K10).
        metin = yol.read_bytes().decode("utf-8")
        for sira, parca in enumerate(BOLUCU.split_text(metin)):
            belgeler.append(parca)
            ustveriler.append({"source": yol.name, "chunk_index": sira})
            kimlikler.append(f"{yol.name}_chunk_{sira}")

    koleksiyon.add(documents=belgeler, metadatas=ustveriler, ids=kimlikler)
    try:
        yield koleksiyon
    finally:
        istemci.delete_collection(ad)


@pytest.mark.yavas
@pytest.mark.entegrasyon
@pytest.mark.parametrize(
    "sorgu",
    [
        # Birinci sorgu: kalibrasyon setindekiyle aynı klinik tablo.
        "Çaydanlığı devirdim, kolum fena halde haşlandı ve derim kabardı.",
        # Tutulan sorgu: belge bunun için ayarlanmadı (tasarım K5).
        "Ütü elimin üstüne düştü, deri soyuldu ve çok acıyor.",
    ],
)
def test_yanik_sikayeti_esigi_geciyor(derleme_koleksiyonu, sorgu):
    sonuc = retrieve_and_rerank(sorgu, derleme_koleksiyonu)

    # Boş liste = eşik altında kalındı, yani hasta "Belirsiz" alıyor.
    assert sonuc, "yanık şikayeti eşiği geçemedi; sistem 'Belirsiz' diyecek"
    assert "yanik.txt" in sonuc[0]
