"""Yerel 7B modelin kaygan çıktısını sabit kelime dağarcığına indiren
normalizasyon fonksiyonlarının davranışını dondurur."""

import pytest

from app.api.ai import (
    _normalize_department,
    _normalize_tetkikler,
    _normalize_triage_code,
    _sadelestir,
)


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
    # maketrans tablosu ya da .lower().strip() zinciri bozulursa modelin
    # "Kirmizi"/"KIRMIZI" yazımı "Kırmızı" ile eşleşmez, her kod "Belirsiz"e düşer.
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
    # Eşleştirme döngüsü iki tarafı da sadeleştirmezse ya da kanonik yazım yerine
    # sadeleştirilmiş hali dönerse, geçerli kodlar kayda yanlış/"Belirsiz" yazılır.
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
    # Liste koruması kalkarsa None/int'te TypeError fırlar, dict'te de anahtarlar
    # tetkik sanılıp listeye sızar.
    assert _normalize_tetkikler(ham) == []


def test_tetkik_elemanlari_stringe_cevrilir():
    # Model sayı döndürürse string'e çevrilmeli, çökmemeli.
    assert _normalize_tetkikler([1, 2]) == ["1", "2"]


def test_few_shot_prompt_metni_sikayet_ve_akuite_icerir():
    """Few-shot metni şikayeti ve akuite alanını taşır; tetkik adı öğretmez."""
    from app.api.ai import few_shot_prompt_metni

    metin = few_shot_prompt_metni(
        [
            {
                "sikayet": "arı soktu, kolum şişti ama nefesim rahat",
                "beklenen_cikti": {
                    "triage_code": "Yeşil",
                    "department": "Yeşil Alan",
                    "onerilen_tetkikler": [],
                },
            }
        ]
    )
    assert "arı soktu, kolum şişti ama nefesim rahat" in metin
    assert "Yeşil Alan" in metin
    assert "Tam kan" not in metin


@pytest.mark.parametrize(
    "ham, triage, beklenen",
    [
        ("Kırmızı Alan", "Kırmızı", "Kırmızı Alan"),
        ("sarı alan", "Sarı", "Sarı Alan"),
        ("  YESIL ALAN  ", "Yeşil", "Yeşil Alan"),
        ("Resüsitasyon", "Kırmızı", "Resüsitasyon"),
        ("Şok Odası", "Kırmızı", "Şok Odası"),
        ("Triyaj Bankosu", "Belirsiz", "Triyaj Bankosu"),
        # Hastane bölümü uydurması → triyaj kodundan akuite alanına
        ("Pulmonoloji", "Kırmızı", "Kırmızı Alan"),
        ("Dahiliye", "Sarı", "Sarı Alan"),
        ("Ortopedi", "Yeşil", "Yeşil Alan"),
        ("İnsan Hakkında", "Yeşil", "Yeşil Alan"),
        (None, "Sarı", "Sarı Alan"),
        ("", "Kırmızı", "Kırmızı Alan"),
        ("Dahiliye", "Belirsiz", "Triyaj Bankosu"),
    ],
)
def test_department_kapali_kelime_dagarcigina_indirgenir(ham, triage, beklenen):
    """Gün 24: model hastane bölümü uydurmasın; çıktı derleme dağarcığında kalsın."""
    assert _normalize_department(ham, triage) == beklenen


def test_department_dagarcik_disi_triyaj_belirsizde_banko():
    """Triyaj Belirsiz iken dağarcık dışı her şey Triyaj Bankosu'na düşer."""
    assert _normalize_department("Kardiyoloji", "Belirsiz") == "Triyaj Bankosu"
