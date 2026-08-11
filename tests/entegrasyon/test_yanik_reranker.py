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


# Triyaj ölçütü taşıyan metnin işaretleri. Başlığa ("Alan Kriterleri") tek başına
# BAKILAMAZ: örtüşmeli bölme başlığı kendi maddelerinden ayırıyor, yani saf kriter
# maddelerinden oluşan bir chunk başlıksız kalabiliyor ve başlığı taşıyan chunk
# ağırlıklı olarak hasta dili olabiliyor. Ek C bu etiketleme hatasını bir kez
# yapıp geri aldı; burada içerik işaretine bakılıyor.
# "TVYA" tek başına da yetmez — İlk Değerlendirme bölümünde hesaplama adımı olarak
# geçiyor; ölçüt olan hâli karşılaştırma operatörüyle gelir (TVYA >%20, <%5, %5-20).
KRITER_ISARETLERI = (
    "Alan Kriterleri",
    "Önerilen Tetkikler",
    "kritik bölge",
    "TVYA >",
    "TVYA <",
    "TVYA %",
)

# Yalnızca yanık protokolünün ölçütleri sayılır: başka bir protokolün kriter
# taşıyan chunk'ının ilk üçe girmesi, yanık hastasının triyaj edilebildiği
# anlamına gelmez.
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
    # sistem "Belirsiz" demez ama kriter görmeden karar verir. Gün 22'nin
    # incelemesinde tam bu kusur bulundu ve tek kanıtı elle yazılıp silinen bir
    # script'ti; bu satır onu kalıcı hale getiriyor.
    assert _kriter_tasiyan_yanik_belgesi_var_mi(sonuc), (
        "dönen yanık belgelerinin hiçbiri triyaj ölçütü taşımıyor; LLM ölçüt "
        "görmeden karar verecek"
    )


@pytest.mark.yavas
@pytest.mark.entegrasyon
def test_kor_yanik_sorgusu_esigi_geciyor_ama_kriter_almiyor(derleme_koleksiyonu):
    """Kör sorgunun BUGÜNKÜ davranışını dondurur — iyileşirse test kırılır.

    Bu sorgu proje sahibi tarafından yanik.txt'nin yeni metni GÖRÜLMEDEN yazıldı;
    kalibrasyon setindeki diğer iki yanık sorgusu protokol metniyle aynı kişi
    tarafından yazıldığı için gerçekten kör tek ölçüm budur (tasarım K5).

    Ölçüm sonucu: eşiği geçiyor (hasta "Belirsiz" almıyor) ama LLM'e yalnızca
    hasta-dili chunk'ı ulaşıyor; Kırmızı kriterleri 0.0011'de kalıyor. Sebep
    yapısal: reranker chunk'ın tamamını puanlıyor, yoğun kelime dağarcığı
    olmayan bir bloğa tek cümle eklemek seyreliyor (Ek C, Gün 22).

    İkinci iddia bilerek "kriter YOK" diyor: bu bir hedef değil, kayıt altına
    alınmış bir kusur. Yapısal düzeltme geldiğinde bu test kırılacak ve o kırılma
    "defekt kapandı" haberidir — testi silmek yerine iddiayı çevirin.
    """
    sorgu = "mangalda kolumu ateşe tuttum, kolum bembeyaz oldu hissetmiyorum"

    sonuc = retrieve_and_rerank(sorgu, derleme_koleksiyonu)

    assert sonuc, "kör yanık sorgusu eşiği geçemedi"
    assert "yanik.txt" in sonuc[0]
    assert not _kriter_tasiyan_yanik_belgesi_var_mi(sonuc), (
        "kör sorgu artık yanık ölçütü alıyor — Gün 22'nin adlandırılmış defekti "
        "kapanmış olabilir; Ek C'yi güncelleyin ve bu testi çevirin"
    )
