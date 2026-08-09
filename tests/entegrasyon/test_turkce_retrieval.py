"""Türkçe sorgunun doğru protokolü getirdiğini gerçek gömme modeliyle sınar.

Bu testin var oluş sebebi somut: ChromaDB'nin varsayılan İngilizce gömme modeli
(`all-MiniLM-L6-v2`) kullanılırken "kaynar su döküldü" sorgusu yanık protokolünü
ilk BEŞE bile sokamıyordu, "yüzü düştü, kolunu kaldıramıyor" sorgusu da inme
protokolünü getiremiyordu — ama hiçbir test bunu görmüyordu, çünkü gerçek modelle
Türkçe retrieval'ı sınayan test yoktu.

Test üretim koşullarını taklit eder: derlemenin TAMAMI, `/document/upload` ile
aynı bölücü ayarlarıyla (chunk_size=1000, overlap=200) parçalanıp gömülür. Bütün
dosyaları tek parça gömmek testi yapay olarak kolaylaştırırdı — 48 chunk arasından
doğruyu bulmak, 15 bütün belge arasından bulmaktan zordur ve üretimde olan budur.

`yavas` + `entegrasyon` işaretli: gerçek bge-m3 modelini (~2.2 GB) yükler ve
ayakta bir ChromaDB ister.
"""

import uuid
from pathlib import Path

import chromadb
import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.config import settings
from app.services.chroma_service import _gomme_fonksiyonu

DERLEME = Path(__file__).resolve().parent.parent.parent / "ornek_dokumanlar" / "protokoller"

# app/api/document.py'deki upload ucuyla birebir aynı ayarlar; test üretimden
# farklı parçalarsa ölçtüğü şey üretimin davranışı olmaz.
BOLUCU = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""],
)


@pytest.fixture(scope="module")
def derleme_koleksiyonu():
    """Derlemenin tamamını chunk'layıp geçici bir koleksiyona gömer.

    Modül kapsamlı: gömme işlemi pahalı, her test için tekrarlanmasın. Koleksiyon
    geçici ve teste özel — canlı `triage_documents` her hasta sorgusunun tarandığı
    yer, testler oraya asla dokunmaz.
    """
    istemci = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    ad = f"test_turkce_retrieval_{uuid.uuid4().hex[:8]}"
    koleksiyon = istemci.create_collection(name=ad, embedding_function=_gomme_fonksiyonu())

    belgeler, ustveriler, kimlikler = [], [], []
    for yol in sorted(DERLEME.glob("*.txt")):
        if yol.name.startswith("_"):
            continue  # şablon dosyası derlemeye girmez
        for sira, parca in enumerate(BOLUCU.split_text(yol.read_text(encoding="utf-8"))):
            belgeler.append(parca)
            ustveriler.append({"source": yol.name, "chunk_index": sira})
            kimlikler.append(f"{yol.name}_chunk_{sira}")

    koleksiyon.add(documents=belgeler, metadatas=ustveriler, ids=kimlikler)
    try:
        yield koleksiyon
    finally:
        istemci.delete_collection(ad)


@pytest.mark.yavas
@pytest.mark.entegrasyon  # gerçek ChromaDB gerektiriyor; depodaki diğer Chroma/Postgres testleriyle aynı
@pytest.mark.parametrize(
    "sorgu, beklenen_kaynak",
    [
        # İkisi de İngilizce gömme modeliyle KIRIK olduğu ölçülerek kanıtlanmış
        # sorgular; hasta ağzından yazılmış, protokol cümlesi kopyalanmamıştır.
        ("Kaynar su elimin üstüne döküldü, hemen su topladı.", "yanik.txt"),
        ("Annemin yüzünün bir tarafı düştü, kolunu kaldıramıyor ve konuşması bozuldu.", "inme.txt"),
    ],
)
def test_turkce_sorgu_dogru_protokolu_getirir(derleme_koleksiyonu, sorgu, beklenen_kaynak):
    sonuc = derleme_koleksiyonu.query(query_texts=[sorgu], n_results=1)

    assert sonuc["metadatas"][0][0]["source"] == beklenen_kaynak
