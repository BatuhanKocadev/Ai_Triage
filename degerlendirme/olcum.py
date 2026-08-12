"""Gün 23 ölçüm çekirdeği — saf fonksiyonlar.

Bu modül ağ, veritabanı ya da model görmez; girdi alır, çıktı döndürür.
Sürücü (`calistir.py`) HTTP tarafını üstlenir. Ayrım, yol haritasının
istediği birim testlerinin Ollama'sız koşabilmesi için (K6).
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# Sistemin üretebileceği ve senaryoların bekleyebileceği triyaj kodları.
# "Belirsiz" hem sistemin eşik altı yanıtı hem de kapsam dışı senaryolar için
# meşru bir beklentidir (kör set bu ihtiyacı ortaya çıkardı).
GECERLI_KODLAR = {"Kırmızı", "Sarı", "Yeşil", "Belirsiz"}

# app/api/ai.py:30-33'teki GenderEnum ile birebir eşleşmek zorunda; uca giden değer
# tam olarak bu dizelerden biri olmalı. Büyük/küçük harf normalizasyonu bilerek
# yapılmıyor: "erkek"i sessizce düzeltmek, yükleyicinin uçtan farklı bir sözleşme
# dayatması olurdu — onun yerine reddedip senaryoyu yazana doğrusunu söylüyoruz.
GECERLI_CINSIYETLER = {"Erkek", "Kadın", "Diğer"}

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

# Metin olması zorunlu alanlar; başka tipte ya da boş/yalnızca boşluk olamazlar.
ZORUNLU_METIN_ALANLARI = ("id", "cinsiyet", "beklenen_bolum")

# Verilirse metin olması gereken, verilmezse None kalabilen alanlar.
# Karar: bu alanlarda boş dize de reddediliyor. "" ile None anlamca farklı
# ("boş adlı kaynak bekle" ile "kapsam dışı"), ikisinin de geçmesi "yok" demenin
# iki yolu olması demekti; tek meşru yol None (ya da alanı hiç yazmamak).
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

    # Senaryonun benzersiz kimliği; sonuçlar ve raporlar bununla eşleştirilir.
    id: str
    # Hastanın kendi cümlesiyle şikayeti; uca symptom_text olarak gider.
    sikayet: str
    # Hastanın yaşı; uca patient_age olarak gider.
    yas: int
    # Uca gender olarak giden cinsiyet; GenderEnum ile birebir eşleşmek zorunda.
    cinsiyet: str
    # Altın standart triyaj kodu; triyaj doğruluğu buna göre ölçülür.
    beklenen_triage_code: str
    # Altın standart bölüm; bölüm doğruluğu buna göre ölçülür.
    beklenen_bolum: str
    # Altın standart tetkik listesi; Jaccard benzerliği bununla hesaplanır.
    beklenen_tetkikler: list[str]
    # Hangi protokolün gelmesi bekleniyor; None = kapsam dışı senaryo.
    beklenen_kaynak: str | None = None
    # Varsa hastanın kronik hastalığı; None = bilinen kronik hastalık yok.
    kronik_hastalik: str | None = None
    # Ölçümde yalnızca fever ve pulse kullanılıyor. Dikkat: app/api/ai.py:35'teki
    # Vitals modeli fazladan anahtarları reddetmiyor, sessizce yok sayıyor
    # (pydantic 2.13.4 varsayılanı extra="ignore"). Yani {"ates": 39} yazılırsa
    # uçtan 422 gelmez; senaryo vitals'sız koşar ve ölçülen senaryo yazılan
    # senaryo olmaz. Anahtar adları bu yüzden elle doğru yazılmak zorunda.
    vitals: dict | None = None
    # Kör senaryolarda dolu; WER yalnızca bu alanı olan senaryolarda hesaplanır.
    ses_dosyasi: str | None = None


@dataclass
class Sonuc:
    """Bir senaryonun sisteme sorulmasından dönen ham kayıt."""

    # Bu sonucun hangi senaryoya ait olduğu; Senaryo.id ile eşleşir.
    senaryo_id: str
    # Sistemin verdiği triyaj kodu; None = cevap alınamadı (bkz. hata alanı).
    cikan_triage_code: str | None = None
    # Sistemin önerdiği bölüm; None = cevap alınamadı.
    cikan_bolum: str | None = None
    # Sistemin önerdiği tetkikler; beklenen_tetkikler ile karşılaştırılır.
    cikan_tetkikler: list[str] = field(default_factory=list)
    # RAG'in döndürdüğü kaynak dosyalar; kaynak doğruluğu bununla ölçülür.
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


def _metin_degeri_dogrula(deger: object, ad: str, sira: int, *, zorunlu: bool) -> None:
    """Tek bir metin değerinin tip ve boşluk kapısı.

    Hem sözlük alanları hem `beklenen_tetkikler` elemanları buradan geçiyor;
    "boş dize gerçek bir beklenti sayılmaz" kuralı tek yerde duruyor.
    """
    if deger is None and not zorunlu:
        return
    if not isinstance(deger, str):
        raise _hata(
            sira,
            f"{ad!r} alanı metin olmalı, {type(deger).__name__} geldi",
        )
    if not deger.strip():
        # Boş dize sessizce geçerse ölçüm onu gerçek bir beklenti sanır; örneğin
        # beklenen_bolum="" her sistem cevabıyla karşılaştırılıp kalıcı sıfır yazar.
        kuyruk = "; alan yoksa None yazın" if not zorunlu else ""
        raise _hata(sira, f"{ad!r} alanı boş olamaz{kuyruk}")


def _metin_dogrula(kayit: dict, alan: str, sira: int, *, zorunlu: bool) -> None:
    """Bir alanın metin olduğunu doğrular; zorunlu değilse None'a izin verir."""
    _metin_degeri_dogrula(kayit.get(alan), alan, sira, zorunlu=zorunlu)


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

    if kayit["cinsiyet"] not in GECERLI_CINSIYETLER:
        raise _hata(
            sira,
            f"'cinsiyet' {sorted(GECERLI_CINSIYETLER)} değerlerinden biri olmalı, "
            f"{kayit['cinsiyet']!r} geldi",
        )

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
    # Elemanlar da zorunlu metin alanlarıyla aynı kapıdan geçiyor: boş bir tetkik
    # adı ("EKG", "") beklenen kümeye gerçek bir beklenti olarak girer ve Jaccard
    # oranını hiç ulaşılamayacak bir tavana çakar.
    for indeks, tetkik in enumerate(tetkikler):
        _metin_degeri_dogrula(
            tetkik, f"beklenen_tetkikler[{indeks}]", sira, zorunlu=True
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
    except UnicodeDecodeError as exc:
        # UnicodeDecodeError, JSONDecodeError'ın alt sınıfı değil; ayrıca yakalanmazsa
        # ham traceback olarak kaçar. Dosyayı Windows'ta Türkçe konuşan biri elle
        # yazacak ve cp1254 kaydedilmiş bir dosyadaki ğ/ı/ş geçerli UTF-8 değildir.
        raise SenaryoHatasi(
            f"Senaryo dosyası UTF-8 kodlamasında değil: {yol} — {exc}. "
            f"Dosyayı UTF-8 olarak kaydedin."
        ) from exc
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


def _sadelestir(metin: str) -> str:
    """Türkçe karakterleri ASCII'ye indirir ve küçük harfe çevirir.

    Yalnızca triyaj kodu ve tetkik adı karşılaştırmasında kullanılır; WER
    normalizasyonunda kullanılmaz (K12), çünkü orada katlama gerçek tanıma
    hatasını gizler. Burada katlamak doğru: ölçülen şey triyaj kalitesi, yerel
    modelin yazım tercihi değil — `app/api/ai.py` de aynı sebeple kendi
    `_sadelestir`ini taşıyor. Seste ise "şiddetli" → "siddetli" gerçek bir
    tanıma hatasıdır ve katlanırsa WER olduğundan iyi görünür.
    """
    esleme = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    sade = metin.translate(esleme)
    sade = unicodedata.normalize("NFKD", sade)
    sade = "".join(k for k in sade if not unicodedata.combining(k))
    return sade.lower().strip()


def triyaj_dogru_mu(beklenen: str, cikan: str | None) -> bool:
    """Beklenen ve çıkan triyaj kodu aynı mı — yazım farkına dayanıklı."""
    if cikan is None:
        return False
    return _sadelestir(beklenen) == _sadelestir(cikan)


def tetkik_ortusmesi(beklenen: list[str], cikan: list[str]) -> float:
    """Beklenen ve önerilen tetkik kümeleri arasındaki Jaccard benzerliği."""
    # Çıkan taraf modelin ham çıktısı, yani güvenilmeyen girdi: boş adlar
    # birleşimi şişirip skoru haksız yere düşürmesin diye burada eleniyor.
    # Beklenen tarafta boş ad zaten yükleme anında reddediliyor (yazım hatası).
    b = {_sadelestir(t) for t in beklenen if t and t.strip()}
    c = {_sadelestir(t) for t in cikan if t and t.strip()}
    if not b and not c:
        return 1.0
    if not b or not c:
        return 0.0
    return len(b & c) / len(b | c)
