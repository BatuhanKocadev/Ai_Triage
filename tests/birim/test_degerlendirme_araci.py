"""Gün 23 ölçüm aracının birim testleri.

Bu testler saf fonksiyonları sınar: Ollama, backend, ChromaDB hiçbirinde
çağrılmaz. Ölçümün kendisi `degerlendirme/calistir.py` ile ayrıca koşulur.
"""
import json

import pytest

from degerlendirme.olcum import (
    GECERLI_KODLAR,
    Ozet,
    Senaryo,
    SenaryoHatasi,
    Sonuc,
    bolum_dogru_mu,
    kaynak_adlarini_ayikla,
    kok_neden,
    ozet,
    sansli_dogru_mu,
    senaryolari_yukle,
    tetkik_ortusmesi,
    triyaj_dogru_mu,
    wer,
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


def test_bolum_karsilastirmasi_yazim_farkina_dayanikli():
    """Bölüm de triyaj kodu gibi karşılaştırılır: katlanan yazım, güvenli None.

    Karşılaştırma `kok_neden` içinde satır içi durursa Görev 5 onu kopyalamak
    zorunda kalır; iki kopya ayrışınca C kutusu ile özet tablosundaki bölüm
    oranı sessizce birbirini tutmaz.
    """
    assert bolum_dogru_mu("Acil Servis", "acil servis") is True
    assert bolum_dogru_mu("Kardiyoloji", "kardıyolojı") is True
    assert bolum_dogru_mu("Acil Servis", "Dahiliye") is False
    # Cevapsızlık bölüm doğruluğu sayılmaz.
    assert bolum_dogru_mu("Acil Servis", None) is False
    assert bolum_dogru_mu("Acil Servis", "") is False


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


# --- Kök neden tasnifi: A (retrieval) / B (muhakeme) / C (biçim) ---


def _senaryo(**degisiklikler) -> Senaryo:
    """Testlerde kullanılan geçerli bir Senaryo nesnesi üretir."""
    varsayilan = {
        "id": "t01",
        "sikayet": "göğsümde baskı var",
        "yas": 58,
        "cinsiyet": "Erkek",
        "beklenen_triage_code": "Kırmızı",
        "beklenen_bolum": "Acil Servis",
        "beklenen_tetkikler": ["EKG", "Troponin"],
        "beklenen_kaynak": "gogus_agrisi.txt",
    }
    varsayilan.update(degisiklikler)
    return Senaryo(**varsayilan)


def test_kok_neden_retrieval_ve_muhakeme_ayrilir():
    """Dört ana hâl: protokol gelmedi (A), geldi ama muhakeme tuttu (B),
    kod doğru ama eksik (C), her şey doğru (None)."""
    senaryo = _senaryo()

    # A: doğru protokol hiç gelmedi
    a = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Yeşil",
        cikan_bolum="Dahiliye",
        cikan_tetkikler=[],
        sources=["bas_agrisi.txt"],
    )
    assert kok_neden(senaryo, a) == "A"

    # B: doğru protokol geldi ama model yanlış kod verdi
    b = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Yeşil",
        cikan_bolum="Acil Servis",
        cikan_tetkikler=["EKG", "Troponin"],
        sources=["gogus_agrisi.txt"],
    )
    assert kok_neden(senaryo, b) == "B"

    # C: kod doğru, tetkikler eksik
    c = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Kırmızı",
        cikan_bolum="Acil Servis",
        cikan_tetkikler=["EKG"],
        sources=["gogus_agrisi.txt"],
    )
    assert kok_neden(senaryo, c) == "C"

    # Tam doğru
    tam = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Kırmızı",
        cikan_bolum="Acil Servis",
        cikan_tetkikler=["EKG", "Troponin"],
        sources=["gogus_agrisi.txt"],
    )
    assert kok_neden(senaryo, tam) is None


def test_esik_alti_yanit_retrieval_hatasi_sayilir():
    """Eşik altında kalmak, retrieval'ın başarısız olmasının başka adıdır (K8).

    İkinci vaka kuralı asıl sabitleyen: `beklenen_kaynak` yazılmamış kapsam içi
    bir senaryo "Belirsiz" alırsa, `"A"`'yı üretebilecek tek kapı Belirsiz
    kapısıdır. Yalnızca birinci vaka olsaydı kapı silinince kontrol kaynak
    kontrolüne düşer, `"gogus_agrisi.txt" not in []` yine `"A"` verir ve kural
    hiç kırmızıya dönmeden kaybolurdu.
    """
    senaryo = _senaryo()
    esik_alti = Sonuc(senaryo_id="t01", cikan_triage_code="Belirsiz", sources=[])

    assert kok_neden(senaryo, esik_alti) == "A"

    kaynaksiz = _senaryo(beklenen_kaynak=None)

    assert kok_neden(kaynaksiz, esik_alti) == "A"


def test_altyapi_hatasi_model_hatasi_sayilmaz():
    """500/timeout/429 muhakeme kutusunu şişirirse Gün 24 yanlış hedefe koşar."""
    senaryo = _senaryo()
    hatali = Sonuc(senaryo_id="t01", hata="timeout")

    assert kok_neden(senaryo, hatali) == "HATA"


def test_altyapi_hatasi_muhakeme_kutusunu_sisirmez():
    """Protokol gelmişken düşen bir istek B'ye yazılırsa muhakeme kutusu şişer.

    Üstteki test `hata` kapısını yalnızca A'ya karşı sınıyor (boş `sources`).
    Asıl tehlike bu: kaynak gelmiş, kod yanlış görünüyor ve istek 500 almış.
    Kapı düşerse bu sonuç "B" olur ve Gün 24 muhakemeyi düzeltmeye koşar.
    """
    senaryo = _senaryo()
    dusen = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Yeşil",
        cikan_bolum="Acil Servis",
        sources=["gogus_agrisi.txt"],
        hata="500 Internal Server Error",
    )

    assert kok_neden(senaryo, dusen) == "HATA"


def test_kapsam_disi_senaryoda_cevap_vermek_retrieval_hatasidir():
    """Beklenti 'Belirsiz' iken sistem kod ürettiyse eşik fazla geçirgen."""
    senaryo = _senaryo(
        id="t02", beklenen_triage_code="Belirsiz", beklenen_kaynak=None
    )
    cevap_verdi = Sonuc(
        senaryo_id="t02",
        cikan_triage_code="Sarı",
        cikan_bolum="Dahiliye",
        sources=["karin_agrisi.txt"],
    )

    assert kok_neden(senaryo, cevap_verdi) == "A"


def test_kapsam_disi_senaryo_dogru_reddedilirse_eksik_sayilmaz():
    """Cevap vermeyi reddetmiş sistemde derecelendirilecek bölüm ya da tetkik yoktur.

    Uç eşik altında `department="Triyaj Bankosu"`, `onerilen_tetkikler=[]`
    döndürüyor (`app/api/ai.py:152-160`). C kapıları koşsaydı **doğru** reddedilen
    her kapsam dışı senaryo "doğru ama eksik" sayılır, C kutusu sahte biçimde
    şişerdi. Senaryo yazarına `beklenen_bolum="Triyaj Bankosu"` yazdırmak da çözüm
    değildi: senaryo dosyasını bir uygulama detayına bağlardı.

    Bölüm tutsa da tutmasa da sonuç aynı olmalı — bu alanlar artık puanlanmıyor.
    """
    reddedildi = Sonuc(
        senaryo_id="t02",
        cikan_triage_code="Belirsiz",
        cikan_bolum="Triyaj Bankosu",
        cikan_tetkikler=[],
        sources=[],
    )

    bolum_tutmuyor = _senaryo(
        id="t02",
        beklenen_triage_code="Belirsiz",
        beklenen_bolum="Acil Servis",
        beklenen_tetkikler=["EKG"],
        beklenen_kaynak=None,
    )
    assert kok_neden(bolum_tutmuyor, reddedildi) is None

    bolum_tutuyor = _senaryo(
        id="t02",
        beklenen_triage_code="Belirsiz",
        beklenen_bolum="Triyaj Bankosu",
        beklenen_tetkikler=[],
        beklenen_kaynak=None,
    )
    assert kok_neden(bolum_tutuyor, reddedildi) is None


def test_sansli_dogru_isaretlenir():
    """Doğru cevap ama beklenen protokol hiç gelmemiş — Gün 24'te bozulabilir."""
    senaryo = _senaryo()
    sansli = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Kırmızı",
        cikan_bolum="Acil Servis",
        cikan_tetkikler=["EKG", "Troponin"],
        sources=["bas_agrisi.txt"],
    )

    assert sansli_dogru_mu(senaryo, sansli) is True

    durust = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Kırmızı",
        cikan_bolum="Acil Servis",
        cikan_tetkikler=["EKG", "Troponin"],
        sources=["gogus_agrisi.txt"],
    )
    assert sansli_dogru_mu(senaryo, durust) is False


def test_kod_dogru_bolum_yanlissa_da_c_kutusuna_girer():
    """C'nin iki kapısı var; tetkikler tamken bölüm yanlışsa da "doğru ama eksik".

    Tetkik kapısı tek başına test edilirse bölüm karşılaştırması sessizce
    bozulabilir (ör. hep True dönebilir) ve C kutusu olduğundan küçük görünür.
    Bölüm hiç dönmediği (None) hâl de aynı kapıdan geçmeli.
    """
    senaryo = _senaryo()
    yanlis_bolum = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Kırmızı",
        cikan_bolum="Dahiliye",
        cikan_tetkikler=["EKG", "Troponin"],
        sources=["gogus_agrisi.txt"],
    )
    assert kok_neden(senaryo, yanlis_bolum) == "C"

    bolumsuz = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Kırmızı",
        cikan_bolum=None,
        cikan_tetkikler=["EKG", "Troponin"],
        sources=["gogus_agrisi.txt"],
    )
    assert kok_neden(senaryo, bolumsuz) == "C"


def test_kaynagi_yazilmamis_senaryoda_yanlis_kod_muhakemeye_yazilir():
    """`beklenen_kaynak` yoksa retrieval'ın suçlu olduğu kanıtlanamaz, B'ye düşer.

    Kapının `beklenen_kaynak and ...` kısmı düşürülürse `None` hiçbir zaman
    `sources` içinde olmadığı için bu senaryolar toptan A'ya yazılır ve
    "en büyük kutu" retrieval gibi görünür — Gün 24 yanlış hedefe koşar.
    """
    senaryo = _senaryo(beklenen_kaynak=None)
    yanlis = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Yeşil",
        cikan_bolum="Acil Servis",
        cikan_tetkikler=["EKG", "Troponin"],
        sources=["gogus_agrisi.txt"],
    )

    assert kok_neden(senaryo, yanlis) == "B"


def test_sansli_dogru_yalnizca_dogru_cevapta_isaretlenir():
    """Yanlış cevap, altyapı hatası ve kaynağı yazılmamış senaryo şanslı sayılmaz."""
    yanlis = Sonuc(
        senaryo_id="t01", cikan_triage_code="Yeşil", sources=["bas_agrisi.txt"]
    )
    assert sansli_dogru_mu(_senaryo(), yanlis) is False

    # `hata` doluysa senaryo ölçülememiştir ve yanındaki alanlar güvenilmez;
    # kod doğru görünse bile şans sayılmamalı. Alanlar bilerek dolu: boş bir
    # Sonuc'ta zaten kod tutmaz, yani `hata` kapısı sınanmamış olurdu.
    hatali = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Kırmızı",
        sources=["bas_agrisi.txt"],
        hata="timeout",
    )
    assert sansli_dogru_mu(_senaryo(), hatali) is False

    # Kaynağı yazılmamış senaryoda "beklenen protokol gelmedi" iddiası kurulamaz.
    kaynaksiz = Sonuc(
        senaryo_id="t01", cikan_triage_code="Kırmızı", sources=["bas_agrisi.txt"]
    )
    assert sansli_dogru_mu(_senaryo(beklenen_kaynak=None), kaynaksiz) is False


# --- Kaynak adı ayıklama: uç dosya adı değil, önekli belge metni döndürüyor ---


def test_kaynak_adlari_onekten_ayiklanir():
    """`app/services/rag_service.py:92` biçimi: `[Kaynak: dosya] belge metni`."""
    ham = [
        "[Kaynak: gogus_agrisi.txt] Göğüs ağrısında ilk 10 dakika: EKG çekilir.",
        "[Kaynak: yanik.txt] Yanık protokolü: TBSA hesaplanır.",
    ]

    assert kaynak_adlarini_ayikla(ham) == ["gogus_agrisi.txt", "yanik.txt"]


def test_ayni_protokolun_chunklari_sirasiyla_tekillestirilir():
    """`sources` "hangi protokoller geldi" sorusunun cevabı, chunk sayımı değil.

    Aynı protokolün birden çok parçası gelir; tekilleştirilmezse liste
    okunamaz hâle gelir ve Görev 5'in kaynak isabeti chunk sayısına bakar.
    Sıra korunuyor çünkü ilk sıra rerank'in en yüksek skorlu belgesi.
    """
    ham = [
        "[Kaynak: yanik.txt] Birinci parça",
        "[Kaynak: gogus_agrisi.txt] Başka protokol",
        "[Kaynak: yanik.txt] İkinci parça",
    ]

    assert kaynak_adlarini_ayikla(ham) == ["yanik.txt", "gogus_agrisi.txt"]


def test_onegi_olmayan_kaynak_oldugu_gibi_kalir():
    """Sözleşme değişirse değer görünür kalmalı, sessizce düşmemeli.

    Atmak, boş bir liste üretip her senaryoyu A kutusuna yazmak demekti —
    yani ölçümün manşetini sessizce bozan tam olarak o hata sınıfı.
    """
    assert kaynak_adlarini_ayikla(["gogus_agrisi.txt"]) == ["gogus_agrisi.txt"]
    assert kaynak_adlarini_ayikla(["Kaynak: x.txt"]) == ["Kaynak: x.txt"]


def test_kapanis_parantezi_olmayan_onek_ayiklanmaz():
    """Yarım kalmış önek ayrıştırılamaz; uydurmak yerine olduğu gibi bırakılır."""
    bozuk = "[Kaynak: yanik.txt Yanık protokolü"

    assert kaynak_adlarini_ayikla([bozuk]) == [bozuk]


def test_bilinmeyen_kaynak_gercek_bir_dosya_adi_gibi_islenir():
    """`rag_service.py:91` üstveri yoksa 'Bilinmeyen Kaynak' yazıyor — gerçek değer."""
    ham = ["[Kaynak: Bilinmeyen Kaynak] Üstverisi olmayan belge"]

    assert kaynak_adlarini_ayikla(ham) == ["Bilinmeyen Kaynak"]


def test_bosluklu_dosya_adi_korunur_bos_ad_dusurulur():
    """Dosya adında boşluk meşru; boş ad ise hiçbir protokolü göstermez."""
    assert kaynak_adlarini_ayikla(["[Kaynak: gogus agrisi.txt] metin"]) == [
        "gogus agrisi.txt"
    ]
    assert kaynak_adlarini_ayikla(["[Kaynak: ] metin"]) == []


def test_bos_kaynak_listesi_bos_doner():
    """Eşik altı yanıtta uç `sources=[]` döndürüyor (app/api/ai.py:159)."""
    assert kaynak_adlarini_ayikla([]) == []


def test_ham_kaynak_dizeleri_kok_nedeni_yaniltmaz():
    """Ayrıştırma iki katmanda da yapılıyor: sürücü atlasa bile tasnif doğru.

    Uç `sources`'u dosya adı olarak döndürmüyor. Ayrıştırma yalnızca sürücüde
    dursaydı, bir kez unutulduğunda her yanlış cevap A kutusuna yazılır ve
    hiçbir test kırmızıya dönmezdi. `kaynak_adlarini_ayikla` etkisiz eleman
    (çıplak dosya adı değişmeden geçiyor), o yüzden `kok_neden` içinde de
    çağırmak bedava.

    İlk iddia testin kendini kandırmadığını gösteriyor: ayrıştırma girdiyi
    gerçekten değiştiriyor, yani iki iddianın aynı olması tesadüf değil.
    """
    senaryo = _senaryo()
    ham = ["[Kaynak: gogus_agrisi.txt] Göğüs ağrısı protokolü: EKG çekilir."]
    assert kaynak_adlarini_ayikla(ham) != ham

    def _sonuc(sources):
        """Yalnızca `sources` alanı değişen, kodu yanlış bir sonuç üretir."""
        return Sonuc(
            senaryo_id="t01",
            cikan_triage_code="Yeşil",
            cikan_bolum="Acil Servis",
            cikan_tetkikler=["EKG", "Troponin"],
            sources=sources,
        )

    # Beklenen protokol gelmiş; hata muhakemede. Ham da verilse ayıklanmış da
    # verilse aynı kutuya düşmeli.
    assert kok_neden(senaryo, _sonuc(ham)) == "B"
    assert kok_neden(senaryo, _sonuc(kaynak_adlarini_ayikla(ham))) == "B"


def test_ham_kaynak_dizeleri_sansli_dogruyu_yaniltmaz():
    """Ayıklama atlanırsa beklenen protokol hiç bulunamaz ve her doğru cevap
    "şanslı" işaretlenir; `sansli_dogru_mu` da kendi içinde normalize ediyor."""
    senaryo = _senaryo()
    ham = ["[Kaynak: gogus_agrisi.txt] Göğüs ağrısı protokolü: EKG çekilir."]
    assert kaynak_adlarini_ayikla(ham) != ham

    dogru = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Kırmızı",
        cikan_bolum="Acil Servis",
        cikan_tetkikler=["EKG", "Troponin"],
        sources=ham,
    )

    # Protokol geldi: şans değil, dürüst doğru.
    assert sansli_dogru_mu(senaryo, dogru) is False


def test_kaynak_adinin_cevresindeki_bosluk_kirpilir():
    """`[Kaynak:  x.txt ]` ile `[Kaynak: x.txt]` aynı protokolü göstermeli."""
    ham = ["[Kaynak:  yanik.txt ] Yanık protokolü: TBSA hesaplanır."]

    assert kaynak_adlarini_ayikla(ham) == ["yanik.txt"]


def test_beklenen_kaynak_yuklemede_kirpilir(tmp_path):
    """`"gogus_agrisi.txt "` doğrulamayı geçer ama kırpılmazsa hiç eşleşmez.

    Ayıklanan adlar kırpılıyor, senaryo tarafı kırpılmasaydı o senaryo sonsuza
    dek A kutusunda otururdu ve doğru cevap verdiğinde "şanslı doğru"
    işaretlenirdi — hata vermeden. Görev 6 bu dosyaları elle yazacak.
    """
    yol = _yaz(tmp_path, _senaryo_sozlugu(beklenen_kaynak="  gogus_agrisi.txt  "))

    senaryo = senaryolari_yukle(yol)[0]

    assert senaryo.beklenen_kaynak == "gogus_agrisi.txt"

    # Kırpılan değer artık gerçekten eşleşiyor: ne A kutusu ne "şanslı doğru".
    dogru = Sonuc(
        senaryo_id="t01",
        cikan_triage_code="Kırmızı",
        cikan_bolum="Acil Servis",
        cikan_tetkikler=["EKG", "Troponin"],
        sources=["[Kaynak: gogus_agrisi.txt] Göğüs ağrısı protokolü"],
    )
    assert kok_neden(senaryo, dogru) is None
    assert sansli_dogru_mu(senaryo, dogru) is False


def test_wer_hesaplanir():
    # Birebir aynı
    assert wer("başım ağrıyor", "başım ağrıyor") == 0.0
    # Beş kelimeden biri yanlış
    assert wer(
        "sabahtan beri başım çok ağrıyor", "sabahtan beri başım cok ağrıyor"
    ) == pytest.approx(1 / 5)
    # Bir kelime eksik (silme)
    assert wer("başım çok ağrıyor", "başım ağrıyor") == pytest.approx(1 / 3)
    # Bir kelime fazla (ekleme)
    assert wer("başım ağrıyor", "başım çok ağrıyor") == pytest.approx(1 / 2)


def test_wer_noktalama_ve_buyuk_harf_yok_sayar():
    assert wer("Başım ağrıyor!", "başım ağrıyor") == 0.0
    assert wer("Işığa bakamıyorum, midem kalkıyor.", "ışığa bakamıyorum midem kalkıyor") == 0.0


def test_wer_turkce_karakteri_asciye_katlamaz():
    """Katlarsak gerçek tanıma hatasını doğru saymış oluruz (K12)."""
    assert wer("şiddetli ağrı", "siddetli agri") == pytest.approx(1.0)


def test_wer_noktali_noktasiz_i_harfi_dogru_kucultulur():
    """Python'un `.lower()`'ı Türkçe bilmez; iki I harfi elle eşlenmeli.

    `"I".lower()` "i" verir ("ı" değil), `"İ".lower()` ise "i" + birleşen
    nokta (iki karakter) verir. Eşleme yapılmazsa cümle başındaki her "I"/"İ"
    tanıma doğruyken bile hata sayılır ve WER olduğundan kötü çıkar. Bu bir
    büyük/küçük harf düzeltmesi; harf katlaması değil (bkz. bir üstteki test).
    """
    assert wer("Işığa bakamıyorum", "ışığa bakamıyorum") == 0.0
    assert wer("İyileşmedi ağrım", "iyileşmedi ağrım") == 0.0


def test_wer_bos_referans():
    assert wer("", "") == 0.0
    assert wer("", "bir şey") == 1.0


def test_wer_bos_hipotez_tam_hata():
    """Ses akışı boş metin döndürürse tüm kelimeler silinmiş sayılır.

    `degerlendirme/` `--cov=app` dışında olduğu için burada test edilmeyen bir
    dal hem takımda hem kapsam kapısında görünmez kalır; hipotezin boş olduğu
    durumda düzenleme mesafesi iç döngüye hiç girmez ve o dal yalnızca bu
    testle kilitleniyor. Boş transkript koşumda gerçekten olabilir (sessiz ya
    da tanınamayan kayıt) ve WER 1.0 yerine 0.0 çıkarsa hata mükemmel skor
    gibi görünür.
    """
    assert wer("başım çok ağrıyor", "") == pytest.approx(1.0)
    # Yalnızca noktalamadan oluşan bir transkript de kelimesizdir.
    assert wer("başım çok ağrıyor", "...") == pytest.approx(1.0)


def test_wer_birin_ustune_cikabilir():
    """WER 1.0'da kırpılmaz; uydurma (halüsinasyon) uzunluğu oranı aşırtır.

    Görev 5 özeti bu sayıyı yüzdeye çevirecek; üst sınır 1.0 sanılırsa
    %100'den büyük bir değer rapora hata gibi girer. Sözleşme burada duruyor.
    """
    assert wer("ağrı", "ağrı var çok fena") == pytest.approx(3.0)


# --- Özet: raporlanan bütün sayılar ve payda kuralları ---


def test_kirmizi_kacirma_ayri_raporlanir():
    """Gerçek Kırmızı iken Yeşil demek klinik olarak tek kritik hatadır."""
    senaryolar = [
        _senaryo(id="k1", beklenen_triage_code="Kırmızı"),
        _senaryo(id="k2", beklenen_triage_code="Kırmızı"),
        _senaryo(id="y1", beklenen_triage_code="Yeşil", beklenen_tetkikler=[]),
    ]
    sonuclar = [
        Sonuc(senaryo_id="k1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="k2", cikan_triage_code="Yeşil",
              cikan_bolum="Acil Servis", sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="y1", cikan_triage_code="Yeşil",
              cikan_bolum="Acil Servis", sources=["gogus_agrisi.txt"]),
    ]

    o = ozet(senaryolar, sonuclar)

    assert o.kirmizi_toplam == 2
    assert o.kirmizi_yakalanan == 1
    assert o.kirmizi_duyarlilik == pytest.approx(0.5)
    # Genel doğruluk Kırmızı duyarlılığından farklı bir sayıdır.
    assert o.dogruluk_tum == pytest.approx(2 / 3)


def test_esik_alti_yanitlar_ayri_sayilir():
    """'Belirsiz' yanlış cevap değil, 'cevap vermedim'dir."""
    senaryolar = [
        _senaryo(id="s1"),
        _senaryo(id="s2"),
        _senaryo(id="s3"),
        _senaryo(id="s4"),
    ]
    sonuclar = [
        Sonuc(senaryo_id="s1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="s2", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="s3", cikan_triage_code="Belirsiz", sources=[]),
        Sonuc(senaryo_id="s4", cikan_triage_code="Yeşil",
              cikan_bolum="Acil Servis", sources=["gogus_agrisi.txt"]),
    ]

    o = ozet(senaryolar, sonuclar)

    assert o.esik_alti == 1
    assert o.esik_alti_orani == pytest.approx(0.25)
    # Tüm senaryolar üzerinden: 2/4. Cevap verilenler üzerinden: 2/3.
    assert o.dogruluk_tum == pytest.approx(0.5)
    assert o.dogruluk_cevaplananlar == pytest.approx(2 / 3)


def test_kapsam_disi_senaryolar_dogruluga_karismaz():
    """Kapsam dışı senaryo kendi çiftiyle raporlanır, doğruluk oranlarına girmez.

    "Doğru şekilde cevap vermedi" ile "doğru triyaj etti" aynı kovaya konursa
    iki sayı da okunamaz hâle gelir (K7).
    """
    senaryolar = [
        _senaryo(id="i1"),
        _senaryo(id="d1", beklenen_triage_code="Belirsiz", beklenen_kaynak=None),
    ]
    sonuclar = [
        Sonuc(senaryo_id="i1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="d1", cikan_triage_code="Belirsiz", sources=[]),
    ]

    o = ozet(senaryolar, sonuclar)

    assert o.toplam == 1
    assert o.dogruluk_tum == 1.0
    assert o.kapsam_disi_toplam == 1
    assert o.kapsam_disi_dogru == 1


def test_altyapi_hatasi_paydadan_dusulur():
    """Altyapı hatası yanlış cevap değildir; paydadan tamamen çıkar.

    Yanlış sayılsaydı doğruluğu olduğundan düşük gösterir, üstelik hata
    kutularını da şişirirdi — iki sayı birden bozulurdu.
    """
    senaryolar = [_senaryo(id="h1"), _senaryo(id="h2")]
    sonuclar = [
        Sonuc(senaryo_id="h1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="h2", hata="500 Sunucu hatası"),
    ]

    o = ozet(senaryolar, sonuclar)

    assert o.olculemedi == 1
    assert o.toplam == 1
    assert o.dogruluk_tum == 1.0


def test_kapsam_disi_senaryo_esik_alti_ve_cevaplanan_paydalarina_girmez():
    """Kapsam dışı 'Belirsiz' doğru cevaptır; eşik altı sayısını şişirmemeli.

    Brief'in dört testinde kapsam dışı senaryo ile eşik altı yanıt hiç yan yana
    gelmiyor, o yüzden `esik_alti` ya da `cevaplanan` paydasının sessizce
    `kapsam_disi`yi de kapsamasını hiçbiri yakalamıyordu. İkisi bir arada
    ölçüldüğünde eşik altı oranı gerçekte olduğundan yüksek çıkardı ve rapor
    "sistem her üç vakadan ikisinde cevap vermiyor" derdi.
    """
    senaryolar = [
        _senaryo(id="i1"),
        _senaryo(id="i2"),
        _senaryo(id="d1", beklenen_triage_code="Belirsiz", beklenen_kaynak=None),
    ]
    sonuclar = [
        Sonuc(senaryo_id="i1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="i2", cikan_triage_code="Belirsiz", sources=[]),
        Sonuc(senaryo_id="d1", cikan_triage_code="Belirsiz", sources=[]),
    ]

    o = ozet(senaryolar, sonuclar)

    assert o.toplam == 2
    # Eşik altı yalnızca kapsam içinde anlamlı: d1'in "Belirsiz"i doğru cevaptır.
    assert o.esik_alti == 1
    assert o.esik_alti_orani == pytest.approx(0.5)
    # Cevap verilenler paydası kapsam içi ∧ cevap verilen = yalnızca i1.
    assert o.dogruluk_tum == pytest.approx(0.5)
    assert o.dogruluk_cevaplananlar == 1.0


def test_jaccard_yalnizca_cevap_verilen_kapsam_ici_senaryolardan_hesaplanir():
    """Tetkik örtüşmesi iki ayrı elemeden geçer: kapsam dışı ve eşik altı.

    Eşik altı yanıtta uç boş tetkik listesi döndürüyor; hesaba katılırsa
    ortalamayı sıfırla aşağı çeker ve "önerilen tetkikler kötü" gibi görünür.
    Kapsam dışı senaryo ise `kok_neden`de zaten puanlanmıyor (Görev 3 kararı);
    burada puanlansaydı özet ile tasnif birbiriyle çelişirdi.
    """
    senaryolar = [
        # Kapsam içi, cevap verilmiş, tetkikler birebir tutuyor → 1.0.
        _senaryo(id="i1"),
        # Kapsam içi ama sistem eşik altında kaldı → hesaba girmemeli.
        _senaryo(id="i2"),
        # Kapsam dışı ve sistem cevap üretmiş (eşik fazla geçirgen) →
        # `cikan_triage_code != "Belirsiz"` elemesine takılmaz, yalnızca
        # `kapsam_ici` kısıtı dışarıda tutar.
        _senaryo(
            id="d1",
            beklenen_triage_code="Belirsiz",
            beklenen_tetkikler=["EKG"],
            beklenen_kaynak=None,
        ),
    ]
    sonuclar = [
        Sonuc(senaryo_id="i1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="i2", cikan_triage_code="Belirsiz", sources=[]),
        Sonuc(senaryo_id="d1", cikan_triage_code="Sarı",
              cikan_bolum="Dahiliye", cikan_tetkikler=[], sources=[]),
    ]

    o = ozet(senaryolar, sonuclar)

    # Yalnızca i1 hesaba girer. i2 girseydi 0.5, d1 girseydi 0.5, ikisi de
    # girseydi 1/3 çıkardı — üç mutasyonun üçü de bu tek sayıyı bozar.
    assert o.jaccard_ortalama == 1.0


def test_kok_neden_dagilimi_kutulara_ayrilir():
    """Gün 24 "en büyük kutuya müdahale et" diyor; dağılım yanlışsa hedef yanlış.

    Doğru sonuç (None) ve altyapı hatası ("HATA") hiçbir kutuya yazılmamalı:
    yazılsalardı A/B/C toplamı senaryo sayısına şişer ve "biçim hatası" oranı
    olduğundan küçük görünürdü. Kapsam dışıyken cevap üretmek ise A'dır ve
    dağılıma girer — `kapsam_disi` dağılım döngüsünden düşerse o hata kaybolur.
    """
    senaryolar = [
        _senaryo(id="a1"),
        _senaryo(id="b1"),
        _senaryo(id="c1"),
        _senaryo(id="n1"),
        _senaryo(id="h1"),
        _senaryo(id="d1", beklenen_triage_code="Belirsiz", beklenen_kaynak=None),
    ]
    sonuclar = [
        # A: beklenen protokol aday havuzuna hiç girmemiş.
        Sonuc(senaryo_id="a1", cikan_triage_code="Yeşil",
              cikan_bolum="Dahiliye", cikan_tetkikler=[],
              sources=["bas_agrisi.txt"]),
        # B: protokol gelmiş ama model yanlış kod vermiş.
        Sonuc(senaryo_id="b1", cikan_triage_code="Yeşil",
              cikan_bolum="Dahiliye", cikan_tetkikler=[],
              sources=["gogus_agrisi.txt"]),
        # C: kod doğru, bölüm yanlış.
        Sonuc(senaryo_id="c1", cikan_triage_code="Kırmızı",
              cikan_bolum="Dahiliye", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        # None: her şey doğru.
        Sonuc(senaryo_id="n1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        # HATA: ölçülemedi.
        Sonuc(senaryo_id="h1", hata="timeout"),
        # A: kapsam dışıyken cevap üretmek eşiğin fazla geçirgen olmasıdır.
        Sonuc(senaryo_id="d1", cikan_triage_code="Sarı",
              cikan_bolum="Dahiliye", sources=[]),
    ]

    o = ozet(senaryolar, sonuclar)

    assert o.kok_neden_dagilimi == {"A": 2, "B": 1, "C": 1}
    assert "HATA" not in o.kok_neden_dagilimi
    assert o.olculemedi == 1
    # c1'in kodu doğru: C kutusundadır ama doğru sayılır.
    assert o.dogru == 2
    assert o.toplam == 4


def test_sansli_dogru_ozette_sayilir():
    """Doğru cevap ama protokol gelmemiş — Gün 24'te bozulabilecek senaryolar.

    Sayılmazsa önce/sonra tablosunda açıklanamayan bir gerileme olarak görünür.
    "Şanslı" olması doğruluğu düşürmez; iki sayı birbirinden bağımsızdır.
    """
    senaryolar = [_senaryo(id="s1"), _senaryo(id="s2")]
    sonuclar = [
        # Doğru cevap, beklenen protokol hiç gelmemiş → şanslı doğru.
        Sonuc(senaryo_id="s1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["bas_agrisi.txt"]),
        # Doğru cevap, doğru protokol → şanslı değil.
        Sonuc(senaryo_id="s2", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
    ]

    o = ozet(senaryolar, sonuclar)

    assert o.sansli_dogru == 1
    assert o.dogru == 2
    assert o.dogruluk_tum == 1.0


def test_altyapi_hatasi_kirmizi_duyarliligi_paydasindan_da_dusulur():
    """Ölçülemeyen bir Kırmızı senaryo duyarlılık paydasına da girmemeli.

    Girseydi tek bir zaman aşımı "Kırmızı duyarlılığı %50" yazdırırdı; bu sayı
    raporun en kritik iddiası ve altyapı gürültüsüne karşı korunmak zorunda.
    """
    senaryolar = [_senaryo(id="k1"), _senaryo(id="k2")]
    sonuclar = [
        Sonuc(senaryo_id="k1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="k2", hata="timeout"),
    ]

    o = ozet(senaryolar, sonuclar)

    assert o.kirmizi_toplam == 1
    assert o.kirmizi_yakalanan == 1
    assert o.kirmizi_duyarlilik == 1.0
    assert o.olculemedi == 1


def test_sonucu_olmayan_senaryo_sayilir_ama_paydaya_girmez():
    """Yarım kalmış bir koşumun kısmi çıktısı sessizce paydayı küçültmemeli.

    Sürücü her senaryo için bir `Sonuc` yazar; ama çöken bir koşumun ara
    dosyasında eksik kayıt olabilir. O dosyayla özet alınırsa doğruluk ölçülen
    alt küme üzerinden hesaplanır. `Ozet.__dict__` kalıcı JSON kaydı olduğu
    için iz tutulmazsa yarım koşum bir daha asla tam koşumdan ayırt edilemez:
    alt kümede hesaplanmış doğruluk tam küme gibi okunur.

    `sonucsuz` bu yüzden ayrı sayılıyor — `olculemedi` değil, çünkü altyapı
    hatası değil "hiç sorulmamış" demektir; paydaya da girmiyor, çünkü
    ölçülmemiş bir senaryo yanlış cevap sayılamaz.
    """
    senaryolar = [_senaryo(id="v1"), _senaryo(id="sorulmadi")]
    sonuclar = [
        Sonuc(senaryo_id="v1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
    ]

    o = ozet(senaryolar, sonuclar)

    assert o.toplam == 1
    assert o.dogruluk_tum == 1.0
    assert o.olculemedi == 0
    # Kayıp senaryo görünür kalır: 2 senaryo verildi, 1'i ölçüldü.
    assert o.sonucsuz == 1
    assert o.toplam + o.kapsam_disi_toplam + o.olculemedi + o.sonucsuz == len(senaryolar)


def test_tam_kosumda_sayilar_senaryo_sayisiyla_denklesir():
    """Her senaryo dört kovadan tam birine düşer; toplamları seti vermeli.

    Bu denklem olmadan `sonucsuz` alanı yalnızca bir sayı; denklemle birlikte
    raporun "elimdeki kayıt tam mı" sorusuna verebileceği tek cevap oluyor.
    """
    senaryolar = [
        _senaryo(id="i1"),
        _senaryo(id="h1"),
        _senaryo(id="d1", beklenen_triage_code="Belirsiz", beklenen_kaynak=None),
        _senaryo(id="yok"),
    ]
    sonuclar = [
        Sonuc(senaryo_id="i1", cikan_triage_code="Kırmızı",
              cikan_bolum="Acil Servis", cikan_tetkikler=["EKG", "Troponin"],
              sources=["gogus_agrisi.txt"]),
        Sonuc(senaryo_id="h1", hata="500 Sunucu hatası"),
        Sonuc(senaryo_id="d1", cikan_triage_code="Belirsiz", sources=[]),
    ]

    o = ozet(senaryolar, sonuclar)

    assert (o.toplam, o.kapsam_disi_toplam, o.olculemedi, o.sonucsuz) == (1, 1, 1, 1)
    assert o.toplam + o.kapsam_disi_toplam + o.olculemedi + o.sonucsuz == len(senaryolar)


def test_kapsam_disi_senaryo_sansli_dogru_sayilmaz():
    """Doğru reddedilen kapsam dışı senaryo retrieval üzerinden puanlanmaz.

    Eşik altı yanıt yolu hiç kaynak döndürmüyor (`app/api/ai.py:152-160`), o
    yüzden `beklenen_kaynak` yazılmış bir kapsam dışı senaryo doğru
    reddedildiğinde HER ZAMAN "şanslı doğru" işaretlenirdi — Gün 24 önce/sonra
    tablosuna sahte bir kırılganlık yazılırdı. Görev 3 kapsam dışı senaryoların
    retrieval üzerinden puanlanmamasına karar vermişti; kural burada da geçerli.

    Yükleyici bu alan birleşimine izin veriyor (kapsam dışı + `beklenen_kaynak`),
    yani tek koruma senaryo yazma konvansiyonu olamaz.
    """
    senaryo = _senaryo(
        id="d1", beklenen_triage_code="Belirsiz", beklenen_kaynak="gogus_agrisi.txt"
    )
    reddedildi = Sonuc(senaryo_id="d1", cikan_triage_code="Belirsiz", sources=[])

    assert sansli_dogru_mu(senaryo, reddedildi) is False

    o = ozet([senaryo], [reddedildi])
    assert o.sansli_dogru == 0
    assert o.kapsam_disi_dogru == 1


def test_bos_hata_dizesi_altyapi_hatasi_sayilmaz():
    """`hata=""` hata değildir; `ozet` bu kararı `kok_neden` ile aynı vermeli.

    Brief'in düzyazısı `hata is None` diyor, kodu doğruluk (truthiness)
    kullanıyor; ikisi yalnızca boş dizede ayrışır. `is not None`'a çevrilirse
    `hata=""` olan sonuç paydadan düşer ama `kok_neden` onu yine A/B/C'ye
    tasnif eder — özet ile dağılım birbirini tutmaz. Boş dize zaten meşru bir
    hata mesajı değil; modüldeki üç çağrı yeri de doğruluk kullanıyor.
    """
    senaryo = _senaryo(id="b1")
    bos_hata = Sonuc(
        senaryo_id="b1", cikan_triage_code="Kırmızı", cikan_bolum="Acil Servis",
        cikan_tetkikler=["EKG", "Troponin"], sources=["gogus_agrisi.txt"], hata="",
    )

    o = ozet([senaryo], [bos_hata])

    assert o.olculemedi == 0
    assert o.toplam == 1
    assert o.dogruluk_tum == 1.0
    # kok_neden aynı kararı veriyor: "HATA" değil, kusursuz sonuç.
    assert kok_neden(senaryo, bos_hata) is None


def test_bos_kumede_sifira_bolunmez():
    """Boş kümede oran tanımsız; rapor basılırken ZeroDivisionError atılamaz.

    Kör set hiç koşulmazsa ya da bütün senaryolar hata alırsa payda sıfırlanır.
    Bu dal `--cov=app` dışında olduğu için yalnızca bu testle görünür.
    """
    o = ozet([], [])

    assert isinstance(o, Ozet)
    assert o.toplam == 0
    assert o.dogru == 0
    assert o.dogruluk_tum == 0.0
    assert o.dogruluk_cevaplananlar == 0.0
    assert o.kirmizi_toplam == 0
    assert o.kirmizi_duyarlilik == 0.0
    assert o.esik_alti_orani == 0.0
    assert o.jaccard_ortalama == 0.0
    assert o.kok_neden_dagilimi == {"A": 0, "B": 0, "C": 0}
    assert o.kapsam_disi_toplam == 0
    assert o.sonucsuz == 0

    # Yalnızca kapsam dışı senaryo varsa da kapsam içi payda sıfırdır.
    yalniz_kapsam_disi = ozet(
        [_senaryo(id="d1", beklenen_triage_code="Belirsiz", beklenen_kaynak=None)],
        [Sonuc(senaryo_id="d1", cikan_triage_code="Belirsiz", sources=[])],
    )
    assert yalniz_kapsam_disi.toplam == 0
    assert yalniz_kapsam_disi.dogruluk_tum == 0.0
    assert yalniz_kapsam_disi.dogruluk_cevaplananlar == 0.0
    assert yalniz_kapsam_disi.jaccard_ortalama == 0.0
    assert yalniz_kapsam_disi.kapsam_disi_toplam == 1
    assert yalniz_kapsam_disi.kapsam_disi_dogru == 1
