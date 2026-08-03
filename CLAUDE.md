# CLAUDE.md

Bu dosya, Claude Code (claude.ai/code) bu depoda kod üzerinde çalışırken referans alması için yazılmıştır.

## Proje özeti

AI Triage (Yapay Zeka Destekli Triage), bir tıbbi triyaj prototip sistemidir. Hastalar şikayetlerini anlatır, backend ilgili klinik protokol dokümanlarını getirir (RAG), yerel bir LLM aciliyeti sınıflandırıp bölüm/tetkik önerir ve sonuç bir doktorun incelemesi için kaydedilir. Kod tabanı, log mesajları, yorumlar ve API alan adları ağırlıklı olarak Türkçedir — mevcut dosyaları düzenlerken bu kurala uyun.

## Sistemi çalıştırma

Tüm stack'i (backend, frontend, Postgres, ChromaDB) Docker Compose ile ayağa kaldırma:

```bash
docker compose up --build
```

- Backend: http://localhost:8000 (FastAPI, `./app:/app/app` bind mount ile dosya değişiklikleri konteynere yansır, ancak konteynerin CMD'sinde `--reload` verilmediği için değişikliklerin etkili olması için konteyneri yeniden başlatmanız gerekir — ya da uvicorn'u `--reload` ile yerelde çalıştırın)
- Frontend: http://localhost:8501 (Streamlit)
- ChromaDB: host'ta 8001 portundan erişilir (konteyner içinde 8000)
- Postgres: localhost:5432, veritabanı `ai_triage`, kullanıcı/şifre `triage`/`triage`

Backend'i yerelde çalıştırmak (Postgres/ChromaDB'ye erişim gerekir, örn. `docker compose up postgres chromadb` ile):

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend'i yerelde çalıştırmak:

```bash
.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

AI analizi (`/ai/analiz`) için ayrıca yerel bir Ollama sunucusu gereklidir — bu konteynerize edilmemiştir; backend ona `OLLAMA_BASE_URL` üzerinden ulaşır (Compose içinde varsayılan `http://host.docker.internal:11434`, konteyner dışında `http://localhost:11434`). Model: `qwen2.5:7b-instruct` (bkz. `app/config/config.py`).

## Veritabanı migration'ları (Alembic)

Konfigürasyon repo kökünde (`alembic.ini`) ama script'ler `app/db/alembic/` altında. `env.py`, `alembic.ini` içindeki URL'i yok sayar ve her zaman `settings.database_url`'i (yani `.env` / ortam değişkeni) okur; böylece veritabanı şifresi sürüm kontrolüne hiç girmez.

```bash
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "mesaj"
.venv\Scripts\python.exe -m alembic upgrade head
```

Yeni modeller `app/models/__init__.py` içinde import edilmelidir (ya da `env.py` çalışmadan önce başka bir şekilde import edilmelidir), aksi halde autogenerate onları `Base.metadata` içinde göremez.

## Yardımcı script'ler

- `scripts/seed_users.py` — üç varsayılan hesabı doğrudan Postgres'te, ORM üzerinden oluşturur: `admin`/`admin123` (rol `admin`), `doctor`/`doctor123` (rol `doctor`), `hasta`/`hasta123` (rol `user`). Migration'lardan sonra, ilk girişten önce çalıştırılmalıdır. **Tam idempotent değildir:** var olan bir kullanıcıyı yeniden eklemez, ama rolü listedekinden farklıysa mevcut satırın rolünü yerinde yeniden yazar (Gün 17 öncesinde `doctor` hesabı `user` rolüyle yazılmıştı). Script canlı `ai_triage` veritabanına karşı çalıştığı için bu yazma işlemi bilinçli tercihtir.
- `scripts/kalibre_esik.py` — mevcut ChromaDB içeriğine karşı ilgili/alakasız sorgular arasındaki reranker skor ayrımını ölçer ve `rerank_threshold` için bir değer önerir. Reranker modeli ya da yüklenen doküman seti değiştiğinde tekrar çalıştırılmalıdır; `/document/upload` ile önceden doküman yüklenmiş olması gerekir.

İkisi de repo kökünden çalıştırılır: `.venv\Scripts\python.exe scripts/<isim>.py`.

## Test ve linting

Testler `tests/` altında, pytest ile çalışır. Bağımlılıklar `requirements-dev.txt` içinde.
`Dockerfile.backend` yalnızca `requirements.txt`'i kurar, yani test **bağımlılıkları**
üretim imajına kurulmaz; ancak `COPY . .` satırı ve `.dockerignore`'da bir dışlama
bulunmaması yüzünden `tests/`, `pytest.ini` ve `requirements-dev.txt` **dosyaları**
imaja kopyalanır. Yapılandırma depo kökündeki `pytest.ini`.

```bash
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -m "not yavas"
```

`entegrasyon` işaretli testler gerçek Postgres ister: `docker compose up -d postgres` ve
`ai_triage_test` veritabanı. Ollama, faster-whisper, ChromaDB ve cross-encoder
(reranker) hiçbir testte çağrılmaz — dördü de `tests/yardimcilar/` altındaki sahte
servislerle değiştirilir (`sahte_llm.py`, `sahte_stt.py`, `sahte_rag.py`) ve **adın
arandığı ad alanında** monkeypatch'lenir; yani adı tanımlayan modülde değil, onu
`import` edip kullanan modülde. Uç testlerinde bu, uç modülüdür
(`app.api.ai.get_structured_completion`, `app.api.ai.get_collection` — `ai.py` bu
adları kendi ad alanına almış durumda). Birim testlerinde ise servis modülü olabilir:
`tests/birim/test_rag_esik_kapisi.py` doğru şekilde `app.services.rag_service` üzerinde
`get_reranker`'ı yamalar, çünkü ad orada tanımlı ve orada aranıyor.

Paketin mevcut durumu ve bilinen kapsam boşlukları için `docs/superpowers/ek-c-ilerleme.md`.

Linter/formatter hâlâ yapılandırılmamıştır.

## Mimari

### AI analizi için istek akışı (`POST /ai/analiz`, `app/api/ai.py`)

1. Yetkilendirme: `require_user_or_admin_role` bağımlılığı JWT'yi doğrular.
2. Getirme (Retrieve): `rag_service.retrieve_and_rerank`, ChromaDB'den (`chroma_service.triage_collection`) `top_k_initial` kadar aday getirir, ardından bunları bir cross-encoder ile (`BAAI/bge-reranker-v2-m3`, `rag_service.py` içinde lazy-load edilen bir singleton) yeniden sıralar ve skorları sigmoid ile normalize eder.
3. Eşik kapısı: en yüksek normalize skor `settings.rerank_threshold`'un altındaysa istek **LLM'e hiç gitmez** — "eşik altında" bir ziyaret olarak `triage_code="Belirsiz"` ile kaydedilir ve doğrudan triyaj bankosuna yönlendirilir. Bu bilinçli bir maliyet/güvenlik kontrolüdür, bug değildir — eşiğin (0.52) nasıl belirlendiğini görmek için `app/config/config.py` içindeki yorumlara ve `scripts/kalibre_esik.py`'ye bakın.
4. LLM: dokümanlar eşiği geçerse, `llm_service.get_structured_completion` yerel bir Ollama modelini `format="json"` ile çağırır ve geçersiz JSON durumunda yeniden dener; yalnızca getirilen dokümanları referans alır (prompt, kaynak dokümanlarda olmayan tetkikleri uydurmayı açıkça yasaklar).
5. Normalizasyon: modelin ham çıktısı sabit triyaj kelime dağarcığına (`Kırmızı`/`Sarı`/`Yeşil`) ve temiz bir tetkik listesine indirgenir — küçük yerel modeller tam yazım/büyük-küçük harfte kayabiliyor (bkz. `_normalize_triage_code`, `_sadelestir`).
6. Kalıcı hale getirme: her sonuç (eşik altı olanlar dahil) `Visit` + `AIRecommendation` çifti olarak yazılır (`app/models/visit.py`), böylece bekleyen vakalar doktor inceleme kuyruğunda görünür.

Eski bulut tabanlı OpenAI SDK istemcisi (`app/services/openai_client.py`) **artık depoda yoktur**; analiz motoru olarak yerini `llm_service.py` (Ollama) almıştır ve adı yalnızca `llm_service.py`'nin docstring'inde tarihsel bir not olarak geçer. Ayarlardaki `openai_api_key` artık isteğe bağlıdır (`app/config/config.py:9`).

### Doküman yükleme (`POST /document/upload`, `app/api/document.py`)

Yalnızca admin. PDF/DOCX/TXT kabul eder, `pdfplumber`/`python-docx` ile metni (ve tabloları, `format_table_to_markdown` ile markdown'a çevirerek) çıkarır, `RecursiveCharacterTextSplitter` ile parçalara ayırır (chunk_size=1000, overlap=200) ve analiz akışının sorguladığı aynı ChromaDB koleksiyonuna upsert eder. Chunk ID'leri deterministiktir (`<dosyaadi>_chunk_<n>`), bu yüzden aynı dosyayı tekrar yüklemek öncekini çoğaltmak yerine üzerine yazar.

### Yetkilendirme (`app/api/auth.py`, `app/services/auth_service.py`)

Standart OAuth2-password-flow JWT auth (`python-jose`, `passlib` üzerinden bcrypt). Kullanıcılar bellekte değil Postgres'te tutulur (`app/models/user.py`) — eski bellek içi `mock_database`'in yerini gerçek tablo almıştır (bkz. `user.py` içindeki docstring).

**Üç rol vardır:** `admin`, `doctor` ve `user`. Route'ları koruyan üç FastAPI bağımlılığı:

| Bağımlılık | Geçen roller | Koruduğu uçlar |
|---|---|---|
| `require_admin_role` | `admin` | `POST /document/upload` |
| `require_user_or_admin_role` | `user`, `admin` | `POST /ai/analiz`, `POST /speech/transkript` |
| `require_doctor_role` | `doctor`, `admin` | `GET /doctor/bekleyen`, `POST /doctor/inceleme` |

`admin` her iki doktor ucundan da geçer ("admin her şeyi görür"). Buna karşılık `doctor` rolü `require_user_or_admin_role` ile korunan uçlardan **403 alır** — hasta başvurusu girmek ile doktor onayı vermek bilinçli olarak ayrı yetkilerdir (tasarım kararı K2, `docs/superpowers/specs/2026-08-03-doktor-uclari-design.md`). `POST /speech/kaydet` bir doğrulama demosudur ve hiçbir yetki bağımlılığı taşımaz.

### Doktor uçları (`app/api/doctor.py`)

- `GET /doctor/bekleyen?limit=20&offset=0` — yalnızca `status == "bekliyor"` ziyaretleri, en yeni önce döndürür. Sıralama `created_at DESC, id DESC`; ikinci anahtar zaman damgaları eşitlendiğinde sayfalamayı belirlenimci kılar. Yapay zekâ önerisi `joinedload` ile aynı sorguda gömülü gelir (`ai_onerisi`, öneri yoksa `null`). `limit`: 1–100, `offset`: `ge=0`; sınır dışı değer 422.
- `POST /doctor/inceleme` — başarıda `201` ve yazılan inceleme satırı. Ziyaret yoksa `404`, ziyaret zaten incelenmişse `409` (önce sorgu, ardından yedek savunma olarak `doctor_reviews.visit_id` unique kısıtı). `doctor_id` istek gövdesinden **alınmaz**, JWT'deki kullanıcıdan okunur.

**Değişmez kural:** doktor onayı `AIRecommendation` satırına asla dokunmaz — üzerine yazmaz, silmez. Onay ayrı bir `doctor_reviews` satırıdır. "Yapay zekâ ne demişti, doktor ne dedi" farkı denetim izidir ve Gün 23'ün değerlendirmesi tam olarak bu farkı ölçecektir (`test_ai_onerisi_degismeden_saklanir`).

### Konfigürasyon (`app/config/config.py`)

Import anında bir kez okunan tek bir `pydantic-settings` `Settings` nesnesi (`settings = get_settings()`), önce ortam değişkenlerinden, sonra `.env`'den beslenir. Docker Compose `CHROMA_HOST`, `CHROMA_PORT`, `OLLAMA_BASE_URL`, `DATABASE_URL`, `JWT_SECRET_KEY`, `OPENAI_API_KEY` değerlerini konteyner ortam değişkeni olarak ayarlar — konteyner içinde bunlar her zaman `.env`'e göre önceliklidir. Servisler (`chroma_service.py`, `rag_service.py`, `llm_service.py`, `auth_service.py`) doğrudan `os.getenv` okumak yerine hepsi buradan `settings`'i import eder.

### Veri modeli (`app/models/`)

- `User` — `users` tablosu, eski auth mock'unun yerini alır.
- `Visit` — tek bir hasta başvurusu (yaş, cinsiyet, şikayet metni, kronik hastalık, vitaller JSON, geliş kanalı `giris_tipi`, durum). `status` modelde `bekliyor`/`incelendi`/`tamamlandi` değerlerini taşır ama pratikte `bekliyor` → `tamamlandi` olarak sürülür: `/ai/analiz` ziyareti `bekliyor` yazar, `POST /doctor/inceleme` onu `tamamlandi` yapar. Ara değer `incelendi`'yi bugün hiçbir kod yolu yazmaz (tasarım kararı K5, ayrı bir reddetme akışı yok).
- `AIRecommendation` — `Visit` ile 1:1 ilişkili (cascade delete), triyaj sonucunu tutar (`triage_code`, `department`, `onerilen_tetkikler`, `ai_note`, `sources`).
- `DoctorReview` — `doctor_reviews` tablosu; incelenen her ziyaret için tek satır (`onaylanan_triage_code`, `onaylanan_tetkikler`, `doktor_notu`, `doctor_id`, `created_at`). `visit_id` **unique**'tir — "bir ziyaret bir kez incelenir" kuralının veritabanı seviyesindeki karşılığı ve uçtaki `409`'un dayanağı — ve ziyaretle birlikte cascade ile silinir. Bu satır `AIRecommendation`'ın yerine geçmez, **yanına** yazılır.

### Frontend (`frontend/app.py`)

Tek dosyalık bir Streamlit uygulaması. Backend ile yalnızca HTTP üzerinden (`BACKEND_URL` ortam değişkeni, varsayılan `localhost:8000`) `requests` kullanarak konuşur — `app/` ile paylaşılan hiçbir Python import'u yoktur. Rol, girişten sonra `/auth/me`'den okunur ve `st.session_state.user_role` içinde tutulur (`frontend/app.py:85`) — kullanıcı adından tahmin **edilmez**; bağlantı yarıda koparsa oturum token'lı ama rolsüz kalmasın diye temizlenir.

Sekme seçimi hâlâ ikili: `user_role == "admin"` ise sohbet + yönetici paneli, aksi hâlde yalnızca sohbet sekmesi. Bunun bugünkü sonucu: **`doctor` rolündeki bir hesap doğru rolle giriş yapar ama sıradan hasta sohbet sekmesine düşer ve gönderdiğinde 403 alır**, çünkü `/ai/analiz`, `/document/upload` ve `/speech/transkript` uçlarının üçü de hâlâ `admin` veya `user` istiyor. Doktor paneli sonraki fazın işidir (Gün 19); o gelene kadar hasta akışını denemek için `hasta` hesabını kullanın.
