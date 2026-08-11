# Gün 22 (ikinci yarı) — CI, Kapsama Kapısı ve Tembel Import Uygulama Planı

> **Ajan çalışanlar için:** ZORUNLU ALT BECERİ: Bu planı görev görev uygulamak için
> superpowers:subagent-driven-development kullanın. Adımlar takip için checkbox
> (`- [ ]`) sözdizimi kullanır.

**Hedef:** Testleri otomatik koşturmak, kapsamayı dayatmak ve bunu mümkün kılmak
için ağır kütüphane import'larını tembelleştirmek.

**Mimari:** Üç görev, sıra bağımlılığa göre. Görev 1 üretim kodundaki ağır
import'ları fonksiyon içine taşır ve ölçümle bir `requirements-ci.txt` üretir —
CI'ın hafif olabilmesinin ön koşulu budur. Görev 2 dal kapsamasını açıp eşiği
dayatır. Görev 3 ikisini de tüketen GitHub Actions workflow'unu yazar.

**Teknoloji:** pytest, pytest-cov, coverage.py, GitHub Actions, Alembic, Postgres 16.
**Yeni çalışma zamanı bağımlılığı eklenmiyor.**

**Tasarım dokümanı:** `docs/superpowers/specs/2026-08-11-gun22-ci-kapsama-design.md`
— çelişkide o belge kazanır, kararlar K1–K11 numaralarıyla oradadır.

## Global Constraints

- **Türkçe açıklama zorunlu.** Eklenen her fonksiyon, alan ve blok yanına tek
  cümlelik Türkçe yorum.
- **Mevcut 153 testin hiçbiri zayıflatılmaz veya yeniden adlandırılmaz.** Yeni
  test eklemek bu kısıtın dışındadır.
- **`rerank_threshold` ve `ornek_dokumanlar/` altındaki protokol metinleri
  değişmez.**
- **Yeni çalışma zamanı bağımlılığı YOK** — `requirements.txt` değişmiyor.
  `requirements-ci.txt` yeni bir dosyadır ve mevcut sürümleri birebir tekrarlar.
- **Saf TDD**, iki istisnayla: kapsama kapısı ve CI workflow'u yapılandırmadır,
  bağlayıcılıkları ters yönden kanıtlanır (aşağıda her görevde yazılı).
- **Python:** `C:\Users\batuh\Desktop\Ai_Triage-myself\.venv\Scripts\python.exe`
- **PostgreSQL ayakta.** `entegrasyon` işaretli testler `ai_triage_test` ister.
- **Commit mesajları ASCII.**
- Paket koşusu: `.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings`

**Ölçülmüş taban çizgisi (bu plandan önce):**

| | Değer |
|---|---|
| Hızlı paket | 153 passed, 5 deselected, ~57 sn |
| Satır kapsaması | %85 |
| Dal kapsaması | %83 |
| Dal kapsaması, `llm_service`+`stt_service` hariç | %87 |
| `app.main` import süresi | 25,5 sn |
| Yüklenen modül sayısı | 5214 |

---

## Dosya Yapısı

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `app/services/rag_service.py` | `torch` + `sentence_transformers` fonksiyon içine | 1 |
| `app/services/stt_service.py` | `torch` + `faster_whisper` fonksiyon içine | 1 |
| `app/services/chroma_service.py` | `chromadb` fonksiyon içine | 1 |
| `tests/birim/test_import_agirligi.py` | **YENİ** — ağır kütüphanelerin çekilmediğini bağlar | 1 |
| `requirements-ci.txt` | **YENİ** — ölçümle yazılan minimal liste | 1 |
| `.coveragerc` | **YENİ** — dal kapsaması + hariç tutulanlar | 2 |
| `pytest.ini` | `--cov-branch --cov-fail-under=87` | 2 |
| `CLAUDE.md` | odaklı koşularda `--no-cov` notu | 2 |
| `.github/workflows/ci.yml` | **YENİ** — `test` ve `migration` işleri | 3 |

---

### Task 1: Tembel import ve minimal CI listesi

**Files:**
- Create: `tests/birim/test_import_agirligi.py`
- Create: `requirements-ci.txt`
- Modify: `app/services/rag_service.py:1-28`
- Modify: `app/services/stt_service.py:1-42`
- Modify: `app/services/chroma_service.py:1-34`

**Interfaces:**
- Consumes: hiçbir şey (ilk görev).
- Produces: `requirements-ci.txt` — Görev 3'ün CI işleri bu dosyayı kurar.
  Üretim kodundaki fonksiyon adları ve imzalar **değişmiyor**:
  `get_reranker()`, `retrieve_and_rerank(...)`, `get_model()`, `transcribe(...)`,
  `get_collection()`, `_gomme_fonksiyonu()` aynı kalır.

- [ ] **Step 1: Muhafız testini yaz**

`tests/birim/test_import_agirligi.py` (yeni dosya):

```python
"""`app.main` import edildiğinde ağır kütüphanelerin YÜKLENMEDİĞİNİ dondurur.

Bu testin var oluş sebebi ölçüldü: tembelleştirmeden önce `app.main` import'u
25,5 saniye sürüyor ve torch, transformers, sentence_transformers, chromadb,
faster_whisper dahil 5214 modül yüklüyordu. Bu, hem her test koşusunun yarısını
hem de CI ortamını büyütüyordu. (Uygulama sırasında ölçüldü: 28,5 sn → 1,85 sn,
5215 → 1077 modül; ortam 1694 MB → 498 MB, torch tek başına 497 MB. Kurulum
SÜRESİ hiç ölçülmedi — planın ilk hâlindeki "2,5 GB" ve "dakikalardan saniyelere"
ifadeleri tahmindi ve düzeltildi.)

Test olmadan, birinin `rag_service`'e modül düzeyinde bir `import torch` geri
koyması hiçbir şeyi kırmaz ve CI sessizce yavaşlar — yol haritasının önceden
uyardığı yere geri dönülür.

Alt süreçte koşuyor (tasarım K10): pytest oturumunun kendi içinde `sys.modules`
sorulamaz, çünkü başka testler `torch`'u zaten yüklemiş olur.
"""

import json
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent.parent

# CI kurulum süresini ve her koşunun ~25 saniyesini belirleyen kütüphaneler.
AGIR_MODULLER = ["torch", "sentence_transformers", "faster_whisper", "chromadb"]

# Alt süreçte koşacak betik: app.main'i import eder ve hangi ağır modüllerin
# yüklendiğini JSON olarak basar.
BETIK = """
import json
import os
import sys

os.environ.setdefault(
    "DATABASE_URL", "postgresql://triage:triage@localhost:5432/ai_triage_test"
)
os.environ.setdefault("JWT_SECRET_KEY", "import-agirligi-testi")

import app.main  # noqa: F401

print(json.dumps([m for m in %s if m in sys.modules]))
"""


def test_app_import_agir_kutuphaneleri_cekmiyor():
    sonuc = subprocess.run(
        [sys.executable, "-c", BETIK % AGIR_MODULLER],
        capture_output=True,
        text=True,
        cwd=str(KOK),
    )

    assert sonuc.returncode == 0, f"alt süreç patladı:\n{sonuc.stderr}"
    yuklenen = json.loads(sonuc.stdout.strip().splitlines()[-1])
    assert yuklenen == [], (
        f"app.main şu ağır kütüphaneleri import zinciriyle çekiyor: {yuklenen}. "
        "Modül düzeyinde import edilmiş olabilirler; fonksiyon içine taşıyın."
    )
```

- [ ] **Step 2: Testi çalıştır, kırmızı olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/birim/test_import_agirligi.py -v --no-cov
```

Beklenen: FAIL, ve mesajda dört modülün de listelendiği görülmeli
(`['torch', 'sentence_transformers', 'faster_whisper', 'chromadb']`).
Raporunda bu çıktıyı birebir göster.

- [ ] **Step 3: `rag_service.py` import'larını taşı**

`app/services/rag_service.py` dosyasının ilk 28 satırını şununla değiştir:

```python
"""RAG servisi: Chroma'dan aday getirme + cross-encoder ile yeniden sıralama."""

# Tip açıklamalarının çalışma zamanında değerlendirilmesini kapatır. ZORUNLU:
# aşağıdaki `_reranker: CrossEncoder | None` satırı, CrossEncoder modül düzeyinde
# import EDİLMEDİĞİ için aksi hâlde NameError verir (tasarım K3).
from __future__ import annotations

from typing import TYPE_CHECKING

from app.config.config import settings
from app.utils.logger import logger

if TYPE_CHECKING:  # yalnızca tip denetleyici için; çalışma zamanında import edilmez
    from sentence_transformers import CrossEncoder

# Model tembel yükleniyor: import anında ~2 GB'lık ağırlık yüklemek hem uygulama
# açılışını hem de testleri gereksiz yere bloke ediyordu.
_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        # torch ve sentence_transformers BURADA import ediliyor, modül düzeyinde
        # değil: modül düzeyinde import her test koşusuna ~25 saniye ve CI'a
        # ortamı ~1,2 GB büyütüyordu (tasarım K2). [Planın ilk hâli burada
        # "2,5 GB" diyordu; ölçülmemişti ve uygulamada düzeltildi.]
        import torch
        from sentence_transformers import CrossEncoder

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Reranker yükleniyor: {settings.reranker_model} ({device})")
        # Aktivasyon açıkça veriliyor: predict()'in olasılık döndürmesi aksi hâlde
        # modelin config dosyasına bağlı kalır. Model ya da kütüphane varsayılanı
        # değişirse predict() sessizce ham logit döndürür ve her eşik anlamsızlaşır.
        _reranker = CrossEncoder(
            settings.reranker_model,
            device=device,
            activation_fn=torch.nn.Sigmoid(),
        )
    return _reranker
```

Dosyanın geri kalanı (`retrieve_and_rerank`) **değişmiyor**. Modül düzeyindeki
`device = ...` satırı kaldırıldı çünkü `torch` artık orada yok; `device` yalnızca
`get_reranker` içinde kullanılıyordu.

- [ ] **Step 4: `stt_service.py` import'larını taşı**

`app/services/stt_service.py` dosyasının 1-42 satırlarını şununla değiştir:

```python
"""Ses tanıma (STT) servisi: faster-whisper ile Türkçe transkripsiyon."""

# Tip açıklamalarının çalışma zamanında değerlendirilmesini kapatır. ZORUNLU:
# aşağıdaki `_model: WhisperModel | None` satırı, WhisperModel modül düzeyinde
# import EDİLMEDİĞİ için aksi hâlde NameError verir (tasarım K3).
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from app.config.config import settings
from app.utils.logger import logger

if TYPE_CHECKING:  # yalnızca tip denetleyici için; çalışma zamanında import edilmez
    from faster_whisper import WhisperModel


class STTError(Exception):
    """Ses dosyası transkript edilemediğinde fırlatılır."""


# Model tembel yükleniyor: import anında ~500 MB ağırlık yüklemek hem uygulama
# açılışını hem de testleri gereksiz yere bloke eder.
_model: WhisperModel | None = None


def _resolve_device() -> tuple[str, str]:
    """Cihazı ve hesaplama tipini seçer; torch yalnızca burada gerekiyor."""
    if settings.whisper_device != "auto":
        device = settings.whisper_device
    else:
        # torch BURADA import ediliyor: modül düzeyinde import CI'a ve her test
        # koşusuna ağırlık ekliyordu (tasarım K2).
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        # faster_whisper BURADA import ediliyor, modül düzeyinde değil.
        from faster_whisper import WhisperModel

        device, compute_type = _resolve_device()
        logger.info(
            f"Whisper modeli yükleniyor: {settings.whisper_model_size} "
            f"({device}, {compute_type})"
        )
        _model = WhisperModel(
            settings.whisper_model_size, device=device, compute_type=compute_type
        )
    return _model
```

`transcribe(...)` fonksiyonu **değişmiyor**.

- [ ] **Step 5: `chroma_service.py` import'larını taşı**

`app/services/chroma_service.py` dosyasını şununla değiştir:

```python
"""ChromaDB bağlantısı ve triyaj koleksiyonu.

Ayarlar pydantic-settings üzerinden okunuyor: önce ortam değişkenleri
(Docker Compose bunları veriyor), yoksa .env dosyası, o da yoksa varsayılan.
"""

from app.config.config import settings

# Bağlantı tembel kuruluyor: import anında kurulursa ChromaDB kapalıyken
# uygulama hiç açılmıyordu (/health bile cevap vermiyordu).
_collection = None


def _gomme_fonksiyonu():
    """Ayarlardaki çok dilli modelden gömme fonksiyonu kurar.

    Açıkça veriliyor çünkü ChromaDB'nin varsayılanı all-MiniLM-L6-v2 (İngilizce);
    Türkçe sorguda ayırt edici olmayan vektör üretip yanlış dokümanları getiriyor.
    """
    # chromadb BURADA import ediliyor, modül düzeyinde değil (tasarım K2).
    from chromadb.utils import embedding_functions

    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model
    )


def get_collection():
    global _collection
    if _collection is None:
        # chromadb BURADA import ediliyor, modül düzeyinde değil (tasarım K2).
        import chromadb

        chroma_client = chromadb.HttpClient(
            host=settings.chroma_host, port=settings.chroma_port
        )
        _collection = chroma_client.get_or_create_collection(
            name="triage_documents",
            embedding_function=_gomme_fonksiyonu(),
        )
    return _collection
```

- [ ] **Step 6: Muhafız testini çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/birim/test_import_agirligi.py -v --no-cov
```

Beklenen: `1 passed`. Yeşil değilse mesaj hangi modülün hâlâ çekildiğini
söyleyecek — o modülü import eden başka bir yer var demektir, ara ve raporla.

- [ ] **Step 7: Kazancı ölç ve raporla**

Import süresini önce/sonra karşılaştır. Aşağıdaki betiği geçici bir dosyaya yaz,
çalıştır, çıktıyı rapora koy, sonra dosyayı sil:

```python
import os, sys, time
os.environ.setdefault("DATABASE_URL", "postgresql://triage:triage@localhost:5432/ai_triage_test")
os.environ.setdefault("JWT_SECRET_KEY", "olcum")
t = time.perf_counter()
import app.main  # noqa
print(f"app.main import: {time.perf_counter() - t:.2f} sn")
print(f"yuklu modul    : {len(sys.modules)}")
```

Taban: **25,5 sn / 5214 modül**. Yeni değerleri raporla.

- [ ] **Step 8: Tüm paketi çalıştır**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings
```

Beklenen: **154 passed** (153 + muhafız testi), 5 deselected. Paket süresini de
raporla — taban ~57 sn.

Mevcut bir test kırmızıya dönerse: bir test `rag_service.device` gibi kaldırılmış
bir modül düzeyi adına dokunuyor olabilir. **Testi değiştirme**, raporla.

- [ ] **Step 9: Commit**

```bash
git add app/services/rag_service.py app/services/stt_service.py app/services/chroma_service.py tests/birim/test_import_agirligi.py
git commit -m "perf: agir kutuphane importlari fonksiyon icine tasindi"
```

- [ ] **Step 10: `requirements-ci.txt`'i ÖLÇÜMLE yaz**

Tahminle yazma (tasarım K4). Yöntem:

1. Temiz bir sanal ortam kur:
   `.venv\Scripts\python.exe -m venv C:\Users\batuh\AppData\Local\Temp\ci_dogrula`
2. Aşağıdaki başlangıç listesini `requirements-ci.txt` olarak yaz
3. O ortamda kur: `C:\Users\batuh\AppData\Local\Temp\ci_dogrula\Scripts\python.exe -m pip install -r requirements-ci.txt -r requirements-dev.txt`
4. O ortamda koş: `C:\Users\batuh\AppData\Local\Temp\ci_dogrula\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov`
5. `ModuleNotFoundError` çıkarsa eksik paketi **sürümüyle** (`requirements.txt`'ten
   birebir) ekle ve 3-4'ü tekrarla. Yeşil olana kadar sürdür.

Başlangıç listesi:

```
# CI icin minimal calisma zamani listesi.
#
# requirements.txt'in kopyasi DEGILDIR: torch ailesi (torch, transformers,
# sentence-transformers, faster-whisper) bilerek DISARIDA. Onlar yalnizca
# `yavas` isaretli testlerde gerekiyor ve CI o testleri hic kosmuyor
# (tasarim K9). Kurulumu dakikalardan saniyelere indiren fark budur.
#
# DIKKAT: bu liste "hicbir agir sey yok" demek degil. pytest, isaret
# filtrelemesini test modullerini TOPLADIKTAN sonra uyguluyor, yani
# tests/entegrasyon/ altindaki `yavas` dosyalar da import ediliyor ve
# chromadb ile langchain-text-splitters bu yuzden listede.
#
# Surumler requirements.txt ile BIREBIR ayni olmali; ayrisirsa CI ile uretim
# farkli kod kosar ve CI'in kanitladigi sey uretim icin gecerli olmaz.

# --- Web katmani ---
fastapi==0.139.0
starlette==1.3.1
uvicorn==0.50.2
python-multipart==0.0.32
anyio==4.14.1

# --- Veritabani ---
SQLAlchemy==2.0.51
psycopg2-binary==2.9.12
alembic==1.18.5

# --- Ayarlar ve dogrulama ---
pydantic==2.13.4
pydantic-settings==2.14.2
python-dotenv==1.2.2

# --- Kimlik dogrulama ---
python-jose==3.5.0
passlib==1.7.4
bcrypt==4.0.1

# --- Test istemcisi (TestClient httpx kullaniyor) ---
httpx==0.28.1

# --- Uc modullerinin modul duzeyinde import ettikleri ---
ollama==0.6.2                    # llm_service modul duzeyinde Client kuruyor
pdfplumber==0.11.10              # document.py metin cikarma
python-docx==1.2.0               # document.py DOCX cikarma
langchain-text-splitters==1.1.2  # document.py chunklama + yavas test modulleri
chromadb==1.5.9                  # yavas test modullerinin toplanmasi icin
```

- [ ] **Step 11: Temiz ortamda yeşil olduğunu doğrula**

Step 10'un 4. adımı `154 passed, 5 deselected` vermeli. Çıktıyı ve **kurulum
süresini** rapora yaz. Listeye eklemek zorunda kaldığın her paketi ve sebebini
ayrıca yaz — plan tahmin etmişti, gerçeği sen ölçüyorsun.

Geçici sanal ortamı sonra sil.

- [ ] **Step 12: Commit**

```bash
git add requirements-ci.txt
git commit -m "build: CI icin olculmus minimal gereksinim listesi"
```

---

### Task 2: Kapsama kapısı

**Files:**
- Create: `.coveragerc`
- Modify: `pytest.ini:3`

**Interfaces:**
- Consumes: Görev 1'den bir şey tüketmez.
- Produces: `.coveragerc` — Görev 3'ün CI'ı bu yapılandırmayı olduğu gibi kullanır,
  ayrıca bayrak vermez.

- [ ] **Step 1: `.coveragerc` yaz**

`.coveragerc` (yeni dosya, depo kökünde):

```ini
# Kapsama olcumu yapilandirmasi. pytest.ini'deki --cov bayraklari bu dosyayi
# otomatik okur; CI ayrica bir sey vermez.

[run]
branch = True
omit =
    # Bilerek sahtelenen dis servis adaptorleri. Testlerde ikisi de HIC
    # calistirilmiyor: yerlerine tests/yardimcilar/sahte_llm.py ve
    # sahte_stt.py geciyor (Ollama ve faster-whisper cagrilmiyor).
    #
    # Olcume dahil edilirlerse global sayi test kalitesini degil BU IKI
    # DOSYANIN BOYUTUNU izler: llm_service'e elli satir eklemek kapsamayi
    # test kalitesiyle ilgisiz bir sebeple dusurur; tersine auth testleri
    # bosaltilsa olu agirlik sayiyi maskeleyebilir (tasarim K6).
    #
    # Bedeli durustluktur: neyin olculmedigi yazilmadan "kapsama %87"
    # iddiasi eksiktir. Bu yuzden Ek C'ye de yaziliyor.
    app/services/llm_service.py
    app/services/stt_service.py
```

- [ ] **Step 2: Eşiksiz ölç ve 87'yi doğrula**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --cov=app --cov-report=term
```

Beklenen: `TOTAL` satırında **%87**. Farklı çıkarsa **eşiği ölçülen değere göre
ayarla** ve sapmayı raporla — plan 87 diyor ama Görev 1 kod ekledi, birkaç puan
oynayabilir. Ölçüm kazanır, plan değil.

- [ ] **Step 3: `pytest.ini`'yi güncelle**

`pytest.ini` içindeki `addopts` satırını şununla değiştir (eşik Step 2'de
ölçtüğün değer):

```
addopts = -q --strict-markers --cov=app --cov-branch --cov-fail-under=87 --cov-report=term-missing
```

- [ ] **Step 4: Kapının çalıştığını doğrula, yeşil koşuyu gör**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings
```

Beklenen: `154 passed`, kapsama satırı %87 ve **`Required test coverage of 87%
reached`** benzeri bir satır. Kapı geçildi.

- [ ] **Step 5: Kapının BAĞLAYICI olduğunu ters yönden kanıtla — ATLANMAZ**

Kapının varlığı, dayattığının kanıtı değil. `pytest.ini`'deki eşiği geçici olarak
`95` yap ve koş:

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings
```

Beklenen: paket **kırmızı**, `FAIL Required test coverage of 95% not reached`.
Çıktıyı rapora birebir yaz, sonra eşiği ölçtüğün değere **geri al** ve yeşil
olduğunu tekrar gör. `git diff pytest.ini` çıktısını da rapora koy — geri
almanın kanıtı o.

- [ ] **Step 6: Odaklı koşuların yan etkisini belgele**

`--cov-fail-under` `pytest.ini`'de olduğu için **her** pytest koşusuna uygulanır.
Tek bir dosya koşturan biri (`pytest tests/birim/test_db_kilidi.py`) kapsamayı
doğal olarak düşük ölçer ve **sahte bir kırmızı** alır — hata "testin kırıldı"
demez, "kapsama yetersiz" der ve teşhisi zordur.

Bu bilinçli bir taviz: kapı evrensel olsun, yalnızca CI'da hatırlanması gereken
bir şey olmasın. Bedeli tek satırlık bir alışkanlık, ve yazılmazsa bir sonraki
kişi buna takılır. `CLAUDE.md`'nin "Test ve linting" bölümünde paket koşusu
komutunun hemen altına ekle:

```markdown
Tek bir dosya ya da tek bir test koşarken `--no-cov` ekleyin:

    .venv\Scripts\python.exe -m pytest tests/birim/test_db_kilidi.py --no-cov

Kapsama kapısı (`--cov-fail-under`) `pytest.ini`'de olduğu için her koşuya
uygulanır; odaklı bir koşu doğal olarak eşiğin altında kalır ve testler geçse
bile paket kırmızı görünür.
```

- [ ] **Step 7: Commit**

```bash
git add .coveragerc pytest.ini CLAUDE.md
git commit -m "test: dal kapsamasi acildi ve esik dayatiliyor"
```

---

### Task 3: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `requirements-ci.txt` (Görev 1), `.coveragerc` + `pytest.ini`
  (Görev 2). Kapsama eşiği `pytest.ini`'den geliyor; workflow ayrıca bayrak
  vermiyor.
- Produces: uzakta koşan iki iş. Kabul ölçütü GitHub'da yeşil koşmalarıdır (K11).

- [ ] **Step 1: Workflow'u yaz**

`.github/workflows/ci.yml` (yeni dosya):

```yaml
# Iki is: `test` paketi kosar ve kapsama kapisini dayatir, `migration` alembic
# zincirinin bos bir veritabanindan kurulabildigini ve geri alinabildigini
# kanitlar. Ikisi de kendi Postgres servisini alir.
#
# `yavas` isaretli testler CI'da HIC kosmaz (tasarim K9): gercek bge-m3 (~2,2 GB),
# cross-encoder ve ayakta bir ChromaDB isterler. Bunun sonucu, CI'in olctugu
# kapsamanin yereldeki `-m "not yavas"` olcumuyle AYNI olmasidir.
name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  test:
    name: Testler ve kapsama kapisi
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: triage
          POSTGRES_PASSWORD: triage
          POSTGRES_DB: ai_triage_test
        ports:
          - 5432:5432
        # Postgres hazir olmadan testler baslarsa baglanti hatasi aliriz.
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      # Test veritabani kilidi (tests/yardimcilar/db_kilidi.py) bu adresi
      # dogruluyor: host beyaz listede (localhost), port 5432, ad ai_triage_test.
      DATABASE_URL: postgresql://triage:triage@localhost:5432/ai_triage_test
      JWT_SECRET_KEY: ci-icin-sahte-anahtar
      OLLAMA_BASE_URL: http://localhost:11434

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
          cache: pip

      # ChromaDB servisi GEREKMIYOR: entegrasyon testlerinde Chroma sahte,
      # yalnizca Postgres gercek.
      - name: Bagimliliklar
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-ci.txt -r requirements-dev.txt

      - name: Testler (kapsama kapisi pytest.ini'den geliyor)
        run: pytest -m "not yavas"

  migration:
    name: Alembic zinciri
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: triage
          POSTGRES_PASSWORD: triage
          POSTGRES_DB: ai_triage
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      # Bilerek uretimdeki ad (ai_triage), test veritabani DEGIL: test isi
      # conftest uzerinden drop_all cagiriyor, ayni adi paylasmak iki isi
      # birbirine baglardi. Ayrica bu, Gun 27 kurulum provasinin provasi.
      #
      # Test veritabani kilidi burada DEVREDE DEGIL ve bu bilinclidir: kilit
      # yalnizca pytest fixture'inin yolunda, alembic'i korumuyor (tasarim K8).
      DATABASE_URL: postgresql://triage:triage@localhost:5432/ai_triage
      JWT_SECRET_KEY: ci-icin-sahte-anahtar

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
          cache: pip

      - name: Bagimliliklar
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-ci.txt

      # Zincir bos bir veritabanindan kurulabiliyor mu, ve geri alinabiliyor mu?
      # Yerel testler semayi create_all ile kuruyor, yani migration'lar pytest
      # altinda HIC kosmuyor; bu is o boslugu kapatiyor.
      - name: upgrade head
        run: alembic upgrade head

      - name: downgrade base
        run: alembic downgrade base

      - name: tekrar upgrade head
        run: alembic upgrade head
```

- [ ] **Step 2: YAML'ı yerelde ayrıştır**

Sözdizimi hatası, uzakta koşmadan yakalanabilecek tek şeydir:

```
.venv\Scripts\python.exe -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); print('YAML gecerli')"
```

`yaml` kurulu değilse (`pyyaml` bağımlılık zincirinde var) bu adımı atla ve
raporla.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: GitHub Actions workflow'u (test + migration isleri)"
```

- [ ] **Step 4: DUR ve kontrolcüye haber ver**

Workflow'un doğruluğu **yerelde kanıtlanamaz** (tasarım K11). Bu görevin son
adımı bir push'tur ve push'u kontrolcü/kullanıcı yapar. Raporunda açıkça yaz:
"workflow yazıldı, YAML geçerli, uzakta koşmadı."

---

## Görevler bittikten sonra: doğrulama

Kontrolcü tarafından yürütülür.

- [ ] **Otomatik**

```
.venv\Scripts\python.exe -m pytest -m "not yavas"
```
`154 passed`, kapsama kapısı geçiliyor.

- [ ] **Kazanç ölçümü raporlandı**

Import süresi ve paket süresi önce/sonra. Taban: 25,5 sn import, ~57 sn paket,
5214 modül.

- [ ] **CI'ı uzakta koştur — ATLANMAZ (tasarım K11)**

Dal `main`'e birleştikten sonra push'la ve GitHub'da **iki işin de yeşil**
olduğunu gör. `test` işi kapsama kapısını dayatmalı; `migration` işi üç alembic
adımını da geçmeli.

İlk koşuda kırmızı çıkması normaldir ve bilgi vericidir — kurulum süresini,
eksik paketi ya da Postgres bağlantı sorununu orada göreceğiz. Kırmızıysa hatayı
düzeltip tekrar push'la; bu gün, iki iş yeşil olmadan bitmez.

- [ ] **Ek C'yi güncelle**

"Gün 22 · İkinci yarı" bölümü: ölçümler (import süresi, paket süresi, kapsama),
CI'ın ne koşup ne koşmadığı, ve **kapsamadan hariç tutulan iki dosya ile
gerekçesi**. Ayrıca birinci yarının devir listesindeki "migration zinciri pytest
altında hiç koşmuyor" maddesini **kapatıldı** olarak işaretle — CI artık koşuyor.

---

## Bitti sayılır

- [ ] `app.main` import'u `torch`, `sentence_transformers`, `faster_whisper` ve `chromadb`'yi çekmiyor; alt süreçte koşan bir test bunu bağlıyor
- [ ] Import ve paket süreleri önce/sonra ölçülüp raporlandı
- [ ] `requirements-ci.txt` ölçümle yazıldı; temiz ortamda `-m "not yavas"` yeşil; her satırın yanında neden orada olduğu yazılı
- [ ] `.coveragerc` dal kapsamasını açıyor, iki adaptörü gerekçesiyle hariç tutuyor
- [ ] `--cov-fail-under` aktif; eşik yükseltilince paketin kırıldığı görüldü ve geri alındı
- [ ] `.github/workflows/ci.yml` iki iş içeriyor ve YAML geçerli
- [ ] **CI GitHub'da koştu, iki iş de yeşil**
- [ ] Ek C'ye ölçümler ve hariç tutulanlar yazıldı; migration borcu kapatıldı olarak işaretlendi
- [ ] Mevcut 153 testin hiçbiri zayıflatılmadı veya yeniden adlandırılmadı
- [ ] `rerank_threshold` ve protokol metinleri değişmedi
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
