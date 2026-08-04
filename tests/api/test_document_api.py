"""Doküman uçlarının testleri: listeleme, silme ve yeniden yükleme davranışı."""

import pytest

from app.api import document as document_modulu
from tests.yardimcilar.sahte_chroma import SahteKoleksiyon


@pytest.fixture
def sahte_koleksiyon(monkeypatch):
    """Doküman uçlarını bellek içi sahte koleksiyona bağlar.

    Yamalama adın arandığı ad alanına uygulanıyor (`app.api.document`), adı
    tanımlayan `chroma_service`'e değil — uç modülü adı kendi ad alanına almış.
    """
    koleksiyon = SahteKoleksiyon()
    monkeypatch.setattr(document_modulu, "get_collection", lambda: koleksiyon)
    return koleksiyon


def _chunk_ekle(koleksiyon, kaynak, adet, kategori="protokol", tarih="2026-08-04"):
    """Sahte koleksiyona bir dosyaya ait `adet` kadar chunk yazar."""
    koleksiyon.upsert(
        documents=[f"{kaynak} parça {i}" for i in range(adet)],
        metadatas=[
            {
                "source": kaynak,
                "upload_date": tarih,
                "category": kategori,
                "chunk_index": i,
            }
            for i in range(adet)
        ],
        ids=[f"{kaynak}_chunk_{i}" for i in range(adet)],
    )


@pytest.mark.entegrasyon
def test_liste_dokumanlari_kaynak_bazinda_gruplar(istemci, sahte_koleksiyon, yetkili_baslik):
    # Panelin ve yol haritasının "yüklenen doküman sayısı" metriği bu uçtan
    # okunuyor; gruplama bozulursa sayı sessizce yanlış çıkar.
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 8)
    _chunk_ekle(sahte_koleksiyon, "karin_agrisi.txt", 6)

    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 200
    kayitlar = {k["kaynak"]: k for k in yanit.json()}
    assert kayitlar["gogus_agrisi.txt"]["chunk_sayisi"] == 8
    assert kayitlar["karin_agrisi.txt"]["chunk_sayisi"] == 6
    assert kayitlar["gogus_agrisi.txt"]["kategori"] == "protokol"
    assert kayitlar["gogus_agrisi.txt"]["yukleme_tarihi"] == "2026-08-04"


@pytest.mark.entegrasyon
def test_liste_bos_koleksiyonda_bos_liste_doner(istemci, sahte_koleksiyon, yetkili_baslik):
    # "Hiç doküman yok" bir hata değil, geçerli bir durum (K3). Sıfır da bir ölçümdür.
    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 200
    assert yanit.json() == []


@pytest.mark.entegrasyon
def test_liste_kaynak_adina_gore_siralanir(istemci, sahte_koleksiyon, yetkili_baslik):
    # ChromaDB get() dönüş sırası garanti değil; ekleme sırası kasıtlı olarak
    # alfabetik değil ve uç yine de belirlenimci sıra vermeli (K4).
    _chunk_ekle(sahte_koleksiyon, "zehirlenme.txt", 2)
    _chunk_ekle(sahte_koleksiyon, "anafilaksi.txt", 2)
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 2)

    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    adlar = [k["kaynak"] for k in yanit.json()]
    assert adlar == ["anafilaksi.txt", "gogus_agrisi.txt", "zehirlenme.txt"]


@pytest.mark.entegrasyon
def test_user_rolu_listeye_403_alir(istemci, sahte_koleksiyon, yetkili_baslik):
    # Bağımlılığı izole sınamak, UCUN onu kullandığını kanıtlamaz — Gün 17+18'de
    # ölçülen desen. Bu test doğrudan uca gidiyor.
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 3)

    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="hasta_ayse", rol="user"),
    )

    assert yanit.status_code == 403
