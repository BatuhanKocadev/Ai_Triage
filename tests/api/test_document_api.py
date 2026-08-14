"""Doküman uçlarının testleri: listeleme, silme ve yeniden yükleme davranışı."""

import pytest

from app.api import document as document_modulu
from tests.yardimcilar.sahte_chroma import SahteKoleksiyon


@pytest.fixture
def sahte_koleksiyon(monkeypatch):
    """Doküman uçlarını bellek içi sahte koleksiyona bağlar."""
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


@pytest.mark.entegrasyon
def test_silme_dosyanin_tum_chunklarini_siler(istemci, sahte_koleksiyon, yetkili_baslik):
    # Yanlış yüklenen bir dosyayı kaldırmanın tek yolu bu uç.
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 8)
    _chunk_ekle(sahte_koleksiyon, "karin_agrisi.txt", 6)

    yanit = istemci.delete(
        "/document",
        params={"kaynak": "gogus_agrisi.txt"},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 200
    assert yanit.json()["silinen_chunk"] == 8
    # Diğer dosyaya dokunulmadığı da kanıtlanıyor.
    assert sahte_koleksiyon.sayac() == 6


@pytest.mark.entegrasyon
def test_olmayan_dosya_silinince_404_doner(istemci, sahte_koleksiyon, yetkili_baslik):
    # Yanlış dosya adı yazan yönetici bunu bilmeli; sessiz başarı yanıltır (K6).
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 3)

    yanit = istemci.delete(
        "/document",
        params={"kaynak": "olmayan.txt"},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 404
    assert sahte_koleksiyon.sayac() == 3


@pytest.mark.entegrasyon
def test_user_rolu_silmeye_403_alir(istemci, sahte_koleksiyon, yetkili_baslik):
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 3)

    yanit = istemci.delete(
        "/document",
        params={"kaynak": "gogus_agrisi.txt"},
        headers=yetkili_baslik(kullanici_adi="hasta_ayse", rol="user"),
    )

    assert yanit.status_code == 403
    # Yetki reddedilirken hiçbir şey silinmemiş olmalı: kapı gövdeden önce durmalı.
    assert sahte_koleksiyon.sayac() == 3


@pytest.mark.entegrasyon
def test_yeniden_yukleme_eski_chunklari_birakmaz(istemci, sahte_koleksiyon, yetkili_baslik):
    # upsert yalnızca kendisine verilen id'lere dokunur. Daha kısa bir sürüm
    # yüklendiğinde eski sürümün fazla chunk'ları koleksiyonda kalırsa sistem
    baslik = yetkili_baslik(kullanici_adi="yonetici", rol="admin")
    uzun_metin = ("Gogus agrisi protokolu. " * 400).encode("utf-8")
    kisa_metin = "Gogus agrisi protokolu kisa surum.".encode("utf-8")

    ilk = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("gogus_agrisi.txt", uzun_metin, "text/plain")},
        headers=baslik,
    )
    assert ilk.status_code == 201
    # Test anlamlı olsun diye: ilk yükleme gerçekten çok parçaya bölünmeli.
    assert ilk.json()["total_chunks"] > 1

    ikinci = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("gogus_agrisi.txt", kisa_metin, "text/plain")},
        headers=baslik,
    )
    assert ikinci.status_code == 201
    ikinci_chunk_sayisi = ikinci.json()["total_chunks"]

    # Koleksiyonda yalnızca ikinci sürümün chunk'ları kalmalı.
    assert sahte_koleksiyon.sayac() == ikinci_chunk_sayisi


@pytest.mark.entegrasyon
def test_yeniden_yukleme_baska_dosyanin_chunklarina_dokunmaz(istemci, sahte_koleksiyon, yetkili_baslik):
    # Temizlik filtresinin KAPSAMINI donduruyor. Filtre "source" yerine
    # "category" olsaydı diğer testler yeşil kalırdı ama üretimde her yükleme
    baslik = yetkili_baslik(kullanici_adi="yonetici", rol="admin")
    uzun_metin = ("Protokol metni ornegi. " * 400).encode("utf-8")
    kisa_metin = "Protokol kisa surum.".encode("utf-8")

    istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("dosya_a.txt", uzun_metin, "text/plain")},
        headers=baslik,
    )
    b_yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("dosya_b.txt", uzun_metin, "text/plain")},
        headers=baslik,
    )
    assert b_yanit.status_code == 201
    b_chunk_sayisi = b_yanit.json()["total_chunks"]

    # A dosyası aynı kategoriyle, daha kısa bir sürümle yeniden yükleniyor.
    a_yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("dosya_a.txt", kisa_metin, "text/plain")},
        headers=baslik,
    )
    assert a_yanit.status_code == 201
    a_chunk_sayisi = a_yanit.json()["total_chunks"]

    # B dosyası hiç dokunulmadan durmalı.
    kalan_b = sahte_koleksiyon.get(where={"source": "dosya_b.txt"})
    assert len(kalan_b["ids"]) == b_chunk_sayisi
    assert sahte_koleksiyon.sayac() == a_chunk_sayisi + b_chunk_sayisi


@pytest.mark.entegrasyon
def test_buyuk_kucuk_harf_dosya_adlari_ayri_chunk_id(istemci, sahte_koleksiyon, yetkili_baslik):
    # safe_filename .lower() yaparsa Yanik.txt ile yanik.txt aynı id'ye düşer
    # ve birbirinin üzerine yazar; kaynak metadata orijinal adı korusa bile.
    baslik = yetkili_baslik(kullanici_adi="yonetici", rol="admin")
    metin = "Yanik protokolu ornek metin.".encode("utf-8")

    a = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("Yanik.txt", metin, "text/plain")},
        headers=baslik,
    )
    b = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("yanik.txt", metin, "text/plain")},
        headers=baslik,
    )
    assert a.status_code == 201
    assert b.status_code == 201
    assert sahte_koleksiyon.sayac() == a.json()["total_chunks"] + b.json()["total_chunks"]
    assert sahte_koleksiyon.get(where={"source": "Yanik.txt"})["ids"]
    assert sahte_koleksiyon.get(where={"source": "yanik.txt"})["ids"]
