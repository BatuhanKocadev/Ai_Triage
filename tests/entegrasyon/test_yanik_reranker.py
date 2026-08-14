"""Yanık şikayetinin reranker eşiğini geçtiğini gerçek modellerle sınar."""

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


# Triyaj ölçütü taşıyan metnin işaretleri. Hepsi ÖLÇÜT metninden; başlık
# ("Alan Kriterleri") bilerek listede YOK.
KRITER_ISARETLERI = (
    "Önerilen Tetkikler",
    "kritik bölge",
    "TVYA >",
    "TVYA <",
    "TVYA %",
    "İnhalasyon yanığı bulguları",
)

# Yalnızca yanık protokolünün ölçütleri sayılır: başka bir protokolün kriter
# taşıyan chunk'ının ilk üçe girmesi, yanık hastasının triyaj edilebildiği
YANIK_KAYNAGI = "[Kaynak: yanik.txt]"


def _kriter_tasiyan_yanik_belgesi_var_mi(sonuc: list[str]) -> bool:
    """Dönen belgeler arasında yanık ÖLÇÜTÜ taşıyan bir chunk var mı."""
    return any(
        YANIK_KAYNAGI in belge and any(isaret in belge for isaret in KRITER_ISARETLERI)
        for belge in sonuc
    )


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

    # Eşiği geçmek yetmez: LLM'e triyaj ÖLÇÜTÜ de ulaşmalı. Bu iddia olmadan test,
    # yalnızca hasta-dili chunk'ının döndüğü kusurlu durumda da yeşil kalırdı —
    assert _kriter_tasiyan_yanik_belgesi_var_mi(sonuc), (
        "dönen yanık belgelerinin hiçbiri triyaj ölçütü taşımıyor; LLM ölçüt "
        "görmeden karar verecek"
    )


@pytest.mark.yavas
@pytest.mark.entegrasyon
def test_kor_yanik_sorgusu_esigi_geciyor_ama_kriter_almiyor(derleme_koleksiyonu):
    """Kör sorgunun BUGÜNKÜ davranışını dondurur — iyileşirse test kırılır."""
    sorgu = "mangalda kolumu ateşe tuttum, kolum bembeyaz oldu hissetmiyorum"

    sonuc = retrieve_and_rerank(sorgu, derleme_koleksiyonu)

    assert sonuc, "kör yanık sorgusu eşiği geçemedi"
    assert "yanik.txt" in sonuc[0]
    assert not _kriter_tasiyan_yanik_belgesi_var_mi(sonuc), (
        "kör sorgu artık yanık ölçütü alıyor — Gün 22'nin adlandırılmış defekti "
        "kapanmış olabilir; Ek C'yi güncelleyin ve bu testi çevirin"
    )
