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
    tetkik_ortusmesi,
    triyaj_dogru_mu,
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


# --- Boş dize: "yok" demenin tek yolu None, "" değil ---


@pytest.mark.parametrize("alan", ["id", "cinsiyet", "beklenen_bolum", "sikayet"])
@pytest.mark.parametrize("deger", ["", "   "])
def test_bos_zorunlu_metin_alani_hata_verir(tmp_path, alan, deger):
    """`beklenen_bolum: ""` sessizce geçerse bölüm doğruluğu kalıcı sıfır yazar."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(**{alan: deger}))

    with pytest.raises(SenaryoHatasi, match=alan):
        senaryolari_yukle(yol)


@pytest.mark.parametrize(
    "alan", ["beklenen_kaynak", "kronik_hastalik", "ses_dosyasi"]
)
@pytest.mark.parametrize("deger", ["", "   "])
def test_bos_istege_bagli_metin_alani_hata_verir(tmp_path, alan, deger):
    """`beklenen_kaynak: ""` ile `None` anlamca farklı; boş dize reddedilir."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(**{alan: deger}))

    with pytest.raises(SenaryoHatasi, match=alan):
        senaryolari_yukle(yol)


def test_istege_bagli_alanlar_none_ile_kabul_edilir(tmp_path):
    """"Yok" demenin meşru yolu None; boş dizeyi reddetmek bunu bozmamalı."""
    yol = _yaz(
        tmp_path,
        _senaryo_sozlugu(beklenen_kaynak=None, kronik_hastalik=None, ses_dosyasi=None),
    )

    senaryo = senaryolari_yukle(yol)[0]

    assert senaryo.beklenen_kaynak is None
    assert senaryo.kronik_hastalik is None
    assert senaryo.ses_dosyasi is None


def test_bosluklu_sikayet_uzunluk_kapisini_gecemez(tmp_path):
    """10 boşluk uzunluk sınırını geçer ama şikayet değildir."""
    yol = _yaz(tmp_path, _senaryo_sozlugu(sikayet=" " * 10))

    with pytest.raises(SenaryoHatasi, match="sikayet"):
        senaryolari_yukle(yol)


@pytest.mark.parametrize("deger", ["", "   "])
def test_bos_tetkik_adi_hata_verir(tmp_path, deger):
    """Boş bir tetkik adı Jaccard hesabına gerçek bir beklenti olarak girer.

    Skaler alanlarda kapatılan kusurun aynısı: `["EKG", ""]` sessizce yüklenirse
    beklenen küme iki elemanlı sayılır ve örtüşme oranı hiç ulaşılamayacak bir
    tavana çarpar.
    """
    yol = _yaz(tmp_path, _senaryo_sozlugu(beklenen_tetkikler=["EKG", deger]))

    with pytest.raises(SenaryoHatasi, match="beklenen_tetkikler"):
        senaryolari_yukle(yol)


def test_ic_bosluklu_tetkik_adi_kabul_edilir(tmp_path):
    """Kapı yalnızca boş adı elemeli; ad içindeki boşluk tamamen meşrudur."""
    adlar = ["Tam Kan Sayımı", "EKG"]
    yol = _yaz(tmp_path, _senaryo_sozlugu(beklenen_tetkikler=adlar))

    assert senaryolari_yukle(yol)[0].beklenen_tetkikler == adlar


def test_utf8_olmayan_dosya_senaryo_hatasi_verir(tmp_path):
    """Windows'ta cp1254 kaydedilmiş dosya ham UnicodeDecodeError vermemeli.

    Senaryo dosyasını Türkçe konuşan biri elle yazacak; cp1254 kaydedilmiş bir
    dosyadaki `ğ`/`ı`/`ş` geçerli UTF-8 değildir. Görev 7'nin sürücüsü bütün
    yükleme hatalarının `SenaryoHatasi` olduğunu varsayıyor.
    """
    yol = tmp_path / "senaryolar.json"
    metin = json.dumps([_senaryo_sozlugu()], ensure_ascii=False)
    yol.write_bytes(metin.encode("cp1254"))

    with pytest.raises(SenaryoHatasi, match="UTF-8"):
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


# --- Karşılaştırma ilkelleri: triyaj kodu ve tetkik örtüşmesi ---


def test_dogruluk_hesaplanir():
    """Dört karşılaştırmadan üçü tutuyorsa doğruluk %75'tir."""
    ciftler = [
        ("Kırmızı", "Kırmızı"),
        ("Sarı", "Sarı"),
        ("Yeşil", "Yeşil"),
        ("Kırmızı", "Yeşil"),
    ]
    dogru = sum(1 for beklenen, cikan in ciftler if triyaj_dogru_mu(beklenen, cikan))

    assert dogru == 3
    assert dogru / len(ciftler) == 0.75


def test_triyaj_karsilastirmasi_yazim_farkina_dayanikli():
    """Yerel model kodu bazen ASCII yazıyor; normalizasyon uçta var ama
    ölçüm aracı da kendi başına dayanıklı olmalı."""
    assert triyaj_dogru_mu("Kırmızı", "kirmizi") is True
    assert triyaj_dogru_mu("Kırmızı", "Sarı") is False


def test_cevapsiz_senaryo_dogru_sayilmaz():
    """Cevapsızlık ile "Belirsiz" ayrı şeyler; ikisi de kod tutmadan doğru sayılmaz."""
    assert triyaj_dogru_mu("Kırmızı", None) is False
    assert triyaj_dogru_mu("Kırmızı", "Belirsiz") is False
    # Kapsam dışı senaryoda cevap vermemek doğrudur.
    assert triyaj_dogru_mu("Belirsiz", "Belirsiz") is True


def test_tetkik_ortusme_orani_hesaplanir():
    """Jaccard: kesişim / birleşim."""
    # {EKG, Troponin} ∩ {EKG, Troponin, D-Dimer} = 2, birleşim = 3
    assert tetkik_ortusmesi(
        ["EKG", "Troponin"], ["EKG", "Troponin", "D-Dimer"]
    ) == pytest.approx(2 / 3)
    assert tetkik_ortusmesi(["EKG"], ["EKG"]) == 1.0
    assert tetkik_ortusmesi(["EKG"], ["Troponin"]) == 0.0
    # İki taraf da boşsa örtüşme tamdır; biri boşsa hiç yoktur.
    assert tetkik_ortusmesi([], []) == 1.0
    assert tetkik_ortusmesi(["EKG"], []) == 0.0


def test_tetkik_ortusmesi_yazim_farkina_dayanikli():
    """Tetkik adında ASCII katlaması doğru: ölçülen şey triyaj kalitesi, yazım değil."""
    assert tetkik_ortusmesi(
        ["Tam Kan Sayımı"], ["tam kan sayimi"]
    ) == 1.0


def test_cikan_taraftaki_bos_tetkik_adi_yok_sayilir():
    """Model çıktısı güvenilmeyen girdi: boş bir ad birleşimi şişirip örtüşmeyi
    haksız yere düşürmemeli. Yazarın elindeki tarafta ise aynı şey hatadır
    (bkz. test_bos_tetkik_adi_hata_verir) — asimetri bilinçli."""
    assert tetkik_ortusmesi(["EKG"], ["EKG", "", "   "]) == 1.0
