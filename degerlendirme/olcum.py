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

# Metin olması zorunlu alanlar; boş ya da başka tipte olamazlar.
ZORUNLU_METIN_ALANLARI = ("id", "cinsiyet", "beklenen_bolum")

# Verilirse metin olması gereken, verilmezse None kalabilen alanlar.
ISTEGE_BAGLI_METIN_ALANLARI = ("beklenen_kaynak", "kronik_hastalik", "ses_dosyasi")

# app/api/ai.py:40 patient_age alanına ge=0 le=120 dayatıyor. Aralık dışı bir
# senaryo koşum sırasında 422 alır ve boşa gider; koşum yerel Ollama yüzünden
# dakikalar sürdüğü için geç patlamak pahalı, o yüzden burada yakalanıyor.
YAS_ALT_SINIR = 0
YAS_UST_SINIR = 120

# app/api/ai.py:42 symptom_text alanına min_length=10 max_length=500 dayatıyor.
SIKAYET_MIN_UZUNLUK = 10
SIKAYET_MAX_UZUNLUK = 500


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


def _hata(sira: int, mesaj: str) -> SenaryoHatasi:
    """Senaryo hatalarını kaçıncı kaydın bozuk olduğunu söyleyecek şekilde biçimlendirir."""
    return SenaryoHatasi(f"{sira}. kayıt: {mesaj}")


def _metin_dogrula(kayit: dict, alan: str, sira: int, *, zorunlu: bool) -> None:
    """Bir alanın metin olduğunu doğrular; zorunlu değilse None'a izin verir."""
    deger = kayit.get(alan)
    if deger is None and not zorunlu:
        return
    if not isinstance(deger, str):
        raise _hata(
            sira,
            f"{alan!r} alanı metin olmalı, {type(deger).__name__} geldi",
        )


def _kaydi_dogrula(kayit: dict, sira: int) -> None:
    """Tek bir senaryo kaydının alan tiplerini ve sınır değerlerini doğrular.

    Varlık kontrolü tek başına yetmiyor: elle yazılmış bir JSON'da
    `"beklenen_tetkikler": "EKG"` sessizce `['E','K','G']`'ye dönüşür ve Jaccard
    skoru kendinden emin ama anlamsız çıkar. Ölçüm gününün tek çıktısı o sayı.
    """
    for alan in ZORUNLU_METIN_ALANLARI:
        _metin_dogrula(kayit, alan, sira, zorunlu=True)

    for alan in ISTEGE_BAGLI_METIN_ALANLARI:
        _metin_dogrula(kayit, alan, sira, zorunlu=False)

    _metin_dogrula(kayit, "sikayet", sira, zorunlu=True)
    uzunluk = len(kayit["sikayet"])
    if not SIKAYET_MIN_UZUNLUK <= uzunluk <= SIKAYET_MAX_UZUNLUK:
        raise _hata(
            sira,
            f"'sikayet' {SIKAYET_MIN_UZUNLUK}-{SIKAYET_MAX_UZUNLUK} karakter "
            f"olmalı, {uzunluk} karakter geldi",
        )

    yas = kayit["yas"]
    # bool bir int alt sınıfıdır; True yaş olarak 1'e eşit sayılmasın diye ayrı eleniyor.
    if isinstance(yas, bool) or not isinstance(yas, int):
        raise _hata(sira, f"'yas' alanı tam sayı olmalı, {type(yas).__name__} geldi")
    if not YAS_ALT_SINIR <= yas <= YAS_UST_SINIR:
        raise _hata(
            sira,
            f"'yas' {YAS_ALT_SINIR}-{YAS_UST_SINIR} aralığında olmalı, {yas} geldi",
        )

    tetkikler = kayit["beklenen_tetkikler"]
    if not isinstance(tetkikler, list):
        raise _hata(
            sira,
            f"'beklenen_tetkikler' liste olmalı, {type(tetkikler).__name__} geldi "
            f'(tek tetkik için de ["EKG"] yazılmalı)',
        )
    for tetkik in tetkikler:
        if not isinstance(tetkik, str):
            raise _hata(
                sira,
                f"'beklenen_tetkikler' elemanları metin olmalı, "
                f"{type(tetkik).__name__} geldi",
            )

    vitals = kayit.get("vitals")
    if vitals is not None and not isinstance(vitals, dict):
        raise _hata(
            sira,
            f"'vitals' sözlük ya da None olmalı, {type(vitals).__name__} geldi",
        )


def senaryolari_yukle(yol: str | Path) -> list[Senaryo]:
    """JSON senaryo dosyasını okur ve şemayı doğrular.

    Eksik alan, hatalı alan tipi, sınır dışı yaş/şikayet uzunluğu, geçersiz
    triyaj kodu ya da tekrarlanan id durumunda `SenaryoHatasi` atar — bozuk bir
    ölçüm setiyle koşmak, ölçüm yapmamaktan daha kötüdür çünkü çıkan sayı
    güvenilir görünür.
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

        _kaydi_dogrula(kayit, sira)

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
