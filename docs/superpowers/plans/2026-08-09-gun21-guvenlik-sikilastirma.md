# Gün 21 — Güvenlik Sıkılaştırma Uygulama Planı

> **Ajan çalışanlar için:** ZORUNLU ALT BECERİ: Bu planı görev görev uygulamak için
> superpowers:subagent-driven-development kullanın. Adımlar takip için checkbox
> (`- [ ]`) sözdizimi kullanır.

**Hedef:** Tıbbi veri işleyen sistemin savunulabilir olması için gereken minimum
güvenlik katmanını kurmak: hız sınırı, dosya içerik doğrulaması, hata sızıntısının
kapatılması, CORS ve gizli anahtar uyarıları.

**Mimari:** Dört görev. Görev 1 hız sınırlayıcıyı ve güvenlik ayarlarını kurar
(birim testleriyle), Görev 2 sınırlayıcıyı iki uca bağlar ve test izolasyonunu
sağlar, Görev 3 dosya doğrulamasını ekler, Görev 4 hata gövdesini ve CORS'u kurar.

**Teknoloji:** FastAPI, pytest. **Yeni kütüphane eklenmiyor** — hız sınırlayıcı ve
imza kontrolü elle yazılıyor (tasarım K1, K4).

**Tasarım dokümanı:** `docs/superpowers/specs/2026-08-09-gun21-guvenlik-sikilastirma-design.md`
— çelişkide o belge kazanır, kararlar K1–K10 numaralarıyla oradadır.

## Global Constraints

- **Türkçe açıklama zorunlu.** Eklenen her fonksiyon ve blok yanına tek cümlelik
  Türkçe yorum.
- **Test adları birebir uygulanır** — sekiz güvenlik testinin adı yol haritasından
  gelir, değiştirilemez.
- **Saf TDD.** Önce test, ÇALIŞTIRARAK kırmızı görülür, sonra üretim kodu.
- **Mevcut 102 test yeşil kalmalı ve HİÇBİRİ DEĞİŞTİRİLMEMELİ.** Taban çizgisi
  `main` üzerinde ölçüldü: `102 passed, 2 deselected`, kapsama %81. Mevcut bir test
  kırmızıya dönerse bu, güvenlik eklemesinin akışı bozduğunun kanıtıdır — testi
  değiştirerek değil, kodu düzelterek çözülür.
- **Yeni bağımlılık YOK.** `requirements.txt` değişmiyor.
- **Reddetme mesajları geneldir** (K5): hangi kontrolün tetiklendiği istemciye
  söylenmez, ayrıntı log'a yazılır.
- **Python:** `C:\Users\batuh\Desktop\Ai_Triage-myself\.venv\Scripts\python.exe`
- **PostgreSQL ayakta.** `entegrasyon` işaretli testler `ai_triage_test` ister.
- **Commit mesajları ASCII.**
- **Yol haritasındaki `/auth/token` bu depoda `/auth/login`'dir** (K9).

---

## Dosya Yapısı

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `app/config/config.py` | güvenlik ayarları tek grupta | 1 |
| `app/utils/hiz_sinirlayici.py` | **YENİ** — kayan pencere sayacı + bağımlılık | 1, 2 |
| `tests/birim/test_hiz_sinirlayici.py` | **YENİ** — sayacın kendi davranışı | 1 |
| `tests/conftest.py` | autouse sıfırlama fixture'ı | 2 |
| `app/api/auth.py`, `app/api/ai.py` | sınırlayıcı bağımlılığı | 2 |
| `tests/api/test_guvenlik.py` | **YENİ** — sekiz saldırı testi | 2, 3, 4 |
| `app/utils/dosya_dogrula.py` | **YENİ** — uzantı/boyut/imza kontrolü | 3 |
| `app/api/document.py` | doğrulamayı çağırır | 3 |
| `app/main.py` | exception handler + CORS | 4 |
| `.env.example` | JWT uyarısı + yeni ayarlar | 4 |

---

### Task 1: Hız sınırlayıcı ve güvenlik ayarları

**Files:**
- Modify: `app/config/config.py`
- Create: `app/utils/hiz_sinirlayici.py`
- Create: `tests/birim/test_hiz_sinirlayici.py`

**Interfaces:**
- Consumes: `settings` (`app/config/config.py`)
- Produces: `HizSinirlayici(limit, pencere_sn, saat)` sınıfı — `izin_ver(anahtar) -> bool`,
  `sifirla() -> None`. Ayrıca modül düzeyinde `giris_sinirlayici` ve
  `genel_sinirlayici` örnekleri. Görev 2 bunları içe aktaracak.

- [ ] **Step 1: Güvenlik ayarlarını ekle**

`app/config/config.py` içinde `access_token_expire_minutes` satırının ALTINA ekle:

```python

    # --- Güvenlik (Gün 21) ---
    # Hız sınırı: aynı IP'den `rate_limit_pencere_sn` saniyede kaç istek kabul edilir.
    # Giriş ucu bilerek daha sıkı: kimlik doğrulaması olmadan çağrılabilen tek
    # yazma ucu ve parola deneme saldırısının hedefi.
    rate_limit_genel: int = 30
    rate_limit_giris: int = 5
    rate_limit_pencere_sn: int = 60
    # Dosya yükleme sınırları; uzantı listesi virgülle ayrılır.
    max_upload_mb: int = 10
    izinli_uzantilar: str = "pdf,docx,txt"
    # CORS: varsayılan yalnızca yerel Streamlit. "*" bırakmak savunulamaz.
    cors_origins: str = "http://localhost:8501"
```

- [ ] **Step 2: Sınırlayıcının birim testlerini yaz**

`tests/birim/test_hiz_sinirlayici.py` (yeni dosya):

```python
"""Hız sınırlayıcının kendi davranışını dondurur.

Uç testleri sınırlayıcının KULLANILDIĞINI gösterir; bu testler DOĞRU ÇALIŞTIĞINI.
İkisi birbirinin yerine geçmez — Gün 17+18'de mutasyonla ölçülen kusur tam olarak
bu ayrımın atlanmasıydı.

Saat enjekte ediliyor: gerçek zamana bağlı test, pencere kaymasını ya hiç
sınayamaz ya da rastgele kırılır.
"""

from app.utils.hiz_sinirlayici import HizSinirlayici


class SahteSaat:
    """Testin elle ilerlettiği saat; time.monotonic yerine geçer."""

    def __init__(self):
        self.an = 0.0

    def __call__(self) -> float:
        return self.an

    def ilerlet(self, saniye: float) -> None:
        self.an += saniye


def test_limit_altinda_izin_verir():
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=3, pencere_sn=60, saat=saat)

    assert sinirlayici.izin_ver("1.2.3.4") is True
    assert sinirlayici.izin_ver("1.2.3.4") is True
    assert sinirlayici.izin_ver("1.2.3.4") is True


def test_limit_asilinca_reddeder():
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=2, pencere_sn=60, saat=saat)
    sinirlayici.izin_ver("1.2.3.4")
    sinirlayici.izin_ver("1.2.3.4")

    assert sinirlayici.izin_ver("1.2.3.4") is False


def test_pencere_kayinca_yeniden_izin_verir():
    # Sabit pencere değil KAYAN pencere: eski kayıtlar düşünce kota geri gelir.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=1, pencere_sn=60, saat=saat)
    assert sinirlayici.izin_ver("1.2.3.4") is True
    assert sinirlayici.izin_ver("1.2.3.4") is False

    saat.ilerlet(61)

    assert sinirlayici.izin_ver("1.2.3.4") is True


def test_anahtarlar_birbirini_etkilemez():
    # Bir IP'nin kotayı tüketmesi başka IP'yi engellememeli.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=1, pencere_sn=60, saat=saat)
    sinirlayici.izin_ver("1.2.3.4")

    assert sinirlayici.izin_ver("5.6.7.8") is True


def test_sifirla_sayaclari_temizler():
    # Testler arası izolasyonun dayanağı; bu metot olmadan bir testin tükettiği
    # kota diğerini 429'a düşürür.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=1, pencere_sn=60, saat=saat)
    sinirlayici.izin_ver("1.2.3.4")

    sinirlayici.sifirla()

    assert sinirlayici.izin_ver("1.2.3.4") is True
```

- [ ] **Step 3: Testleri çalıştır, kırmızı olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/birim/test_hiz_sinirlayici.py -v --no-cov
```
Beklenen: beşi de `ModuleNotFoundError: No module named 'app.utils.hiz_sinirlayici'`
ile FAIL. Raporunda bu çıktıyı birebir göster.

- [ ] **Step 4: Sınırlayıcıyı yaz**

`app/utils/hiz_sinirlayici.py` (yeni dosya):

```python
"""Bellek içi kayan pencere hız sınırlayıcı ve onu uçlara bağlayan bağımlılık.

Kütüphane yerine elle yazıldı (tasarım K1): yeni bağımlılık requirements ve Docker
imajına yayılırdı, buna karşılık sayaç kırk satır. Asıl belirleyici test izolasyonu
oldu — burada `sifirla()` bir metot, kütüphanede iç depolamaya elle müdahale.

Sayaçlar süreç belleğinde yaşıyor. Tek uvicorn süreci çalıştığı için bu doğru
çözüm; çok süreçli bir dağıtımda paylaşılan bir depo (Redis vb.) gerekir.
"""

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status

from app.config.config import settings


class HizSinirlayici:
    """Anahtar başına, kayan pencere içinde istek sayar."""

    def __init__(self, limit: int, pencere_sn: int, saat=time.monotonic):
        self.limit = limit
        self.pencere_sn = pencere_sn
        # Saat enjekte edilebilir: testler gerçek zamana bağlı kalmasın.
        self._saat = saat
        self._kayitlar: dict[str, deque] = defaultdict(deque)

    def izin_ver(self, anahtar: str) -> bool:
        """İstek kabul edilebilir mi; kabul edilirse zaman damgasını kaydeder."""
        simdi = self._saat()
        kuyruk = self._kayitlar[anahtar]
        # Kuyruk zaman sırasında olduğu için pencereden çıkanları baştan atmak yeter.
        while kuyruk and simdi - kuyruk[0] >= self.pencere_sn:
            kuyruk.popleft()
        if len(kuyruk) >= self.limit:
            return False
        kuyruk.append(simdi)
        return True

    def sifirla(self) -> None:
        """Tüm sayaçları siler; testler arası izolasyon buna dayanıyor."""
        self._kayitlar.clear()


# Uygulama genelinde tek örnek: sayaçlar süreç belleğinde tutuluyor.
giris_sinirlayici = HizSinirlayici(
    limit=settings.rate_limit_giris, pencere_sn=settings.rate_limit_pencere_sn
)
genel_sinirlayici = HizSinirlayici(
    limit=settings.rate_limit_genel, pencere_sn=settings.rate_limit_pencere_sn
)


def hiz_siniri(sinirlayici: HizSinirlayici):
    """Verilen sınırlayıcıyı uygulayan bir FastAPI bağımlılığı üretir.

    Bağımlılık olarak yazıldı, middleware olarak değil (tasarım K2): yol haritası
    uç bazında farklı sınır istiyor ve hangi ucun korunduğu böylece kodda görünür.
    """

    async def _kontrol(request: Request):
        # İstemci IP'si yoksa (test/proxy) tek bir kovada toplanıyor.
        anahtar = request.client.host if request.client else "bilinmeyen"
        if not sinirlayici.izin_ver(anahtar):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Çok fazla istek. Lütfen biraz bekleyin.",
            )

    return _kontrol
```

- [ ] **Step 5: Testleri çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/birim/test_hiz_sinirlayici.py -v --no-cov
```
Beklenen: `5 passed`.

- [ ] **Step 6: Tüm paketi çalıştır**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: `107 passed`. Sınırlayıcı henüz hiçbir uca bağlı değil, mevcut testler
etkilenmemeli.

- [ ] **Step 7: Commit**

```bash
git add app/config/config.py app/utils/hiz_sinirlayici.py tests/birim/test_hiz_sinirlayici.py
git commit -m "feat: bellek ici hiz sinirlayici ve guvenlik ayarlari (102 -> 107)"
```

---

### Task 2: Sınırlayıcıyı uçlara bağla ve test izolasyonunu kur

**Files:**
- Modify: `tests/conftest.py`
- Modify: `app/api/auth.py:21`
- Modify: `app/api/ai.py:125`
- Create: `tests/api/test_guvenlik.py`

**Interfaces:**
- Consumes: `HizSinirlayici`, `giris_sinirlayici`, `genel_sinirlayici`, `hiz_siniri`
  (Görev 1)
- Produces: `tests/api/test_guvenlik.py` dosyası — Görev 3 ve 4 testlerini bu
  dosyanın SONUNA ekleyecek.

- [ ] **Step 1: Test izolasyon fixture'ını ekle**

Bu adım ATLANMAZ ve önce gelir (tasarım K3). `tests/conftest.py` dosyasının SONUNA
ekle:

```python
@pytest.fixture(autouse=True)
def hiz_sinirlarini_sifirla():
    """Her testten önce hız sayaçlarını temizler.

    TestClient her istekte aynı IP'yi kullanıyor. Sıfırlanmazsa bir testin
    tükettiği kota diğerini 429'a düşürür ve hata "güvenlik çalışıyor" değil
    "test altyapısı bozuldu" biçiminde görünür — teşhisi zor bir sınıf.
    """
    from app.utils.hiz_sinirlayici import genel_sinirlayici, giris_sinirlayici

    giris_sinirlayici.sifirla()
    genel_sinirlayici.sifirla()
    yield
```

- [ ] **Step 2: İlk iki güvenlik testini yaz**

`tests/api/test_guvenlik.py` (yeni dosya):

```python
"""Güvenlik kurallarının testleri; her test bir saldırıyı taklit eder.

Bu dosyadaki testler "kural var mı" değil "kural UCU koruyor mu" sorusunu
yanıtlar. Kuralın kendi davranışı tests/birim/ altında ayrıca sınanıyor.
"""

import pytest

from app.config.config import settings
from tests.yardimcilar.veri_uretici import ziyaret_verisi


@pytest.mark.entegrasyon
def test_ardarda_istek_hiz_sinirina_takilir(istemci, yetkili_baslik, esik_alti):
    # /ai/analiz yerel LLM'i çalıştıran en pahalı uç; sınırsız çağrı servisi tüketir.
    # Gövde bilerek GEÇERLİ gönderiliyor: FastAPI'de gövde doğrulaması ile bağımlılık
    # çözümü aynı aşamada yürüyor ve geçersiz gövdeyle 422'nin 429'dan önce dönme
    # ihtimali var — o durumda test yanlış sebeple kırılır ve hız sınırı hakkında
    # hiçbir şey kanıtlamaz. `esik_alti` fixture'ı gerçek LLM'e gidilmesini önlüyor.
    baslik = yetkili_baslik(kullanici_adi="hasta_ayse", rol="user")
    son_durum = None
    for _ in range(settings.rate_limit_genel + 1):
        son_durum = istemci.post(
            "/ai/analiz", json=ziyaret_verisi(), headers=baslik
        ).status_code

    assert son_durum == 429


@pytest.mark.entegrasyon
def test_giris_denemesi_hiz_sinirli(istemci):
    # Parola deneme saldırısı: /auth/login kimlik doğrulaması olmadan çağrılabilen
    # tek yazma ucu, bu yüzden sınırı diğerlerinden sıkı.
    son_durum = None
    for _ in range(settings.rate_limit_giris + 1):
        son_durum = istemci.post(
            "/auth/login", data={"username": "yok", "password": "yanlis"}
        ).status_code

    assert son_durum == 429
```

- [ ] **Step 3: Testleri çalıştır, kırmızı olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/api/test_guvenlik.py -v --no-cov
```
Beklenen: ikisi de FAIL — sınır bağlı olmadığı için `429` yerine başka bir kod
dönecek (`422` ya da `401`). Raporunda bu çıktıyı birebir göster.

- [ ] **Step 4: Sınırlayıcıyı giriş ucuna bağla**

`app/api/auth.py` dosyasının import bloğuna ekle:

```python
from app.utils.hiz_sinirlayici import giris_sinirlayici, hiz_siniri
```

Ardından `@router.post("/login", response_model=Token)` satırını şununla değiştir:

```python
# Parola deneme saldırısına karşı sıkı sınır (Gün 21).
@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(hiz_siniri(giris_sinirlayici))],
)
```

- [ ] **Step 5: Sınırlayıcıyı analiz ucuna bağla**

`app/api/ai.py` dosyasının import bloğuna ekle:

```python
from app.utils.hiz_sinirlayici import genel_sinirlayici, hiz_siniri
```

Ardından `@router.post("/analiz", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)`
satırını şununla değiştir:

```python
# En pahalı uç: yerel LLM'i çalıştırıyor, kötüye kullanım servisi tüketir (Gün 21).
@router.post(
    "/analiz",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(hiz_siniri(genel_sinirlayici))],
)
```

`Depends` her iki dosyada da zaten `fastapi`'den import edilmiş; yeniden ekleme.

- [ ] **Step 6: Testleri çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/api/test_guvenlik.py -v --no-cov
```
Beklenen: `2 passed`.

- [ ] **Step 7: Tüm paketi çalıştır — EN KRİTİK ADIM**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: `109 passed`.

Herhangi bir MEVCUT test `429` ile kırmızıya dönerse Step 1'deki fixture çalışmıyor
demektir. **Testi değiştirerek çözme** — fixture'ın `autouse=True` olduğunu ve
`tests/conftest.py` içinde (alt dizinde değil) tanımlandığını doğrula.

- [ ] **Step 8: Commit**

```bash
git add tests/conftest.py app/api/auth.py app/api/ai.py tests/api/test_guvenlik.py
git commit -m "feat: hiz siniri /auth/login ve /ai/analiz uclarina baglandi (107 -> 109)"
```

---

### Task 3: Dosya yükleme doğrulaması

**Files:**
- Create: `app/utils/dosya_dogrula.py`
- Modify: `app/api/document.py:70-73`
- Modify: `tests/api/test_guvenlik.py` (dosya sonuna 3 test)

**Interfaces:**
- Consumes: `settings.max_upload_mb`, `settings.izinli_uzantilar` (Görev 1)
- Produces: `dosyayi_dogrula(dosya_adi: str, icerik: bytes) -> str` — geçerliyse
  uzantıyı döndürür, değilse `HTTPException` fırlatır.

- [ ] **Step 1: Üç testi yaz**

`tests/api/test_guvenlik.py` dosyasının SONUNA ekle:

```python
@pytest.mark.entegrasyon
def test_desteklenmeyen_uzantili_dosya_reddedilir(
    istemci, yetkili_baslik, dokuman_yazmayi_engelle
):
    # Yürütülebilir dosya bilgi tabanına hiç girmemeli.
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("zararli.exe", b"MZ\x90\x00", "application/octet-stream")},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 400


@pytest.mark.entegrasyon
def test_cok_buyuk_dosya_reddedilir(istemci, yetkili_baslik, dokuman_yazmayi_engelle):
    # Boyut sınırı bellek tüketimini ve chunk patlamasını engelliyor.
    buyuk = b"a" * (settings.max_upload_mb * 1024 * 1024 + 1)
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("buyuk.txt", buyuk, "text/plain")},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 413


@pytest.mark.entegrasyon
def test_pdf_gibi_gorunen_bozuk_dosya_reddedilir(
    istemci, yetkili_baslik, dokuman_yazmayi_engelle
):
    # Uzantıya güvenmek yetmez: saldırgan .exe dosyasını .pdf diye adlandırabilir.
    # Gerçek PDF "%PDF-" ile başlar.
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("sahte.pdf", b"MZ\x90\x00 bu bir PDF degil", "application/pdf")},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 400
```

- [ ] **Step 2: Testleri çalıştır, kırmızı olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/api/test_guvenlik.py -v --no-cov
```
Beklenen: `2 passed, 3 failed`. Boyut testi ve sahte PDF testi kesin FAIL eder.
`.exe` testi bugünkü kodda da `400` alabilir (mevcut uzantı kontrolü yüzünden) —
o durumda geçmesi normaldir, raporunda belirt.

- [ ] **Step 3: Doğrulayıcıyı yaz**

`app/utils/dosya_dogrula.py` (yeni dosya):

```python
"""Yüklenen dosyanın uzantısını, boyutunu ve gerçek içeriğini doğrular.

Uzantıya güvenmek yetmez: saldırgan yürütülebilir bir dosyayı .pdf diye
adlandırabilir. Bu yüzden dosyanın baş baytlarındaki imza da kontrol ediliyor.
Kütüphane kullanılmadı (tasarım K4): yalnızca üç biçim destekleniyor ve
python-magic Windows'ta ayrıca libmagic ikilisi istiyor.
"""

from fastapi import HTTPException, status

from app.config.config import settings

# Biçimlerin dosya başındaki imzaları. DOCX aslında bir ZIP arşividir.
IMZALAR = {
    "pdf": b"%PDF-",
    "docx": b"PK\x03\x04",
}

# Reddetme mesajı bilerek tek ve genel (tasarım K5): saldırgana hangi kontrolü
# aştığını söylemek, kontrolü aşmasını kolaylaştırır.
GENEL_RET = "Desteklenmeyen dosya"


def izinli_uzantilar() -> set[str]:
    """Ayardaki virgülle ayrılmış listeyi kümeye çevirir."""
    return {u.strip().lower() for u in settings.izinli_uzantilar.split(",") if u.strip()}


def dosyayi_dogrula(dosya_adi: str, icerik: bytes) -> str:
    """Uzantı, boyut ve içerik imzasını kontrol eder; geçerliyse uzantıyı döndürür."""
    uzanti = dosya_adi.lower().rsplit(".", 1)[-1] if "." in dosya_adi else ""
    if uzanti not in izinli_uzantilar():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET)

    # Boyut ayrı bir kodla dönüyor: istemcinin dosyayı küçültmesi gerektiğini
    # bilmesi gerek, bu bir saldırı ipucu değil.
    if len(icerik) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Dosya çok büyük",
        )

    beklenen_imza = IMZALAR.get(uzanti)
    if beklenen_imza and not icerik.startswith(beklenen_imza):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET)

    # TXT'nin imzası yok; geçerli UTF-8 olması tek kontrol edilebilir özelliği.
    if uzanti == "txt":
        try:
            icerik.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET
            )

    return uzanti
```

- [ ] **Step 4: Doğrulamayı upload ucuna bağla**

`app/api/document.py` import bloğuna ekle:

```python
from app.utils.dosya_dogrula import dosyayi_dogrula
```

Ardından şu iki satırı:

```python
        file_content = await file.read()
        extracted_text = ""
        file_extension = file.filename.lower().split('.')[-1]
```

şununla değiştir:

```python
        file_content = await file.read()
        extracted_text = ""
        # Uzantı, boyut ve gerçek içerik imzası burada doğrulanıyor (Gün 21).
        file_extension = dosyayi_dogrula(file.filename, file_content)
```

Alttaki `if/elif/else` zinciri olduğu gibi kalıyor; `else` dalı artık ulaşılamaz
ama savunma katmanı olarak duruyor.

- [ ] **Step 5: Testleri çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/api/test_guvenlik.py -v --no-cov
```
Beklenen: `5 passed`.

- [ ] **Step 6: Tüm paketi çalıştır**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: `112 passed`. Mevcut `/document/upload` testleri geçerli `.txt` içerik
gönderdiği için etkilenmemeli.

- [ ] **Step 7: Commit**

```bash
git add app/utils/dosya_dogrula.py app/api/document.py tests/api/test_guvenlik.py
git commit -m "feat: dosya yukleme uzanti boyut ve imza dogrulamasi (109 -> 112)"
```

---

### Task 4: Hata gövdesi, CORS ve gizli anahtar uyarıları

**Files:**
- Modify: `app/main.py`
- Modify: `.env.example`
- Modify: `tests/api/test_guvenlik.py` (dosya sonuna 3 test)

**Interfaces:**
- Consumes: `settings.cors_origins` (Görev 1)
- Produces: üretim kodunda yeni ad yok; `/` altındaki tüm uçların hata gövdesi
  standartlaşıyor.

- [ ] **Step 1: Son üç testi yaz**

`tests/api/test_guvenlik.py` dosyasının SONUNA ekle:

```python
@pytest.mark.entegrasyon
def test_hata_mesajinda_yigin_izi_yok(istemci, yetkili_baslik, monkeypatch):
    # Yığın izi ve dosya yolları istemciye sızarsa saldırgan iç yapıyı öğrenir.
    # Beklenmeyen bir istisna, /document/liste üzerinden tetikleniyor.
    from app.api import document as document_modulu

    def _patlat():
        raise RuntimeError("gizli-ic-detay-sizmamali")

    monkeypatch.setattr(document_modulu, "get_collection", _patlat)

    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 500
    govde = yanit.text
    assert "gizli-ic-detay-sizmamali" not in govde
    assert "Traceback" not in govde
    assert "RuntimeError" not in govde
    # İzleme kodu, sızıntı yaratmadan log'daki satırla eşleşmeyi sağlıyor.
    assert yanit.json()["izleme_kodu"]


@pytest.mark.entegrasyon
def test_gecersiz_jwt_ile_401_ve_detay_sizmaz(istemci, jeton_uret):
    # İki FARKLI başarısızlık sebebi aynı yanıtı vermeli: "kullanıcı yok" ile
    # "jeton bozuk" ayrımı dışarı verilirse saldırgan geçerli kullanıcı adı
    # numaralandırabilir.
    olmayan_kullanici_jetonu = jeton_uret(kullanici_adi="hic_olmayan", rol="user")
    bozuk_jeton = "bu.gecerli.bir.jwt.degil"

    yanit_a = istemci.get(
        "/auth/me", headers={"Authorization": f"Bearer {olmayan_kullanici_jetonu}"}
    )
    yanit_b = istemci.get("/auth/me", headers={"Authorization": f"Bearer {bozuk_jeton}"})

    assert yanit_a.status_code == 401
    assert yanit_b.status_code == 401
    assert yanit_a.json()["detail"] == yanit_b.json()["detail"]


@pytest.mark.entegrasyon
def test_cors_sadece_izinli_kaynaga_acik(istemci):
    # İKİ yönlü doğrulama şart. Yalnızca "izinsiz origin başlık almamalı" demek
    # bağlayıcı DEĞİL: CORS middleware'i hiç yokken de o başlık dönmez, yani test
    # düzeltmeden önce de geçerdi. İzinli origin'in başlığı ALDIĞINI da
    # doğrulamak, middleware'in gerçekten kurulu olmasını zorunlu kılıyor.
    izinli = [k.strip() for k in settings.cors_origins.split(",") if k.strip()][0]

    izinli_yanit = istemci.get("/health/", headers={"Origin": izinli})
    izinsiz_yanit = istemci.get("/health/", headers={"Origin": "http://kotu-site.example"})

    assert izinli_yanit.headers.get("access-control-allow-origin") == izinli
    assert (
        izinsiz_yanit.headers.get("access-control-allow-origin")
        != "http://kotu-site.example"
    )
```

- [ ] **Step 2: Testleri çalıştır, kırmızı olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/api/test_guvenlik.py -v --no-cov
```
Beklenen: `5 passed, 3 failed`.

DİKKAT — `test_hata_mesajinda_yigin_izi_yok` bu adımda `RuntimeError` fırlatarak
FAIL edebilir (500 dönmek yerine). Sebebi: `TestClient` varsayılan olarak sunucu
istisnalarını yeniden fırlatır. Step 3'teki fixture değişikliği bunu çözüyor.

- [ ] **Step 3: TestClient'ı sunucu istisnalarını yutacak şekilde ayarla**

`tests/conftest.py` içindeki `istemci` fixture'ında `TestClient(app)` çağrısını
şununla değiştir:

```python
    # raise_server_exceptions=False: global exception handler'ın ürettiği 500
    # yanıtı test edilebilsin diye. Varsayılan davranış istisnayı yeniden
    # fırlatır ve handler'ın çıktısı hiç görülmez.
    with TestClient(app, raise_server_exceptions=False) as c:
```

- [ ] **Step 4: Exception handler ve CORS'u ekle**

`app/main.py` dosyasını şununla değiştir:

```python
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, speech, ai, document, auth, doctor
from app.config.config import settings
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Tıbbi Triyaj Pipeline API başlatılıyor...")
    yield
    logger.info("Tıbbi Triyaj Pipeline API kapatılıyor...")

app = FastAPI(
    title="Tıbbi Triyaj Pipeline API",
    description=(
        "Hastalardan alınan ses kayıtlarını metne çeviren (Speech-to-Text) "
        "ve OpenAI modelleri kullanarak semptom analizi gerçekleştiren "
        "yapay zekâ destekli modern REST servis."
    ),
    version="1.0.0",
    contact={
        "name": "Batuhan Koca",
        "url": "https://github.com/BatuhanKocadev/Ai_Triage.git",
        "email": "batuhankocadev@gmail.com",
    },
    license_info={
        "name": "MIT License",
    },
    lifespan=lifespan
)

# İzinli origin'ler ayardan okunuyor; "*" bırakmak herhangi bir siteden tarayıcı
# üzerinden çağrı yapılmasına izin verirdi (Gün 21).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[k.strip() for k in settings.cors_origins.split(",") if k.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def beklenmeyen_hata_yakalayici(request: Request, hata: Exception):
    """Beklenmeyen istisnada tam izi log'a yazar, istemciye yalnızca kod döner.

    Yığın izi ve dosya yolları istemciye sızarsa saldırgan iç yapıyı öğrenir.
    İzleme kodu, sızıntı yaratmadan log'daki satırla eşleşmeyi mümkün kılıyor:
    kullanıcı "şu kodu aldım" der, operatör log'da o kodu arar.
    """
    izleme_kodu = uuid.uuid4().hex[:8]
    logger.exception(
        f"[{izleme_kodu}] Beklenmeyen hata: {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Sunucu hatası", "izleme_kodu": izleme_kodu},
    )


app.include_router(health.router)
app.include_router(speech.router)
app.include_router(ai.router)
app.include_router(document.router)
app.include_router(auth.router)
app.include_router(doctor.router)
```

- [ ] **Step 5: `.env.example`'ı güncelle**

`.env.example` içindeki `JWT_SECRET_KEY` satırının ÜSTÜNE şu uyarıyı ekle:

```
# UYARI: Asagidaki anahtar ornektir. Uretimde MUTLAKA degistirin.
# Uretmek icin: python -c "import secrets; print(secrets.token_hex(32))"
```

Dosyanın SONUNA ekle:

```

# --- Guvenlik (Gun 21) ---
# Ayni IP'den RATE_LIMIT_PENCERE_SN saniyede kabul edilen istek sayisi.
RATE_LIMIT_GENEL=30
RATE_LIMIT_GIRIS=5
RATE_LIMIT_PENCERE_SN=60
# Dosya yukleme sinirlari.
MAX_UPLOAD_MB=10
IZINLI_UZANTILAR=pdf,docx,txt
# CORS: virgulle ayrilmis izinli origin listesi.
CORS_ORIGINS=http://localhost:8501
```

- [ ] **Step 6: Testleri çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/api/test_guvenlik.py -v --no-cov
```
Beklenen: `8 passed`.

- [ ] **Step 7: Tüm paketi çalıştır**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings
```
Beklenen: `115 passed`, kapsama %81'in altına düşmemeli.

- [ ] **Step 8: Commit**

```bash
git add app/main.py .env.example tests/conftest.py tests/api/test_guvenlik.py
git commit -m "feat: global hata govdesi, izleme kodu ve CORS (112 -> 115)"
```

---

## Görevler bittikten sonra: doğrulama

Kontrolcü tarafından yürütülür.

- [ ] **Otomatik**

```
.venv\Scripts\python.exe -m pytest -m "not yavas"
```
`115 passed`, kapsama %81'in altına düşmemeli.

- [ ] **Hız sınırını elle gör**

Backend'i yeni kodla yeniden başlat, aynı uca art arda istek at, `429` aldığını gör.

- [ ] **Gün 19'un uçtan uca döngüsünü tekrarla — ATLANMAZ (tasarım K10)**

Yol haritası bunu açıkça "atlanmaz" diye işaretliyor. `hasta` ile şikayet gir,
analiz sonucunu al; `doctor` ile bekleyen vakada onay ver. Güvenlik eklemeleri bu
akışı bozmamalı. Özellikle dikkat: dosya doğrulaması ya da hız sınırı yanlış
ayarlanmışsa akış sessizce kırılır.

- [ ] **Bilgi tabanına gerçek bir protokol yükle**

`ornek_dokumanlar/protokoller/` altından bir `.txt` yükle; `400` almadığını doğrula.
Doğrulayıcı geçerli dosyaları reddediyorsa `IZINLI_UZANTILAR` ya da imza kontrolü
hatalı.

---

## Bitti sayılır

- [ ] Sekiz güvenlik testi yeşil, her biri önce kırmızı görüldü
- [ ] Sınırlayıcının beş birim testi yeşil (enjekte edilmiş saatle)
- [ ] Mevcut 102 test hâlâ yeşil ve hiçbiri değiştirilmedi
- [ ] Toplam `-m "not yavas"` sayısı 102 → **115**
- [ ] Hız sınırı elle görüldü: art arda istek, `429`
- [ ] Gün 19'un uçtan uca döngüsü tekrarlandı ve bozulmadı
- [ ] `.env.example` JWT uyarısını ve yeni ayarları içeriyor
- [ ] Güvenlik ayarları `config.py`'de tek grupta
- [ ] Yeni bağımlılık eklenmedi (`requirements.txt` değişmedi)
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
