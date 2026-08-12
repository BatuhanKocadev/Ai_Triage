"""Gün 23 ölçüm aracının birim testleri.

Bu testler saf fonksiyonları sınar: Ollama, backend, ChromaDB hiçbirinde
çağrılmaz. Ölçümün kendisi `degerlendirme/calistir.py` ile ayrıca koşulur.
"""
import json

import pytest

from degerlendirme.olcum import (
    GECERLI_KODLAR,
    Senaryo,
    SenaryoHatasi,
    senaryolari_yukle,
)


def _senaryo_sozlugu(**degisiklikler):
    """Testlerde kullanılan geçerli bir senaryo sözlüğü üretir."""
    temel = {
        "id": "t01",
        "sikayet": "göğsümde baskı var, sol kolum uyuşuyor",
        "yas": 58,
        "cinsiyet": "Erkek",
        "beklenen_triage_code": "Kırmızı",
        "beklenen_bolum": "Acil Servis",
        "beklenen_tetkikler": ["EKG", "Troponin"],
        "beklenen_kaynak": "gogus_agrisi.txt",
    }
    temel.update(degisiklikler)
    return temel


def test_senaryo_dosyasi_okunur_ve_dogrulanir(tmp_path):
    yol = tmp_path / "senaryolar.json"
    yol.write_text(json.dumps([_senaryo_sozlugu()]), encoding="utf-8")

    senaryolar = senaryolari_yukle(yol)

    assert len(senaryolar) == 1
    assert isinstance(senaryolar[0], Senaryo)
    assert senaryolar[0].id == "t01"
    assert senaryolar[0].beklenen_tetkikler == ["EKG", "Troponin"]


def test_eksik_alanli_senaryo_hata_verir(tmp_path):
    bozuk = _senaryo_sozlugu()
    del bozuk["beklenen_triage_code"]
    yol = tmp_path / "senaryolar.json"
    yol.write_text(json.dumps([bozuk]), encoding="utf-8")

    with pytest.raises(SenaryoHatasi, match="beklenen_triage_code"):
        senaryolari_yukle(yol)


def test_gecersiz_triyaj_kodu_hata_verir(tmp_path):
    bozuk = _senaryo_sozlugu(beklenen_triage_code="Turuncu")
    yol = tmp_path / "senaryolar.json"
    yol.write_text(json.dumps([bozuk]), encoding="utf-8")

    with pytest.raises(SenaryoHatasi, match="Turuncu"):
        senaryolari_yukle(yol)


def test_tekrarlanan_id_hata_verir(tmp_path):
    yol = tmp_path / "senaryolar.json"
    yol.write_text(
        json.dumps([_senaryo_sozlugu(), _senaryo_sozlugu()]), encoding="utf-8"
    )

    with pytest.raises(SenaryoHatasi, match="t01"):
        senaryolari_yukle(yol)


def test_belirsiz_gecerli_bir_beklenti(tmp_path):
    """Kapsam dışı senaryolarda sistemin cevap vermemesi doğru davranıştır."""
    kapsam_disi = _senaryo_sozlugu(
        id="t02", beklenen_triage_code="Belirsiz", beklenen_kaynak=None
    )
    yol = tmp_path / "senaryolar.json"
    yol.write_text(json.dumps([kapsam_disi]), encoding="utf-8")

    senaryolar = senaryolari_yukle(yol)

    assert senaryolar[0].beklenen_triage_code == "Belirsiz"
    assert senaryolar[0].beklenen_kaynak is None
    assert "Belirsiz" in GECERLI_KODLAR


def _yaz(tmp_path, *kayitlar):
    """Verilen senaryo sözlüklerini geçici bir JSON dosyasına yazıp yolu döndürür."""
    yol = tmp_path / "senaryolar.json"
    yol.write_text(json.dumps(list(kayitlar)), encoding="utf-8")
    return yol


# --- Tip doğrulaması: varlık kontrolü tek başına şemayı doğrulamaz ---


def test_tetkikler_metin_verilirse_hata_verir(tmp_path):
    """`"EKG"` sessizce `['E','K','G']` olursa Jaccard sayısı anlamsız çıkar."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(beklenen_tetkikler="EKG"))

    with pytest.raises(SenaryoHatasi, match="beklenen_tetkikler"):
        senaryolari_yukle(yol)


def test_tetkik_elemanlari_metin_olmali(tmp_path):
    yol = _yaz(tmp_path, _senaryo_sozlugu(beklenen_tetkikler=["EKG", 42]))

    with pytest.raises(SenaryoHatasi, match="beklenen_tetkikler"):
        senaryolari_yukle(yol)


def test_bos_tetkik_listesi_kabul_edilir(tmp_path):
    """Hiç tetkik beklenmeyen senaryo meşrudur; boş liste hata değildir."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(beklenen_tetkikler=[]))

    assert senaryolari_yukle(yol)[0].beklenen_tetkikler == []


@pytest.mark.parametrize("yas", [0, 120])
def test_sinir_yaslari_kabul_edilir(tmp_path, yas):
    """app/api/ai.py:40 ge=0 le=120 diyor; uçlar geçerli."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(yas=yas))

    assert senaryolari_yukle(yol)[0].yas == yas


@pytest.mark.parametrize("yas", [-1, 121])
def test_aralik_disi_yas_hata_verir(tmp_path, yas):
    """Aralık dışı yaş koşumda 422 alır; senaryo boşa gider, erken patlasın."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(yas=yas))

    with pytest.raises(SenaryoHatasi, match="yas"):
        senaryolari_yukle(yol)


@pytest.mark.parametrize("yas", ["58", 58.5, None, True])
def test_int_olmayan_yas_hata_verir(tmp_path, yas):
    """`True` bir int alt sınıfıdır ve 1'e eşittir; yaş olarak kabul edilmemeli."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(yas=yas))

    with pytest.raises(SenaryoHatasi, match="yas"):
        senaryolari_yukle(yol)


@pytest.mark.parametrize("uzunluk", [10, 500])
def test_sinir_uzunluklu_sikayet_kabul_edilir(tmp_path, uzunluk):
    """app/api/ai.py:42 min_length=10 max_length=500 diyor; uçlar geçerli."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(sikayet="a" * uzunluk))

    assert len(senaryolari_yukle(yol)[0].sikayet) == uzunluk


@pytest.mark.parametrize("uzunluk", [9, 501])
def test_aralik_disi_sikayet_uzunlugu_hata_verir(tmp_path, uzunluk):
    yol = _yaz(tmp_path, _senaryo_sozlugu(sikayet="a" * uzunluk))

    with pytest.raises(SenaryoHatasi, match="sikayet"):
        senaryolari_yukle(yol)


def test_metin_olmayan_sikayet_hata_verir(tmp_path):
    yol = _yaz(tmp_path, _senaryo_sozlugu(sikayet=12345))

    with pytest.raises(SenaryoHatasi, match="sikayet"):
        senaryolari_yukle(yol)


@pytest.mark.parametrize("alan", ["id", "cinsiyet", "beklenen_bolum"])
def test_zorunlu_metin_alanlari_str_olmali(tmp_path, alan):
    yol = _yaz(tmp_path, _senaryo_sozlugu(**{alan: 7}))

    with pytest.raises(SenaryoHatasi, match=alan):
        senaryolari_yukle(yol)


@pytest.mark.parametrize("alan", ["beklenen_kaynak", "kronik_hastalik", "ses_dosyasi"])
def test_istege_bagli_metin_alanlari_str_ya_da_none_olmali(tmp_path, alan):
    yol = _yaz(tmp_path, _senaryo_sozlugu(**{alan: 7}))

    with pytest.raises(SenaryoHatasi, match=alan):
        senaryolari_yukle(yol)


@pytest.mark.parametrize("cinsiyet", ["Erkek", "Kadın", "Diğer"])
def test_gecerli_cinsiyetler_kabul_edilir(tmp_path, cinsiyet):
    """app/api/ai.py:30-33 GenderEnum tam olarak bu üç dizeyi kabul ediyor."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(cinsiyet=cinsiyet))

    assert senaryolari_yukle(yol)[0].cinsiyet == cinsiyet


@pytest.mark.parametrize("cinsiyet", ["erkek", "Bay"])
def test_gecersiz_cinsiyet_hata_verir(tmp_path, cinsiyet):
    """Küçük harf de dahil; uca giden değer birebir eşleşmezse koşumda 422 gelir."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(cinsiyet=cinsiyet))

    with pytest.raises(SenaryoHatasi, match="cinsiyet"):
        senaryolari_yukle(yol)


def test_gecersiz_cinsiyet_mesaji_kabul_edilen_degerleri_yazar(tmp_path):
    """Senaryoyu yazan kişi hatadan ne yazması gerektiğini öğrenebilmeli."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(cinsiyet="Bay"))

    with pytest.raises(SenaryoHatasi) as hata:
        senaryolari_yukle(yol)

    mesaj = str(hata.value)
    for gecerli in ("Erkek", "Kadın", "Diğer"):
        assert gecerli in mesaj


def test_cinsiyet_sessizce_normalize_edilmez(tmp_path):
    """Yükleyici uçtan farklı bir sözleşme dayatmamalı; düzeltmek yerine reddediyor."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(cinsiyet="ERKEK"))

    with pytest.raises(SenaryoHatasi, match="cinsiyet"):
        senaryolari_yukle(yol)


def test_vitals_sozluk_olmali(tmp_path):
    yol = _yaz(tmp_path, _senaryo_sozlugu(vitals=[37.5, 90]))

    with pytest.raises(SenaryoHatasi, match="vitals"):
        senaryolari_yukle(yol)


def test_tum_istege_bagli_alanlar_dolu_senaryo_yuklenir(tmp_path):
    """Doğrulama fazla sıkı olmamalı: geçerli tam kayıt sorunsuz geçmeli."""
    tam = _senaryo_sozlugu(
        kronik_hastalik="hipertansiyon",
        vitals={"fever": 38.2, "pulse": 104},
        ses_dosyasi="t01.wav",
    )
    yol = _yaz(tmp_path, tam)

    senaryo = senaryolari_yukle(yol)[0]

    assert senaryo.vitals == {"fever": 38.2, "pulse": 104}
    assert senaryo.kronik_hastalik == "hipertansiyon"
    assert senaryo.ses_dosyasi == "t01.wav"
