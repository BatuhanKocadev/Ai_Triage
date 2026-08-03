# Gün 17+18 — Doktor uçları: bekleyen vakalar ve onay akışı

**Tarih:** 3 Ağustos 2026
**Dal:** `gun17-doktor-uclari`
**Kaynak:** `AI_Triage_Son_Yol_Haritasi.docx`, "GÜN 17+18 · Doktor uçları" bölümü
**Durum:** Onaylandı (kullanıcı "dosyaya göre ilerle, soru sorma" talimatı verdi; aşağıdaki
açık kararlar bu yetkiyle alınmıştır ve her biri gerekçelidir)

## Amaç

Doktorun bekleyen vakaları listeleyebildiği ve bir yapay zekâ önerisini inceleyip
onaylayabildiği API katmanı. Bugün sistemin "karar destek" iddiasını gerçek kılan parça
yazılıyor: şu anda zincir kararın kendisinde kopuyor — `/ai/analiz` bir öneri üretip
veritabanına yazıyor, ama o öneriyi bir insanın gözden geçirdiğine dair hiçbir kayıt yok.

Bugün UI yazılmıyor. Streamlit doktor paneli Gün 19'un işi; bugünün çıktısı o panelin
konuşacağı sözleşmedir.

## Mevcut durumun özeti

`/ai/analiz` her başvuru için bir `Visit` + `AIRecommendation` çifti yazıyor
(`app/api/ai.py:94-122`). Eşik altında kalan, yani LLM'e hiç gitmeyen başvurular da
yazılıyor — `triage_code="Belirsiz"`, `department="Triyaj Bankosu"`. `Visit.status`
varsayılan olarak `"bekliyor"`. Yani bekleyen vaka kuyruğunun verisi zaten birikiyor,
onu okuyacak ve kapatacak uç yok.

Yetkilendirmede iki rol var: `require_admin_role` ve `require_user_or_admin_role`
(`app/services/auth_service.py:77-92`).

## Kararlar

Yol haritası bu gün için beş soru bırakmıştı. Kod okunduğunda beş tane daha çıktı.
Hepsinin cevabı burada; plan ve subagent brief'leri bu bölümü tek doğru kaynak sayacak.

### K1 — `doctor` üçüncü bir roldür

`users.role` bundan sonra `"admin" | "user" | "doctor"` alır. Yeni bağımlılık
`require_doctor_role`: `"doctor"` ve `"admin"` geçer, `"user"` 403 alır, jetonsuz istek
401 alır.

Admin'in geçmesi yol haritasının açık kararı ("admin her şeyi görür"). Sütun tipi
`String(20)`, yani şema değişikliği gerekmiyor — yalnızca kabul edilen değer kümesi
büyüyor ve `app/models/user.py:16`'daki `# "admin" veya "user"` yorumu güncellenecek.

### K2 — `doctor` rolü `/ai/analiz`'e erişemez, ve seed'e `hasta` hesabı eklenir

`require_user_or_admin_role` **genişletilmiyor**. Hasta başvurusu girmek ile doktor
onayı vermek ayrı yetkilerdir; rol ayrımının tek anlamı budur.

Bunun yakaladığı gerçek tuzak: `scripts/seed_users.py:20` bugün `doctor` adında bir hesap
üretiyor ama rolü `"user"`. O hesabın rolünü `"doctor"` yapmak, sistemde `user` rolünde
hiç hesap bırakmaz ve hasta giriş akışı demo sırasında 403 ile ölür. Bu yüzden seed
listesi şu hâle gelir:

| kullanıcı | parola | rol | ne yapar |
|---|---|---|---|
| `admin` | `admin123` | `admin` | doküman yükler, her şeyi görür |
| `doctor` | `doctor123` | `doctor` | bekleyen vakaları görür, onaylar |
| `hasta` | `hasta123` | `user` | `/ai/analiz` ile başvuru girer |

Script idempotent kalır. Mevcut veritabanında `doctor` hesabı zaten `role="user"` ile
yazılmış olabileceği için, script var olan kaydın rolünü de düzeltir — yoksa "atlandı"
deyip yanlış rolü olduğu gibi bırakır.

> Gün 19 notu: `frontend/app.py` rolü kullanıcı adından tahmin ediyor (`"admin"` → admin
> sekmesi), `/auth/me`'den okumuyor. Üçüncü rol bu tahmini kesin olarak bozar. Düzeltmesi
> Gün 19'un kapsamında, bugün frontend'e dokunulmuyor.

### K3 — `DoctorReview` alan adları

```
doctor_reviews
  id                       Integer, PK
  visit_id                 UUID, FK(visits.id, ondelete="CASCADE"), unique, not null
  doctor_id                Integer, FK(users.id), not null
  onaylanan_triage_code    String(20), not null
  onaylanan_tetkikler      JSON, not null (boş liste olabilir)
  doktor_notu              String, nullable
  created_at               DateTime(timezone=True), not null
```

Yol haritası zaman damgasına `olusturma_zamani` diyor; **`created_at` kullanılıyor**.
Gerekçe: `visits` ve `ai_recommendations` tablolarının ikisinde de `created_at` var
(`app/models/visit.py:30`); üçüncü tabloya farklı bir ad koymak, Gün 19'da bu üç tabloyu
birleştiren sorguları ve raporun veri modeli bölümünü gereksiz yere karıştırır. Domain
alanlarının Türkçe kalması (`onaylanan_tetkikler`, `doktor_notu`) mevcut konvansiyona
uygun — `AIRecommendation.onerilen_tetkikler` ile simetrik: **öneri** yapay zekânın,
**onay** doktorun.

`visit_id` üzerindeki `unique` kısıtı, "bir ziyaret bir kez incelenir" kuralının
veritabanı seviyesindeki karşılığıdır.

### K4 — Onay `AIRecommendation`'a dokunmaz

Bugünün en önemli tasarım kararı ve mentöre anlatılacak cümle: doktor triyaj kodunu
değiştirdiğinde yapay zekânın orijinal önerisi **değiştirilmez, üzerine yazılmaz,
silinmez**. Onay ayrı bir satır olarak `doctor_reviews`'e yazılır.

Gerekçe: tıbbi bir sistemde "yapay zekâ ne demişti, doktor ne dedi" farkı denetlenebilir
olmak zorunda. Gün 23'ün değerlendirme seti de tam olarak bu farkı ölçecek — öneriyi
onayla ezersek o ölçüm imkânsız hâle gelir. Bu, testle kanıtlanacak bir kural
(`test_ai_onerisi_degismeden_saklanir`), yorumla geçilecek bir niyet değil.

### K5 — Reddetme akışı yok

Ayrı bir "reddet" ucu ya da durumu yazılmıyor. Doktor zaten triyaj kodunu ve tetkik
listesini değiştirip onaylayabiliyor; "reddetme" bunun özel bir hâli. Ayrı bir akış
eklemek üçüncü bir durum değeri, ikinci bir uç ve dört test daha getirir — bugünün
kapsamı buna değmez (YAGNI).

`Visit.status` değerleri bu yüzden pratikte `"bekliyor" → "tamamlandi"` olarak kullanılır.
Modeldeki `"incelendi"` ara değeri yerinde bırakılıyor ama bu gün hiçbir kod yolu onu
yazmıyor.

### K6 — Sayfalama: `limit` / `offset`

`GET /doctor/bekleyen?limit=20&offset=0`. `limit`: `ge=1, le=100`, varsayılan `20`.
`offset`: `ge=0`, varsayılan `0`. Sınır dışı değer Pydantic/FastAPI tarafından 422 ile
reddedilir.

Sayfa numarası yerine limit/offset seçildi: FastAPI'de `Query(...)` ile doğrudan ifade
ediliyor, testi tek satır, ve Streamlit tarafında "daha fazla göster" düğmesine birebir
oturuyor.

### K7 — Doktor notu opsiyonel

`doktor_notu` boş bırakılabilir. Doktor yapay zekânın önerisini olduğu gibi onaylıyorsa
not yazmaya zorlamak akışı yavaşlatır ve boş/anlamsız notlar üretir.

### K8 — `onaylanan_triage_code` yalnızca üç değeri kabul eder

Şemada `Literal["Kırmızı", "Sarı", "Yeşil"]`. Geçersiz değer 422 döner.

`"Belirsiz"` bilerek dışarıda: o, yapay zekânın "karar veremedim" çıktısı. Doktorun işi
tam olarak belirsizliği gidermek olduğu için, doktorun "Belirsiz" onaylamasına izin
vermek ucun varlık sebebini boşa çıkarır.

### K9 — Test fixture'ı `create_all` ile kalıyor, alembic'e geçilmiyor

Yol haritasının "TAKILIRSAN" bölümü, entegrasyon testleri için `test_motoru` fixture'ının
`alembic upgrade head` çalıştırmasını öneriyor. **Bu öneri uygulanmıyor.**

Gerekçe: `tests/conftest.py:41` bugün `Base.metadata.create_all` kullanıyor ve mevcut 67
testin tamamı bu fixture'a bağlı. `DoctorReview` `Base.metadata`'ya kaydolduğu için
`create_all` onu da üretir — yani testler alembic'e geçilmeden çalışır. Fixture'ı
değiştirmek bugünün riskini, bugünkü işle ilgisi olmayan bir yerde büyütür.

Migration'ın gerçekten çalıştığı ayrı ve elle doğrulanır: `alembic upgrade head` sonrası
`alembic current` çıktısının head revizyonunu göstermesi, "BİTTİ SAYILIR" listesinin
maddesidir. Yani migration testle değil, doğrulama adımıyla garanti altına alınır.

### K10 — Görevler sıralı yürütülür, paralel değil

Yol haritası "dört subagent paralel çalıştığında bir güne sığıyor" diyor. Görev 3 ve
Görev 4 aynı üç dosyaya (`app/api/doctor.py`, `app/schemas/doctor.py`,
`tests/api/test_doctor_api.py`) yazıyor; paralel çalıştırmak çakışma üretir.
subagent-driven-development de paralel implementer'ı yasaklıyor.

Görevler sırayla koşacak, her birinin sonunda inceleme yapılacak. Gün yine sığar: dört
görevin toplam kapsamı iki yeni dosya, bir migration ve 17 test.

## Uçların sözleşmesi

### `GET /doctor/bekleyen`

Yetki: `require_doctor_role`.

Yanıt: `BekleyenVaka` listesi, en yeni ziyaret önce (`Visit.created_at DESC`).
Yalnızca `status == "bekliyor"` olan ziyaretler. Yapay zekâ önerisi aynı yanıtta gömülü
gelir — doktor iki ekran arasında gidip gelmesin diye. İlişki `joinedload` ile tek
sorguda çekilir.

```
BekleyenVaka:
  visit_id, patient_age, gender, symptom_text, chronic_disease, vitals,
  giris_tipi, created_at,
  ai_onerisi: AIOnerisi | null
      triage_code, department, onerilen_tetkikler, ai_note, sources
```

`ai_onerisi` neden `null` olabilir: `Visit` ve `AIRecommendation` ayrı satırlar ve ilişki
`uselist=False` bir opsiyonel bağ. Bugünkü tek yazma yolu (`_kaydet`) ikisini birlikte
yazıyor, ama şema bunu garanti etmiyor; uç, önerisiz bir ziyaret görürse çökmek yerine
`null` döndürür.

### `POST /doctor/inceleme`

Yetki: `require_doctor_role`.

İstek gövdesi: `visit_id`, `onaylanan_triage_code`, `onaylanan_tetkikler`, `doktor_notu`.

`doctor_id` gövdeden **alınmaz**, JWT'deki kullanıcıdan okunur. Aksi hâlde bir doktor
başka bir doktorun adına onay yazabilirdi.

Davranış:
1. Ziyaret yoksa → `404`.
2. Ziyaretin incelemesi zaten varsa → `409`. Uç önce sorgular; veritabanındaki unique
   kısıt yedek savunmadır (`IntegrityError` yakalanıp yine `409`'a çevrilir).
3. `DoctorReview` yazılır, `Visit.status = "tamamlandi"` yapılır.
4. `AIRecommendation` satırına dokunulmaz (K4).

Yanıt: yazılan incelemenin kendisi (`IncelemeYaniti`) — `id`, `visit_id`, `doctor_id`,
`onaylanan_triage_code`, `onaylanan_tetkikler`, `doktor_notu`, `created_at`.

## Testler

17 test, hepsi önce kırmızı görülecek. Ad ve dağılım yol haritasından birebir alınmıştır.

**Görev 1 — `tests/birim/test_auth_service.py`** (mevcut dosyaya eklenir)
- `test_doktor_rolu_bekleyen_vakalari_gorebilir`
- `test_user_rolu_doktor_ucuna_403_alir`
- `test_admin_doktor_uclarina_erisebilir`

**Görev 2 — `tests/entegrasyon/test_doktor_inceleme_kaliciligi.py`** (yeni paket,
`entegrasyon` işaretli)
- `test_inceleme_ziyarete_bagli_kaydedilir`
- `test_ziyaret_silinince_inceleme_de_silinir`
- `test_ayni_ziyarete_ikinci_inceleme_reddedilir`

**Görev 3 — `tests/api/test_doctor_api.py`**
- `test_bekleyen_liste_sadece_bekliyor_durumundakileri_dondurur`
- `test_liste_en_yeni_once_siralanir`
- `test_liste_sayfalanir`
- `test_liste_ai_onerisini_de_icerir`
- `test_jetonsuz_liste_401`

**Görev 4 — `tests/api/test_doctor_api.py`**
- `test_onay_ziyaret_durumunu_tamamlandi_yapar`
- `test_onayda_doktorun_degistirdigi_triyaj_kodu_kaydedilir`
- `test_onayda_tetkik_listesi_degistirilebilir`
- `test_ai_onerisi_degismeden_saklanir`
- `test_olmayan_ziyaret_icin_404`
- `test_zaten_incelenmis_ziyaret_icin_409`

Doktor uçları Ollama, Whisper, ChromaDB ya da reranker'a hiç dokunmuyor — bu uçlarda
sahte servis gerekmiyor. Buna karşılık `tests/api/conftest.py`'deki `esik_alti` ve
`dokuman_yazmayi_engelle` fixture'larının varlık sebebi olan desen burada da geçerli:
**yetki testi uç gövdesine ilerlerse ne olur?** Doktor uçlarında cevap "gerçek test
veritabanına yazar" — ve `db_oturum` fixture'ı her testi rollback'lediği için bu zararsız.
Yani bu uçlar için ek koruma fixture'ı gerekmiyor; bu, dikkatsizlik değil ölçülmüş bir
karardır.

## Dosya kapsamı

| Görev | Dokunulan dosyalar |
|---|---|
| 1 | `app/services/auth_service.py`, `app/models/user.py`, `scripts/seed_users.py`, `tests/birim/test_auth_service.py` |
| 2 | `app/models/doctor_review.py` (yeni), `app/models/__init__.py`, `app/db/alembic/versions/*` (yeni), `tests/entegrasyon/__init__.py` (yeni), `tests/entegrasyon/test_doktor_inceleme_kaliciligi.py` (yeni) |
| 3 | `app/api/doctor.py` (yeni), `app/schemas/doctor.py` (yeni), `app/main.py`, `tests/api/test_doctor_api.py` (yeni) |
| 4 | `app/api/doctor.py`, `app/schemas/doctor.py`, `tests/api/test_doctor_api.py` |

## Kapsam dışı

- Streamlit doktor paneli (Gün 19)
- Reddetme akışı (K5)
- İncelemeyi düzenleme veya silme uçları
- `app/api/ai.py` içindeki inline Pydantic modellerinin `app/schemas/` altına taşınması —
  yol haritası bunu REFACTOR adımında öneriyor, ama `ai.py`'nin şemalarını oynatmak
  `/ai/analiz`'in 20 testine dokunur. Gün 22'ye bırakılıyor.
- `frontend/app.py`'deki rol tahmininin düzeltilmesi (Gün 19)

## Bitti sayılır

- [ ] `doctor` rolü var, `require_doctor_role` yazıldı, `seed_users.py` üç hesabı üretiyor
- [ ] `doctor_reviews` tablosu migration ile oluştu, `alembic current` = head
- [ ] `GET /doctor/bekleyen` ve `POST /doctor/inceleme` çalışıyor
- [ ] 17 testin tamamı önce kırmızı görüldü, şimdi yeşil
- [ ] Mevcut 67 test hâlâ yeşil
- [ ] Onaydan sonra `AIRecommendation` değişmiyor (test + SQL kanıtı)
- [ ] Her yeni fonksiyon/sütun yanında tek cümlelik Türkçe açıklama var
- [ ] Dal `main`'e birleşti
