# Gün 23 — Değerlendirme Seti ve Doğruluk Ölçümü Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sistemin triyaj doğruluğunu, Kırmızı duyarlılığını, eşik altı oranını ve ses tanıma WER'ini ölçen; yanlışları otomatik olarak retrieval / muhakeme / biçim kutularına ayıran bir ölçüm aracı kurmak ve bir kez koşmak.

**Architecture:** `degerlendirme/` paketi iki parçadır. `olcum.py` ağ ve model görmeyen **saf** fonksiyonlar taşır ve birim testleri yalnızca ona bakar. `calistir.py` sürücüdür: HTTP ile `/ai/analiz` ve `/speech/transkript` uçlarını çağırır, `olcum.py`'yi kullanır, rapor yazar. Paket `app`'i **hiç import etmez**.

**Tech Stack:** Python 3.11, pytest, `requests`, standart kütüphane (yeni bağımlılık yok).

**Spec:** `docs/superpowers/specs/2026-08-12-gun23-degerlendirme-design.md` (K1–K15)

## Global Constraints

- **`app/` altında hiçbir dosya değişmez.** Bu bir ölçüm günüdür, düzeltme günü değil (K1). `top_k_initial`, `rerank_threshold` (0.005), protokol metinleri ve mevcut 157 testin hiçbiri değişmez.
- **`degerlendirme/` paketi `app`'i import etmez** (K5). Yalnızca `requests` ve standart kütüphane.
- **Yeni bağımlılık eklenmez** (K11). `requirements.txt` ve `requirements-ci.txt` değişmez; `tests/birim/test_ci_gereksinimleri.py` pariteyi dayatıyor.
- **Odaklı test koşularında `--no-cov` zorunlu.** `pytest.ini`'deki `--cov-fail-under=87` her koşuya uygulanıyor; onsuz paket sahte kırmızı verir.
- **`--cov=app` değişmez** (K13). `degerlendirme/` kapsama ölçümünün dışındadır.
- **TDD zorunlu.** Her adımda önce test yazılır, kırmızı görüldüğü rapor edilir, sonra üretim kodu yazılır.
- **Türkçe yorum kuralı:** eklenen her yeni fonksiyon/alanın yanına tek cümlelik Türkçe açıklama.
- Test dosyası: `tests/birim/test_degerlendirme_araci.py` (tek dosya, tüm birim testleri).

## Dosya yapısı

| Dosya | Sorumluluk |
|---|---|
| `degerlendirme/__init__.py` | Paket işareti (boş) |
| `degerlendirme/olcum.py` | Saf ölçüm: veri sınıfları, yükleyici, karşılaştırma, WER, özet |
| `degerlendirme/calistir.py` | Sürücü: ön uçuş, HTTP, 429 yönetimi, kısmi kayıt, raporlama |
| `degerlendirme/kor_senaryolar.json` | Kullanıcının yazdığı 8-9 kör senaryo |
| `degerlendirme/senaryolar.json` | Uygulayıcının protokollerden türettiği ~18 senaryo |
| `degerlendirme/few_shot_havuzu.json` | 3-5 örnek — asla ölçülmez (K4) |
| `degerlendirme/sonuclar/` | `YYYY-AA-GG.md` ve `YYYY-AA-GG.json` |
| `tests/birim/test_degerlendirme_araci.py` | 8 birim testi |

---

### Task 1: Paket iskeleti ve senaryo yükleyici

**Files:**
- Create: `degerlendirme/__init__.py`
- Create: `degerlendirme/olcum.py`
- Create: `tests/birim/test_degerlendirme_araci.py`

**Interfaces:**
- Consumes: —
- Produces: `Senaryo` (frozen dataclass), `Sonuc` (dataclass), `GECERLI_KODLAR: set[str]`, `senaryolari_yukle(yol: str | Path) -> list[Senaryo]`, `SenaryoHatasi(Exception)`

Bu görev spec'in "Riskler" bölümündeki `sys.path` varsayımını da doğruluyor: `tests/` altında `__init__.py` olduğu için pytest depo kökünü `sys.path`'e ekler ve `import degerlendirme.olcum` çalışmalıdır. Adım 2 bunu kanıtlıyor; çalışmazsa çözüm `pytest.ini`'ye `pythonpath = .` eklemektir.

- [ ] **Step 1: Write the failing test**

`tests/birim/test_degerlendirme_araci.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'degerlendirme'`

Bu hata `degerlendirme/` paketi henüz yok demektir, beklenen budur. Eğer paket oluşturulduktan sonra da aynı hatayı verirse `sys.path` varsayımı yanlış demektir — o zaman `pytest.ini`'nin `[pytest]` bölümüne `pythonpath = .` satırı eklenir ve bu plan notu güncellenir.

- [ ] **Step 3: Write minimal implementation**

`degerlendirme/__init__.py` — boş dosya.

`degerlendirme/olcum.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add degerlendirme/__init__.py degerlendirme/olcum.py tests/birim/test_degerlendirme_araci.py
git commit -m "feat: degerlendirme paketi ve senaryo yukleyici (5 test)"
```

---

### Task 2: Triyaj doğruluğu ve tetkik örtüşmesi

**Files:**
- Modify: `degerlendirme/olcum.py`
- Modify: `tests/birim/test_degerlendirme_araci.py`

**Interfaces:**
- Consumes: `Senaryo`, `Sonuc` (Task 1)
- Produces: `triyaj_dogru_mu(beklenen: str, cikan: str | None) -> bool`, `tetkik_ortusmesi(beklenen: list[str], cikan: list[str]) -> float`

Tetkik karşılaştırmasında Türkçe karakter **ASCII'ye katlanır** ("Tam Kan Sayımı" ≈ "Tam kan sayimi"). Bu, K12'nin WER kuralıyla çelişmez: K12 ses tanıma hatasını gizlememek için katlamayı yasaklıyor; burada ölçülen şey triyaj kalitesi, yerel modelin yazım tercihi değil. `app/api/ai.py` zaten aynı sebeple `_sadelestir` taşıyor.

- [ ] **Step 1: Write the failing test**

`tests/birim/test_degerlendirme_araci.py` dosyasının import satırına `tetkik_ortusmesi` ve `triyaj_dogru_mu` eklenir, sonra:

```python
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
    assert tetkik_ortusmesi(
        ["Tam Kan Sayımı"], ["tam kan sayimi"]
    ) == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: FAIL — `ImportError: cannot import name 'triyaj_dogru_mu'`

- [ ] **Step 3: Write minimal implementation**

`degerlendirme/olcum.py`'ye eklenir (import bloğuna `import unicodedata` ekle):

```python
def _sadelestir(metin: str) -> str:
    """Türkçe karakterleri ASCII'ye indirir ve küçük harfe çevirir.

    Yalnızca triyaj kodu ve tetkik adı karşılaştırmasında kullanılır; WER
    normalizasyonunda kullanılmaz (K12), çünkü orada katlama gerçek tanıma
    hatasını gizler.
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
    b = {_sadelestir(t) for t in beklenen if t and t.strip()}
    c = {_sadelestir(t) for t in cikan if t and t.strip()}
    if not b and not c:
        return 1.0
    if not b or not c:
        return 0.0
    return len(b & c) / len(b | c)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add degerlendirme/olcum.py tests/birim/test_degerlendirme_araci.py
git commit -m "feat: triyaj karsilastirmasi ve tetkik Jaccard olcumu (10 test)"
```

---

### Task 3: Kök neden tasnifi

**Files:**
- Modify: `degerlendirme/olcum.py`
- Modify: `tests/birim/test_degerlendirme_araci.py`

**Interfaces:**
- Consumes: `Senaryo`, `Sonuc`, `triyaj_dogru_mu`, `tetkik_ortusmesi`
- Produces: `kok_neden(senaryo: Senaryo, sonuc: Sonuc) -> str | None`, `sansli_dogru_mu(senaryo: Senaryo, sonuc: Sonuc) -> bool`

Tasnif kuralı (spec K9):

| Dönüş | Koşul |
|---|---|
| `"HATA"` | `sonuc.hata` dolu — altyapı hatası, model hatası sayılmaz |
| `"A"` | Kod yanlış **ve** (beklenti "Belirsiz" iken sistem cevap verdi **veya** sistem "Belirsiz" dedi **veya** `beklenen_kaynak` `sources` içinde yok) |
| `"B"` | Kod yanlış, doğru protokol gelmiş — muhakeme hatası |
| `"C"` | Kod **doğru** ama bölüm yanlış ya da tetkik örtüşmesi tam değil |
| `None` | Her şey doğru |

`"C"` doğru cevaplarla birlikte görünür; yani A+B yanlış sayısını, C ise "doğru ama eksik" sayısını verir. Bu ayrım yol haritasının Gün 24 tanımıyla birebir aynı.

- [ ] **Step 1: Write the failing test**

Import satırına `kok_neden`, `sansli_dogru_mu`, `Sonuc` eklenir, sonra:

```python
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
    """Eşik altında kalmak, retrieval'ın başarısız olmasının başka adıdır (K8)."""
    senaryo = _senaryo()
    esik_alti = Sonuc(senaryo_id="t01", cikan_triage_code="Belirsiz", sources=[])

    assert kok_neden(senaryo, esik_alti) == "A"


def test_altyapi_hatasi_model_hatasi_sayilmaz():
    senaryo = _senaryo()
    hatali = Sonuc(senaryo_id="t01", hata="timeout")

    assert kok_neden(senaryo, hatali) == "HATA"


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: FAIL — `ImportError: cannot import name 'kok_neden'`

- [ ] **Step 3: Write minimal implementation**

```python
def kok_neden(senaryo: Senaryo, sonuc: Sonuc) -> str | None:
    """Bir sonucu A (retrieval) / B (muhakeme) / C (biçim) kutusuna ayırır.

    Gün 24 "en büyük kutuya müdahale et" diyor; bu tasnif ölçülmezse o karar
    tahminle verilir. Doğru sonuçta None döner, altyapı hatasında "HATA".
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
        if senaryo.beklenen_kaynak and senaryo.beklenen_kaynak not in sonuc.sources:
            return "A"
        return "B"

    # Kod doğru: bölüm ya da tetkikler tutmuyorsa biçim/kapsam hatası.
    bolum_dogru = _sadelestir(senaryo.beklenen_bolum) == _sadelestir(
        sonuc.cikan_bolum or ""
    )
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
    return senaryo.beklenen_kaynak not in sonuc.sources
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add degerlendirme/olcum.py tests/birim/test_degerlendirme_araci.py
git commit -m "feat: kok neden tasnifi A/B/C ve sansli dogru isareti (15 test)"
```

---

### Task 4: WER hesaplama

**Files:**
- Modify: `degerlendirme/olcum.py`
- Modify: `tests/birim/test_degerlendirme_araci.py`

**Interfaces:**
- Consumes: —
- Produces: `wer(referans: str, hipotez: str) -> float`

Yeni bağımlılık yok (K11). Normalizasyon küçük harf + noktalama temizliği; **Türkçe karakter katlanmaz** (K12).

- [ ] **Step 1: Write the failing test**

Import satırına `wer` eklenir, sonra:

```python
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


def test_wer_bos_referans():
    assert wer("", "") == 0.0
    assert wer("", "bir şey") == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: FAIL — `ImportError: cannot import name 'wer'`

- [ ] **Step 3: Write minimal implementation**

`import re` eklenir, sonra:

```python
def _kelimelere_ayir(metin: str) -> list[str]:
    """WER için metni normalize edip kelimelere böler.

    Küçük harfe indirir ve noktalamayı atar; Türkçe karakteri ASCII'ye
    KATLAMAZ (K12) — katlarsak "şiddetli" → "siddetli" tanıma hatası doğru
    sayılır ve WER olduğundan iyi çıkar. Küçük harfe indirme Python'un
    Türkçe'ye özgü olmayan kuralıyla yapılıyor; referans ve hipotez aynı
    işlemden geçtiği için karşılaştırma tutarlı kalır.
    """
    temiz = re.sub(r"[^\w\s]", " ", metin, flags=re.UNICODE)
    return temiz.lower().split()


def wer(referans: str, hipotez: str) -> float:
    """Kelime hata oranı: düzenleme mesafesi / referans kelime sayısı.

    Standart Levenshtein, kelime düzeyinde. Yeni bağımlılık eklememek için
    elle yazıldı (K11): `jiwer` iki gereksinim dosyasını birden güncellemeyi
    gerektirir ve ölçüm gününde gereksiz bir CI riski yaratır.
    """
    ref = _kelimelere_ayir(referans)
    hip = _kelimelere_ayir(hipotez)

    if not ref:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
git add degerlendirme/olcum.py tests/birim/test_degerlendirme_araci.py
git commit -m "feat: bagimliliksiz WER hesaplamasi (19 test)"
```

---

### Task 5: Özet — raporlanan bütün sayılar

**Files:**
- Modify: `degerlendirme/olcum.py`
- Modify: `tests/birim/test_degerlendirme_araci.py`

**Interfaces:**
- Consumes: hepsi (Task 1-4)
- Produces: `Ozet` (dataclass), `ozet(senaryolar: list[Senaryo], sonuclar: list[Sonuc]) -> Ozet`

Payda kuralları — bunlar spec'in K7 kararının somut hâli:

- `kapsam_ici` = `beklenen_triage_code != "Belirsiz"` olan senaryolar
- `olculebilir` = `sonuc.hata is None` olanlar
- `dogruluk_tum` paydası = kapsam içi ∧ ölçülebilir senaryolar
- `dogruluk_cevaplananlar` paydası = aynı küme, eksi sistemin "Belirsiz" dedikleri
- Kapsam dışı senaryolar **iki doğruluk sayısının hiçbirine girmez**; kendi çiftiyle raporlanır. Gerekçe: "doğru şekilde cevap vermedi" ile "doğru triyaj etti" aynı kovaya konursa iki sayı da okunamaz hâle gelir.

- [ ] **Step 1: Write the failing test**

Import satırına `Ozet`, `ozet` eklenir, sonra:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: FAIL — `ImportError: cannot import name 'ozet'`

- [ ] **Step 3: Write minimal implementation**

```python
@dataclass
class Ozet:
    """Bir koşumun bütün raporlanan sayıları — rapor tablosu buradan basılır."""

    toplam: int
    dogru: int
    dogruluk_tum: float
    dogruluk_cevaplananlar: float
    kirmizi_toplam: int
    kirmizi_yakalanan: int
    kirmizi_duyarlilik: float
    esik_alti: int
    esik_alti_orani: float
    jaccard_ortalama: float
    kok_neden_dagilimi: dict[str, int]
    sansli_dogru: int
    olculemedi: int
    kapsam_disi_toplam: int
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: 23 passed

- [ ] **Step 5: Commit**

```bash
git add degerlendirme/olcum.py tests/birim/test_degerlendirme_araci.py
git commit -m "feat: ozet - dogruluk, kirmizi duyarlilik, esik alti, kok neden dagilimi (23 test)"
```

---

### Task 6: Senaryo verisi ve sızıntı kapısı

**Files:**
- Create: `degerlendirme/kor_senaryolar.json`
- Create: `degerlendirme/senaryolar.json`
- Create: `degerlendirme/few_shot_havuzu.json`
- Modify: `tests/birim/test_degerlendirme_araci.py`

**Interfaces:**
- Consumes: `senaryolari_yukle` (Task 1)
- Produces: üç JSON veri dosyası

Bu görev kod değil **veri** üretiyor, ama sızıntı kuralı testle bağlanıyor (K4).

**Kör senaryolar** `degerlendirme/KOR_SENARYOLAR_SEN_DOLDUR.md` dosyasındaki metinlerden birebir kopyalanır — **metin değiştirilmez, düzeltilmez, kısaltılmaz.** Kullanıcının yazdığı hâli ölçümün girdisidir; "iyileştirmek" körlüğü yok eder. Etiketler (`beklenen_*`) uygulayıcı tarafından **protokol dosyaları okunarak** atanır (K3).

**Etiketleme yordamı — her senaryo için sırayla:**

1. `ornek_dokumanlar/protokoller/` altındaki ilgili protokolü aç.
2. Şikayetteki bulguları protokolün akuite kriterleriyle eşleştir.
3. `beklenen_triage_code`'u o kritere dayanarak ata; **hangi satıra dayandığını** senaryonun `gerekce` alanına yaz (şemada isteğe bağlı, yalnızca insan için).
4. `beklenen_bolum` ve `beklenen_tetkikler`'i aynı protokolden al.
5. Şikayet hiçbir protokolün kriterlerine oturmuyorsa `beklenen_triage_code: "Belirsiz"` ve `beklenen_kaynak: null` ata — sistemin cevap vermemesi doğru davranıştır.

**Kör senaryo şikayet metinleri** (şablondan, değiştirilmeden):

| id | Şikayet | Ses |
|---|---|---|
| `kor_01` | Sabah kalktığımdan beri başımın sağ tarafı felaket zonkluyor. Ağrısı resmen gözüme vuruyor. Işığa falan hiç bakamıyorum, midem kalkıyor. | `ses/kor_01.m4a` |
| `kor_02` | Merdivenden inerken ayağım burkuldu. Bileğim inanılmaz şişti, üstüne kesinlikle basamıyorum. Durduğu yerde zonkluyor resmen. | `ses/kor_02.m4a` |
| `kor_03` | Dünden beri karnıma kramplar giriyor. Midem sürekli bulanıyor, ağzıma bir lokma bir şey koyamadım. Biraz da ateşim çıktı galiba. | `ses/kor_03.m4a` |
| `kor_04` | Üç gündür geçmeyen bir öksürüğüm var. Yutkunurken boğazım jilet gibi kesiliyor. Bir de derin nefes almaya çalışırken sırtıma garip bir ağrı saplanıyor. | `ses/kor_04.m4a` |
| `kor_05` | Çay demlerken kaynar su elime döküldü. Bileğime kadar kıpkırmızı oldu, şimdiden su toplamaya başladı. Acısından yerimde duramıyorum. | `ses/kor_05.m4a` |
| `kor_06` | Dün akşam dışarıda bir şeyler yemiştim, sabahtan beri her yerim deliler gibi kaşınıyor. Kollarımda kırmızı kırmızı lekeler çıktı, yüzüm de hafiften şişmeye başladı. | `ses/kor_06.m4a` |
| `kor_07` | İki gündür idrara çıkarken çok fena yanmam oluyor. Belimin sağ tarafına, boşluğuma doğru da öyle bir ağrı vuruyor ki nefesimi kesiyor. | `ses/kor_07.m4a` |
| `kor_08` | Kaç gündür üstümde bir kırgınlık var, bütün eklemlerim sızlıyor. Sürekli üşüyorum, ara ara titreme geliyor ama alnım da yanıyor sanki. | `ses/kor_08.m4a` |
| `kor_09` | Dün akşam yanlış ilaç içmişim bu yüzden kendimi iyi hissetmiyorum | `ses/kor_09.m4a` |

**`kor_09` bilerek zor bir vakadır ve metni değiştirilmeyecek.** İlaç adı, miktar ve belirti içermiyor; yalnızca "yanlış ilaç" ve "iyi hissetmiyorum" var. Gerçek bir hasta telefonda tam olarak böyle konuşur ve retrieval'ın en zorlandığı girdi budur. Etiketlenirken `zehirlenme.txt`'nin **bilinmeyen madde / miktar bilinmiyor** dalına bakılmalı; protokol böyle bir dal tanımlamıyorsa `beklenen_triage_code: "Belirsiz"` meşru bir etikettir ve gerekçesi `gerekce` alanına yazılır. Senaryoyu "ölçülebilir olsun diye" zenginleştirmek körlüğü yok eder.

Yaş ve cinsiyet kullanıcı tarafından verilmemiş; uygulayıcı şikayetle tutarlı, sıradan değerler atar (ör. `kor_01` için 34/Kadın). Vitals bilgisi şikayette yoksa `null` bırakılır — uydurulan bir nabız değeri ölçüme girmeyen bir değişken ekler.

**Türetilmiş set** ~18 senaryo, 15 protokolün tamamını kapsayacak biçimde. Zehirlenme, yanık ve inme mutlaka bulunur. Bunlar protokoller okunarak yazılır; `kaynak` alanı hangi protokolden türediklerini gösterir.

**Few-shot havuzu** 3-5 örnek: kısa şikayet → beklenen JSON çıktı. Ölçüm setinden **hiçbir senaryo** buraya kopyalanmaz.

Örnek kayıt (`kor_05` için, etiketler `yanik.txt` okunarak atanmış olacak):

```json
{
  "id": "kor_05",
  "sikayet": "Çay demlerken kaynar su elime döküldü. Bileğime kadar kıpkırmızı oldu, şimdiden su toplamaya başladı. Acısından yerimde duramıyorum.",
  "yas": 41,
  "cinsiyet": "Kadın",
  "kronik_hastalik": null,
  "vitals": null,
  "beklenen_triage_code": "Sarı",
  "beklenen_bolum": "Acil Servis",
  "beklenen_tetkikler": ["Yanık alanı değerlendirmesi"],
  "beklenen_kaynak": "yanik.txt",
  "ses_dosyasi": "ses/kor_05.m4a",
  "gerekce": "yanik.txt: ikinci derece, TVYA <%10, ekstremite — Sarı"
}
```

Few-shot havuzu kaydı (ölçüm setinde bulunmayan bir konu):

```json
{
  "id": "fs_01",
  "sikayet": "arı soktu, kolum şişti ama nefesim rahat",
  "beklenen_cikti": {
    "triage_code": "Yeşil",
    "department": "Acil Servis",
    "onerilen_tetkikler": []
  }
}
```

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

DEGERLENDIRME = Path(__file__).resolve().parents[2] / "degerlendirme"


def test_senaryo_dosyalari_semaya_uyar():
    """Üç veri dosyasının ikisi ölçüm setidir ve şemaya uymak zorundadır."""
    kor = senaryolari_yukle(DEGERLENDIRME / "kor_senaryolar.json")
    turetilmis = senaryolari_yukle(DEGERLENDIRME / "senaryolar.json")

    assert len(kor) >= 8
    assert len(turetilmis) >= 15
    # Yol haritası 20-30 senaryo istiyor.
    assert len(kor) + len(turetilmis) >= 20
    # Kör senaryoların hepsinin ses dosyası olmalı — WER onlardan hesaplanıyor.
    assert all(s.ses_dosyasi for s in kor)


def test_few_shot_havuzu_olcum_setiyle_kesismiyor():
    """Sızıntı kuralı (K4): ölçüm setindeki hiçbir senaryo prompt'a örnek olamaz.

    Kural yorumla değil testle dayatılıyor; Gün 21'in dersi, kodun işlediği
    kuraldan başka bir şey anlatan yorumun sonradan yanlış ayarlandığıydı.
    """
    import json

    kor = senaryolari_yukle(DEGERLENDIRME / "kor_senaryolar.json")
    turetilmis = senaryolari_yukle(DEGERLENDIRME / "senaryolar.json")
    havuz = json.loads(
        (DEGERLENDIRME / "few_shot_havuzu.json").read_text(encoding="utf-8")
    )

    olcum_metinleri = {_sadelestir(s.sikayet) for s in kor + turetilmis}
    havuz_metinleri = {_sadelestir(k["sikayet"]) for k in havuz}

    assert olcum_metinleri & havuz_metinleri == set()

    olcum_idleri = {s.id for s in kor + turetilmis}
    havuz_idleri = {k["id"] for k in havuz}
    assert olcum_idleri & havuz_idleri == set()


def test_kor_ve_turetilmis_setler_ayri_dosyada():
    """K2: iki setin sayıları ayrı raporlanabilsin diye fiziksel ayrım şart."""
    kor = senaryolari_yukle(DEGERLENDIRME / "kor_senaryolar.json")
    turetilmis = senaryolari_yukle(DEGERLENDIRME / "senaryolar.json")

    assert {s.id for s in kor} & {s.id for s in turetilmis} == set()
    assert all(s.id.startswith("kor_") for s in kor)
```

Test dosyasının import satırına `_sadelestir` eklenir.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: FAIL — `SenaryoHatasi: Senaryo dosyası bulunamadı`

- [ ] **Step 3: Write the data files**

Yukarıdaki yordamı izleyerek üç JSON dosyasını yaz. Protokolleri **oku** ve her etiketi bir kritere dayandır.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: 26 passed

- [ ] **Step 5: Commit**

```bash
git add degerlendirme/*.json degerlendirme/KOR_SENARYOLAR_SEN_DOLDUR.md tests/birim/test_degerlendirme_araci.py
git commit -m "feat: kor + turetilmis olcum setleri ve sizinti kapisi (26 test)"
```

---

### Task 7: Koşum sürücüsü

**Files:**
- Create: `degerlendirme/calistir.py`

**Interfaces:**
- Consumes: `olcum.py`'nin tamamı
- Produces: çalıştırılabilir script; `degerlendirme/sonuclar/YYYY-AA-GG.{md,json}` üretir

Sürücü birim testi almıyor (K6) — saf olmayan tek parça budur ve doğrulaması Task 8'deki gerçek koşumdur.

- [ ] **Step 1: Write the driver**

`degerlendirme/calistir.py`:

```python
"""Gün 23 ölçüm sürücüsü.

Senaryoları gerçek HTTP uçlarına gönderir, sonuçları `olcum.py` ile
değerlendirir ve `sonuclar/` altına tarihli rapor yazar. `app` modülünü
import etmez (K5): ölçülen şey gerçek kullanım yoludur.

Kullanım (main checkout'undan, .env orada):
    .venv\\Scripts\\python.exe degerlendirme/calistir.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from degerlendirme.olcum import (  # noqa: E402
    Senaryo,
    Sonuc,
    kok_neden,
    ozet,
    sansli_dogru_mu,
    senaryolari_yukle,
    tetkik_ortusmesi,
    triyaj_dogru_mu,
    wer,
)

BACKEND = "http://localhost:8000"
BURASI = Path(__file__).resolve().parent
SONUCLAR = BURASI / "sonuclar"
BEKLENEN_CHUNK = 51
BEKLENEN_DOSYA = 15
# WER bu eşiğin üstüne çıkarsa sorun tanıma değil, ses-metin eşleşmesidir.
WER_HIZALAMA_ESIGI = 0.6


class OnUcusHatasi(Exception):
    """Ön uçuş kontrolü düştüğünde atılır; koşum hiç başlamaz."""


def jeton_al(kullanici: str, parola: str) -> str:
    """OAuth2 password flow ile jeton alır (form-data, JSON değil)."""
    yanit = requests.post(
        f"{BACKEND}/auth/login",
        data={"username": kullanici, "password": parola},
        timeout=15,
    )
    if yanit.status_code != 200:
        raise OnUcusHatasi(
            f"Giriş başarısız ({kullanici}): {yanit.status_code} {yanit.text[:200]}"
        )
    return yanit.json()["access_token"]


def on_ucus() -> tuple[str, str]:
    """Koşum öncesi dört kontrol; biri düşerse hiç başlamayız.

    Gün 20'nin dersi: /health/ 200 dönmesi kimlik doğrulamasının çalıştığını
    kanıtlamaz — bilgi_tabani_kur.py tam bu yüzden bilgi tabanını boşaltacaktı.
    """
    try:
        saglik = requests.get(f"{BACKEND}/health/", timeout=10)
    except requests.RequestException as exc:
        raise OnUcusHatasi(f"Backend'e ulaşılamıyor ({BACKEND}): {exc}") from exc
    if saglik.status_code != 200:
        raise OnUcusHatasi(f"/health/ {saglik.status_code} döndü")

    hasta_jetonu = jeton_al("hasta", "hasta123")
    admin_jetonu = jeton_al("admin", "admin123")

    liste = requests.get(
        f"{BACKEND}/document/liste",
        headers={"Authorization": f"Bearer {admin_jetonu}"},
        timeout=30,
    )
    if liste.status_code != 200:
        raise OnUcusHatasi(f"/document/liste {liste.status_code} döndü")
    kayitlar = liste.json()
    toplam_chunk = sum(k["chunk_sayisi"] for k in kayitlar)
    if len(kayitlar) != BEKLENEN_DOSYA or toplam_chunk != BEKLENEN_CHUNK:
        raise OnUcusHatasi(
            f"Bilgi tabanı beklenenden farklı: {len(kayitlar)} dosya / "
            f"{toplam_chunk} chunk (beklenen {BEKLENEN_DOSYA}/{BEKLENEN_CHUNK}). "
            "scripts/bilgi_tabani_kur.py ile yeniden kurun."
        )

    print(f"Ön uçuş tamam: {len(kayitlar)} dosya / {toplam_chunk} chunk")
    return hasta_jetonu, admin_jetonu


def _429_bekleyerek_gonder(gonder, aciklama: str, deneme_sayisi: int = 4):
    """429 alınca artan aralıklarla bekler; sınırı kapatmıyoruz (K10)."""
    bekleme = 20
    for deneme in range(deneme_sayisi):
        yanit = gonder()
        if yanit.status_code != 429:
            return yanit, deneme
        print(f"  429 alındı ({aciklama}), {bekleme} sn bekleniyor…")
        time.sleep(bekleme)
        bekleme *= 2
    return yanit, deneme_sayisi


def senaryoyu_sor(senaryo: Senaryo, jeton: str) -> tuple[Sonuc, int]:
    """Tek senaryoyu /ai/analiz'e gönderir ve Sonuc'a çevirir."""
    govde = {
        "patient_age": senaryo.yas,
        "gender": senaryo.cinsiyet,
        "symptom_text": senaryo.sikayet,
        "chronic_disease": senaryo.kronik_hastalik,
        "giris_tipi": "metin",
    }
    if senaryo.vitals:
        govde["vitals"] = senaryo.vitals

    yanit, kota_carpma = _429_bekleyerek_gonder(
        lambda: requests.post(
            f"{BACKEND}/ai/analiz",
            json=govde,
            headers={"Authorization": f"Bearer {jeton}"},
            timeout=180,
        ),
        senaryo.id,
    )

    if yanit.status_code != 200:
        return (
            Sonuc(
                senaryo_id=senaryo.id,
                hata=f"{yanit.status_code}: {yanit.text[:200]}",
            ),
            kota_carpma,
        )

    veri = yanit.json()
    return (
        Sonuc(
            senaryo_id=senaryo.id,
            cikan_triage_code=veri.get("triage_code"),
            cikan_bolum=veri.get("department"),
            cikan_tetkikler=veri.get("onerilen_tetkikler") or [],
            sources=veri.get("sources") or [],
            visit_id=veri.get("visit_id"),
        ),
        kota_carpma,
    )


def sesi_transkript_et(senaryo: Senaryo, jeton: str) -> str | None:
    """Kör senaryonun ses kaydını /speech/transkript'e gönderir."""
    if not senaryo.ses_dosyasi:
        return None
    yol = BURASI / senaryo.ses_dosyasi
    if not yol.exists():
        print(f"  Ses dosyası yok, WER atlanıyor: {yol}")
        return None

    with yol.open("rb") as dosya:
        icerik = dosya.read()

    yanit, _ = _429_bekleyerek_gonder(
        lambda: requests.post(
            f"{BACKEND}/speech/transkript",
            files={"file": (yol.name, icerik, "audio/mp4")},
            headers={"Authorization": f"Bearer {jeton}"},
            timeout=300,
        ),
        f"{senaryo.id} ses",
    )
    if yanit.status_code != 200:
        print(f"  Transkript hatası ({senaryo.id}): {yanit.status_code}")
        return None
    return yanit.json().get("transcript")


def seti_kosur(senaryolar: list[Senaryo], jeton: str, etiket: str) -> list[Sonuc]:
    """Bir seti baştan sona koşar ve her senaryodan sonra diske yazar (K15)."""
    sonuclar: list[Sonuc] = []
    ara_dosya = SONUCLAR / f"{date.today().isoformat()}-{etiket}-ham.json"
    SONUCLAR.mkdir(exist_ok=True)

    for sira, senaryo in enumerate(senaryolar, start=1):
        print(f"[{etiket} {sira}/{len(senaryolar)}] {senaryo.id}")
        sonuc, _ = senaryoyu_sor(senaryo, jeton)
        if senaryo.ses_dosyasi:
            sonuc.transkript = sesi_transkript_et(senaryo, jeton)
        sonuclar.append(sonuc)
        # Kısmi kayıt: 20. senaryoda çöken koşum 19 ölçümü kaybetmesin.
        ara_dosya.write_text(
            json.dumps([s.__dict__ for s in sonuclar], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return sonuclar


def _wer_tablosu(senaryolar: list[Senaryo], sonuclar: list[Sonuc]) -> tuple[list, float]:
    """Kör senaryolar için WER; referans metin senaryonun kendi şikayetidir."""
    harita = {s.senaryo_id: s for s in sonuclar}
    satirlar = []
    for senaryo in senaryolar:
        sonuc = harita.get(senaryo.id)
        if not sonuc or not sonuc.transkript:
            continue
        oran = wer(senaryo.sikayet, sonuc.transkript)
        satirlar.append((senaryo.id, oran, sonuc.transkript))
    ortalama = sum(o for _, o, _ in satirlar) / len(satirlar) if satirlar else 0.0
    return satirlar, ortalama


def rapor_yaz(bloklar: list[tuple[str, list[Senaryo], list[Sonuc]]]) -> Path:
    """Markdown raporu ve ham JSON'u sonuclar/ altına yazar."""
    SONUCLAR.mkdir(exist_ok=True)
    bugun = date.today().isoformat()
    md = [f"# Gün 23 değerlendirme sonuçları — {bugun}", ""]
    md.append("Tek koşum. Ollama belirlenimsizdir; Gün 24 aynı etiketle kıyaslanacak.")
    md.append("")

    ham: dict = {"tarih": bugun, "bloklar": {}}

    for etiket, senaryolar, sonuclar in bloklar:
        o = ozet(senaryolar, sonuclar)
        md.append(f"## {etiket}")
        md.append("")
        md.append("| Ölçü | Değer |")
        md.append("|---|---|")
        md.append(f"| Ölçülen senaryo | {o.toplam} |")
        md.append(f"| Doğru triyaj | {o.dogru} |")
        md.append(f"| **Genel doğruluk (tüm)** | **%{o.dogruluk_tum * 100:.1f}** |")
        md.append(
            f"| **Genel doğruluk (cevaplananlar)** | **%{o.dogruluk_cevaplananlar * 100:.1f}** |"
        )
        md.append(
            f"| **Kırmızı duyarlılık** | **%{o.kirmizi_duyarlilik * 100:.1f}** "
            f"({o.kirmizi_yakalanan}/{o.kirmizi_toplam}) |"
        )
        md.append(f"| Eşik altı oranı | %{o.esik_alti_orani * 100:.1f} ({o.esik_alti}) |")
        md.append(f"| Tetkik Jaccard (ort.) | {o.jaccard_ortalama:.2f} |")
        md.append(
            f"| Kök neden A/B/C | {o.kok_neden_dagilimi['A']} / "
            f"{o.kok_neden_dagilimi['B']} / {o.kok_neden_dagilimi['C']} |"
        )
        md.append(f"| Şanslı doğru | {o.sansli_dogru} |")
        md.append(f"| Ölçülemedi (altyapı) | {o.olculemedi} |")
        md.append(
            f"| Kapsam dışı (doğru/toplam) | {o.kapsam_disi_dogru}/{o.kapsam_disi_toplam} |"
        )
        md.append("")

        md.append("### Senaryo kırılımı")
        md.append("")
        md.append("| id | Beklenen | Çıkan | Kaynak geldi mi | Kutu |")
        md.append("|---|---|---|---|---|")
        harita = {s.senaryo_id: s for s in sonuclar}
        for senaryo in senaryolar:
            sonuc = harita.get(senaryo.id)
            if not sonuc:
                continue
            kaynak_geldi = (
                "—"
                if not senaryo.beklenen_kaynak
                else ("evet" if senaryo.beklenen_kaynak in sonuc.sources else "HAYIR")
            )
            kutu = kok_neden(senaryo, sonuc) or "doğru"
            md.append(
                f"| {senaryo.id} | {senaryo.beklenen_triage_code} | "
                f"{sonuc.cikan_triage_code or 'HATA'} | {kaynak_geldi} | {kutu} |"
            )
        md.append("")

        ham["bloklar"][etiket] = {
            "ozet": o.__dict__,
            "sonuclar": [s.__dict__ for s in sonuclar],
        }

    # WER yalnızca ses kaydı olan blokta anlamlı.
    for etiket, senaryolar, sonuclar in bloklar:
        satirlar, ortalama = _wer_tablosu(senaryolar, sonuclar)
        if not satirlar:
            continue
        md.append(f"## Ses tanıma (WER) — {etiket}")
        md.append("")
        md.append("| id | WER | Transkript |")
        md.append("|---|---|---|")
        for sid, oran, metin in satirlar:
            md.append(f"| {sid} | {oran:.3f} | {metin[:80]}… |")
        md.append("")
        md.append(f"**Ortalama WER: {ortalama:.3f}**")
        md.append("")
        if ortalama > WER_HIZALAMA_ESIGI:
            md.append(
                f"> UYARI: ortalama WER {WER_HIZALAMA_ESIGI}'ın üstünde. Bu genellikle "
                "tanıma kalitesini değil, ses dosyalarının yanlış senaryoyla "
                "eşleştirilmiş olduğunu gösterir — eşleşmeyi doğrulayın."
            )
            md.append("")
        md.append(
            "Dürüst sınır: kullanıcı kendi yazdığı metni okudu. Okunan konuşma, "
            "telaşlı bir hastanın konuşmasından kolaydır; bu WER iyimser taraflıdır."
        )
        md.append("")
        ham["bloklar"][etiket]["wer_ortalama"] = ortalama

    md_yolu = SONUCLAR / f"{bugun}.md"
    md_yolu.write_text("\n".join(md), encoding="utf-8")
    (SONUCLAR / f"{bugun}.json").write_text(
        json.dumps(ham, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return md_yolu


def main() -> int:
    try:
        hasta_jetonu, _ = on_ucus()
    except OnUcusHatasi as exc:
        print(f"ÖN UÇUŞ DÜŞTÜ: {exc}")
        return 1

    kor = senaryolari_yukle(BURASI / "kor_senaryolar.json")
    turetilmis = senaryolari_yukle(BURASI / "senaryolar.json")

    kor_sonuclari = seti_kosur(kor, hasta_jetonu, "kor")
    turetilmis_sonuclari = seti_kosur(turetilmis, hasta_jetonu, "turetilmis")

    yol = rapor_yaz(
        [
            ("Kör set", kor, kor_sonuclari),
            ("Türetilmiş set", turetilmis, turetilmis_sonuclari),
        ]
    )
    print(f"\nRapor yazıldı: {yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify the driver imports and fails cleanly without a backend**

Run: `.venv\Scripts\python.exe degerlendirme/calistir.py`
Expected: Backend kapalıysa `ÖN UÇUŞ DÜŞTÜ: Backend'e ulaşılamıyor…` ve çıkış kodu 1. Traceback **görülmemeli** — ön uçuş hatayı yakalıyor.

- [ ] **Step 3: Verify unit tests still pass**

Run: `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
Expected: 26 passed

- [ ] **Step 4: Commit**

```bash
git add degerlendirme/calistir.py
git commit -m "feat: olcum surucusu - on ucus, 429 yonetimi, kismi kayit, rapor"
```

---

### Task 8: Gerçek ölçüm koşumu ve Ek C kaydı

**Files:**
- Create: `degerlendirme/sonuclar/YYYY-AA-GG.md`, `degerlendirme/sonuclar/YYYY-AA-GG.json`
- Modify: `docs/superpowers/ek-c-ilerleme.md`

**Interfaces:**
- Consumes: her şey
- Produces: ölçülmüş sayılar

- [ ] **Step 1: Bring the environment up**

```bash
docker compose up -d postgres chromadb
ollama list
```

`main` checkout'undan koşulmalı — `.env` orada, yani doğru Chroma portu (8001) ve backend'le aynı JWT anahtarı gelir. Backend ayrı bir terminalde:

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

8000 portunu başka bir proje tutuyorsa (`PycharmProjects\fastapi`, `books:app`) önce o kapatılmalı.

- [ ] **Step 2: Run the full suite to confirm no regression**

Run: `.venv\Scripts\python.exe -m pytest -m "not yavas"`
Expected: 157 + 26 = **183 passed**, kapsama kapısı geçiyor (`degerlendirme/` `--cov=app` dışında olduğu için oran değişmemeli).

- [ ] **Step 3: Run the measurement**

Run: `.venv\Scripts\python.exe degerlendirme/calistir.py`
Expected: Ön uçuş "15 dosya / 51 chunk" basar, her senaryo sırayla koşar (yerel Ollama yüzünden birkaç dakika), rapor yolu basılır.

- [ ] **Step 4: Sanity-check the output before believing it**

Raporu aç ve üç şeye bak:

1. **Ortalama WER < 0.6 mı?** Değilse ses-metin eşleşmesi bozuk demektir; senaryo/kayıt sırasını doğrula, ölçümü tekrarla.
2. **Yanık ve zehirlenme senaryoları A kutusunda mı?** Spec bunu önceden ilan etti. Değilse ya defekt kendiliğinden kapanmış ya da senaryo beklenenden farklı bir protokole düşmüş — ikisi de araştırılmalı, sessiz geçilmemeli.
3. **Kör set ile türetilmiş setin sayıları ayrışıyor mu?** Ayrışıyorsa bulgu odur ve Ek C'ye ayrı bir başlıkla yazılır.

- [ ] **Step 5: Write the Ek C section**

`docs/superpowers/ek-c-ilerleme.md` sonuna "Gün 23" bölümü: bu gün ne yapıldı, ölçümler tablosu, kör/türetilmiş ayrışması, önceden ilan edilen defektlerin doğrulanıp doğrulanmadığı, "Gün 24'e devredilenler" listesi, süreç notu.

- [ ] **Step 6: Commit**

```bash
git add degerlendirme/sonuclar docs/superpowers/ek-c-ilerleme.md
git commit -m "measure: Gun 23 olcum sonuclari ve Ek C kaydi"
```

---

## Self-Review

**Spec coverage:**

| Spec maddesi | Görev |
|---|---|
| K1 olduğu gibi ölçüm, `app/` değişmez | Global Constraints + Task 8 Step 2 |
| K2 iki yazarlı set, ayrı dosya, ayrı rapor | Task 6, Task 7 `rapor_yaz` blokları |
| K3 sorgu/etiket yazarlığı ayrımı | Task 6 etiketleme yordamı |
| K4 sızıntı testle dayatılır | Task 6 `test_few_shot_havuzu_olcum_setiyle_kesismiyor` |
| K5 `app` import edilmez | Task 7 (yalnızca `requests`) |
| K6 saf çekirdek / sürücü | Task 1-5 vs Task 7 |
| K7 doğruluk iki kez | Task 5 `dogruluk_tum` / `dogruluk_cevaplananlar` |
| K8 "Belirsiz" → A | Task 3 `test_esik_alti_yanit_retrieval_hatasi_sayilir` |
| K9 kök neden tasnifi + iki kenar durum | Task 3 |
| K10 hız sınırı kapatılmaz | Task 7 `_429_bekleyerek_gonder` |
| K11 bağımlılıksız WER | Task 4 |
| K12 Türkçe karakter katlanmaz | Task 4 `test_wer_turkce_karakteri_asciye_katlamaz` |
| K13 kapsama kapısına dokunulmaz | Global Constraints + Task 8 Step 2 |
| K14 ziyaretler silinmez, `visit_id` kaydedilir | Task 1 `Sonuc.visit_id`, Task 7 |
| K15 kısmi sonuç korunur | Task 7 `seti_kosur` ara dosyası |
| Yol haritasının 5 zorunlu testi | Task 1, 2, 3, 5 (isimler birebir korunmadı; `test_dogruluk_hesaplanir`, `test_kirmizi_kacirma_ayri_raporlanir`, `test_tetkik_ortusme_orani_hesaplanir`, `test_esik_alti_yanitlar_ayri_sayilir`, `test_senaryo_dosyasi_okunur_ve_dogrulanir` hepsi mevcut) |
| Ön uçuş | Task 7 `on_ucus` |
| WER hizalama koruması | Task 7 `WER_HIZALAMA_ESIGI` + Task 8 Step 4 |

**Type consistency:** `Senaryo`, `Sonuc`, `Ozet` alan adları Task 1/5'te tanımlandığı gibi Task 3, 5, 7'de kullanılıyor. `kok_neden` her yerde `str | None` döndürüyor ve `"HATA"` değeri `kok_neden_dagilimi`'ne yazılmıyor (sözlükte yalnızca A/B/C anahtarları var, `if kutu in dagilim` bunu sağlıyor). `_sadelestir` Task 2'de tanımlanıp Task 3, 5, 6'da kullanılıyor.

**Bilinen boşluk:** `kor_09` (zehirlenme) kullanıcıdan gelmediyse Task 6 onu atlar ve Ek C'ye "zehirlenme kör sette ölçülmedi" yazılır.
