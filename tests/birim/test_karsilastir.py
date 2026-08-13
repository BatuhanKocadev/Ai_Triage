"""karsilastir.py önce/sonra ortalamasının gürültü okumasını dondurur."""

from degerlendirme.karsilastir import GURULTU_TABANI_PUAN, raporla


def _ozet(dogru: int, toplam: int, **extra) -> dict:
    return {
        "toplam": toplam,
        "dogru": dogru,
        "dogruluk_tum": dogru / toplam if toplam else None,
        "kirmizi_duyarlilik": None,
        "esik_alti_orani": 0.0,
        "jaccard_ortalama": 0.5,
        "kok_neden_dagilimi": {"A": 1, "B": 1, "C": 1, **extra.get("dagilim", {})},
    }


def _ham(tarih: str, dogru: int, kod: str) -> dict:
    return {
        "tarih": tarih,
        "bloklar": {
            "Kör set": {
                "ozet": _ozet(3, 8),
                "sonuclar": [
                    {
                        "senaryo_id": "kor_01",
                        "cikan_triage_code": "Sarı",
                        "cikan_tetkikler": ["EKG"],
                        "hata": None,
                    }
                ],
            },
            "Türetilmiş set": {
                "ozet": _ozet(dogru, 19),
                "sonuclar": [
                    {
                        "senaryo_id": "tur_04",
                        "cikan_triage_code": kod,
                        "cikan_tetkikler": ["EKG", "Troponin"],
                        "hata": None,
                    },
                    {
                        "senaryo_id": "tur_01",
                        "cikan_triage_code": "Kırmızı",
                        "cikan_tetkikler": ["EKG"],
                        "hata": None,
                    },
                ],
            },
        },
    }


def test_karsilastir_gurultu_icinde_acikca_yazar():
    """+5 puan gürültü tabanının altında kalmalı — sahte iyileşme yazılmaz."""
    once = _ham("2026-08-13", dogru=15, kod="Kırmızı")  # %78.9
    # 16/19 ≈ %84.2 → +5.3 civarı tam tabanda; 15.5 yok, 16 kullan
    sonra = [_ham("2026-08-14", dogru=16, kod="Sarı") for _ in range(3)]
    metin = raporla(once, sonra)
    assert "gürültü tabanının" in metin
    # 16/19 - 15/19 = 1/19 ≈ 5.26 < 5.3 → içinde
    assert "içinde" in metin
    assert str(GURULTU_TABANI_PUAN) in metin


def test_karsilastir_tur04_kodlarini_listeler():
    """tur_04 salınımı tabloda görünür kalmalı."""
    once = _ham("2026-08-13", dogru=15, kod="Kırmızı")
    sonralar = [
        _ham("a", 15, "Kırmızı"),
        _ham("b", 16, "Sarı"),
        _ham("c", 15, "Kırmızı"),
    ]
    metin = raporla(once, sonralar)
    assert "Sarı" in metin
    assert "tur_04" in metin
