"""Yerel 7B modelin kaygan çıktısını sabit kelime dağarcığına indiren
normalizasyon fonksiyonlarının davranışını dondurur."""

import pytest

from app.api.ai import _normalize_tetkikler, _normalize_triage_code, _sadelestir


@pytest.mark.parametrize(
    "girdi, beklenen",
    [
        ("Kırmızı", "kirmizi"),
        ("KIRMIZI", "kirmizi"),
        ("Yeşil", "yesil"),
        ("  Sarı  ", "sari"),
        ("ŞİĞÜÖÇ", "siguoc"),
    ],
)
def test_sadelestir_turkce_karakterleri_ascii_yapar(girdi, beklenen):
    assert _sadelestir(girdi) == beklenen


@pytest.mark.parametrize(
    "ham_kod, beklenen",
    [
        ("Kırmızı", "Kırmızı"),
        ("kirmizi", "Kırmızı"),   # model ASCII yazmış
        ("KIRMIZI", "Kırmızı"),   # model büyük harf yazmış
        ("  sari  ", "Sarı"),     # boşluklu ve ASCII
        ("yesil", "Yeşil"),
        ("Mavi", "Belirsiz"),     # geçerli kümede yok
        ("", "Belirsiz"),
    ],
)
def test_triyaj_kodu_gecerli_kumeye_indirgenir(ham_kod, beklenen):
    assert _normalize_triage_code(ham_kod) == beklenen


@pytest.mark.parametrize("ham_kod", [None, 42, ["Kırmızı"], {"kod": "Kırmızı"}])
def test_string_olmayan_triyaj_kodu_belirsiz_doner(ham_kod):
    # Model bazen string yerine başka tip döndürebiliyor; çökmemeli.
    assert _normalize_triage_code(ham_kod) == "Belirsiz"


def test_tetkik_listesi_temizlenir():
    # Baştaki/sondaki boşluklar silinir, boş elemanlar atılır.
    assert _normalize_tetkikler(["  Tam kan sayımı  ", "", "  ", "EKG"]) == [
        "Tam kan sayımı",
        "EKG",
    ]


def test_tek_string_tetkik_listeye_cevrilir():
    # Model liste yerine tek string döndürürse listeye sarılmalı.
    assert _normalize_tetkikler("EKG") == ["EKG"]


@pytest.mark.parametrize("ham", [None, 42, {"a": 1}])
def test_liste_olmayan_tetkik_bos_liste_doner(ham):
    assert _normalize_tetkikler(ham) == []


def test_tetkik_elemanlari_stringe_cevrilir():
    # Model sayı döndürürse string'e çevrilmeli, çökmemeli.
    assert _normalize_tetkikler([1, 2]) == ["1", "2"]
