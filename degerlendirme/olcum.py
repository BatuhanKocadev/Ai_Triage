"""Gün 23 ölçüm çekirdeği — saf fonksiyonlar.

Bu modül ağ, veritabanı ya da model görmez; girdi alır, çıktı döndürür.
Sürücü (`calistir.py`) HTTP tarafını üstlenir. Ayrım, yol haritasının
istediği birim testlerinin Ollama'sız koşabilmesi için (K6).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Sistemin üretebileceği ve senaryoların bekleyebileceği triyaj kodları.
# "Belirsiz" hem sistemin eşik altı yanıtı hem de kapsam dışı senaryolar için
# meşru bir beklentidir (kör set bu ihtiyacı ortaya çıkardı).
GECERLI_KODLAR = {"Kırmızı", "Sarı", "Yeşil", "Belirsiz"}

# Senaryo sözlüğünde bulunması zorunlu alanlar; eksiği yükleme anında patlar.
ZORUNLU_ALANLAR = (
    "id",
    "sikayet",
    "yas",
    "cinsiyet",
    "beklenen_triage_code",
    "beklenen_bolum",
    "beklenen_tetkikler",
)


class SenaryoHatasi(Exception):
    """Senaryo dosyası okunamadığında ya da şemaya uymadığında atılır."""


@dataclass(frozen=True)
class Senaryo:
    """Tek bir değerlendirme senaryosu — ölçümün girdisi ve altın standardı."""

    id: str
    sikayet: str
    yas: int
    cinsiyet: str
    beklenen_triage_code: str
    beklenen_bolum: str
    beklenen_tetkikler: list[str]
    # Hangi protokolün gelmesi bekleniyor; None = kapsam dışı senaryo.
    beklenen_kaynak: str | None = None
    kronik_hastalik: str | None = None
    # Yalnızca fever ve pulse taşır; app/api/ai.py:35 bundan fazlasını kabul etmiyor.
    vitals: dict | None = None
    # Kör senaryolarda dolu; WER yalnızca bu alanı olan senaryolarda hesaplanır.
    ses_dosyasi: str | None = None


@dataclass
class Sonuc:
    """Bir senaryonun sisteme sorulmasından dönen ham kayıt."""

    senaryo_id: str
    cikan_triage_code: str | None = None
    cikan_bolum: str | None = None
    cikan_tetkikler: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    # Koşumun yarattığı ziyaret; silinmiyor, video demosunda kullanılacak (K14).
    visit_id: str | None = None
    # Ses akışından dönen metin; WER bunu referansla karşılaştırır.
    transkript: str | None = None
    # Altyapı hatası (500, timeout, 429 tükenmesi); doluysa senaryo ölçülemedi.
    hata: str | None = None


def senaryolari_yukle(yol: str | Path) -> list[Senaryo]:
    """JSON senaryo dosyasını okur ve şemayı doğrular.

    Eksik alan, geçersiz triyaj kodu ya da tekrarlanan id durumunda
    `SenaryoHatasi` atar — bozuk bir ölçüm setiyle koşmak, ölçüm yapmamaktan
    daha kötüdür çünkü çıkan sayı güvenilir görünür.
    """
    yol = Path(yol)
    try:
        ham = json.loads(yol.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SenaryoHatasi(f"Senaryo dosyası bulunamadı: {yol}") from exc
    except json.JSONDecodeError as exc:
        raise SenaryoHatasi(f"Senaryo dosyası geçerli JSON değil: {yol} — {exc}") from exc

    if not isinstance(ham, list):
        raise SenaryoHatasi(f"Senaryo dosyası bir liste olmalı: {yol}")

    senaryolar: list[Senaryo] = []
    gorulen_idler: set[str] = set()
    for sira, kayit in enumerate(ham):
        if not isinstance(kayit, dict):
            raise SenaryoHatasi(f"{sira}. kayıt bir sözlük değil")

        for alan in ZORUNLU_ALANLAR:
            if alan not in kayit:
                raise SenaryoHatasi(
                    f"{sira}. kayıtta zorunlu alan eksik: {alan}"
                )

        kod = kayit["beklenen_triage_code"]
        if kod not in GECERLI_KODLAR:
            raise SenaryoHatasi(
                f"{kayit['id']}: geçersiz triyaj kodu {kod!r} "
                f"(geçerliler: {sorted(GECERLI_KODLAR)})"
            )

        if kayit["id"] in gorulen_idler:
            raise SenaryoHatasi(f"Tekrarlanan senaryo id: {kayit['id']}")
        gorulen_idler.add(kayit["id"])

        senaryolar.append(
            Senaryo(
                id=kayit["id"],
                sikayet=kayit["sikayet"],
                yas=kayit["yas"],
                cinsiyet=kayit["cinsiyet"],
                beklenen_triage_code=kod,
                beklenen_bolum=kayit["beklenen_bolum"],
                beklenen_tetkikler=list(kayit["beklenen_tetkikler"]),
                beklenen_kaynak=kayit.get("beklenen_kaynak"),
                kronik_hastalik=kayit.get("kronik_hastalik"),
                vitals=kayit.get("vitals"),
                ses_dosyasi=kayit.get("ses_dosyasi"),
            )
        )

    return senaryolar
