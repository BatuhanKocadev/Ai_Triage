"""Gün 23 ölçüm çekirdeği — saf fonksiyonlar.

Bu modül ağ, veritabanı ya da model görmez; girdi alır, çıktı döndürür.
Sürücü (`calistir.py`) HTTP tarafını üstlenir. Ayrım, yol haritasının
istediği birim testlerinin Ollama'sız koşabilmesi için (K6).
"""
from __future__ import annotations

import json
import re
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

# Ucun kaynak dizelerine taktığı önek (`app/services/rag_service.py:92`);
# `kaynak_adlarini_ayikla` dosya adını bunun ardından okur.
KAYNAK_ONEKI = "[Kaynak: "

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
    # AYIKLANMIŞ kaynak dosya adları (`["gogus_agrisi.txt"]`), ham önekli belge
    # dizeleri değil; kaynak doğruluğu ve A/B ayrımı bununla ölçülür. Sürücü bu
    # alanı uçtan gelen listeyi `kaynak_adlarini_ayikla`'dan geçirerek doldurmak
    # zorunda — ham yazılırsa beklenen kaynak hiçbir zaman bulunamaz ve ölçüm
    # sessizce her şeyi A kutusuna yazar (bkz. kaynak_adlarini_ayikla docstring'i).
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

        # Ayıklanan kaynak adları kırpılıyor; senaryo tarafı kırpılmazsa
        # `"gogus_agrisi.txt "` doğrulamayı geçer ama hiçbir zaman eşleşmez ve o
        # senaryo hata vermeden sonsuza dek A kutusunda oturur. Dosyaları Görev
        # 6'da elle yazan kişi bu boşluğu göremez.
        ham_kaynak = kayit.get("beklenen_kaynak")

        senaryolar.append(
            Senaryo(
                id=kayit["id"],
                sikayet=kayit["sikayet"],
                yas=kayit["yas"],
                cinsiyet=kayit["cinsiyet"],
                beklenen_triage_code=kod,
                beklenen_bolum=kayit["beklenen_bolum"],
                beklenen_tetkikler=list(kayit["beklenen_tetkikler"]),
                beklenen_kaynak=ham_kaynak.strip() if ham_kaynak else None,
                kronik_hastalik=kayit.get("kronik_hastalik"),
                vitals=kayit.get("vitals"),
                ses_dosyasi=kayit.get("ses_dosyasi"),
            )
        )

    return senaryolar


def _sadelestir(metin: str) -> str:
    """Türkçe karakterleri ASCII'ye indirir ve küçük harfe çevirir.

    Yalnızca triyaj kodu, bölüm adı ve tetkik adı karşılaştırmasında kullanılır;
    WER normalizasyonunda kullanılmaz (K12), çünkü orada katlama gerçek tanıma
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


def _ad_esit_mi(beklenen: str, cikan: str | None) -> bool:
    """İki adı yazım farkını katlayarak karşılaştırır; cevapsızlık asla eşleşmez."""
    if cikan is None:
        return False
    return _sadelestir(beklenen) == _sadelestir(cikan)


def triyaj_dogru_mu(beklenen: str, cikan: str | None) -> bool:
    """Beklenen ve çıkan triyaj kodu aynı mı — yazım farkına dayanıklı."""
    return _ad_esit_mi(beklenen, cikan)


def bolum_dogru_mu(beklenen: str, cikan: str | None) -> bool:
    """Beklenen ve önerilen bölüm aynı mı — yazım farkına dayanıklı.

    Ayrı bir fonksiyon çünkü `kok_neden`'in C kutusu ile Görev 5'in bölüm oranı
    tek bir tanımdan beslenmeli. Bugün gövdesi `triyaj_dogru_mu` ile aynı, o
    yüzden ikisi de `_ad_esit_mi`'ye delege ediyor: aynı karşılaştırmanın
    ikinci bir birebir kopyası, önlemek için çıkarıldığı kaymayı bir seviye
    yukarıda geri getirirdi. Bölüm bir gün eş anlamlıları ("Acil" ~ "Acil
    Servis") tanımak zorunda kalırsa delegasyon silinip gövde buraya yazılır.
    """
    return _ad_esit_mi(beklenen, cikan)


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


def kaynak_adlarini_ayikla(sources: list[str]) -> list[str]:
    """Ucun döndürdüğü `"[Kaynak: dosya] belge metni"` dizelerinden dosya adını çıkarır.

    Ölçümün en sessiz tuzağı burada: uç `sources` alanını dosya adı olarak
    döndürmüyor (`app/services/rag_service.py:92`, biçimi
    `tests/api/test_ai_analiz_api.py:73` kilitliyor). Ham dizeler ayıklanmadan
    karşılaştırılırsa `beklenen_kaynak` hiçbir zaman bulunamaz; her yanlış cevap
    A kutusuna, her doğru cevap "şanslı doğru"ya yazılır ve hiçbir test kırılmaz.
    Ayrıştırma bu yüzden sürücüde değil, testli çekirdekte duruyor (K6).

    Tanınmayan biçim atılmaz, olduğu gibi geçer: uç sözleşmesi değişirse
    eşleşmeyen bir değer görünür kalsın, sessizce boş liste üretilmesin.
    """
    adlar: list[str] = []
    for kayit in sources:
        ad = kayit
        if kayit.startswith(KAYNAK_ONEKI):
            govde = kayit[len(KAYNAK_ONEKI):]
            kapanis = govde.find("]")
            # Kapanış yoksa önek yarım kalmış demektir; uydurmak yerine ham bırakılır.
            if kapanis != -1:
                ad = govde[:kapanis].strip()
        # Aynı protokolün birden çok chunk'ı gelir; soru "hangi protokoller geldi",
        # kaç parça geldiği değil. Sıra korunuyor: ilk sıra en yüksek rerank skoru.
        if ad and ad not in adlar:
            adlar.append(ad)
    return adlar


def _gelen_kaynaklar(sonuc: Sonuc) -> list[str]:
    """Sonucun kaynaklarını her hâlükârda dosya adına indirger.

    `Sonuc.sources`'un sözleşmesi ayıklanmış dosya adları, ama ayrıştırma tek
    başına sürücüde dursaydı bir kez unutulduğunda ölçüm sessizce her şeyi A
    kutusuna yazardı ve hiçbir test kırmızıya dönmezdi. `kaynak_adlarini_ayikla`
    etkisiz eleman olduğu için burada ikinci kez çağırmak bedava.
    """
    return kaynak_adlarini_ayikla(sonuc.sources)


def kok_neden(senaryo: Senaryo, sonuc: Sonuc) -> str | None:
    """Bir sonucu A (retrieval) / B (muhakeme) / C (biçim) kutusuna ayırır.

    Gün 24 "en büyük kutuya müdahale et" diyor; bu tasnif ölçülmezse o karar
    tahminle verilir. Doğru sonuçta None döner, altyapı hatasında "HATA".

    Kapsam dışı senaryolar (`beklenen_triage_code == "Belirsiz"`) doğru
    reddedildiğinde `beklenen_bolum` ve `beklenen_tetkikler` **puanlanmaz**:
    cevap vermeyi reddetmiş bir sistemde derecelendirilecek bölüm ya da tetkik
    yoktur, onları puanlamak kategori hatası olur. Alanlar yükleyicide zorunlu
    olmaya devam ediyor, yalnızca bu şekilde ölçüme girmiyorlar.
    """
    if sonuc.hata:
        return "HATA"

    kod_dogru = triyaj_dogru_mu(senaryo.beklenen_triage_code, sonuc.cikan_triage_code)

    if not kod_dogru:
        # Kapsam dışı senaryoda cevap üretmek, eşiğin fazla geçirgen olmasıdır.
        if senaryo.beklenen_triage_code == "Belirsiz":
            return "A"
        # Eşik altında kalmak retrieval başarısızlığıdır (K8).
        if sonuc.cikan_triage_code == "Belirsiz":
            return "A"
        # Beklenen protokol aday havuzuna hiç girmediyse hata retrieval'dadır.
        beklenen_kaynak = senaryo.beklenen_kaynak
        if beklenen_kaynak and beklenen_kaynak not in _gelen_kaynaklar(sonuc):
            return "A"
        return "B"

    # Kapsam dışı senaryo doğru reddedilmiş: puanlanacak bölüm/tetkik yok.
    if senaryo.beklenen_triage_code == "Belirsiz":
        return None

    # Kod doğru: bölüm ya da tetkikler tutmuyorsa biçim/kapsam hatası.
    bolum_dogru = bolum_dogru_mu(senaryo.beklenen_bolum, sonuc.cikan_bolum)
    tetkikler_tam = tetkik_ortusmesi(
        senaryo.beklenen_tetkikler, sonuc.cikan_tetkikler
    ) == 1.0
    if not bolum_dogru or not tetkikler_tam:
        return "C"

    return None


def sansli_dogru_mu(senaryo: Senaryo, sonuc: Sonuc) -> bool:
    """Doğru cevap verildiği hâlde beklenen protokolün gelmediği durum.

    Model cevabı yanlış bağlamdan ya da kendi ön bilgisinden üretmiştir;
    Gün 24'te retrieval düzeltilince bu senaryolar bozulabilir. İşaretlenmezse
    önce/sonra tablosunda açıklanamayan bir gerileme olarak görünür.
    """
    if sonuc.hata or not senaryo.beklenen_kaynak:
        return False
    if not triyaj_dogru_mu(senaryo.beklenen_triage_code, sonuc.cikan_triage_code):
        return False
    return senaryo.beklenen_kaynak not in _gelen_kaynaklar(sonuc)


def _kelimelere_ayir(metin: str) -> list[str]:
    """WER için metni normalize edip kelimelere böler.

    Küçük harfe indirir ve noktalamayı atar; Türkçe karakteri ASCII'ye
    KATLAMAZ (K12) — katlarsak "şiddetli" → "siddetli" tanıma hatası doğru
    sayılır ve WER olduğundan iyi çıkar. Bu yüzden aynı modüldeki
    `_sadelestir` buradan ÇAĞRILMAZ; o fonksiyon triyaj/bölüm/tetkik adı
    karşılaştırması içindir.

    Küçük harfe indirmeden önce yalnızca noktalı/noktasız I çifti eşleniyor,
    çünkü Python'un `.lower()`'ı Türkçe bilmez: "I" → "i" verir ("ı" değil) ve
    "İ" → "i" + birleşen nokta (iki karakter) verir. Bu bir BÜYÜK/KÜÇÜK HARF
    düzeltmesidir, harf katlaması değil — "I" ile "ı" aynı harfin iki hâli,
    "ş" ile "s" ise ayrı harflerdir ve ikincisi katlanmaz (K12). Eşleme
    olmasaydı cümle başındaki "Işığa", tanıma doğruyken bile hata sayılırdı ve
    WER olduğundan kötü çıkardı.
    """
    esleme = str.maketrans("Iİ", "ıi")
    temiz = re.sub(r"[^\w\s]", " ", metin, flags=re.UNICODE)
    return temiz.translate(esleme).lower().split()


def wer(referans: str, hipotez: str) -> float:
    """Kelime hata oranı: düzenleme mesafesi / referans kelime sayısı.

    Standart Levenshtein, kelime düzeyinde. Yeni bağımlılık eklememek için
    elle yazıldı (K11): `jiwer` iki gereksinim dosyasını birden güncellemeyi
    gerektirir ve ölçüm gününde gereksiz bir CI riski yaratır.

    Ekleme cezalandırıldığı için sonuç 1.0'ı aşabilir; oran kırpılmıyor,
    uydurma bir transkript uzunluğu oranında görünür kalsın.
    """
    ref = _kelimelere_ayir(referans)
    hip = _kelimelere_ayir(hipotez)

    if not ref:
        # Referans yoksa bölünecek kelime de yok: hipotez de boşsa hata yok,
        # doluysa tamamı fazlalık sayılıp tam hata (1.0) yazılıyor.
        return 0.0 if not hip else 1.0

    onceki_satir = list(range(len(hip) + 1))
    for i in range(1, len(ref) + 1):
        simdiki_satir = [i] + [0] * len(hip)
        for j in range(1, len(hip) + 1):
            maliyet = 0 if ref[i - 1] == hip[j - 1] else 1
            simdiki_satir[j] = min(
                onceki_satir[j] + 1,           # silme
                simdiki_satir[j - 1] + 1,      # ekleme
                onceki_satir[j - 1] + maliyet, # değiştirme
            )
        onceki_satir = simdiki_satir

    return onceki_satir[len(hip)] / len(ref)


@dataclass
class Ozet:
    """Bir koşumun bütün raporlanan sayıları — rapor tablosu buradan basılır."""

    # Kapsam içi ∧ ölçülebilir senaryo sayısı; iki doğruluk oranının da temeli.
    toplam: int
    # Bu paydada triyaj kodu tutan senaryo sayısı.
    dogru: int
    # dogru / toplam — eşik altı yanıtlar paydada KALIR.
    dogruluk_tum: float
    # dogru / cevap verilenler — eşik altı yanıtlar paydadan DÜŞÜLÜR. İki oran
    # birlikte basılır: tek sayı olsaydı "Belirsiz"leri paydadan atmak doğruluğu
    # istendiği kadar şişirebilirdi, aradaki fark ise eşik altı oranının kendisidir.
    dogruluk_cevaplananlar: float
    # Kapsam içi ∧ ölçülebilir Kırmızı senaryo sayısı (duyarlılığın paydası).
    kirmizi_toplam: int
    # Bunlardan gerçekten Kırmızı olarak işaretlenenler.
    kirmizi_yakalanan: int
    # kirmizi_yakalanan / kirmizi_toplam — raporun klinik olarak en kritik sayısı.
    kirmizi_duyarlilik: float
    # Sistemin "Belirsiz" dediği kapsam içi senaryo sayısı (cevapsızlık, yanlışlık değil).
    esik_alti: int
    # esik_alti / toplam — iki doğruluk sayısı arasındaki farkın sebebi.
    esik_alti_orani: float
    # Cevap verilen kapsam içi senaryolarda tetkik örtüşmesinin (Jaccard) ortalaması.
    jaccard_ortalama: float
    # Yanlışların A (retrieval) / B (muhakeme) / C (biçim) sayıları; Gün 24 hedefi.
    kok_neden_dagilimi: dict[str, int]
    # Doğru cevap verilmiş ama beklenen protokol hiç gelmemiş senaryo sayısı.
    sansli_dogru: int
    # Altyapı hatası yüzünden hiçbir paydaya girmeyen senaryo sayısı.
    olculemedi: int
    # Beklentisi "Belirsiz" olan (kapsam dışı) ölçülebilir senaryo sayısı.
    kapsam_disi_toplam: int
    # Bunlardan doğru şekilde reddedilenler; doğruluk oranlarına KARIŞMAZ.
    kapsam_disi_dogru: int


def _oran(pay: int, payda: int) -> float:
    """Sıfıra bölmeyi 0.0'a çeviren yardımcı — boş kümede oran tanımsızdır."""
    return pay / payda if payda else 0.0


def ozet(senaryolar: list[Senaryo], sonuclar: list[Sonuc]) -> Ozet:
    """Senaryo ve sonuç listelerinden raporlanan bütün sayıları üretir."""
    sonuc_haritasi = {s.senaryo_id: s for s in sonuclar}

    kapsam_ici: list[tuple[Senaryo, Sonuc]] = []
    kapsam_disi: list[tuple[Senaryo, Sonuc]] = []
    olculemedi = 0

    for senaryo in senaryolar:
        sonuc = sonuc_haritasi.get(senaryo.id)
        if sonuc is None:
            continue
        if sonuc.hata:
            olculemedi += 1
            continue
        if senaryo.beklenen_triage_code == "Belirsiz":
            kapsam_disi.append((senaryo, sonuc))
        else:
            kapsam_ici.append((senaryo, sonuc))

    dogru = sum(
        1
        for s, r in kapsam_ici
        if triyaj_dogru_mu(s.beklenen_triage_code, r.cikan_triage_code)
    )
    esik_alti = sum(1 for _, r in kapsam_ici if r.cikan_triage_code == "Belirsiz")
    cevaplanan = len(kapsam_ici) - esik_alti

    kirmizi = [
        (s, r) for s, r in kapsam_ici if _sadelestir(s.beklenen_triage_code) == "kirmizi"
    ]
    kirmizi_yakalanan = sum(
        1 for s, r in kirmizi if triyaj_dogru_mu(s.beklenen_triage_code, r.cikan_triage_code)
    )

    # Jaccard yalnızca cevap verilen senaryolarda anlamlı; "Belirsiz" yanıtta
    # tetkik listesi zaten boş döner ve ortalamayı haksız yere aşağı çeker.
    # Kaynak `kapsam_ici`: kapsam dışı senaryolar `kok_neden`de de puanlanmıyor
    # (cevap vermeyi reddetmiş sistemde derecelendirilecek tetkik yoktur), buraya
    # girselerdi özet ile A/B/C tasnifi birbiriyle çelişirdi.
    jaccardlar = [
        tetkik_ortusmesi(s.beklenen_tetkikler, r.cikan_tetkikler)
        for s, r in kapsam_ici
        if r.cikan_triage_code != "Belirsiz"
    ]

    dagilim: dict[str, int] = {"A": 0, "B": 0, "C": 0}
    sansli = 0
    for s, r in kapsam_ici + kapsam_disi:
        kutu = kok_neden(s, r)
        if kutu in dagilim:
            dagilim[kutu] += 1
        if sansli_dogru_mu(s, r):
            sansli += 1

    return Ozet(
        toplam=len(kapsam_ici),
        dogru=dogru,
        dogruluk_tum=_oran(dogru, len(kapsam_ici)),
        dogruluk_cevaplananlar=_oran(dogru, cevaplanan),
        kirmizi_toplam=len(kirmizi),
        kirmizi_yakalanan=kirmizi_yakalanan,
        kirmizi_duyarlilik=_oran(kirmizi_yakalanan, len(kirmizi)),
        esik_alti=esik_alti,
        esik_alti_orani=_oran(esik_alti, len(kapsam_ici)),
        jaccard_ortalama=(sum(jaccardlar) / len(jaccardlar)) if jaccardlar else 0.0,
        kok_neden_dagilimi=dagilim,
        sansli_dogru=sansli,
        olculemedi=olculemedi,
        kapsam_disi_toplam=len(kapsam_disi),
        kapsam_disi_dogru=sum(
            1
            for s, r in kapsam_disi
            if triyaj_dogru_mu(s.beklenen_triage_code, r.cikan_triage_code)
        ),
    )
