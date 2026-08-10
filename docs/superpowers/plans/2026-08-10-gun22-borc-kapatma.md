# Gün 22 (birinci yarı) — Borç Kapatma Uygulama Planı

> **Ajan çalışanlar için:** ZORUNLU ALT BECERİ: Bu planı görev görev uygulamak için
> superpowers:subagent-driven-development kullanın. Adımlar takip için checkbox
> (`- [ ]`) sözdizimi kullanır.

**Hedef:** Ek C'de altı gündür biriken teknik borcun, Gün 22'nin ikinci yarısını (CI)
mümkün kılan ve Gün 23'ün ölçümünü kurtaran beş maddesini kapatmak.

**Mimari:** Üç görev, türüne göre ayrılmış. Görev 1 yalnızca test altyapısına dokunur
(üretim kodu değişmez), Görev 2 tek bir Alembic revision'ında iki şema değişikliği
yapar, Görev 3 protokol metnini ve ölçüm setini düzeltir. Sıra bağlayıcıdır: retrieval
en sona kalır ki kalibrasyon koşulurken paket zaten yeşil olsun.

**Teknoloji:** pytest, SQLAlchemy, Alembic, ChromaDB, sentence-transformers.
**Yeni kütüphane eklenmiyor** — URL ayrıştırma için SQLAlchemy'nin kendi `make_url`'ü
kullanılıyor (zaten bağımlılık).

**Tasarım dokümanı:** `docs/superpowers/specs/2026-08-10-gun22-borc-kapatma-design.md`
— çelişkide o belge kazanır, kararlar K1–K11 numaralarıyla oradadır.

## Global Constraints

- **Türkçe açıklama zorunlu.** Eklenen her fonksiyon, alan ve blok yanına tek
  cümlelik Türkçe yorum.
- **Mevcut testlerin hiçbiri değiştirilmez, zayıflatılmaz veya yeniden adlandırılmaz.**
  Taban çizgisi `main` üzerinde: `137 passed, 2 deselected`, kapsama %85.
- **Saf TDD**, iki istisnayla: `doctor_id` index'i için test yazılmaz (K8) ve speech
  yamalaması mutasyonla kanıtlanır (K9). Bunların dışında önce test yazılır ve
  ÇALIŞTIRILARAK kırmızı görülür.
- **`rerank_threshold = 0.005` DEĞİŞMEZ** (K3). Kalibrasyon bunu doğrulamak için
  koşulur, yeni değer aramak için değil.
- **Yeni bağımlılık YOK.** `requirements.txt` değişmiyor.
- **Python:** `C:\Users\batuh\Desktop\Ai_Triage-myself\.venv\Scripts\python.exe`
- **PostgreSQL ayakta.** `entegrasyon` işaretli testler `ai_triage_test` ister.
- **Commit mesajları ASCII.**
- Paket koşusu: `.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov`

---

## Dosya Yapısı

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `tests/yardimcilar/db_kilidi.py` | **YENİ** — test DB adresinin güvenli olup olmadığına karar verir | 1 |
| `tests/birim/test_db_kilidi.py` | **YENİ** — kilidin kendi davranışı | 1 |
| `tests/conftest.py` | kilidi çağırır (karar mantığı burada durmaz) | 1 |
| `tests/api/conftest.py` | **YENİ fixture** `transkript_engelle` | 1 |
| `tests/api/test_speech_api.py` | üç teste fixture eklenir | 1 |
| `app/models/visit.py` | `visit_id` unique | 2 |
| `app/db/alembic/versions/<yeni>.py` | **YENİ** — unique + index, tek revision | 2 |
| `tests/entegrasyon/test_doctor_review_kisitlari.py` | **YENİ** — unique kısıtının testi | 2 |
| `ornek_dokumanlar/protokoller/yanik.txt` | hasta dili eklenir | 3 |
| `scripts/kalibre_esik.py` | yanık sorgusu yeniden yazılır + tutulan sorgu | 3 |
| `tests/entegrasyon/test_yanik_reranker.py` | **YENİ** — `yavas`, reranker eşiği | 3 |

---

### Task 1: Test altyapısı — DB kilidi ve speech yamalaması

**Files:**
- Create: `tests/yardimcilar/db_kilidi.py`
- Create: `tests/birim/test_db_kilidi.py`
- Modify: `tests/conftest.py:34-39`
- Modify: `tests/api/conftest.py` (dosya sonuna fixture)
- Modify: `tests/api/test_speech_api.py:18,25,38`

**Interfaces:**
- Produces: `tests.yardimcilar.db_kilidi.hedef_guvenli_mi(url_metni: str) -> tuple[bool, str]`
  — `(guvenli, sebep)` döndürür; güvenliyse `sebep` boş dizedir.
- Produces: `transkript_engelle` fixture'ı (`tests/api/conftest.py`). Sonraki
  görevler kullanmaz; yalnızca `test_speech_api.py` tüketir.

- [ ] **Step 1: Kilidin birim testlerini yaz**

`tests/birim/test_db_kilidi.py` (yeni dosya):

```python
"""Test veritabanı kilidinin kendi davranışını dondurur.

Kilit, şemayı tamamen silen `Base.metadata.drop_all`'u koruyor. Bugünkü kontrol
`endswith("/ai_triage_test")` idi ve iki yönden kusurluydu: üretim sunucusundaki
aynı adlı veritabanı geçiyordu, buna karşılık `?sslmode=require` gibi meşru bir
URL takılıyordu. Bu testler ikisini birden bağlar.
"""

from tests.yardimcilar.db_kilidi import hedef_guvenli_mi


def test_yerel_test_veritabani_kabul_edilir():
    guvenli, _ = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test"
    )

    assert guvenli is True


def test_uzak_host_ayni_ad_olsa_bile_reddedilir():
    # Asıl tehlike bu: üretim sunucusunda ai_triage_test adlı bir veritabanı
    # varsa eski kilit onu korumuyordu ve drop_all oraya iniyordu.
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@prod-host:5432/ai_triage_test"
    )

    assert guvenli is False
    assert "host" in sebep


def test_yanlis_veritabani_adi_reddedilir():
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage"
    )

    assert guvenli is False
    assert "veritabanı" in sebep


def test_query_stringli_yerel_url_kabul_edilir():
    # Eski sonek testi burada YANLIŞ yönde başarısız oluyordu: meşru bir CI
    # koşusunu durduruyordu.
    guvenli, _ = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test?sslmode=require"
    )

    assert guvenli is True


def test_docker_servis_adi_kabul_edilir():
    # docker compose ve CI servis konteynerinin host adı "postgres".
    guvenli, _ = hedef_guvenli_mi(
        "postgresql://triage:triage@postgres:5432/ai_triage_test"
    )

    assert guvenli is True


def test_ayristirilamayan_url_reddedilir():
    # Kilit şüphede kapanır: anlamadığı bir adrese güvenmez.
    guvenli, _ = hedef_guvenli_mi("bu bir url degil")

    assert guvenli is False
```

- [ ] **Step 2: Testleri çalıştır, kırmızı olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/birim/test_db_kilidi.py -v --no-cov
```
Beklenen: altısı da `ModuleNotFoundError: No module named 'tests.yardimcilar.db_kilidi'`
ile FAIL. Raporunda bu çıktıyı birebir göster.

- [ ] **Step 3: Kilidi yaz**

`tests/yardimcilar/db_kilidi.py` (yeni dosya):

```python
"""Test veritabanı adresinin yıkıcı işlemler için güvenli olup olmadığına karar verir.

Karar mantığı conftest'ten ayrı bir modülde: conftest içindeki bir dal test
edilemez, buradaki fonksiyon edilebilir. Kilit `Base.metadata.drop_all`'u
koruyor, yani yanlış karar bütün bir şemayı siler.

Fonksiyon adı bilerek `test_` ile BAŞLAMIYOR: bir test modülüne import edilen
`test_*` adlı her fonksiyonu pytest test sanıp toplamaya çalışır ve parametresi
olduğu için `fixture 'url_metni' not found` diye kırılır. Adı "daha açıklayıcı"
diye `test_hedefi_...` biçimine çevirmeyin.
"""

from sqlalchemy.engine import make_url

# Yalnızca bu host'larda test veritabanı düşürülebilir. "postgres" docker compose
# ve CI servis konteynerinin adıdır. Ortam değişkeniyle geçiş bilinçli olarak
# YOKTUR (tasarım K6): kolay kaçış kapısı olan kilit, kilit değildir.
IZINLI_HOSTLAR = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})

# Testlerin dokunmasına izin verilen tek veritabanı adı.
TEST_VERITABANI = "ai_triage_test"


def hedef_guvenli_mi(url_metni: str) -> tuple[bool, str]:
    """Adres test veritabanına mı işaret ediyor; (guvenli, sebep) döndürür."""
    try:
        url = make_url(url_metni)
    except Exception:
        # Şüphede kapan: ayrıştıramadığımız bir adrese güvenmeyiz.
        return False, "adres ayrıştırılamadı"

    if url.database != TEST_VERITABANI:
        return False, f"veritabanı adı {TEST_VERITABANI!r} değil: {url.database!r}"

    # Host boşsa (Unix soketi) yerel kabul edilir; uzak bir sokete bağlanılamaz.
    host = url.host or "localhost"
    if host not in IZINLI_HOSTLAR:
        return False, f"host beyaz listede değil: {host!r}"

    return True, ""
```

- [ ] **Step 4: Testleri çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/birim/test_db_kilidi.py -v --no-cov
```
Beklenen: `6 passed`.

- [ ] **Step 5: conftest'i kilide bağla**

`tests/conftest.py` içindeki import bloğuna ekle (diğer `# noqa: E402` satırlarının yanına):

```python
from tests.yardimcilar.db_kilidi import hedef_guvenli_mi  # noqa: E402
```

Ardından `test_motoru` fixture'ındaki şu bloğu:

```python
    if not settings.database_url.endswith("/ai_triage_test"):
        pytest.exit(
            f"Testler yalnızca ai_triage_test üzerinde çalışır. "
            f"Bulunan: {settings.database_url}",
            returncode=3,
        )
```

şununla değiştir:

```python
    # Kararın kendisi tests/yardimcilar/db_kilidi.py'de ve orada ayrıca test
    # ediliyor; burada yalnızca sonucu uygulanıyor.
    guvenli, sebep = hedef_guvenli_mi(settings.database_url)
    if not guvenli:
        pytest.exit(
            f"Testler yalnızca yerel ai_triage_test üzerinde çalışır ({sebep}). "
            f"Bulunan: {settings.database_url}",
            returncode=3,
        )
```

- [ ] **Step 6: Paketi çalıştır**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: **taban + 6** (bu görevin eklediği altı birim testi). Mutlak sayı
bilerek yazılmıyor: Gün 21'de plandaki tahmini sayı gerçekle tutmadı ve planı
baştan yanlışladı. Koşudan önce tabanı kendin ölç, sonra farkı doğrula.

Asıl regresyon kontrolü şu: paket hâlâ koşuyorsa kilit meşru adresi kabul
ediyor demektir. Paket `pytest.exit` ile duruyorsa kilit fazla sıkı bağlandı.

- [ ] **Step 7: Commit**

```bash
git add tests/yardimcilar/db_kilidi.py tests/birim/test_db_kilidi.py tests/conftest.py
git commit -m "fix: test db kilidi host dogruluyor ve query string'i kirmiyor"
```

- [ ] **Step 8: `transkript_engelle` fixture'ını yaz**

`tests/api/conftest.py` dosyasının import bloğuna ekle:

```python
from app.api import speech as speech_modulu
```

Dosyanın SONUNA ekle:

```python
@pytest.fixture
def transkript_engelle(monkeypatch):
    """Yetki/doğrulama testlerinin gerçek faster-whisper modeline ulaşmasını önler.

    DİKKAT — gereksiz görünse bile SİLMEYİN, `dokuman_yazmayi_engelle` ile aynı
    sebepten. Bu testler bugün uç gövdesine hiç girmiyor (401/400 daha önce
    dönüyor), ama tam da korudukları kural gevşerse istek gövdeye ilerliyor ve
    `transcribe` çağrılıyor — yani faster-whisper `medium` modeli indirilip
    yükleniyor: yüzlerce MB indirme, dakikalarca CPU. CI'da bu, testleri on
    dakikanın üstüne çıkaran bilinen tuzağın ta kendisidir.

    Yamalama uç modülünün ad alanına uygulanıyor (`app.api.speech.transcribe`),
    servis modülüne değil: `speech.py` adı kendi ad alanına almış durumda.
    """

    def _asla_cagrilmamali(dosya_yolu: str) -> str:
        raise AssertionError(
            "Gerçek transcribe çağrıldı — uçtaki koruma gevşemiş demektir. "
            "Bu testin gerçek modeli yüklemesi beklenmiyor."
        )

    monkeypatch.setattr(speech_modulu, "transcribe", _asla_cagrilmamali)
```

- [ ] **Step 9: Üç teste fixture'ı ekle**

`tests/api/test_speech_api.py` içinde YALNIZCA imzalar değişir; gövdeler ve
assert'ler olduğu gibi kalır.

`def test_jetonsuz_istek_401_doner(istemci):`
→ `def test_jetonsuz_istek_401_doner(istemci, transkript_engelle):`

`def test_desteklenmeyen_format_400_doner(istemci, yetkili_baslik):`
→ `def test_desteklenmeyen_format_400_doner(istemci, yetkili_baslik, transkript_engelle):`

`def test_cok_buyuk_dosya_400_doner(istemci, yetkili_baslik):`
→ `def test_cok_buyuk_dosya_400_doner(istemci, yetkili_baslik, transkript_engelle):`

- [ ] **Step 10: Testleri çalıştır, hâlâ yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/api/test_speech_api.py -v --no-cov
```
Beklenen: hepsi PASS. Bu adım bir davranış değişikliği DEĞİL — fixture'ın mevcut
sonuçları bozmadığını doğruluyor.

- [ ] **Step 11: Mutasyonla bağlayıcılığı kanıtla — ATLANMAZ (tasarım K9)**

Bu görevin tek gerçek kanıtı budur; fixture'ın eklenmiş olması onu kanıtlamaz.

`app/api/speech.py` içindeki uzantı beyaz listesi kontrolünü geçici olarak
devre dışı bırak (örneğin koşulu `if False and ...` yap), sonra:

```
.venv\Scripts\python.exe -m pytest tests/api/test_speech_api.py::test_desteklenmeyen_format_400_doner -v --no-cov
```

Beklenen: test `AssertionError: Gerçek transcribe çağrıldı ...` ile FAIL eder —
yani gerçek modeli indirmeye çalışmak yerine temiz kırmızı verir. **Mutasyonu
geri al** ve testin yeniden geçtiğini doğrula. Her iki çıktıyı da raporuna
birebir yaz.

- [ ] **Step 12: Paketi çalıştır ve commit'le**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: Step 6'daki sayının **aynısı** — bu adımda yeni test eklenmedi,
yalnızca üç mevcut teste fixture bağlandı. Sayı arttıysa yanlışlıkla test
eklenmiş, azaldıysa bir test kırılmış demektir.

```bash
git add tests/api/conftest.py tests/api/test_speech_api.py
git commit -m "fix: speech yetki/dogrulama testleri gercek STT'ye ulasamiyor"
```

---

### Task 2: Şema — `visit_id` unique ve `doctor_id` index

**Files:**
- Modify: `app/models/visit.py` (`AIRecommendation.visit_id`)
- Create: `app/db/alembic/versions/<otomatik>_gun22_kisitlar.py`
- Create: `tests/entegrasyon/test_doctor_review_kisitlari.py`

**Interfaces:**
- Consumes: Görev 1'den bir şey tüketmez.
- Produces: veritabanı kısıtı; üretim kodunda yeni ad yok.

- [ ] **Step 1: Kısıt testini yaz**

`tests/entegrasyon/test_doctor_review_kisitlari.py` (yeni dosya):

```python
"""Bir ziyaretin en fazla bir yapay zekâ önerisi olabileceğini veritabanı
seviyesinde dondurur.

Bu kural bugün yalnızca ORM'de vardı: Visit.recommendation ilişkisi
`uselist=False` diyor ama sütunda unique kısıtı yoktu. İkinci bir öneri satırı
yazılabilseydi ilişki yalanlanır, ayrıca doktor kuyruğundaki joinedload + LIMIT
sorgusu 20 satır yerine 19 farklı ziyaret döndürüp bekleyen bir vakayı SESSİZCE
düşürürdü — kuyruktan kaybolan hasta demek.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.visit import AIRecommendation, Visit


@pytest.mark.entegrasyon
def test_ayni_ziyarete_ikinci_oneri_yazilamaz(db_oturum):
    ziyaret = Visit(
        id=uuid.uuid4(),
        patient_age=44,
        gender="Kadın",
        symptom_text="Göğsümde sıkışma var",
        status="bekliyor",
    )
    db_oturum.add(ziyaret)
    db_oturum.flush()

    db_oturum.add(
        AIRecommendation(
            visit_id=ziyaret.id,
            triage_code="Kırmızı",
            department="Kardiyoloji",
            onerilen_tetkikler=["EKG"],
        )
    )
    db_oturum.flush()

    # İkinci öneri: veritabanı reddetmeli.
    db_oturum.add(
        AIRecommendation(
            visit_id=ziyaret.id,
            triage_code="Yeşil",
            department="Dahiliye",
            onerilen_tetkikler=[],
        )
    )

    with pytest.raises(IntegrityError):
        db_oturum.flush()
```

- [ ] **Step 2: Testi çalıştır, kırmızı olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/entegrasyon/test_doctor_review_kisitlari.py -v --no-cov
```
Beklenen: `DID NOT RAISE <class 'sqlalchemy.exc.IntegrityError'>` ile FAIL —
bugün ikinci satır sorunsuz yazılıyor. Raporunda bu çıktıyı birebir göster.

- [ ] **Step 3: Modeli güncelle**

`app/models/visit.py` içindeki `AIRecommendation.visit_id` sütununda
`index=True` satırını şununla değiştir:

```python
        # unique: bir ziyaretin en fazla bir önerisi olur. Visit.recommendation
        # ilişkisi zaten uselist=False diyordu; kısıt onu veritabanında da
        # dayatıyor (Gün 22). unique zaten index oluşturur, ayrıca index=True gerekmez.
        unique=True,
```

- [ ] **Step 4: Migration üret**

```
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "gun22 kisitlar"
```

Üretilen dosyayı aç ve `down_revision = "72dffb9e5194"` olduğunu doğrula.
`upgrade()` gövdesinin şunu içerdiğinden emin ol (autogenerate eski index'i
düşürüp unique kısıt eklemeyi kaçırırsa elle yaz):

```python
def upgrade() -> None:
    # Bir ziyarete iki öneri yazılmasını engeller (Gün 22).
    op.drop_index("ix_ai_recommendations_visit_id", table_name="ai_recommendations")
    op.create_unique_constraint(
        "uq_ai_recommendations_visit_id", "ai_recommendations", ["visit_id"]
    )
    # Gün 23'ün doktor bazlı raporlaması bu index'i isteyecek.
    op.create_index(
        "ix_doctor_reviews_doctor_id", "doctor_reviews", ["doctor_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_doctor_reviews_doctor_id", table_name="doctor_reviews")
    op.drop_constraint(
        "uq_ai_recommendations_visit_id", "ai_recommendations", type_="unique"
    )
    op.create_index(
        "ix_ai_recommendations_visit_id", "ai_recommendations", ["visit_id"], unique=False
    )
```

Index adını doğrulamak için önce şunu koş ve çıktıyı raporuna yaz:

```
docker exec ai_triage_postgres psql -U triage -d ai_triage -c "\d ai_recommendations"
```

- [ ] **Step 5: Migration'ı uygula ve geri alınabilirliğini sına**

```
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic downgrade -1
.venv\Scripts\python.exe -m alembic upgrade head
```
Üçü de hatasız bitmeli. Çıktıyı raporuna yaz.

- [ ] **Step 6: Testi çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/entegrasyon/test_doctor_review_kisitlari.py -v --no-cov
```
Beklenen: `1 passed`.

- [ ] **Step 7: Paketi çalıştır**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: Görev 1 sonundaki sayı **+ 1**.

Mevcut bir test `IntegrityError` ile kırmızıya dönerse, o test aynı ziyarete
iki öneri yazıyor demektir — **testi değiştirme**, önce gerçekten öyle mi
diye bak ve raporla.

- [ ] **Step 8: Commit**

```bash
git add app/models/visit.py app/db/alembic/versions/ tests/entegrasyon/test_doctor_review_kisitlari.py
git commit -m "fix: ai_recommendations.visit_id unique, doctor_reviews.doctor_id index"
```

---

### Task 3: Retrieval — `yanik.txt` hasta dili ve ölçüm seti

**Files:**
- Modify: `scripts/kalibre_esik.py` (ILGILI listesi, yanık bölümü)
- Modify: `ornek_dokumanlar/protokoller/yanik.txt`
- Create: `tests/entegrasyon/test_yanik_reranker.py`

**Interfaces:**
- Consumes: `app.services.rag_service.retrieve_and_rerank`,
  `app.services.chroma_service._gomme_fonksiyonu`, `settings.rerank_threshold`
- Produces: yeni ad yok; ölçüm seti ve protokol metni değişir.

**SIRA BAĞLAYICIDIR (tasarım K5).** Tutulan sorgu, `yanik.txt`'ye
dokunulmadan ÖNCE yazılır. Sonradan yazılan tutulan sorgu tutulmuş sayılmaz.

- [ ] **Step 1: Tutulan ikinci sorguyu ÖNCE yaz**

`scripts/kalibre_esik.py` içindeki `ILGILI` listesinde `# yanık` yorumunun
altındaki satırı bul:

```python
    # yanık
    "Kaynar su elimin üstüne döküldü, hemen su toplamaya başladı.",
```

Şununla değiştir:

```python
    # yanık — birinci sorgu: protokolün kelimelerini kullanmadan, hasta ağzından.
    # ESKİ sorgu ("Kaynar su elimin üstüne döküldü, hemen su toplamaya başladı.")
    # yerine yazıldı: yanik.txt'ye hasta dili eklenirken o cümlenin öbekleri
    # belgeye girecekti ve ölçüm kendi kendini doğrulayan bir sızıntıya dönüşecekti
    # — Gün 20'de inme.txt'de tam bu olmuştu (tasarım K4).
    "Çaydanlığı devirdim, kolum fena halde haşlandı ve derim kabardı.",
    # yanık — İKİNCİ, TUTULAN sorgu (tasarım K5). Bu satır yanik.txt'ye
    # dokunulmadan ÖNCE yazıldı ve belge düzenlenirken buna BAKILMADI. Amacı,
    # düzeltmenin tek bir cümleye ezberlenmediğini kanıtlamak: yalnızca birinci
    # sorgu geçip bu geçmezse düzeltme yetersizdir.
    "Ütü elimin üstüne düştü, deri soyuldu ve çok acıyor.",
```

- [ ] **Step 2: Reranker testini yaz**

`tests/entegrasyon/test_yanik_reranker.py` (yeni dosya):

```python
"""Yanık şikayetinin reranker eşiğini geçtiğini gerçek modellerle sınar.

Mevcut `test_turkce_retrieval.py` BİRİNCİ AŞAMAYI (gömme) ölçüyor ve bugün
geçiyor — doğru protokol getiriliyor. Kırık olan ikinci aşama: reranker
`yanik.txt`'ye 0.0005 veriyor, eşik ise 0.005. Sonuç, yanık hastasına
"Belirsiz" denmesi.

Bağlayıcılık üretim yolunun kendisinden geliyor: `retrieve_and_rerank` eşiğin
altında kalınca BOŞ LİSTE döndürüyor. Yani skor yetersizse test doğal olarak
kırmızı olur, ayrıca eşik karşılaştırması yazmaya gerek yok.

`yavas` + `entegrasyon`: gerçek bge-m3 ve bge-reranker-v2-m3 modellerini yükler,
ayakta bir ChromaDB ister.
"""

import uuid
from pathlib import Path

import chromadb
import pytest
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.config import settings
from app.services.chroma_service import _gomme_fonksiyonu
from app.services.rag_service import retrieve_and_rerank

DERLEME = Path(__file__).resolve().parent.parent.parent / "ornek_dokumanlar" / "protokoller"

# app/api/document.py'deki upload ucuyla birebir aynı ayarlar.
BOLUCU = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""],
)


@pytest.fixture(scope="module")
def derleme_koleksiyonu():
    """Derlemenin tamamını üretimle aynı biçimde chunk'layıp geçici koleksiyona gömer."""
    istemci = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    ad = f"test_yanik_reranker_{uuid.uuid4().hex[:8]}"
    koleksiyon = istemci.create_collection(name=ad, embedding_function=_gomme_fonksiyonu())

    belgeler, ustveriler, kimlikler = [], [], []
    for yol in sorted(DERLEME.glob("*.txt")):
        if yol.name.startswith("_"):
            continue  # şablon dosyası derlemeye girmez
        # HAM BAYT okunup decode ediliyor: /document/upload da böyle yapıyor.
        # read_text() Windows'ta CRLF'i LF'e çevirir ve test üretimden FARKLI
        # metin gömer; chunk sınırları kayar (tasarım K10).
        metin = yol.read_bytes().decode("utf-8")
        for sira, parca in enumerate(BOLUCU.split_text(metin)):
            belgeler.append(parca)
            ustveriler.append({"source": yol.name, "chunk_index": sira})
            kimlikler.append(f"{yol.name}_chunk_{sira}")

    koleksiyon.add(documents=belgeler, metadatas=ustveriler, ids=kimlikler)
    try:
        yield koleksiyon
    finally:
        istemci.delete_collection(ad)


@pytest.mark.yavas
@pytest.mark.entegrasyon
@pytest.mark.parametrize(
    "sorgu",
    [
        # Birinci sorgu: kalibrasyon setindekiyle aynı klinik tablo.
        "Çaydanlığı devirdim, kolum fena halde haşlandı ve derim kabardı.",
        # Tutulan sorgu: belge bunun için ayarlanmadı (tasarım K5).
        "Ütü elimin üstüne düştü, deri soyuldu ve çok acıyor.",
    ],
)
def test_yanik_sikayeti_esigi_geciyor(derleme_koleksiyonu, sorgu):
    sonuc = retrieve_and_rerank(sorgu, derleme_koleksiyonu)

    # Boş liste = eşik altında kalındı, yani hasta "Belirsiz" alıyor.
    assert sonuc, "yanık şikayeti eşiği geçemedi; sistem 'Belirsiz' diyecek"
    assert "yanik.txt" in sonuc[0]
```

- [ ] **Step 3: Testi çalıştır, kırmızı olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/entegrasyon/test_yanik_reranker.py -v --no-cov -m ""
```

`-m ""` işaret filtresini kapatır, yoksa `yavas` test seçilmez.

Beklenen: ikisi de `AssertionError: yanık şikayeti eşiği geçemedi` ile FAIL.
İlk koşu modelleri indirebilir, uzun sürer. Raporunda çıktıyı birebir göster.

- [ ] **Step 4: `yanik.txt`'ye hasta dilini ekle**

**YALNIZCA birinci sorguya bakarak düzenle; Step 1'de yazdığın tutulan sorguya
BAKMA** (tasarım K5).

`ornek_dokumanlar/protokoller/yanik.txt` içinde "Yanık — İlk Değerlendirme"
başlığının ALTINA, mevcut ilk maddenin ÜSTÜNE şu bölümü ekle:

```
Yanık — Hastanın Anlattığı Belirtiler
- Hastalar yanığı genellikle şöyle tarif eder: sıcak su, kaynar su veya çay/çorba
  döküldü; ocakta, sobada, ütüde veya fırında yandım; elimi/kolumu yaktım.
- Ciltte kabarma, su toplama, kabarcık, deri soyulması, kızarma ve şiddetli
  yanma hissi tarif edilir; bu tabloların klinik karşılığı bül ve epidermal
  ayrışmadır.
- Haşlanma (sıcak sıvı teması) en sık görülen yanık biçimidir ve çoğunlukla
  el, kol, göğüs ve bacak yüzeyini tutar.
- Elektrik çarpması, kimyasal madde teması ve alev/duman ile temas da bu
  protokol kapsamındadır.
```

Bu metin **protokolün bakış açısından** yazılmıştır: hastaların yanığı genel
olarak nasıl tarif ettiğini anlatır, ölçüm sorgusunu tekrarlamaz (tasarım K4).

- [ ] **Step 5: Testi çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/entegrasyon/test_yanik_reranker.py -v --no-cov -m ""
```

Beklenen: `2 passed`. **Tutulan sorgu da geçmelidir.**

Yalnızca birinci sorgu geçiyorsa düzeltme ezberlenmiş demektir: metni
genişlet, **eşiği indirme** (tasarım K3). Yalnızca ikinci sorgu geçiyorsa
raporla — beklenmedik bir sonuçtur.

- [ ] **Step 6: Paketi çalıştır**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: `passed` sayısı Görev 2 sonundakiyle **aynı** kalır (eklenen test
`yavas` işaretli, bu koşuda seçilmiyor); `deselected` ise **2 artar** — yeni
test parametrize ve iki vakası var.

- [ ] **Step 7: Commit**

```bash
git add ornek_dokumanlar/protokoller/yanik.txt scripts/kalibre_esik.py tests/entegrasyon/test_yanik_reranker.py
git commit -m "fix: yanik protokolune hasta dili, kalibrasyon sorgusu yeniden yazildi"
```

---

## Görevler bittikten sonra: doğrulama

Kontrolcü tarafından yürütülür. **Bu adımlar `main` checkout'undan koşulur** —
`.env` orada, yani doğru Chroma portu (8001) ve backend'le aynı JWT anahtarı
gelir; worktree'lerde `.env` yoktur.

- [ ] **Otomatik**

```
.venv\Scripts\python.exe -m pytest -m "not yavas"
```
Taban 137'nin üstünde (bu plan yedi test ekliyor: altı birim kilit testi + bir
kısıt testi), kapsama **%85'in altına düşmemeli**. Mutlak sayı yerine bu iki
koşul bağlayıcıdır.

- [ ] **Bilgi tabanını yeniden kur — ATLANMAZ**

`yanik.txt` değişti; bilgi tabanı yeniden yüklenmeden kalibrasyon **eski
gömmeleri** ölçer ve çıkan sayı anlamsız olur.

```
.venv\Scripts\python.exe scripts/bilgi_tabani_kur.py
```

Çıktıda 15 dosya ve chunk sayısı görünmeli (yeni bölüm eklendiği için 48'den
büyük olması beklenir).

- [ ] **Kalibrasyonu koş ve eşiğin değişmediğini doğrula**

```
.venv\Scripts\python.exe scripts/kalibre_esik.py
```

Beklenen: **18/19 ilgili**, **0/10 alakasız**. Açık kalan tek sorgu `inme`'nin
karaktersiz yazımı olmalı (tasarım K2). `rerank_threshold` **0.005'te kalır** —
script başka bir değer önerse bile `config.py` değiştirilmez (tasarım K3).

Çıktıyı Ek C'ye yazmak üzere sakla.

- [ ] **Ek C'yi güncelle**

Kapatılan beş maddeyi Ek C'nin ilgili devir bölümlerinde **kapatıldı** olarak
işaretle (satır 326, 640, 878, 1052 bölümleri) ve "Gün 22 · Borç kapatma"
bölümünü ekle: ölçümler, kalibrasyon çıktısı, kapatılan ve açık kalan maddeler.
Açık listede asılı kalan kapalı madde bırakma.

---

## Bitti sayılır

- [ ] Test sayısı 137'den artmış; mevcut hiçbir test değişmemiş veya zayıflamamış
- [ ] DB kilidi host doğruluyor, query string'li meşru URL'i durdurmuyor, kaçış kapısı yok
- [ ] Speech'in üç testi `transcribe` yamalıyor; mutasyon kanıtı raporda (K9)
- [ ] `ai_recommendations.visit_id` unique; ikinci öneri `IntegrityError` veriyor
- [ ] `doctor_reviews.doctor_id` index'li; `upgrade` ve `downgrade` sınandı
- [ ] `yanik.txt` hasta dilini kapsıyor; kalibrasyon sorgusu yeniden yazıldı (K4)
- [ ] Tutulan ikinci yanık sorgusu **de** eşiği geçiyor (K5)
- [ ] Kalibrasyon 18/19 ilgili, 0/10 alakasız; `rerank_threshold` hâlâ 0.005 (K3)
- [ ] Yeni `yavas` test ham bayt okuyor (K10)
- [ ] Kapatılan her madde Ek C'de kapatıldı olarak işaretlendi
- [ ] Yeni bağımlılık eklenmedi (`requirements.txt` değişmedi)
- [ ] Her yeni fonksiyon/alan/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
