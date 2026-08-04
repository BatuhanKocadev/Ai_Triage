# Ek C — İlerleme Çizelgesi

## Gün 11–16 · Test ağı günü (31 Temmuz – 1 Ağustos 2026)

### Bu gün ne yapıldı

Gün 1–16 arasında yazılan üretim kodunun **hiç testi yoktu**. Bu gün geriye
dönük bir test ağı örüldü: `pytest` çatısı kuruldu, gerçek Postgres üzerinde
işlem-bazlı izolasyon veren fixture'lar yazıldı, dış servisler (Ollama,
faster-whisper, ChromaDB, cross-encoder) sahtelerle değiştirildi ve dokuz
görevde toplam **67** test eklendi (68 yazıldı; biri tekrar olduğu için son
düzeltme turunda silindi, aşağıda "Test paketinin kendi zayıflıkları" madde 10).

Yöntem: her test **kırmızı görülmeden sayılmadı**. Testler mevcut davranışı
dondurduğu (karakterizasyon testi) için çoğu ilk koşuda yeşil geçiyor; bu yüzden
her davranış grubu için ilgili üretim satırı kasten bozuldu, testin kırmızıya
döndüğü görüldü ve değişiklik geri alındı. Kırmızı görülmemiş bir test, hiçbir
şey ölçmediği hâlde güven veren bir testtir — bu gün boyunca kabul edilmedi.

Global kısıt: **bu gün üretim kodu yazılmadı.** Tek istisna, bir testin ortaya
çıkardığı gerçek hata idi (aşağıdaki hata tablosu, satır 1) ve kullanıcı
onayıyla uygulandı.

---

### Ölçümler

| Ölçüm | Değer |
|---|---|
| Toplam test sayısı | **67** (`pytest --collect-only` → 67 tests collected) |
| Geçen / kalan | **67 passed / 0 failed** (`pytest -m "not yavas"`, 21.42 sn) |
| Kapsama (`app/`) | **%72** (536 ifadenin 149'u kapsanmıyor) |
| Test dosyası sayısı | 8 (`tests/api/` 4, `tests/birim/` 4) + 2 `conftest.py` (`tests/`, `tests/api/`) |
| Uyarı | 2 (ikisi de üçüncü parti kütüphane, aşağıda açıklandı) |
| Hiç test görmeyen modüller | **Yok** — `app/` altındaki 21 **içe aktarılabilir** modülün hepsi kapsama raporunda görünüyor. Ancak dört modülde yalnızca modül iskeleti (import'lar, `def`/dekoratör satırları) çalışıyor, **fonksiyon gövdeleri hiç çalışmıyor**: `document.py` (%17), `llm_service.py` (%24), `stt_service.py` (%37), `chroma_service.py` (%50). Gerekçeleri aşağıdaki tabloda. |

**"21 modül" ile "24 dosya" farkı.** `app/` altında toplam 24 `.py` dosyası var
(`find app -name "*.py" | wc -l` → 24), kapsama raporunda 21 satır görünüyor.
Aradaki üçü Alembic'e ait: `app/db/alembic/env.py` ve
`app/db/alembic/versions/` altındaki iki migration. Hiçbiri testlerde import
edilmiyor **ve** coverage.py'nin dosya taraması `__init__.py` içermeyen alt
dizinlere inmiyor (`app/db/alembic/` içermiyor), dolayısıyla bu üç dosya
kapsama paydasına hiç girmiyor. "Hiç test görmeyen modül yok" iddiası bu üçü
kapsamaz — migration'lar da test edilmiyor, yalnızca ölçülmüyor.

`-m "not yavas"` bugün **hiçbir testi elemiyor**: `yavas` işaretli test yok
(`grep -rn "mark.yavas" tests/` boş döner). 67 sayısı paketin tamamıdır.
İşaret ileride Ollama/Whisper modeli gerektiren testler eklenirse diye
`pytest.ini` içinde hazır bekletiliyor.

#### Test dosyası başına dağılım

| Dosya | Test | Neyi donduruyor |
|---|---|---|
| `tests/birim/test_triyaj_normalizasyon.py` | 22 | `_sadelestir`, `_normalize_triage_code`, `_normalize_tetkikler` |
| `tests/api/test_speech_api.py` | 11 | `/speech/transkript` sözleşmesi (Whisper modeli yüklenmeden) |
| `tests/api/test_ai_analiz_api.py` | 10 | `/ai/analiz` sözleşmesi: 422/200, eşik altı yolu, DB yazımı |
| `tests/birim/test_rag_esik_kapisi.py` | 8 | Eşik altı / üstü / tam sınır davranışı |
| `tests/api/test_auth_api.py` | 6 | Jeton ve rol kapıları (401 / 403) |
| `tests/birim/test_auth_service.py` | 5 | Parola hash'i, JWT üretimi ve süresi |
| `tests/api/test_saglik.py` | 3 | `/health` + veritabanı izolasyon tripwire'ı |
| `tests/birim/test_config.py` | 2 | Ayarların ortamdan okunduğu (import zinciri sağlam) |

#### Modül bazında kapsama

`pytest --cov=app --cov-report=term-missing -m "not yavas"` çıktısı:

```
Name                             Stmts   Miss  Cover   Missing
--------------------------------------------------------------
app\api\__init__.py                  0      0   100%
app\api\ai.py                       88      3    97%   141-143
app\api\auth.py                     20      7    65%   26-38, 47
app\api\document.py                 93     77    17%   18-32, 35-45, 48-62, 70-143
app\api\health.py                    7      0   100%
app\api\speech.py                   50      1    98%   34
app\config\config.py                22      0   100%
app\db\__init__.py                   0      0   100%
app\db\database.py                  11      4    64%   19-23
app\main.py                         15      0   100%
app\models\__init__.py               3      0   100%
app\models\user.py                  12      1    92%   24
app\models\visit.py                 33      2    94%   44, 73
app\schemas\auth.py                  8      0   100%
app\schemas\speech.py                2      0   100%
app\services\auth_service.py        52      2    96%   66, 83
app\services\chroma_service.py       8      4    50%   17-20
app\services\llm_service.py         33     25    24%   38-71, 76-83
app\services\rag_service.py         40      6    85%   20-23, 29-30
app\services\stt_service.py         27     17    37%   23-28, 33-42, 48-57
app\utils\logger.py                 12      0   100%
--------------------------------------------------------------
TOTAL                              536    149    72%
```

**%72'yi doğru okumak.** Kapsanmayan 149 ifadenin büyük çoğunluğu bilinçli bir
seçimin sonucu, ihmal değil:

| Modül | Neden düşük | Bilinçli mi |
|---|---|---|
| `llm_service.py` %24 | Ollama'ya HTTP isteği atan gövde. Testlerde `sahte_llm.py` ile değiştiriliyor; gerçek çağrı hiçbir testte yapılmıyor. | Evet — Global Kısıt: dış servis çalıştırılmaz |
| `stt_service.py` %37 | faster-whisper modelini yükleyen gövde. `sahte_stt.py` ile değiştiriliyor. | Evet |
| `chroma_service.py` %50 | `get_collection()` içindeki tembel `HttpClient` kurulumu; ChromaDB ayakta olmadan çalışamaz. | Evet |
| `document.py` %17 | `/document/upload` gövdesi PDF/DOCX ayrıştırıp ChromaDB'ye upsert ediyor. Bugün yalnızca **yetki kapısı** test edildi (403/401), gövde değil. | Evet, ama boşluk olarak kayıtlı (aşağıda) |
| `database.py` %64 | `get_db()` gövdesi testlerde `dependency_overrides` ile değiştiriliyor; test oturumu onun yerine geçiyor. | Evet |
| `user.py`, `visit.py` | Yalnızca `__repr__` metotları (satır 24 / 44 / 73). | Evet — tanılama amaçlı |
| **`auth.py` %65** | **`/auth/login` (26-38) ve `/auth/me` (47) hiçbir testten geçmiyor.** | **Hayır — gerçek boşluk** |

---

### Testlerin ortaya çıkardığı hatalar

| # | Hata | Kök neden | Düzeltme | Dosya |
|---|---|---|---|---|
| 1 | Kullanımdan kaldırılmış (deprecated) Starlette sabiti: `StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.` Uyarı Görev 8'de, yeni yazılan 422 testleri çalıştırıldığında ilk kez göründü. | Starlette bu sabiti RFC 9110'un adlandırmasına uydurmak için yeniden adlandırdı; eski ad hâlâ çalışıyor ama her kullanımda uyarı basıyor ve ileride kaldırılacak. Uyarının **16 gün boyunca görünmemesinin sebebi**: `app/` içinde bu sabit yalnızca bu iki satırda geçiyor ve o iki satır 422 hata dallarında; hiçbir test o dallara ulaşmamıştı, dolayısıyla kod hiç çalıştırılmamıştı. Kapsama raporundaki "kapsanmayan satır", çalıştırılmadığı için **görünmeyen bir kusuru** da saklıyordu. | Her iki satırdaki `status.HTTP_422_UNPROCESSABLE_ENTITY` → `status.HTTP_422_UNPROCESSABLE_CONTENT`. Sayısal değer aynı (422), davranış değişmiyor. Testler zaten 422 assert ettiği için sayısal eşdeğerliği paketin kendisi kanıtlıyor: düzeltmeden sonra `test_speech_api.py` 11/11 yeşil **ve** uyarı çıktıdan kayboldu. | `app/api/speech.py:73`, `app/api/speech.py:80` |

> Bu, test ağının bulduğu **tek** üretim sorunudur ve bu günün başlık sonucudur.
> Bulgu, testin bir assert'i patlatmasıyla değil, daha önce hiç çalıştırılmamış
> bir kod yolunun ilk kez çalıştırılmasıyla ortaya çıktı — geriye dönük test
> yazmanın tipik getirisi budur.
>
> Global Kısıt "bu gün üretim kodu yazılmaz" diyordu; istisnası "bir testin
> ortaya çıkardığı gerçek hata". Kullanıcı 1 Ağustos 2026'da bu istisnanın
> uygulanmasını açıkça onayladı. **Bu iki satır, bugün `app/` altında yapılan
> tek değişikliktir.**

#### Uyarı filtresi hakkında önemli düzeltme

`pytest.ini` içinde `filterwarnings = error::DeprecationWarning:app.*` girdisi
var. Bu girdi yukarıdaki uyarıyı **hiçbir zaman yakalayamazdı** ve bunun
birbirinden **bağımsız iki** sebebi var:

1. **Kategori.** `StarletteDeprecationWarning`, `DeprecationWarning`'den değil
   **`UserWarning`**'den türüyor (`starlette/exceptions.py:36`).
2. **Modül kapsamı.** Kategori düzeltilse bile `:app.*` kapsamı tutmaz.
   Starlette uyarıyı `stacklevel=3` ile basıyor (`starlette/status.py:200-204`),
   yani uyarı `app.api.speech`'e değil bir **üstteki çerçeveye** atfediliyor.

Ölçüm (mutasyon: `speech.py`'deki iki sabit geçici olarak eski
`HTTP_422_UNPROCESSABLE_ENTITY` adına döndürüldü, ölçümden sonra
`git checkout` ile geri alındı; koşu `pytest tests/api/test_speech_api.py`):

| `filterwarnings` değeri | Sonuç |
|---|---|
| `error::UserWarning:app.*` | **Ateşlemiyor.** `11 passed, 4 warnings`. Kategori artık doğru, ama uyarı `app.*` modülüne atfedilmiyor: çıktıda kaynak olarak `.venv/Lib/site-packages/fastapi/routing.py:344` görünüyor. `stacklevel=3`'ün doğrudan kanıtı. |
| `error::UserWarning` | Ateşliyor, ama hedefe hiç ulaşmadan: `tests/conftest.py:14`'teki `from fastapi.testclient import TestClient` sırasında üçüncü parti uyarı hataya dönüyor ve paket **toplanamıyor** (`ImportError while loading conftest`). |
| `error:.*HTTP_422_UNPROCESSABLE_ENTITY.*:UserWarning` | **Ateşliyor ve yalnızca hedefi vuruyor.** `2 failed, 9 passed, 2 warnings` — kalan iki uyarı üçüncü parti olanlar, onlara dokunmuyor. |

Dolayısıyla önceki metnin "filtreyi genişletmek çözüm değildir" sonucu **fazla
güçlüydü**. Doğrusu: çıplak `error::UserWarning` (ve `error`) gerçekten
kullanılamaz — üçüncü parti gürültüsünü de hataya çevirir, hatta toplama
aşamasında paketi durdurur. Ama **mesaj kapsamlı** bir filtre temiz bir
seçenekti: hedefi hataya çevirir, üçüncü parti uyarılara dokunmaz. Bugün
değerlendirilmedi; kayıt dışı kalmasın diye buraya yazıldı.

> **Tuzak:** mesaj kapsamlı filtre `pytest.ini`'nin `filterwarnings` satırına
> yazılmalı — pytest ini filtrelerinde mesaj desenini **regex** olarak işler.
> Komut satırındaki `-W` ise (CPython davranışını taklit ederek) mesaj desenini
> kaçırır (escape) ve birebir eşleştirir; aynı desen orada sessizce çalışmaz.
> Ölçüm sırasında bu ayrım bizzat gözlendi.

**`pytest.ini`'deki `filterwarnings` satırı silinmedi.** Bütünsel inceleme onu
ölü konfigürasyon sayıp kaldırılmasını önerdi, kullanıcı kararı bunu ezdi:
satır *bu* uyarı için atıl, ama `app/` kodundan varsayılan `stacklevel` ile
fırlatılan bir `DeprecationWarning` için hâlâ ateşler. Silmek gerçek bir
korumayı kaldırırdı.

Bu bölüm, "uyarı filtrem var, demek ki korunuyorum" varsayımının yanlış
olabileceğinin somut örneğidir — üstelik **iki ayrı** sebepten.

#### Kalan iki uyarı (bilinçli olarak bırakıldı)

1. `fastapi/testclient.py:1` — `httpx` ile `starlette.testclient` kullanımı
   deprecated, `httpx2` öneriliyor. FastAPI'nin kendi dosyasından geliyor.
2. `chromadb/telemetry/opentelemetry/__init__.py:128` — `asyncio.iscoroutinefunction`
   Python 3.16'da kaldırılacak.

İkisi de üçüncü parti kütüphane kaynaklıdır, `app/` kodumuzdan gelmiyor ve bu
görevin kapsamı dışındadır. Bağımlılık yükseltmesiyle çözülürler.

---

### Bilinen kapsam boşlukları (test ağının göremediği yerler)

Bu tablo bugünün en değerli çıktılarından biri: testler hangi davranışları
**dondurmadığını** da belgeliyor. Aşağıdakiler mutasyon denemelerinde hayatta
kalan ya da incelemelerde tespit edilen gerçek boşluklardır. "Hayatta kaldı"
demek: o satır silinse ya da bozulsa paket yine 67/67 yeşil verir.

**Kapsam beyanı — bu ağ yalnızca backend'i ölçüyor.** `--cov=app` paydası
`app/` ile sınırlı. `frontend/app.py` (339 satır; tek dosyalık Streamlit
uygulamasının tamamı) ve `scripts/seed_users.py` (50 satır; admin/doctor
hesaplarını yaratan script) **hiç test görmüyor ve bu belgedeki hiçbir
yüzdenin içinde değil** — %72 onlara rağmen değil, onlar sayılmadan hesaplandı.
"Bu paket fark etmeden üretimde ne bozulabilir?" sorusunun en büyük dürüst
cevabı aşağıdaki satırlar değil, bu iki dosyadır: kullanıcının gördüğü
uygulamanın tamamı ve ilk girişi mümkün kılan script. Aşağıdaki tablo
backend'in içindeki boşlukları listeler.

| Dosya:satır | Korumasız davranış | Neden önemli |
|---|---|---|
| `app/api/ai.py:141-143` | `except Exception` → `relevant_documents = []`. RAG çökerse hasta sessizce "Belirsiz / Triyaj Bankosu"na düşüyor — meşru eşik-altı sonucuyla **aynı** kod yolundan. | Doktor "bu şikayete uygun protokol yok" ile "getirme sistemi bozuk"u ayırt edemiyor. Davranışsal olarak dosyadaki en önemli kapsanmamış dal. Kapsama raporunda da tek eksik satır grubu (`ai.py` %97). |
| `app/api/auth.py:26-38` | **`/auth/login` ucu hiçbir testten geçmiyor.** Yanlış parolada 401 dönen dal, `verify_password`'ün gerçek kullanıcıya karşı çalışması ve jetonun `ACCESS_TOKEN_EXPIRE_MINUTES` ile dağıtılması korumasız. | Testler jetonu `jeton_uret` fixture'ıyla doğrudan üretiyor, giriş ucundan geçmiyor. Yani "yanlış parolayla giriş yapılamaz" iddiası bugün **hiçbir test tarafından savunulmuyor** — uygulamanın en temel güvenlik iddiası. Bu, bugünkü ölçümde ortaya çıkan yeni bulgudur. |
| `app/services/rag_service.py:82` | `if score >= threshold` filtresi tamamen silinse hiçbir test yakalamaz. Sınır operatörü pinli, maddenin varlığı değil. | Yakalanmayan senaryo üretimde tipik: en iyi doküman eşiği geçerken `[:top_k_final]` içindeki alttaki geçmiyor (`config.py:31-34`'e göre ilgili skorlar 0.502-0.664, eşik 0.52). Yani egzotik değil, olağan durum. |
| `app/services/auth_service.py:83` | `require_admin_role`'ün **izin veren** dalı (`return current_user`) hiçbir testten geçmiyor. Bugün yalnızca reddeden dal (403) test edildi. | "Admin doküman yükleyebilir" iddiası korumasız. Test etmek gerçek ChromaDB gerektirdiği için bugün yapılamadı; koleksiyonu sahtelemek ya da CI'da Chroma ayağa kaldırmak gerekir. |
| `app/api/document.py:70-143` | `/document/upload` gövdesinin tamamı (PDF/DOCX/TXT ayrıştırma, chunk'lama, deterministik chunk ID üretimi, ChromaDB upsert) test edilmiyor — modül %17. | Aynı dosyanın tekrar yüklenince çoğaltmak yerine üzerine yazması (`<dosyaadi>_chunk_<n>`) belgelenmiş bir davranış ama pinli değil. ChromaDB bağımlılığı yüzünden ertelendi. |
| `app/api/document.py:141-143` | Geniş `except Exception` → jenerik 500 "Upload error". **Altyapı arızası** (ChromaDB erişilemez) ile **öngörülmemiş her iç hata** (splitter'ın patlaması, `file.filename` `None` gelince `AttributeError`, …) çağırana ayırt edilemez tek bir 500 olarak dönüyor. Girdi hataları bu kapsamda **değil**: satır 139-140'taki `except HTTPException: raise`, gövde içinde üretilen altı 400'ü olduğu gibi geçiriyor (bozuk PDF `:78-80`, bozuk DOCX `:84-86`, kodlama hatası `:90-91`, desteklenmeyen uzantı `:93`, boş içerik `:96`, chunk'lama başarısız `:107-108`). | Görev 9'un 1. mutasyonu sırasında gözlemlendi: yetki kapısı devre dışı bırakılınca istek gövdeye ilerledi ve ChromaDB'ye ulaşamayıp bu dala düştü (`Upload error: Could not connect to a Chroma server`). `ai.py:141-143`'teki desenin aynısı: gerçek bir arıza, olağan bir sonuç gibi görünüyor. Girdi/altyapı ayrımının doğru yapılmış olması bu ucun güçlü yanı; kalan boşluk, altyapı arızasının kendi içinde teşhis edilemez olması. Kayıt dışı kalmasın diye buraya yazıldı. |
| `app/api/ai.py:66` | `maketrans` tablosunun 12 eşlemesinden 4'ü (küçük harf `ğ ü ö ç`) pinlenmemiş; hiçbir test girdisi bu harfleri içermiyor (ne testlerde ne `GECERLI_TRIYAJ_KODLARI`'nda). | Tablo bozulursa modelin o harfleri içeren çıktıları sessizce "Belirsiz"e düşer. Tek bir parametrize vakası (`"ĞÜÖÇ ğüöç"`) kapatır. |
| `app/services/auth_service.py:61-69` | `get_current_user`'da `None` jeton koruması yok; `jwt.decode` `except JWTError` ile sarılı ama `AttributeError` o hiyerarşide değil. | Bugün ulaşılamaz (`oauth2_scheme` `auto_error=True` ile 401'i önce döndürüyor), ama satır 27 yeniden yapılandırılırsa ya da `get_current_user` doğrudan çağrılırsa **500 döner**. Bugün deneysel olarak doğrulandı: `auto_error=False` yapıldığında `jose/jws.py:180: AttributeError: 'NoneType' object has no attribute 'rsplit'` → 401 yerine 500. Önerilen sertleştirme: `try` bloğunun başına `if not token: raise auth_exception`. |
| `app/services/auth_service.py:66` | Jetonda `sub` ya da `role` eksikse 401 dönen dal test edilmiyor. Kapsama raporunda da eksik satır olarak görünüyor. | İmzası geçerli ama eksik alanlı bir jeton üretilebilirse bu dal tek savunma hattı. |
| `app/services/auth_service.py:46-47` | Jetonun 15 dakikalık varsayılan süresi pinli değil. `test_jeton_kullanici_adi_ve_rol_tasir` `"exp"` alanının varlığını assert etmiyor; bu iki satır silinse (jetonlar süresiz olur) hiçbir test kırılmaz. | Süresiz jeton ciddi bir güvenlik gerilemesi olur. Düzeltmesi tek satır: `assert "exp" in icerik`. |
| `app/api/ai.py:80` | `logger.warning` silinse paket yeşil kalır. Satır **çalışıyor** ("Mavi" ve "" vakaları oradan geçiyor) ama loga assert eden yok. | Yalnızca tanılama yan etkisi korumasız; dönüş değeri tam pinli. Düşük öncelik; `caplog` ile tek satırda kapatılır. |
| `app/api/speech.py:84-88` | Gizlilik özelliği — şikayet metninin (sağlık verisi) loglanmaması — yalnızca **doğru**, pinlenmiş değil. Log satırı `len(metin)` ve süreyi basıyor ama `caplog` kullanan test yok; `f"...transkript={metin}"` yazılsa 11 testin hepsi yeşil kalır. | İnceleyici bunu "en değerli 12. test adayı" olarak nitelendirdi. Sağlık verisi loglama KVKK açısından gerçek bir risk. |
| `app/api/speech.py` `sure_saniye` büyüklüğü | `sure_saniye >= 0` assert'i neredeyse boş: 1000x'lik bir birim hatası yeşil geçer (mutasyonla kanıtlandı). **Aralık assert'i bunu çözmez**: sahte `transcribe` anında döndüğü için `sure_saniye` her testte 0.0'dır, 1000 ile çarpılsa yine 0.0 olur. | Tek gerçek çözüm uyuyan bir sahte + zaman penceresi assert'i, o da kırılgan (flaky) test demek. Bilinçli karar: `>= 0` kalsın, büyüklüğün pinlenmediği burada kayıt altına alınsın. |
| `app/api/speech.py:95-96` | `finally: os.remove(gecici_dosya_yolu)` silinse hiçbir test kırmızı olmaz. | Geçici dosya sızıntısı; manuel kontrol yapıldı ve doğru çalışıyor, ama otomatik koruma yok. |
| `app/api/speech.py:34` | `/speech/kaydet` ucu (Pydantic doğrulama gösterimi: UUID / regex / EmailStr / min-max) hiçbir testten geçmiyor. | Analiz akışının parçası değil, bu yüzden düşük öncelikli. |

---

### Test paketinin kendi zayıflıkları

Boşluklar üretim kodunun neyinin korunmadığını anlatıyor; bu bölüm **testlerin
kendisindeki** sorunları kayıt altına alıyor. Hepsi görev incelemelerinde
tespit edilip bilinçli olarak ertelendi.

| # | Konu | Ayrıntı |
|---|---|---|
| 1 | Yanıltıcı test yorumu | `test_bos_koleksiyon_sonucu_bos_liste_doner`'in yorumu "reranker çağrılmadan boş dönmeli" diyor ama bunu **hiçbir şey assert etmiyor**; `rag_service.py:58-59` tamamen silinse test yine yeşil kalır. Testin gerçek koruma değeri farklı: boş yolun `IndexError` fırlatmaması (satır 72'deki `scored_docs and` kısa devresi). Yorum, verilmeyen bir garantiyi tarif ediyor. Yorum plandan birebir geldiği için bu görevde düzeltilmedi. |
| 2 | Adı fazla vaat eden test | `test_suresi_dolmus_jeton_reddedilir` aslında `jose.jwt.decode`'u doğrudan test ediyor, `app/` içindeki reddetme yolunu değil. Gerçekte `auth_service.py:44-45`'i pinliyor. Güçlü hâli: API üzerinden süresi dolmuş jetonla 401 beklemek. |
| 3 | Testin ağır uca bağlanması (**kapatıldı**) | `test_auth_api.py`'deki 4 API testi auth kapısını `/ai/analiz` üzerinden yokluyor — uygulamanın en ağır ucu. Hepsi auth katmanında kısa devre yapıyor, ama tek satırlık bir üretim değişikliği onları RAG/LLM hattına sürükleyebilirdi ve o dosyada bunu engelleyen hiçbir şey yoktu. Son düzeltme turunda dördüne de `esik_alti` verildi (madde 10'a bakınız); artık kapı gerilerse istek gerçek `get_collection()`'a değil sahteye gidiyor. |
| 4 | Sahte servis kapsamı | `esik_alti` yaması `get_structured_completion`'ı yamalamıyor; **sekiz** test (`test_ai_analiz_api.py` 4, `test_auth_api.py` 4) Ollama'dan yalnızca eşik kapısı (`ai.py:145`) da sağlam kaldığı sürece uzak duruyor. Bunlardan yedisi bu senaryoda açıkta; sekizincisi (`test_esik_altinda_llm_cagrilmaz_ve_belirsiz_doner`) `get_structured_completion`'ı kendisi yamaladığı için korunuyor. Doğrulama **ve** kapı birlikte bozulursa o yedi test gerçek LLM'e gider. |
| 5 | Yamalanmayan sahte | `test_speech_api.py`'deki 2. ve 3. test (`.txt` reddi, boyut sınırı) `transcribe`'ı yamalamıyor; yorum "STT hiç çağrılmadan reddedilmeli" diyor ama bunu hiçbir şey ayırt etmiyor. Yamalanırsa hem iddia pinlenir hem `WHISPER_MODEL_SIZE` geçici çözümüne gerek kalmaz. |
| 6 | Görünenden dar kapsam | `test_string_olmayan_triyaj_kodu_belirsiz_doner`'de 4 tip vakasının 3'ü mutasyon altında aynı şekilde patlıyor (`AttributeError: translate`) — dört ayrı vaka gibi görünüp tek bir mekanizmayı ölçüyor. |
| 7 | Eksik assert | `test_dokumanlar_skora_gore_siralanir` yalnızca `sonuc[0]`'ı assert ediyor. `len(sonuc) == 2` + `sonuc[1]` eklenirse tam sıralama bedavaya pinlenir. |
| 8 | Eksik assert | Mutlu yol testi `AnalysisResponse.status` alanını hiç assert etmiyor; eşik altı testi `sources == []` ve açıklayıcı `ai_note`'u pinlemiyor. |
| 9 | Kısmi mutasyon kanıtı | Görev 4'ün 4. mutasyonu `test_jeton_kullanici_adi_ve_rol_tasir`'ın yalnızca `sub` yarısını yanlışlıyor; `role` assert'i için bağımsız kırmızı kanıtı yok. |
| 10 | Tekrar eden test (**kapatıldı**) | `test_jetonsuz_istek_401_doner` hem `tests/api/test_auth_api.py:9` hem `tests/api/test_ai_analiz_api.py` içindeydi; ikisi de kendi görev brief'inden gelmişti. Bu satır önce **"birebir aynı"** ve **"doğru evi `test_auth_api.py`"** diyordu; ikisi de yanlıştı. Kopyalar `esik_alti` fixture'ı bakımından farklıydı ve **korunan kopya `test_ai_analiz_api.py`'dekiydi** — `esik_alti` o dosyada tanımlı olduğu için `test_auth_api.py` ona erişemiyordu. Tavsiye olduğu gibi uygulansaydı güçlü kopya silinip korumasız olan bırakılırdı. Yapılan sıra: (1) `esik_alti` `tests/api/conftest.py`'ye taşındı, (2) `test_auth_api.py`'deki dört `/ai/analiz` testine verildi, (3) **ancak ondan sonra** `test_ai_analiz_api.py`'deki kopya silindi. Sıra bu işin özüydü; iki ayrı commit'te yapıldı ki kayıtta da görünsün. Test sayısı 68 → 67. |
| 11 | Örtük assert | `test_saglik.py`'deki iki izolasyon testinde açık assert yok; pass/fail `db_oturum.commit()` patlar mı diye örtülüyor. Tripwire için meşru ama paketin geri kalanındaki açık-assert üslubundan sapıyor. |
| 12 | Ölü import | `tests/birim/test_rag_esik_kapisi.py`'de `import pytest` kullanılmıyor (yalnızca `monkeypatch` fixture'ı var, o import gerektirmez). Plandan birebir korunmuş; silinmeli. |
| 13 | Eksik yorum | `tests/conftest.py`'deki `join_transaction_mode` yorumu, connection pool'un `reset_on_return="rollback"` varsayılanının `islem.rollback()`'i bağımsız olarak yedeklediğini söylemiyor. İleride bakan biri `rollback`'i silince testlerin kırmızı olmamasına şaşırabilir. |
| 14 | Fixture teardown'u fazla geniş | `istemci` fixture'ının teardown'u `app.dependency_overrides.clear()` kullanıyor, yalnızca `get_db` anahtarını silmiyor. Bugün tek override o, ama ileride başka override eklenirse sessizce silinir. |
| 15 | `asyncio_mode` ayarsız | `pytest-asyncio` kurulu ama `pytest.ini`'de `asyncio_mode` yok. Bugün etkisiz: pakette hiç `async def test_` yok (`/speech/transkript` async ama `TestClient` onu kendi sürüyor). İlk async test eklendiğinde ayarlanmalı. |
| 16 | `/document/upload` testleri korumasız (**kapatıldı**) | Madde 3 ile aynı sınıftan, ama daha ağır sonuçlu ve birleştirme anına kadar kimse görmedi — üç inceleyici de `/ai/analiz` desenine odaklanıp aynı desenin bu uçta tekrarlandığını kaçırdı. `test_admin_olmayan_dokuman_yukleyemez` ve `test_dokuman_yukleme_jetonsuz_401_doner` hiçbir şey yamalamıyordu ve ilkinin yorumu *"403 dönerken ChromaDB'ye dokunulmaz, bu yüzden test güvenli"* diyordu — Görev 7'de **reddedilen** gerekçenin aynısı. Fark şu: `esik_alti`'nın önlediği risk gerçek servisten **okumaktı**; burada `document.py:125` `get_collection().upsert(...)` çalıştırıyor, yani her hasta sorgusunun tarandığı `triage_documents` koleksiyonuna **yazmak**. Kapatma: `tests/api/conftest.py`'ye `dokuman_yazmayi_engelle` fixture'ı eklendi; `upsert` çağrılırsa `AssertionError` fırlatıyor. Kanıt: `auth_service.py:78` mutasyonuyla koşulduğunda uç gerçekten gövdeye ilerledi ve fixture yazmayı yakaladı (`document.py:142` log satırı). Fixture olmasaydı o çağrı gerçek koleksiyona giderdi. |

---

### Mutasyon kanıtı özeti

Her görevde, o görevin testlerinin gerçekten bir şey ölçtüğünü kanıtlamak için
üretim kodunda kasıtlı bozmalar (mutasyon) yapıldı ve kırmızı görüldü.

| Görev | Mutasyon | Sonuç |
|---|---|---|
| Görev 4 — Auth | 8 | 8/8 gerçek kırmızı |
| Görev 5 — RAG eşiği | 11 | Hepsi kırmızı, Critical/Important bulgu yok |
| Görev 6 — Normalizasyon | 12 | 12/12 kırmızı |
| Görev 7 — `/ai/analiz` | 12 | 12/12 kırmızı |
| Görev 8 — Ses zinciri | 8 (7 davranış grubu) | Hepsi kırmızı |
| Görev 9 — `require_admin_role` | 2 | 2/2 kırmızı (aşağıda) |
| Görev 9 — bütünsel | 1 | 7 test kırmızı (aşağıda) |

**Bu sayıların kaynağı.** Tablodaki 54 mutasyonun tamamı, görev raporlarından
ve SDD ledger'ından alınan **beyanlardır**; her iki kaynak da birleştirmeden
(merge) sonra siliniyor. Bu belgeden komut/çıktı ile yeniden üretilebilen tek
grup Görev 9'unkilerdir (aşağıda üçünün de kırmızısı gösteriliyor); kalan 51
mutasyon için burada tekrarlanabilir kanıt yok. Ek C'nin kendi süreç notu
"Rapordaki iddialar komut/çıktı ile desteklenmeli" dediği için bu ayrım açıkça
yazıldı.

Görev 1–3 (çatı ve fixture'lar) için ledger ayrı mutasyon sayısı tutmadı;
Görev 2'nin izolasyon testi bir düzeltme turunda commit tabanlı sızıntı
dedektörüne çevrildi, böylece kırmızısı mekanizmaya bağlandı.

#### Görev 9'un mutasyonları

**1. `app/services/auth_service.py:78`** — `if current_user.role != "admin":` →
`if False:` (admin kontrolü tamamen devre dışı).
Sonuç: `test_admin_olmayan_dokuman_yukleyemez` **kırmızı** —
`assert 500 == 403`. Diğer 5 test yeşil kaldı, yani mutasyon tam da hedeflediği
davranışı vuruyor.

**2. `app/services/auth_service.py:27`** — `OAuth2PasswordBearer(tokenUrl="auth/login")`
→ `..., auto_error=False` (jetonsuz istekte otomatik 401 kaldırıldı).
Sonuç: `test_dokuman_yukleme_jetonsuz_401_doner` ve `test_jetonsuz_istek_401_doner`
**kırmızı** — `AttributeError: 'NoneType' object has no attribute 'rsplit'`
(`jose/jws.py:180`). Bu aynı zamanda yukarıdaki `auth_service.py:61-69`
boşluğunun deneysel kanıtıdır: `AttributeError`, `except JWTError` tarafından
yakalanmıyor, dolayısıyla 401 yerine 500 dönüyor.

**3. Bütünsel mutasyon — `app/api/ai.py:23`** —
`GECERLI_TRIYAJ_KODLARI = {"Kırmızı", "Sarı", "Yeşil"}` →
`{"Kirmizi", "Sari", "Yesil"}` (Türkçe karakterler ASCII'ye çevrildi).
Sonuç: **7 test kırmızı**, hem birim hem entegrasyon katmanında:

```
FAILED tests/api/test_ai_analiz_api.py::test_basarili_analiz_200_ve_sema_alanlari - AssertionError: assert 'Sari' == 'Sarı'
FAILED tests/api/test_ai_analiz_api.py::test_ziyaret_ve_oneri_veritabanina_yazilir - AssertionError: assert 'Sari' == 'Sarı'
FAILED tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[Kırmızı-Kırmızı] - AssertionError: assert 'Kirmizi' == 'Kırmızı'
FAILED tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[kirmizi-Kırmızı] - AssertionError: assert 'Kirmizi' == 'Kırmızı'
FAILED tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[KIRMIZI-Kırmızı] - AssertionError: assert 'Kirmizi' == 'Kırmızı'
FAILED tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[  sari  -Sarı] - AssertionError: assert 'Sari' == 'Sarı'
FAILED tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[yesil-Yeşil] - AssertionError: assert 'Yesil' == 'Yeşil'
```

Bütünsel mutasyonun anlamı: triyaj sözlüğündeki tek bir karakter değişikliği
hem birim testinden hem uçtan uca API testinden yakalanıyor. Ağ gerçekten
davranış ölçüyor, sadece kod çalıştırmıyor. Mutasyon geri alındı ve `app/`
altında yalnızca onaylı 422 değişikliği kaldığı `git status --short -- app/`
ile doğrulandı.

---

### Kapatılan konular

| Konu | Nasıl kapandı |
|---|---|
| `require_admin_role` hiçbir testten geçmiyordu | Görev 4'te tespit edildi, kullanıcı onayıyla Görev 9 Adım 0 olarak eklendi. Artık `/document/upload` için hem 403 (admin olmayan) hem 401 (jetonsuz) testi var, ikisi de mutasyonla kırmızı görüldü. **Not:** izin veren dal (satır 83) hâlâ açık — yukarıdaki boşluk tablosuna bakınız. |
| Planda yanlış mutasyon hedefi | Görev 4'ün brief'i mutasyon için `auth_service.py:78` / `require_admin_role`'u gösteriyordu; oysa o görevin testleri `require_user_or_admin_role`'dan geçiyordu (doğrusu `:87`). Uygulayıcı bunu fark etti, plan düzeltildi. `:78` mutasyonu bugün doğru evine, Görev 9'a taşındı. |
| Veritabanı izolasyonu şüphesi | Görev 2'de açılan soru Görev 7'de kapandı. `yetkili_baslik` her testte aynı benzersiz `test_kullanici`'yı ekliyor ve `test_ai_analiz_api.py`'deki 5 test `_kaydet` üzerinden gerçekten `commit` ediyor; izolasyon bozuk olsa `users` tablosundaki unique kısıtında çatışırdı. Arka arkaya iki temiz tam koşu izolasyonun **çalıştığını** kanıtlıyor, yalnızca "çatışmadığını" değil. |
| **`tests/conftest.py` üretim şemasını silebilirdi** | `os.environ.setdefault("DATABASE_URL", ...)` değişken **zaten tanımlıysa hiçbir şey yapmaz**. Durum tam olarak budur: `docker compose` içinde backend servisi `DATABASE_URL`'i üretim `ai_triage`'ına işaret ederek export ediyor, ve değişkeni job değişkeni olarak veren her CI işi aynı durumda. `test_motoru` sonra o adrese `create_all`, oturum sonunda `drop_all` uyguluyordu — yani üretim şeması silinirdi. `test_config.py`'nin "URL `/ai_triage_test` ile biter" assert'i koruma değildi: `tests/api/` `tests/birim/`'den önce toplanıyor (onlarca test çoktan yanlış veritabanına yazmış olurdu) ve `drop_all` başarısızlıklardan bağımsız olarak teardown'da yine koşuyor. Çözüm: `create_engine`'e dokunmadan önce hedefi doğrulayan fail-fast `pytest.exit` kilidi (`tests/conftest.py`, `test_motoru`'nun ilk satırları). `pytest.fail` değil `pytest.exit` — amaç tek testi kırmızı yapmak değil, oturumu durdurmak. **Hiçbir görev incelemesi bunu görmedi**: her inceleme yalnızca kendi görevinin diff'ini görüyordu ve bu satır Görev 1'den beri hiç değişmemişti, yani hiçbir diff'te belirmedi. Bulgu ancak tüm dalı birden gören bütünsel incelemeden çıktı. Kanıt aşağıdaki "Doğrulama kanıtı" bölümünde. |
| `.coverage` dosyası takipsizdi | `.gitignore:52` içinde; `git check-ignore -v .coverage` ile doğrulandı. Depoya sızmıyor. |
| `asyncio_mode` boşluğu | Kontrolör kararı: gerçek bir boşluk değil, plan boyunca hiç async test fonksiyonu yok. Yine de ileriye dönük not olarak yukarıda kayıtlı. |

---

### Gün 22'ye devredilenler

**1. Kalıcılık (durability) testi.** `test_ziyaret_ve_oneri_veritabanina_yazilir`
dayanıklılığı değil, "flush'lanmış ve oturumda görünür"ü ölçüyor:
`AIRecommendation` `ai.py:113`'te yalnızca `db.add` ediliyor ve `conftest.py`
`autoflush=False` kullanıyor, dolayısıyla `db.commit()` yerine `db.flush()`
konsa test yine yeşil kalır. Bu dikkatsizlik değil, kurulumun doğası: test ile
istek aynı oturumu paylaştığı için commit ile flush içeriden ayırt edilemez.

Ayırt etmek için ikinci bir bağımsız oturumdan sorgulayan bir fixture gerekir;
o oturum rollback korumasının dışında kalacağı için kendi verisini kendi
temizlemek zorundadır. Kullanıcı kararı (1 Ağustos 2026): bugün eklenmeyecek,
Gün 22'de (test derinleştirme ve CI günü) ele alınacak.

**1b. Güvenlik kilidinin sınırı.** `tests/conftest.py`'deki `test_motoru`
kilidi yalnızca veritabanı **adını** kontrol ediyor, host ya da kullanıcıyı
değil. Şu URL kilitten geçer:

```
postgresql://triage:triage@prod-host:5432/ai_triage_test
```

Yani üretim sunucusunda `ai_triage_test` adlı bir veritabanı varsa kilit onu
korumaz. Bugünkü tehdit modelinde (yerel makine + CI) yeterli, ama Gün 22'de
CI kurulurken host doğrulaması da eklenmeli. Kilidin yanlış yönde başarısız
olduğu bir durum daha var: sorgu parametreli bir URL (`.../ai_triage_test?sslmode=require`)
sonek testini geçemez ve meşru bir CI koşusunu durdurur — güvenli yönde
başarısızlık, ama Gün 22'de düzeltilmeli.

**1c. Aynı kusur deseninin üçüncü örneği.** `test_speech_api.py`'de üç test
(`test_jetonsuz_istek_401_doner`, `test_desteklenmeyen_format_400_doner`,
`test_cok_buyuk_dosya_400_doner`) `transcribe`'ı yamalamıyor. Uzantı beyaz
listesi ya da boyut sınırı gevşerse istek gövdeye ilerler ve gerçek
faster-whisper `medium` modeli yüklenir — yüzlerce MB indirme, dakikalarca CPU.

Bu, zaten kapatılmış madde 3 (`/ai/analiz`) ve madde 16 (`/document/upload`)
ile **aynı mekanizmadır**. Kayda değer olan, aynı kusurun bu belgede üç farklı
ağırlıkta değerlendirilmiş olması: `/ai/analiz`'deki Important sayılıp
düzeltildi, `/document/upload`'daki birleştirme anında bulunup düzeltildi,
buradaki ise madde 5 olarak Minor'da kaldı. Ağırlık farkı gerçek bir teknik
gerekçeye değil, hangi incelemede görüldüğüne dayanıyordu. Kullanıcı kararı
(2 Ağustos 2026): Gün 22'ye bırakıldı. Çözümü tanıdık — `dokuman_yazmayi_engelle`
fixture'ının `transcribe` için birebir muadili.

**2. Öncelik sırasına konmuş test adayları.** Yukarıdaki boşluk tablosundan
Gün 22'de kapatılması önerilen ilk beş test:

1. `/auth/login` uçtan uca testi — doğru parolayla 200 + jeton, yanlış parolayla 401.
   (Uygulamanın en temel güvenlik iddiası, bugün tamamen korumasız.)
2. `app/api/ai.py:141-143` — `retrieve_and_rerank` istisna fırlattığında hastanın
   nereye düştüğü. Aynı zamanda "getirme bozuk" ile "protokol yok" ayrımını
   üretim kodunda ayırmak için bir tasarım kararı gerektiriyor.
3. `caplog` ile gizlilik testi — `/speech/transkript` log'una şikayet metninin
   yazılmadığı. ("En değerli 12. test.")
4. `assert "exp" in icerik` — jeton süresinin varlığını pinler, tek satır.
5. `_sadelestir` için `"ĞÜÖÇ ğüöç"` parametrize vakası — `maketrans` tablosunun
   pinlenmemiş 4 eşlemesini kapatır, tek satır.

**3. Sertleştirme (ayrı görev).** `get_current_user`'ın başına
`if not token: raise auth_exception`. Üretim kodu değişikliği olduğu için bugünkü
Global Kısıt kapsamına girmiyor.

**4. Ertelenen test-kalitesi düzeltmeleri.** Yukarıdaki "Test paketinin kendi
zayıflıkları" tablosundaki 16 maddenin **13'ü**. Üçü kapatıldı: madde 3 (auth
testlerinin ağır uca korumasız bağlanması) ve madde 10 (tekrar eden test) son
düzeltme turunda, madde 16 (`/document/upload` testlerinin korumasızlığı)
birleştirme öncesi son kontrolde. Üçü de gerçek bir güvenlik ağı boşluğuydu,
ertelenemezdi. Kalan 13 madde paketin doğruluğunu bozmuyor, hepsi güç/netlik
kaybı.

Madde 16'nın geç bulunması kendi başına bir ders: aynı kusur deseni iki farklı
uçta vardı, `/ai/analiz`'deki kopyası üç ayrı incelemede tartışıldı ve düzeltildi,
`/document/upload`'daki kopyası hiçbirinde görülmedi. Bir deseni bir yerde
düzeltmek, aynı deseni başka yerlerde aramayı gerektiriyor.

---

### Süreç notları

- **Mutasyonlar her zaman `try/finally` + `git checkout` içinde koşturulmalı.**
  31 Temmuz'da bir düzeltme turu ajanı, mutasyon uygulanmış hâldeyken
  durduruldu ve diskte `auth_service.py:44`'te `if False:` bıraktı — bu, her
  jetonun ömrünü sessizce sabitleyen bir değişiklikti. Mola notunda yakalandı ve
  geri alındı. Görev 9'un üç mutasyonu da bu yüzden `try/finally` içinde
  koşturuldu; ayrıca `CHROMA_PORT` ölü bir porta çevrildi ki mutasyon altında
  yetki kapısı açıldığında gerçek ChromaDB'ye yanlışlıkla yazılmasın.
- **Rapordaki iddialar komut/çıktı ile desteklenmeli.** Görev 3'ün raporunda
  "imza doğrulama scripti" iddiası komut ve çıktı gösterilmeden checklist olarak
  sunulmuştu; inceleyici bağımsız olarak diff'e karşı doğruladı ve iddia gerçek
  çıktı, ama kanıt standardı tutarsızdı.
- **Plan değişiklikleri kodla aynı commit'te belgelendi.** Görev 2'de plandaki
  Adım 2 kodu insan onayıyla değiştirildi ve plan belgesi de aynı commit'te
  güncellendi, böylece spec ile kod eş kaldı.
- **Model seçimi.** SDD'nin "en ucuz yeterli model" kuralı kullanıcı talimatıyla
  ezildi: 31 Temmuz'da tüm subagent'ların Opus ile gönderilmesi istendi.
- **Görev 5–8 seri koşturuldu** (kullanıcı kararı), planın öngördüğü paralel
  blok yerine — her görevden sonra inceleme yapılabilsin diye.
- **Mimari not (RAG).** `rag_service.py`'de eşik iki yerde birden uygulanıyor:
  satır 72'deki kapı ve satır 82'deki filtre. Sıralama azalan olduğu için en
  üstteki eşiğin altındaysa zaten hepsi altındadır ve satır 82 listeyi kendi
  başına boşaltır; satır 72'nin tek benzersiz katkısı bir log satırıdır.

---

### Doğrulama kanıtı

#### 1. Veritabanı güvenlik kilidi gerçekten ateşliyor mu?

Kilit, bu dalda yazılan tek yeni mantık parçası. Paketteki her davranış gibi
**kırmızı görülmeden kabul edilmedi**: `DATABASE_URL` kasten üretim
veritabanına çevrilip paket koşuldu (yalnızca o koşu için; kalıcı
ayarlanmadı).

```
$ $env:DATABASE_URL = "postgresql://triage:triage@localhost:5432/ai_triage"
$ .venv\Scripts\python.exe -m pytest -m "not yavas" --override-ini="addopts=" -v --no-header

============================= test session starts =============================
collecting ... collected 67 items

tests/api/test_ai_analiz_api.py::test_kisa_sikayet_422_doner 

============================= 2 warnings in 1.16s =============================
! _pytest.outcomes.Exit: Testler yalnızca ai_triage_test üzerinde çalışır. Bulunan: postgresql://triage:triage@localhost:5432/ai_triage !

$ echo $LASTEXITCODE
3
```

Okunuşu: 67 test **toplandı**, ilk test adı yazıldı ama `PASSED`/`FAILED`
almadan oturum kapandı. Kilit `create_engine`'den önce çalıştığı için ne motor
açıldı ne `create_all` koştu — ve `drop_all`'a hiç sıra gelmedi. Süre 1.16 sn.
Çıkış kodu 3 (`pytest.exit(..., returncode=3)`), yani CI bunu normal test
başarısızlığından ayırt edebilir.

Üretim şemasının el değmemiş kaldığı bağımsız olarak da doğrulandı:

```
ai_triage      -> ['ai_recommendations', 'alembic_version', 'users', 'visits']
ai_triage_test -> []
```

(`ai_triage_test`'in boş olması beklenen durumdur: `test_motoru` şemayı her
oturumun başında kurup sonunda `drop_all` ile kaldırıyor.)

#### 2. Paketin tamamı

```
$ .venv\Scripts\python.exe -m pytest -m "not yavas" --override-ini="addopts=" -v --no-header

============================= test session starts =============================
collecting ... collected 67 items

tests/api/test_ai_analiz_api.py::test_kisa_sikayet_422_doner PASSED      [  1%]
tests/api/test_ai_analiz_api.py::test_gecersiz_yas_422_doner PASSED      [  2%]
tests/api/test_ai_analiz_api.py::test_gecersiz_giris_tipi_422_doner PASSED [  4%]
tests/api/test_ai_analiz_api.py::test_basarili_analiz_200_ve_sema_alanlari PASSED [  5%]
tests/api/test_ai_analiz_api.py::test_klinik_uyari_nota_eklenir PASSED   [  7%]
tests/api/test_ai_analiz_api.py::test_esik_altinda_llm_cagrilmaz_ve_belirsiz_doner PASSED [  8%]
tests/api/test_ai_analiz_api.py::test_llm_hatasi_502_doner PASSED        [ 10%]
tests/api/test_ai_analiz_api.py::test_ziyaret_ve_oneri_veritabanina_yazilir PASSED [ 11%]
tests/api/test_ai_analiz_api.py::test_ses_kaynakli_basvuru_giris_tipi_ses_kaydedilir PASSED [ 13%]
tests/api/test_ai_analiz_api.py::test_varsayilan_giris_tipi_metindir PASSED [ 14%]
tests/api/test_auth_api.py::test_jetonsuz_istek_401_doner PASSED         [ 16%]
tests/api/test_auth_api.py::test_bozuk_jeton_401_doner PASSED            [ 17%]
tests/api/test_auth_api.py::test_tanimsiz_rol_403_doner PASSED           [ 19%]
tests/api/test_auth_api.py::test_veritabaninda_olmayan_kullanicinin_jetonu_401_doner PASSED [ 20%]
tests/api/test_auth_api.py::test_admin_olmayan_dokuman_yukleyemez PASSED [ 22%]
tests/api/test_auth_api.py::test_dokuman_yukleme_jetonsuz_401_doner PASSED [ 23%]
tests/api/test_saglik.py::test_saglik_ucu_200_doner PASSED               [ 25%]
tests/api/test_saglik.py::test_izolasyon_denegi_ilk_testte_commit_edilir PASSED [ 26%]
tests/api/test_saglik.py::test_izolasyon_denegi_ikinci_testte_hala_yaratilabilir PASSED [ 28%]
tests/api/test_speech_api.py::test_jetonsuz_istek_401_doner PASSED       [ 29%]
tests/api/test_speech_api.py::test_desteklenmeyen_format_400_doner PASSED [ 31%]
tests/api/test_speech_api.py::test_cok_buyuk_dosya_400_doner PASSED      [ 32%]
tests/api/test_speech_api.py::test_basarili_transkript_metin_sure_ve_model_doner PASSED [ 34%]
tests/api/test_speech_api.py::test_stt_hatasi_422_doner PASSED           [ 35%]
tests/api/test_speech_api.py::test_bos_transkript_422_doner PASSED       [ 37%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.wav] PASSED [ 38%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.mp3] PASSED [ 40%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.m4a] PASSED [ 41%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.ogg] PASSED [ 43%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.webm] PASSED [ 44%]
tests/birim/test_auth_service.py::test_parola_hashlenir_ve_dogrulanir PASSED [ 46%]
tests/birim/test_auth_service.py::test_gecersiz_parola_reddedilir PASSED [ 47%]
tests/birim/test_auth_service.py::test_ayni_parola_farkli_hash_uretir PASSED [ 49%]
tests/birim/test_auth_service.py::test_jeton_kullanici_adi_ve_rol_tasir PASSED [ 50%]
tests/birim/test_auth_service.py::test_suresi_dolmus_jeton_reddedilir PASSED [ 52%]
tests/birim/test_config.py::test_ayarlar_env_dosyasindan_okunur PASSED   [ 53%]
tests/birim/test_config.py::test_veritabani_url_test_veritabanini_gosterir PASSED [ 55%]
tests/birim/test_rag_esik_kapisi.py::test_koleksiyon_yoksa_bos_liste_doner PASSED [ 56%]
tests/birim/test_rag_esik_kapisi.py::test_esik_altinda_bos_liste_doner PASSED [ 58%]
tests/birim/test_rag_esik_kapisi.py::test_esik_ustunde_dokuman_doner PASSED [ 59%]
tests/birim/test_rag_esik_kapisi.py::test_tam_esik_degeri_dahil_edilir PASSED [ 61%]
tests/birim/test_rag_esik_kapisi.py::test_dokuman_kaynagi_ciktiya_eklenir PASSED [ 62%]
tests/birim/test_rag_esik_kapisi.py::test_dokumanlar_skora_gore_siralanir PASSED [ 64%]
tests/birim/test_rag_esik_kapisi.py::test_metadata_filtresi_koleksiyona_gecirilir PASSED [ 65%]
tests/birim/test_rag_esik_kapisi.py::test_bos_koleksiyon_sonucu_bos_liste_doner PASSED [ 67%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[K\u0131rm\u0131z\u0131-kirmizi] PASSED [ 68%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[KIRMIZI-kirmizi] PASSED [ 70%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[Ye\u015fil-yesil] PASSED [ 71%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[  Sar\u0131  -sari] PASSED [ 73%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[\u015e\u0130\u011e\xdc\xd6\xc7-siguoc] PASSED [ 74%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[K\u0131rm\u0131z\u0131-K\u0131rm\u0131z\u0131] PASSED [ 76%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[kirmizi-K\u0131rm\u0131z\u0131] PASSED [ 77%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[KIRMIZI-K\u0131rm\u0131z\u0131] PASSED [ 79%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[  sari  -Sar\u0131] PASSED [ 80%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[yesil-Ye\u015fil] PASSED [ 82%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[Mavi-Belirsiz] PASSED [ 83%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[-Belirsiz] PASSED [ 85%]
tests/birim/test_triyaj_normalizasyon.py::test_string_olmayan_triyaj_kodu_belirsiz_doner[None] PASSED [ 86%]
tests/birim/test_triyaj_normalizasyon.py::test_string_olmayan_triyaj_kodu_belirsiz_doner[42] PASSED [ 88%]
tests/birim/test_triyaj_normalizasyon.py::test_string_olmayan_triyaj_kodu_belirsiz_doner[ham_kod2] PASSED [ 89%]
tests/birim/test_triyaj_normalizasyon.py::test_string_olmayan_triyaj_kodu_belirsiz_doner[ham_kod3] PASSED [ 91%]
tests/birim/test_triyaj_normalizasyon.py::test_tetkik_listesi_temizlenir PASSED [ 92%]
tests/birim/test_triyaj_normalizasyon.py::test_tek_string_tetkik_listeye_cevrilir PASSED [ 94%]
tests/birim/test_triyaj_normalizasyon.py::test_liste_olmayan_tetkik_bos_liste_doner[None] PASSED [ 95%]
tests/birim/test_triyaj_normalizasyon.py::test_liste_olmayan_tetkik_bos_liste_doner[42] PASSED [ 97%]
tests/birim/test_triyaj_normalizasyon.py::test_liste_olmayan_tetkik_bos_liste_doner[ham2] PASSED [ 98%]
tests/birim/test_triyaj_normalizasyon.py::test_tetkik_elemanlari_stringe_cevrilir PASSED [100%]

============================== warnings summary ===============================
..\..\..\.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\batuh\Desktop\Ai_Triage-myself\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

..\..\..\.venv\Lib\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  C:\Users\batuh\Desktop\Ai_Triage-myself\.venv\Lib\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(f):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 67 passed, 2 warnings in 21.42s =======================
```

> pytest, parametrize test kimliklerindeki ASCII dışı karakterleri kaçırarak
> (escape) basar; yukarıdaki \u0131 -> `ı`, \u015f -> `ş`, \u011e -> `Ğ` demektir.
> Bu blok komut çıktısının birebir kopyasıdır, elle güzelleştirilmemiştir.

Ortam: Windows 11, Python 3.14.6, pytest 8.4.2, gerçek PostgreSQL
(`ai_triage_test` veritabanı). Ollama, faster-whisper, ChromaDB ve cross-encoder
**hiçbir testte çalıştırılmadı** — `tests/yardimcilar/` altındaki sahtelerle
değiştirildiler.

---

## Gün 17+18 · Doktor uçları — bekleyen vakalar ve onay akışı (3 Ağustos 2026)

### Bu gün ne yapıldı

Dört görev, dördü de ayrı subagent'la ve her birinin sonunda incelemeyle: `doctor`
rolü + `require_doctor_role`, `DoctorReview` modeli + migration `72dffb9e5194`,
`GET /doctor/bekleyen`, `POST /doctor/inceleme`. Ardından tüm dal için geniş bir
kod incelemesi ve tek düzeltme dalgası.

Tasarım kararları (K1–K10) `docs/superpowers/specs/2026-08-03-doktor-uclari-design.md`,
görev adımları `docs/superpowers/plans/2026-08-03-gun17-18-doktor-uclari.md`.

### Ölçümler

| | Önce | Sonra |
|---|---|---|
| Test sayısı | 67 | **86** |
| `app/` kapsaması | %72 | **%75** |
| Uç sayısı | 5 | 7 |
| Rol sayısı | 2 | 3 |

Dalın commit'leri: `d33c6e7` (rol), `bf5283e`+`8463048` (model+migration),
`b83b939` (liste ucu), `71d1c6a` (onay ucu), `23c3ca1` (inceleme düzeltmeleri).

### İncelemenin bulduğu gerçek hatalar

1. **Sayfalama belirlenimci değildi.** Liste yalnızca `created_at DESC` ile
   sıralanıyordu. Zaman damgaları eşitlendiğinde — ki toplu ekleme bunu garanti
   eder, Gün 23'ün değerlendirme seti toplu eklenecek — Postgres'in eşitlik
   grubu içindeki sırası tanımsızdır ve `OFFSET 0` ile `OFFSET 2` sorguları
   arasında değişebilir. Sonuç: aynı vaka iki sayfada birden görünebilir ya da
   hiçbirinde görünmeyebilirdi. Bir triyaj kuyruğunda bu, hastanın iki kez
   listelenmesi veya sessizce düşmesi demek. Düzeltme: `Visit.id.desc()` ikinci
   anahtarı (`23c3ca1`).
2. **`AIOnerisi` şeması sütunlardan katıydı.** `ai_note`, `onerilen_tetkikler` ve
   `sources` şemada zorunluydu ama sütunlar `nullable=True`. Pydantic v2'de
   varsayılan yalnızca alan **yokken** devreye girer; `from_attributes` ile alan
   `None` taşıyarak var olur ve doğrulama patlar. Hata `_bekleyen_vakaya_cevir`
   içinde oluştuğu için tek bozuk satır bütün kuyruğu 500'e düşürürdü, o satırı
   atlamazdı. Bugün ulaşılamaz (tek yazma yolu `_kaydet` NULL üretemiyor) ama
   şema artık NULL'a toleranslı.
3. **Uçlar kendi yetki kapılarına hiçbir testle bağlı değildi.** Bu, Gün 11–16'da
   üç uçta belgelenen desenin dördüncü tekrarı. Görev 1'in
   `test_user_rolu_doktor_ucuna_403_alir` testi `require_doctor_role`'ü izole
   sınıyordu; ucun onu **kullandığını** hiçbir şey kanıtlamıyordu. Mutasyon
   deneyi bunu ölçtü: her iki uçtaki `Depends(require_doctor_role)` düz
   `Depends(get_current_user)` ile değiştirildiğinde paketin tamamı yeşil
   kalıyordu — yani `user` rolündeki bir jeton hasta şikayet metinlerini
   okuyabilirdi ve tek bir test bunu görmezdi. Planın 17 testine iki test daha
   eklendi (`test_user_rolu_bekleyen_listesine_403_alir`,
   `test_user_rolu_inceleme_ucuna_403_alir`); eklendikten sonra aynı mutasyon
   **yalnızca** o iki testi kırmızıya düşürdü.
4. **Onay ucu hiç log basmıyordu** — üstelik denetim izinin ta kendisi olan modül.
   Ayrıca her `IntegrityError` "Bu ziyaret zaten incelendi"ye çevriliyordu; bir
   `doctor_id` yabancı anahtar ihlali doktora anlamsız bir mesaj gösterip hiçbir
   iz bırakmayacaktı.

### Belgelerdeki olgusal hatalar (düzeltildi)

- `CLAUDE.md` iki rol ve iki bağımlılık diyordu; artık üç. Veri modeli listesinde
  `DoctorReview` yoktu. `seed_users.py` açıklaması üç hesabı ve **mevcut satırın
  rolünü yerinde yeniden yazdığını** söylemiyordu.
- Hem `CLAUDE.md` hem tasarım dokümanı, `frontend/app.py`'nin rolü kullanıcı
  adından tahmin ettiğini söylüyordu. **Yanlış** — frontend rolü `/auth/me`'den
  okuyor (`frontend/app.py:85`). Bu iddia tasarım dokümanına `CLAUDE.md`'den
  miras kalmıştı; ikisi de düzeltildi.
- Tasarım dokümanı `doctor` rolünün iki uçtan dışlandığını söylüyordu; üç
  (`/speech/transkript` de `require_user_or_admin_role` kullanıyor).

### Gün 22'ye devredilenler (bu günden)

Aşağıdakiler incelemede bulundu, bilinçli olarak ertelendi. Hiçbiri davranışı
bugün bozmuyor.

1. `AIOnerisi`'nin katı olduğu üç alanın **sütun tarafı** hâlâ `nullable=True`
   (`app/models/visit.py`). Şema artık toleranslı; asıl temizlik sütunları
   `nullable=False` yapmak ve migration yazmak.
2. `ai_recommendations.visit_id` **unique değil**, oysa `Visit.recommendation`
   ilişkisi `uselist=False` diyor. Bir ziyarete iki öneri satırı yazılırsa hem
   ilişki yalanlanır hem de `joinedload` + `LIMIT 20` 19 farklı ziyaret döndürüp
   bekleyen bir vakayı sessizce düşürür. Yeni `doctor_reviews.visit_id` doğru
   şekilde unique; eski tablo hiç olmamıştı. Kendi migration'ını ister.
3. `doctor_reviews.doctor_id` index'siz — doktora göre sorgu gerektiğinde
   (Gün 23 raporlaması) eklenmeli.
4. `limit`/`offset` sınırları (`ge=1, le=100`, `ge=0`) hiçbir testle tutturulmuyor.
5. `_bekleyen_vakaya_cevir`'in on alan eşlemesinden dördü hâlâ doğrulanmıyor
   (`patient_age`, `chronic_disease`, `vitals`, `created_at`); `response_model`
   yalnızca tip uyumsuz takasları yakalar.
6. Liste ucu `Visit.status == "bekliyor"` ile, onay ucu `DoctorReview` varlığıyla
   "işlenmiş mi" sorusunu yanıtlıyor — iki ayrı doğruluk kaynağı. Bugün tek yazıcı
   ikisini birlikte güncellediği için ayrışamıyorlar; ileride bir "vakayı yeniden
   aç" özelliği gelirse ayrışır ve vaka kuyrukta görünüp sonsuza dek 409 döner.
7. `test_inceleme_ziyarete_bagli_kaydedilir` yazdığı oturumdan okuyor; JSON
   sütununun Postgres gidiş-dönüşü asıl olarak `test_onayda_tetkik_listesi_degistirilebilir`
   tarafından kapsanıyor, beklenen testte değil.
8. `IntegrityError` yakalayıcısı artık logluyor ama hâlâ her ihlali tek mesaja
   çeviriyor; ihlal türünü ayırt etmiyor.
9. Migration'ın `downgrade()`'i tabloyu düşürürken onaylanmış ziyaretleri
   `status='tamamlandi'` hâlinde bırakır — kim kapattı, neye karar verdi bilgisi
   kaybolur. Downgrade geliştirme kaçış kapısıdır, üretimde temiz geri alma
   beklenmemeli.

### Süreç notu

Düzeltme dalgası ajanı API harcama limitine takılıp yarıda kesildi; iki dosyada
commit'lenmemiş ama tutarlı düzenleme kaldı. SDD ledger'ına yazılan "MOLA"
bölümü sayesinde hangi maddenin bittiği tek tek biliniyordu ve iş kaldığı yerden
sürdürüldü — hiçbir adım tekrarlanmadı. Ledger'ın varlık sebebi tam olarak budur.

---

## Gün 19 · Streamlit doktor paneli (4 Ağustos 2026)

### Bu gün ne yapıldı

Backend'e hiç dokunulmadı — Gün 17+18'in iki ucu sözleşmeyi zaten kuruyordu.
`frontend/app.py`'ye rol→sekme haritası, `istek_at()` yardımcısı, `hasta_sekmesi()`
çıkarımı ve doktor paneli (liste + onay formu) eklendi; o sözleşmeyi donduran dört
backend testi yazıldı.

Tasarım kararları (K1–K12) `docs/superpowers/specs/2026-08-03-gun19-doktor-paneli-design.md`,
görev adımları `docs/superpowers/plans/2026-08-03-gun19-doktor-paneli.md`.

Dalın commit'leri: `9be69c4` (tasarım), `5ae7d6a` (plan), `577935c` (dört test),
`8a5dfdb` (sekme haritası + `istek_at`), `fcf41c4` (panel), `6525221` (inceleme
düzeltmeleri). `main`'e `acf465c` ile `--no-ff` birleşti.

### Ölçümler

| | Önce | Sonra |
|---|---|---|
| Test sayısı | 86 | **90** |
| `app/` kapsaması | %75 | **%75** (değişmedi — gün frontend günüydü) |
| Uç sayısı | 7 | 7 (backend değişmedi) |

Kapsamanın sabit kalması beklenen sonuç: Streamlit otomatik test edilmiyor (K12),
dört yeni test zaten var olan backend davranışını donduruyor.

### Tarayıcı testi: yedi adımın da kanıtı

Planın yedi adımı gerçek tarayıcıda, gerçek Ollama ve gerçek Postgres ile koşuldu.

| Adım | Kanıt |
|---|---|
| 1 · `hasta` yalnızca sohbet | Tek sekme: "Kullanıcı Sohbet Ekranı" |
| 2 · Analiz döndü | 62/Erkek/nabız 112, göğüs ağrısı → **Kırmızı / Acil Kardiyoloji**, kaynak dokümanlar geldi (eşik kapısı aşıldı) |
| 3 · `doctor` yalnızca panel | Tek sekme: "Doktor Paneli" |
| 4 · Vaka kartı | Şikayet, vitaller (`Ateş 38.2 °C · Nabız 96 /dk`), giriş kanalı, yapay zekâ notu, kaynaklar |
| 5 · Onay | Sarı→**Kırmızı**, `Batın BT` eklendi (K5: AI'ın önermediği tetkik), not yazıldı |
| 6 · Listeden düştü | Yeşil banner "Vaka onaylandı: Kırmızı", sayaç **9 → 8** |
| 7 · `admin` üç sekme | Sohbet + Doktor + Yönetici |

**Değişmez kuralın canlı kanıtı** (ziyaret `647c67fc-eb36-4382-8d46-b54893410457`):

| Alan | Değer |
|---|---|
| `status` | `bekliyor` → `tamamlandi` |
| `ai_kodu` | `Sarı` — değişmedi |
| `doktor_kodu` | `Kırmızı` |
| `ai_tetkikler` | 4 tetkik — değişmedi |
| `doktor_tetkikler` | 5 tetkik (`Batın BT` eklenmiş) |
| `onaylayan` | `doctor` — JWT'den, gövdeden değil |

Yapay zekânın satırına dokunulmadı, doktorunki yanına yazıldı. Gün 23'ün ölçeceği
denetim izi budur.

### Tarayıcı testinin bulduğu gerçek sorunlar

Hiçbiri Gün 19 kodunun kusuru değil; üçü de **hata bilgisinin operatöre hiç
ulaşmaması** deseninin ayrı yüzleri. Desen Gün 17+18'in 4. maddesiyle (onay ucu
hiç log basmıyordu) aynı kökten.

1. **`/auth/login` kullanıcı adındaki boşluğu kırpmıyor.** Kullanıcı adı alanına
   kaçan tek bir sondaki boşluk (`'doctor '`) `get_user`'ı boş döndürüyor ve uç
   401 veriyor. Kullanıcı ekranda doğru yazdığını gördüğü için hata anlaşılmaz
   hâle geliyor. Bu, testin bulduğu en pahalı sorun: teşhisi yaklaşık yarım saat
   aldı.
2. **Giriş hata dalı bütün başarısızlıkları tek mesaja indiriyor**
   (`frontend/app.py:487`). 401, 422, 500 — hepsi "Kullanıcı adı veya şifre
   hatalı!". "Kullanıcı bulunamadı" ile "parola yanlış" ayrımı da yok. Yukarıdaki
   1. maddeyi görünmez kılan şey tam olarak buydu.
3. **`istek_at` istisnayı hiç loglamadan yutuyor** (`frontend/app.py:65`).
   Kullanıcıya doğru mesajı gösteriyor ama hiçbir iz bırakmıyor.

### Kök nedeni bulunamayan tek olay

Doktor panelinin **ilk** çiziminde bir kez "Sunucuya ulaşılamadı" hatası alındı ve
bir daha tekrarlamadı. Elenenler, kanıtla: aynı ortamdan aynı çağrı çalışıyordu
(HTTP 401 döndü), giriş çağrıları o an başarılıydı, hata 3 saniyeden kısa sürede
oluştu (zaman aşımı değil), tanı kodu eklendikten sonra üç denemede hiç tekrar
etmedi. `istek_at`'e geçici log konuldu ve tek satır iz kalmadı. Spekülatif
düzeltme yazılmadı. Yukarıdaki 3. madde uygulanırsa bir dahaki sefere yakalanır.

### Gün 22'ye devredilenler (bu günden)

1. `/auth/login` kullanıcı adını `.strip()` ile kırpsın (yukarıda 1).
2. Giriş hata dalı durum koduna göre ayrışsın ve loglasın (yukarıda 2).
3. `istek_at` istisnayı `logging.warning` ile kaydetsin (yukarıda 3).
4. `seed_users.py` gerçekten idempotent değil: var olan kullanıcının **parolasını**
   hiç yeniden yazmıyor, yalnızca rolünü düzeltiyor. Bugün bir soruna yol açmadı
   (parolalar doğruydu) ama script'in adı yaptığından fazlasını vaat ediyor.
5. Streamlit'in hiç otomatik testi yok (K12). Rol→sekme haritası bugün elle
   doğrulandı; bir dahaki değişiklikte yine elle doğrulanması gerekecek.

### Süreç notu

Giriş hatasını teşhis ederken iki kez yanlış kök neden ilan ettim: önce "seed
parolası bozuk", sonra "bayat backend süreci". İkisi de ölçüm yerine tahmindi.
Birincisi canlı veritabanında gereksiz bir parola yazmasına, ikincisi çalışan
backend'in gereksiz yere yeniden başlatılmasına yol açtı. Gerçek kök neden ancak
gönderilen değerler **loglandığında** görüldü — ilk yapılması gereken oydu.

Ders, sistematik hata ayıklamanın birinci fazının tam olarak söylediği şey: çok
bileşenli bir sistemde önce bileşen sınırlarına kanıt topla, sonra hipotez kur.
Buradaki sınır arayüz→backend'di ve tek bir `print` onu on dakikada kapatırdı.

---

## Gün 20 · Bilgi tabanı yönetimi (4 Ağustos 2026)

### Bu gün ne yapıldı

**Gün 20'nin üçte biri.** Yol haritasındaki başlık "bilgi tabanı yönetimi + gerçek
protokol verisi + eşik kalibrasyonu"; bugün yalnızca **birincisi** bitti. İkincisi
ve üçüncüsü staj yerinden gelmeyen protokol dokümanlarına bağlı — derleme kamuya
açık kaynaklardan elle hazırlanıyor (`ornek_dokumanlar/protokoller/`), hazır
olduğunda toplu yükleme ve `kalibre_esik.py` koşulacak.

Bu sıralama bilinçli: liste ve silme uçları dosyalardan **önce** yazılmalıydı ki
yanlış yüklenen temizlenebilsin.

Eklenenler: `GET /document/liste`, `DELETE /document?kaynak=`, ve `POST
/document/upload`'ın hayalet chunk düzeltmesi. `tests/api/test_document_api.py`
bugün doğdu — doküman uçlarının bugüne kadar kendi test dosyası yoktu.

Tasarım kararları (K1–K9) `docs/superpowers/specs/2026-08-04-gun20-bilgi-tabani-yonetimi-design.md`,
görev adımları `docs/superpowers/plans/2026-08-04-gun20-bilgi-tabani-yonetimi.md`.

Dalın commit'leri: `d232289` (sahte koleksiyon + liste ucu), `ec4e55f` (silme ucu),
`314abb1` (hayalet chunk düzeltmesi), `44b3a96` (son inceleme düzeltmeleri).

### Ölçümler

| | Önce | Sonra |
|---|---|---|
| Test sayısı | 90 | **99** |
| `app/` kapsaması | %75 | **%80** |
| Doküman ucu sayısı | 1 | 3 |
| Bilgi tabanı | 4 chunk / 2 dosya | değişmedi (derleme bekleniyor) |

Kapsamanın %75'ten %80'e çıkması, `POST /document/upload` gövdesinin bugüne kadar
hiçbir testte çalışmamış olmasından: yetki testleri 403'te duruyordu, uç gövdesine
hiç girilmiyordu.

### Mevcut kodda bulunan gerçek hata: hayalet chunk

`upload`, chunk id'lerini `{güvenli_dosya_adı}_chunk_{sıra}` diye üretip `upsert`
ediyordu. `upsert` yalnızca kendisine verilen id'lere dokunur. Bir dosya 10 chunk
olarak yüklenip sonra kısaltılıp 6 chunk olarak yeniden yüklenince, eski sürümün
7–10 numaralı chunk'ları bilgi tabanında **kalıyordu**.

Sonucu şu: sistem silinmiş bir metinden alıntı yapabilir ve yanıttaki `sources`
alanı onu hâlâ o dosyaya bağlar — yani projenin bütün savunması olan izlenebilirlik
iddiası sessizce yalanlanır. Protokol dosyalarını düzelte düzelte ilerleyecek bir
günde bu kaçınılmazdı.

### Son incelemenin bulduğu gerçek sorunlar

Görev incelemeleri üçünü de temiz geçirdi; asıl bulgular tüm-dal incelemesinden geldi.

1. **Silmenin kapsamını hiçbir test dondurmuyordu.** Temizlik filtresi
   `{"source": ...}` yerine `{"category": ...}` olsaydı 98 testin **hepsi yeşil
   kalırdı** — ama üretimde her yükleme aynı kategorideki bütün bilgi tabanını
   silerdi. 15 protokol dosyasının hepsi `category="protokol"` ile yükleneceği için
   bu, tek bir yüklemede derlemenin tamamının yok olması demekti. Mutasyon deneyi
   ölçtü: filtre `category`'ye çevrildiğinde yeni test `assert 0 == 12` ile kırmızıya
   düştü — üstelik üç yükleme de `201` dönüyordu, yani hata tamamen sessizdi.
   Bu, Gün 11–16 ve Gün 17+18'de belgelenen desenin **beşinci** tekrarı: bir kuralı
   izole sınamak, üretim kodunun onu kullandığını kanıtlamıyor.
2. **Sil-sonra-yaz, yarıda kalan yüklemeyi veri kaybına çeviriyordu.** `delete`
   başarılı olup `upsert` patlarsa (Chroma bağlantısı, embedding hesabı) önceki iyi
   sürüm zaten silinmiş olurdu ve elde hiçbir şey kalmazdı; eskiden başarısız yükleme
   etkisizdi. Sıra çevrildi: eski id'ler okunur → `upsert` → yalnızca yeni sürümde
   karşılığı olmayan eski id'ler silinir. K5 bu yönde güncellendi. Kalan risk çok
   daha hafif: `upsert` başarılı olup `delete` patlarsa veri kaybı olmaz, yalnızca
   artakalan chunk kalır ve bir sonraki başarılı yükleme onu toplar.
3. **`dokuman_yazmayi_engelle` fixture'ı körelmişti.** `_YazmayiReddedenKoleksiyon`
   yalnızca `upsert` tanımlıyordu; `upload` artık `get` ve `delete` de çağırdığı için
   fixture'ın açıklayıcı `AssertionError`'ı yerine `AttributeError` fırlıyor ve
   `except Exception` onu 500'e çeviriyordu. Gerçek koleksiyona yazılmama güvencesi
   duruyordu ama teşhis kaybolmuştu — fixture'ın var oluş sebebi olan uzun uyarı
   mesajına artık ulaşılamıyordu.
4. **`CLAUDE.md` üç yerde olgusal olarak yanlışlaşmıştı** — chunk id davranışı, rol
   tablosundaki korunan uç listesi, ve sahte servis listesi. Gün 19'da da aynı desen
   çıkmıştı: dal davranışı değiştiriyor, belge eski iddiayı taşımaya devam ediyor.

### Sahte servisin gerçeğe sadakati

Testler bellek içi `tests/yardimcilar/sahte_chroma.py` ile koşuyor. Sahte gerçeği
yanlış taklit ederse testler yeşil verip üretim patlar — bu dalın en büyük riski
buydu. Kontrolcü gerçek ChromaDB'ye karşı üç çağrıyı da doğruladı: dolu koleksiyonda
`get(include=["metadatas"])` iki dosyayı 2'şer chunk'la döndürdü, `get(where=...)`
olmayan dosyada 0 eşleşme verdi, `delete(where=...)` hatasız kabul edildi ve hiçbir
şey silmedi. Ayrıca **boş** koleksiyonda `delete` ayrıca sınandı (geçici bir
koleksiyonla) — `docker compose down -v` sonrası ilk yükleme yolu bu ve orada
patlasa her temiz kurulum bozulurdu.

### Gün 22'ye devredilenler (bu günden)

1. **K9 — dosya adı normalizasyon çakışması.** `upload` id'leri `.lower()` **ve**
   boşluk→alt çizgi ile normalize ediyor ama `source` metadata'sına orijinal adı
   yazıyor. `Rapor A.txt` sonra `Rapor_A.txt` yüklenirse temizlik eşleşmez. İlk
   sanıldığı gibi "kasıtlı" bir senaryo değil — dosyayı yeniden adlandıran biri
   kazara düşer.
2. Silme ucunda `get()` + `delete()` atomik değil; raporlanan `silinen_chunk` sayısı
   eşzamanlı bir yazmada sapabilir. `delete(where=...)` yerine `delete(ids=...)`
   yazmak sayıyı fiilen silinen kümeye eşitler.
3. `entegrasyon` işareti `pytest.ini`'de "gerçek Postgres/ChromaDB gerektirir" diyor
   ama bu testlerde ChromaDB sahte, yalnızca Postgres gerçek. İşaret yanlış değil,
   geniş — aynı gevşeklik `esik_alti` kullanan testlerde de var, tek seferde
   çözülmeli.
4. `sahte_chroma.py` `include` parametresini yok sayıyor; gerçek Chroma
   `include=["metadatas"]` ile `documents`'ı `None` döndürür. Bugün zararsız (yalnızca
   `metadatas` okunuyor) ama sahtenin gerçekten ayrıldığı tek yer burası.
5. İki yeni uçta `response_model` yok; depodaki diğer router'ların hepsinde var.
   Sözleşme bugün testlerle tutuluyor ama OpenAPI şeması boş kalıyor.
6. `GET /document/liste` bütün üstverileri belleğe çekiyor, limit yok. 2 dosyada
   sorun değil, derleme büyüyünce not.
7. K8 (kategori/tarih en küçük `chunk_index`'ten okunur) farklı değerli chunk'larla
   ayrıca sınanmıyor; K5 sayesinde bugün gözlemlenebilir fark üretmiyor.

### Süreç notu

Üç görevin üçü de görev incelemesini ilk seferde temiz geçti, ama tüm-dal incelemesi
dört Important bulgu çıkardı. İkisi (silme kapsamı, veri kaybı penceresi) tek tek
görevlere bakarken görünmüyordu — çünkü ikisi de **görevler arası** ilişkiden
doğuyordu: kapsam sorunu ancak koleksiyonda birden fazla dosya varken ortaya çıkıyor,
veri kaybı penceresi ise Görev 3'ün Görev 1'den devraldığı sıralamadan geliyor.

Görev bazlı inceleme dar kapsamda doğruluğu ölçüyor; geniş inceleme parçaların
birlikte doğru olup olmadığını. İkisi birbirinin yerine geçmiyor — bu günün kanıtı
bu.
