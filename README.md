# AI Triage — Yapay Zekâ Destekli Tıbbi Triyaj

Hasta şikayetini **yazılı veya sesli** alan, ilgili klinik triyaj protokolünü
kendi bilgi tabanından getiren (RAG), **yerel** bir dil modeliyle aciliyet kodu
(Kırmızı / Sarı / Yeşil), yönlendirilecek alan ve tetkik önerisi üreten, sonucu
**bir doktorun onayına** düşüren prototip.

Hasta verisi makineden çıkmaz: dil modeli de, konuşma tanıma da, vektör
veritabanı da yerelde çalışır. Bulut LLM servisi kullanılmaz.

> **Klinik uyarı.** Bu bir karar *destek* prototipidir, tanı aracı değildir.
> Her öneri hekim onayına tabidir ve sistem yapay zekânın önerisini doktorun
> kararının yanına ayrı bir kayıt olarak saklar — üzerine yazmaz.

---

## 1. Gereksinimler

| Bileşen | Sürüm / not |
|---|---|
| Python | 3.14 (`.venv` ile) |
| Docker Desktop | Postgres + ChromaDB için |
| [Ollama](https://ollama.com) | Konteynerize **edilmemiştir**, ana makinede çalışır |
| Disk | ~6 GB (LLM 4,7 GB + gömme/reranker modelleri) |
| RAM | 8 GB önerilir (reranker + whisper CPU'da çalışır) |

GPU gerekmez; her şey CPU'da çalışır, karşılığında ilk istek yavaştır (bkz. §7).

---

## 2. Kurulum

### 2.1 Depoyu al ve ortamı hazırla

```bash
git clone https://github.com/BatuhanKocadev/Ai_Triage.git
cd Ai_Triage
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # testler için
```

### 2.2 Ortam değişkenleri

```bash
copy .env.example .env
```

Sonra `.env` içinde **`JWT_SECRET_KEY`'i mutlaka değiştirin**:

```bash
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Diğer değerler yerel kurulum için olduğu gibi çalışır. Tam liste ve her ayarın
ne işe yaradığı `.env.example` içinde yorumlarıyla duruyor.

### 2.3 Altyapıyı kaldır

```bash
docker compose up -d postgres chromadb
```

- Postgres → `localhost:5432`, veritabanı `ai_triage`, kullanıcı/şifre `triage`/`triage`
- ChromaDB → host'ta **8001** (konteyner içinde 8000)

### 2.4 Veritabanı şemasını kur

```bash
.venv\Scripts\python.exe -m alembic upgrade head
```

### 2.5 Başlangıç hesaplarını oluştur

```bash
.venv\Scripts\python.exe -m scripts.seed_users
```

| Kullanıcı | Parola | Rol | Ne yapabilir |
|---|---|---|---|
| `admin` | `admin123` | admin | Her şey; doküman yükleme |
| `doctor` | `doctor123` | doctor | Yalnızca doktor paneli, onay verme |
| `hasta` | `hasta123` | user | Yalnızca şikayet girme |

Script tekrar çalıştırılabilir: var olan hesabın rolü ve parolası listedeki
değerlere senkronlanır.

### 2.6 Dil modelini indir

```bash
ollama pull qwen2.5:7b-instruct
```

### 2.7 Backend'i başlat

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**Kurulumun doğrulaması:**

```bash
curl http://localhost:8000/health/
```

`bagimliliklar` altında `postgres`, `chromadb` ve `ollama` alanlarının üçü de
`"ok": true` olmalı ve `tumu_ok` `true` dönmeli. Biri `false` ise mesaj alanı
nerede takıldığınızı söyler — §7'ye bakın.

### 2.8 Bilgi tabanını kur

Sistem, bilgi tabanı boşken hiçbir şikayete cevap veremez (eşik kapısı devreye
girer ve `Belirsiz` döner). Depodaki 15 örnek protokolü yükleyin:

```bash
.venv\Scripts\python.exe -m scripts.bilgi_tabani_kur
```

### 2.9 Arayüzü başlat

```bash
.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

→ http://localhost:8501

---

## 3. Tam döngüyü deneme

1. `hasta` ile giriş yapın, şikayeti yazın ya da mikrofonla anlatın.
2. Sistem triyaj kodu, alan ve tetkik önerir; kaynak protokolü de gösterir.
3. Çıkış yapıp `doctor` ile girin → **Doktor Paneli** sekmesinde bekleyen vaka görünür.
4. Onaylayın veya değiştirin. Yapay zekânın önerisi **silinmez**, doktor kararı
   ayrı bir satır olarak yazılır — denetim izi budur.

---

## 4. Mimari — kısaca

```
Streamlit (frontend/app.py)
        │  HTTP (requests)
        ▼
FastAPI (app/main.py)
        ├── /auth       JWT, üç rol (admin / doctor / user)
        ├── /ai/analiz  RAG → eşik kapısı → LLM → normalizasyon → kayıt
        ├── /speech     faster-whisper ile ses → metin
        ├── /document   protokol yükleme (yalnızca admin)
        ├── /doctor     bekleyen kuyruk + onay
        └── /health     üç bağımlılığın durumu
                │
    ┌───────────┼───────────────┐
    ▼           ▼               ▼
 Postgres    ChromaDB        Ollama
 (ziyaret,   (protokoller,   (qwen2.5:7b-instruct)
  onay)       bge-m3)
```

**Analiz akışının kritik adımı:** getirilen protokoller bir cross-encoder ile
yeniden sıralanır ve en yüksek skor eşiğin altındaysa istek **LLM'e hiç
gitmez** — `Belirsiz` olarak kaydedilip triyaj bankosuna yönlendirilir. Bu bir
hata değil, bilinçli bir güvenlik kontrolüdür: sistem bilmediği konuda cevap
uydurmaz.

Ayrıntılı mimari, tasarım kararları ve bilinen sınırlar için
[`CLAUDE.md`](CLAUDE.md) ve [`docs/superpowers/ek-c-ilerleme.md`](docs/superpowers/ek-c-ilerleme.md).

---

## 5. Testler

```bash
.venv\Scripts\python.exe -m pytest -m "not yavas"
```

`entegrasyon` işaretli testler gerçek Postgres ister (`docker compose up -d
postgres` ve `ai_triage_test` veritabanı). `yavas` işaretliler gerçek model
indirir, o yüzden varsayılan koşuda dışarıda.

**Tek dosya koşarken `--no-cov` ekleyin** — kapsama kapısı her koşuya
uygulanıyor, odaklı koşu doğal olarak eşiğin altında kalır ve testler geçse
bile paket kırmızı görünür:

```bash
.venv\Scripts\python.exe -m pytest tests/api/test_saglik.py --no-cov
```

---

## 6. Ölçüm (değerlendirme seti)

Sistemin doğruluğu ölçülebilir durumda:

```bash
.venv\Scripts\python.exe -m degerlendirme.calistir
```

29 senaryoyu gerçek uçlara gönderir ve `degerlendirme/sonuclar/` altına tarihli
rapor yazar. **Modül olarak çağrılmak zorunda** (`-m` ile); dosya yolu vererek
çağırmak `ModuleNotFoundError` verir.

Ölçülen son değerler ve nasıl okunmaları gerektiği Ek C'nin "Gün 23" ve
"Gün 24" bölümlerinde.

---

## 7. Sorun giderme

| Belirti | Sebep ve çözüm |
|---|---|
| `/health` → `ollama: false` | Ollama çalışmıyor ya da model yok. `ollama serve` ve `ollama pull qwen2.5:7b-instruct`. |
| `/health` → `chromadb: false` | `docker compose up -d chromadb`. Portun **8001** olduğunu doğrulayın (konteyner içi 8000). |
| `/health` → `postgres: false` | `docker compose up -d postgres`. `.env` içindeki `DATABASE_URL`'i kontrol edin. |
| 8000 portu dolu | Başka bir FastAPI projesi tutuyor olabilir. Onu kapatın ya da `--port 8080` ile başlatıp `BACKEND_URL`'i güncelleyin. |
| İlk analiz ~90 saniye sürüyor | Normal: ilk istek reranker'ı ve LLM'i belleğe alır. Sonrakiler hızlıdır. Demo öncesi bir ısıtma isteği atın. |
| Konteynerden Ollama görünmüyor | `host.docker.internal` Linux'ta çalışmaz. Compose'da `extra_hosts` tanımlı; Linux'ta `OLLAMA_BASE_URL`'i ana makine IP'siyle verin. |
| `scripts/*.py` → `ModuleNotFoundError: app` | Script'ler **modül olarak** çağrılır: `-m scripts.<ad>`. Dosya yolu vererek (`python scripts/seed_users.py`) çağırmak `sys.path`'e repo kökünü değil `scripts/` klasörünü koyar ve `app` bulunamaz. |
| Her şikayete `Belirsiz` dönüyor | Bilgi tabanı boş. §2.8'i çalıştırın. |
| Doküman yükleyince eski sürüm kalıyor | Yükleme aynı dosya adını üzerine yazar; farklı adla yüklediyseniz `DELETE /document?kaynak=<ad>` ile eskisini silin. |

---

## 8. Bilinen sınırlar

Dürüst olmak, teslimden sonra sürpriz yaşamaktan iyidir:

- **Ölçüm setinin gürültü tabanı ~5 puan.** Tek koşumluk doğruluk farkları
  anlamlı değildir; karşılaştırma birden çok koşumun ortalamasıyla yapılmalı.
- **Kör değerlendirme seti hiç Kırmızı vaka içermiyor**, bu yüzden klinik olarak
  en kritik sayı yalnızca etiketlerini geliştiricinin yazdığı sette ölçülebiliyor.
  Onuncu kör senaryo (Kırmızı arketipli) gelecek çalışma olarak duruyor.
- **Tetkik adları tam eşitlikle karşılaştırılıyor**, yani `Hemogram (Tam kan
  sayımı)` ile `Tam kan sayımı` eşleşmiyor ve Jaccard skoru olduğundan düşük
  okunuyor. Bu, modelin yanlış tetkik önerdiği anlamına gelmez.
- **Few-shot örnekleri kapalı** (`settings.few_shot_aktif = False`). Açıkken
  model, getirilmiş protokol kriterini örneklere bakarak ezip bir Kırmızı vakayı
  Sarı'ya düşürüyordu; ölçülüp geri alındı.
- **Streamlit arayüzünün otomatik testi yok.**
- Bilgi tabanındaki protokoller kamuya açık kaynaklardan derlenmiştir; kurumsal
  kullanımda kurumun kendi protokolleriyle değiştirilmelidir.
