"""Gün 24 önce/sonra tablosu — birden fazla koşum JSON'unu ortalar."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BURASI = Path(__file__).resolve().parent
# Gün 23'te ölçülen gürültü: payda 19 iken tek senaryo manşeti 5,3 puan oynatır.
GURULTU_TABANI_PUAN = 5.3
IZLENEN_SENARYO = "tur_04"


def _yukle(yol: Path) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))


def _oran_yuzde(deger: float | None) -> str:
    if deger is None:
        return "n/d"
    return f"%{deger * 100:.1f}"


def _ortalama(degerler: list[float | None]) -> float | None:
    sayilar = [d for d in degerler if d is not None]
    if not sayilar:
        return None
    return sum(sayilar) / len(sayilar)


def _blok_ozet(ham: dict, blok: str) -> dict:
    return ham["bloklar"][blok]["ozet"]


def _tetkik_ortalamasi(ham: dict, blok: str) -> float:
    """Cevaplanan senaryolarda ortalama önerilen tetkik sayısı (few-shot bastırma)."""
    sonuclar = ham["bloklar"][blok]["sonuclar"]
    uzunluklar = [
        len(s.get("cikan_tetkikler") or [])
        for s in sonuclar
        if not s.get("hata") and s.get("cikan_triage_code") != "Belirsiz"
    ]
    return sum(uzunluklar) / len(uzunluklar) if uzunluklar else 0.0


def _senaryo_kodu(ham: dict, senaryo_id: str) -> str | None:
    for blok in ham["bloklar"].values():
        for s in blok["sonuclar"]:
            if s["senaryo_id"] == senaryo_id:
                return s.get("cikan_triage_code")
    return None


def raporla(once: dict, sonralar: list[dict]) -> str:
    """Önce/sonra markdown metnini üretir."""
    satirlar = [
        "# Gün 24 — Önce / sonra tablosu",
        "",
        f"Baseline: `{once.get('tarih')}` (Gün 23, değiştirilmedi).",
        f"Sonra koşum sayısı: **{len(sonralar)}** (manşet = ortalama).",
        f"Gürültü tabanı (Gün 23): **{GURULTU_TABANI_PUAN} puan** "
        f"(kaynak: `{IZLENEN_SENARYO}` salınımı).",
        "",
        "## Manşet metrikler",
        "",
        "| Ölçü | Önce (kör) | Sonra ort. (kör) | Önce (tür.) | Sonra ort. (tür.) |",
        "|---|---|---|---|---|",
    ]

    def hucre(hamlar: list[dict], blok: str, alan: str) -> str:
        return _oran_yuzde(_ortalama([_blok_ozet(h, blok).get(alan) for h in hamlar]))

    satirlar.append(
        "| Genel doğruluk | "
        f"{hucre([once], 'Kör set', 'dogruluk_tum')} | "
        f"{hucre(sonralar, 'Kör set', 'dogruluk_tum')} | "
        f"{hucre([once], 'Türetilmiş set', 'dogruluk_tum')} | "
        f"{hucre(sonralar, 'Türetilmiş set', 'dogruluk_tum')} |"
    )
    satirlar.append(
        "| Kırmızı duyarlılık | "
        f"{hucre([once], 'Kör set', 'kirmizi_duyarlilik')} | "
        f"{hucre(sonralar, 'Kör set', 'kirmizi_duyarlilik')} | "
        f"{hucre([once], 'Türetilmiş set', 'kirmizi_duyarlilik')} | "
        f"{hucre(sonralar, 'Türetilmiş set', 'kirmizi_duyarlilik')} |"
    )
    satirlar.append(
        "| Eşik altı oranı | "
        f"{hucre([once], 'Kör set', 'esik_alti_orani')} | "
        f"{hucre(sonralar, 'Kör set', 'esik_alti_orani')} | "
        f"{hucre([once], 'Türetilmiş set', 'esik_alti_orani')} | "
        f"{hucre(sonralar, 'Türetilmiş set', 'esik_alti_orani')} |"
    )

    once_j = _blok_ozet(once, "Türetilmiş set").get("jaccard_ortalama")
    sonra_j = _ortalama(
        [_blok_ozet(h, "Türetilmiş set").get("jaccard_ortalama") for h in sonralar]
    )
    satirlar.extend(
        [
            "",
            f"Türetilmiş Jaccard önce: **{once_j if once_j is not None else 'n/d'}**, "
            f"sonra ort.: **{sonra_j if sonra_j is not None else 'n/d'}**.",
            "",
            "## A/B/C (türetilmiş, ortalama sayılar)",
            "",
        ]
    )
    for kutu in ("A", "B", "C"):
        once_n = _blok_ozet(once, "Türetilmiş set")["kok_neden_dagilimi"].get(kutu, 0)
        sonra_n = _ortalama(
            [
                float(
                    _blok_ozet(h, "Türetilmiş set")["kok_neden_dagilimi"].get(kutu, 0)
                )
                for h in sonralar
            ]
        )
        satirlar.append(f"- **{kutu}**: önce {once_n}, sonra ort. {sonra_n:.1f}")

    once_tet = _tetkik_ortalamasi(once, "Türetilmiş set")
    sonra_tet = _ortalama([_tetkik_ortalamasi(h, "Türetilmiş set") for h in sonralar])
    satirlar.extend(
        [
            "",
            "## Few-shot tetkik bastırma izi",
            "",
            f"Ortalama önerilen tetkik sayısı (türetilmiş, Belirsiz hariç): "
            f"önce **{once_tet:.2f}**, sonra ort. **{sonra_tet:.2f}**.",
            "",
            f"## `{IZLENEN_SENARYO}` salınımı",
            "",
        ]
    )
    kodlar = [_senaryo_kodu(h, IZLENEN_SENARYO) for h in sonralar]
    satirlar.append(
        f"Sonra koşumlarda `{IZLENEN_SENARYO}` kodları: "
        + ", ".join(k or "?" for k in kodlar)
    )
    satirlar.append(f"Önce: `{_senaryo_kodu(once, IZLENEN_SENARYO)}`.")

    once_d = _blok_ozet(once, "Türetilmiş set").get("dogruluk_tum")
    sonra_d = _ortalama(
        [_blok_ozet(h, "Türetilmiş set").get("dogruluk_tum") for h in sonralar]
    )
    satirlar.extend(["", "## Dürüst okuma", ""])
    if once_d is None or sonra_d is None:
        satirlar.append(
            "Türetilmiş doğruluk tanımsız; iyileşme iddiası kurulamaz."
        )
    else:
        fark_puan = (sonra_d - once_d) * 100
        if abs(fark_puan) < GURULTU_TABANI_PUAN:
            satirlar.append(
                f"Türetilmiş doğruluk farkı **{fark_puan:+.1f} puan** — "
                f"gürültü tabanının (**{GURULTU_TABANI_PUAN}**) **içinde**. "
                "Few-shot / önkoşul etkisi tek başına manşet iyileşmesi diye "
                "raporlanamaz."
            )
        else:
            satirlar.append(
                f"Türetilmiş doğruluk farkı **{fark_puan:+.1f} puan** — "
                f"gürültü tabanının (**{GURULTU_TABANI_PUAN}**) **üstünde**."
            )
    satirlar.append("")
    return "\n".join(satirlar)


def main(argv: list[str] | None = None) -> int:
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--once", type=Path, required=True)
    parser.add_argument("--sonra", type=Path, nargs="+", required=True)
    parser.add_argument(
        "--cikti",
        type=Path,
        default=BURASI / "sonuclar" / "gun24-once-sonra.md",
    )
    args = parser.parse_args(argv)

    once = _yukle(args.once)
    sonralar = [_yukle(p) for p in args.sonra]
    metin = raporla(once, sonralar)
    args.cikti.parent.mkdir(parents=True, exist_ok=True)
    args.cikti.write_text(metin, encoding="utf-8")
    print(metin)
    print(f"\nYazıldı: {args.cikti}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
