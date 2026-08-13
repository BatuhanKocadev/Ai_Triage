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
| `llm_service.py` %24 **(bu sayı artık geçersiz — Gün 22'den beri kapsamadan hariç, bkz. aşağıdaki Gün 22 ikinci yarı bölümü)** | Ollama'ya HTTP isteği atan gövde. Testlerde `sahte_llm.py` ile değiştiriliyor; gerçek çağrı hiçbir testte yapılmıyor. | Evet — Global Kısıt: dış servis çalıştırılmaz |
| `stt_service.py` %37 **(bu sayı artık geçersiz — aynı sebeple hariç)** | faster-whisper modelini yükleyen gövde. `sahte_stt.py` ile değiştiriliyor. | Evet |
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

> **Durum güncellemesi (11 Ağustos 2026, Gün 22 birinci yarısı).**
> **Madde 1b (güvenlik kilidinin sınırı) KAPATILDI** — kilit artık host doğruluyor
> ve query string'li meşru adresi kırmıyor; karar mantığı
> `tests/yardimcilar/db_kilidi.py`'de ve **on beş** birim testiyle bağlı.
> Kilit URL'in görünen hâlini değil, psycopg2'ye verilecek çözülmüş hedefi
> doğruluyor; on beş bypass vektörü ölçülerek kapatıldı.
> **Madde 1c (aynı kusur deseninin üçüncü örneği) KAPATILDI** — `test_speech_api.py`'deki
> üç test artık `transkript_engelle` ile yamalı; desenin bilinen tüm örnekleri kapandı.
> **Madde 2'nin birinci sırası (`/auth/login` uçtan uca testi) ÇOKTAN KAPANMIŞTI** —
> Gün 21 kapatmış ama bu liste güncellenmediği için altı gün açık göründü.
> Kalan maddeler (1 kalıcılık testi, 2'nin diğer dört sırası, 3, 4) **açık**.

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

> **Durum güncellemesi (11 Ağustos 2026, Gün 22 birinci yarısı).**
> **Madde 2 (`ai_recommendations.visit_id` unique değil) KAPATILDI** — migration
> `6922a872c59d`; sessiz veri kaybı yolu (doktor kuyruğundan düşen hasta) kapandı.
> **Madde 3 (`doctor_reviews.doctor_id` index'siz) KAPATILDI** — aynı revision.
> Kalan yedi madde **açık**.

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

---

## Gün 20 · Kapanış — retrieval boru hattı ve eşik kalibrasyonu (6–9 Ağustos 2026)

### Gün 20 nasıl üçe bölündü

Yol haritasındaki başlık "bilgi tabanı yönetimi + gerçek protokol verisi + eşik
kalibrasyonu". Birinci parça 4 Ağustos'ta bitti (üstteki bölüm). Kalan iki parça,
ölçüm yapmaya kalkınca ortaya çıkan iki gerçek hata yüzünden ayrı bir mini projeye
dönüştü.

### Derleme: kurumdan gelmedi, kamuya açık kaynaklardan derlendi

Staj yeri protokol dokümanlarını bulamadı. Derleme Sağlık Bakanlığı tebliği, ATUDER
materyali ve ESI el kitabı gibi **kamuya açık kaynaklardan** elle hazırlandı: 15
klinik başlık, `ornek_dokumanlar/protokoller/` altında.

Yüklemeden önce iki temizlik gerekti. Dosyalarda bir yapay zekâ aracının bıraktığı
**298 adet `[cite: N]` işareti** vardı; bunlar gömme vektörünü kirletir, LLM'e bağlam
olarak gider ve doktor panelinde ekranda görünürdü. Ayrıca üç yazım hatası
(`müşadeye`→müşahedeye, `taşipne`→takipne, `desoryante`→dezoryante) ve iki
tutarsızlık düzeltildi — `taşipne` özellikle dikkat çekiciydi çünkü diğer üç dosya
aynı terimi doğru yazıyordu.

Aynı konuyu iki kez anlatan iki eski dosya derleme dışı bırakıldı ve yeni `DELETE`
ucuyla bilgi tabanından silindi.

### Ölçüm yapmaya kalkınca çıkan iki hata

Derleme yüklendikten (47 chunk) ve `kalibre_esik.py` koşulduktan sonra çıkan tablo
şuydu: **18 ilgili sorgunun 10'u eleniyor**, ve ilgili skorların minimumu (0.5001)
alakasız skorların maksimumundan (0.5004) **düşük**. İki sınıf iç içe geçmişti.
Önerilen eşik gerçek acillerin %56'sını "Belirsiz"e düşürüyordu.

Bu, eşik seçimiyle çözülebilecek bir sorun değildi; ölçülen şeyin kendisi bozuktu.

**A — Çift sigmoid.** `CrossEncoder.predict()` modelin kendi `Sigmoid()`
aktivasyonunu zaten uyguluyor, yani `[0,1]` aralığında olasılık döndürüyor.
`rag_service` bunu `calculate_sigmoid` ile ikinci kez eziyordu. Sonuç: tüm skor
uzayı `sigmoid(0)=0.500` ile `sigmoid(1)=0.731` arasına sıkışıyor, ayrım gücünün
~%77'si atılıyordu. Mevcut `rerank_threshold = 0.52` bu bozuk ölçekte kalibre
edilmişti.

**B — Birinci aşama İngilizce gömme kullanıyordu.** ChromaDB koleksiyonu
`DefaultEmbeddingFunction` (`all-MiniLM-L6-v2`) ile kurulmuştu. Türkçe sorguda
ürettiği vektörler sinyal taşımıyordu: "Kaynar su elimin üstüne döküldü" sorgusunda
`yanik.txt` ilk **beşe** bile giremiyordu; FAST inme sorgusunda `inme.txt` yoktu.
`top_k_initial = 10` olduğu için 47 chunk'tan yalnızca 10'u reranker'a ulaşıyor ve
o 10'u seçen mekanizma buydu — reranker doğru dokümanı hiç görmüyordu.

**Bu hata dün yoktu çünkü ölçülemiyordu.** 4 chunk varken `n_results=10`
koleksiyonun tamamını getiriyordu; birinci aşamanın kalitesi sonucu hiç
etkilemiyordu. Derleme büyüyünce ortaya çıktı.

### Testler bunu neden yakalamadı

`test_rag_esik_kapisi.py` sahte reranker'a **logit ölçeğinde** değer veriyordu
(`-10.0`, `10.0`). Gerçek `predict()` ise olasılık döndürüyor. Sahte, gerçek
sözleşmenin yanlışını kodlamıştı; `-10 → eşik altı` ve `10 → eşik üstü` testleri
kodda sigmoid olsa da olmasa da geçiyordu. Ayrıca gerçek modelle Türkçe retrieval'ı
sınayan hiçbir test yoktu.

Bu, Gün 11–16 ve 17+18'de belgelenen desenin aynısı: **sahte servis gerçeği yanlış
taklit ederse testler yeşil verir, üretim bozulur.**

### Ölçümler

| | Önce | Sonra |
|---|---|---|
| Test sayısı | 99 | **102** (+1 `yavas`) |
| `app/` kapsaması | %80 | **%81** |
| Bilgi tabanı | 47 chunk, `default`/384 | **48 chunk, `sentence_transformer`/1024** |
| İlgili skorlar | 0.5001 – 0.6721 | **0.0005 – 0.7381** |
| Alakasız skorlar | 0.5000 – 0.5004 | **0.0000 – 0.0030** |
| İki sınıf | **iç içe** | **ayrık** |

Commit'ler: `26b8659` (birleştirme), `44be342` (eşik kalibrasyonu).

### Seçilen eşik ve gerekçesi

`rerank_threshold = 0.005`. Alakasız maksimumun (0.0030) 1.7 katı, bir sonraki net
ilgili skora (0.0089) kadar olan boşlukta. **16/18 ilgili geçer, 0/10 alakasız
geçer.**

Script maksimum kapsama noktasını (0.0030, 17/18) öneriyor ama kendi uyarısını da
basıyor: güvenlik payı yalnızca +0.0001. Triyajda yanlış kabul, kaçırılan bir
vakadan tehlikelidir — bir basamak yukarısı seçildi.

Sayının küçük olması bir hata değil: reranker olasılık döndürüyor ve bu derlemede
alakasız eşleşmeler sıfıra yapışıyor. Önemli olan mutlak değer değil, iki sınıf
arasındaki ayrım.

### Kalibrasyon scriptinin kendi hatası

`kalibre_esik.py` eşik adaylarını sabit bir aralıktan (0.300–0.950) tarıyordu.
Düzeltme skor ölçeğini tamamen değiştirdiği için tarama asıl ayrım bölgesini
(0.003 civarı) **hiç görmedi** ve 18 ilgiliden 12'sini eleyen `0.335`'i önerdi.
Adaylar artık ölçülen skorlardan türetiliyor; çıktı güvenlik payını ve elenen
sorguların skorlarını da basıyor.

Ders: bir ölçüm aracının sabit varsayımları, ölçtüğü şey değişince sessizce
yanıltıcı hâle gelir.

### "C maddesi" ölçümle tek dosyaya indi

Tasarımın K8 kararı "derlemenin hasta diline yaklaştırılması ölçümden sonra, yalnızca
zayıf çıkan başlıklara" diyordu. Ölçüm `inme.txt`'yi işaret etti: dosya yalnızca
"FAST-ED" kısaltmasını kullanıyor, **yüz düşmesi / kolda güçsüzlük / konuşma
bozukluğu ifadeleri hiç geçmiyordu**. Hasta ise tam o kelimelerle geliyor, bu yüzden
sorgu `bilinc_degisikligi.txt`'ye düşüyordu. O dosyaya FAST bulgularının düz Türkçesi
ve belirti başlangıç saati (trombolitik penceresi için klinik olarak da gerekli)
eklendi. 15 dosya körlemesine elden geçirilmedi.

### Son incelemenin engellediği iki felaket

1. **Bilgi tabanı boşalacaktı.** `bilgi_tabani_kur.py` `/health/` 200 dönmesine
   güvenip koleksiyonu düşürecekti; oysa `/auth/me` o sırada **401** veriyordu ve 15
   dosyanın hepsi hata alacaktı. Ayrıca worktree'de `.env` olmadığı için script
   ChromaDB yerine backend'in portuna (8000) bağlanıyordu. Artık kimlik ön uçuşu,
   Chroma `heartbeat()` ve yükleme sonrası gömme doğrulaması (EF adı + 1024 boyut)
   var; sonda da "backend'in koleksiyon tekili bayat, yeniden başlat" uyarısı basıyor.
2. **Ölçüm setine sızıntı.** `inme.txt`'ye eklenen FAST cümlesi, kalibrasyondaki inme
   sorgusunun üç öbeğini de neredeyse birebir tekrarlıyordu — eşik şişirilmiş bir
   skorla seçilecekti. Sorgu, aynı klinik tabloyu protokolün kelimelerini
   kullanmadan anlatacak şekilde yeniden yazıldı.

### Doğrulama

Bilgi tabanı bge-m3 ile yeniden kuruldu ve gömme yapılandırması doğrulandı
(`sentence_transformer` / 1024). Kırık olduğu ölçülerek kanıtlanan sorgular ve üç
kontrol sorgusu canlı bilgi tabanına karşı denendi: **5/5 sorguda doğru protokol
reranker'a ulaştı ve reranker doğru olanı seçti.**

Bu ölçümde kendi kriterim de düzeltildi: başta "doğru doküman 1. sırada mı" diye
bakıyordum, oysa iki aşamalı boru hattında birinci aşamanın görevi doğru dokümanı
**ilk 10'a sokmak**; kararı reranker veriyor. `inme.txt` Türkçe sorguda 2.,
karaktersiz sorguda 8. sırada geliyor — ikisinde de reranker'a ulaşıyor.

### Gün 22'ye devredilenler (bu günden)

> **Durum güncellemesi (11 Ağustos 2026, Gün 22 birinci yarısı).**
> **Madde 1 (`yanik.txt` reranker'da çok zayıf) KISMEN KAPATILDI** — skor
> 0.0005 → 0.3848 ve hasta artık "Belirsiz" almıyor; **kalibrasyon-1 için**
> Sarı/Yeşil kriterleri ile tetkikler LLM'e ulaşıyor (kör sorguda ulaşmıyor).
> **Ama Kırmızı kriterleri hâlâ ulaşılamıyor** (üç
> sorguda 0.0002/0.0003/0.0011) ve sebebi yapısal; Gün 23 devir listesinde
> adlandırılmış defekt olarak duruyor.
> Madde 2 (karaktersiz yazım) **açık**, K2 ile bilerek ertelendi.
> Kalan maddeler **açık**.

1. **`yanik.txt` reranker'da çok zayıf.** Doğru doküman seçiliyor ama skoru 0.0005 —
   eşiğin altında, yani sistem "Belirsiz" diyor. Dosya "TVYA", "Parkland formülü"
   gibi klinik terimlerle yazılmış; hasta "kaynar su döküldü, su topladı" diyor.
   `inme.txt`'ye uygulanan C maddesi buraya da uygulanmalı.
2. **Karaktersiz yazım skorları belirgin düşürüyor.** İnme sorgusu Türkçe yazımda
   0.0089, karaktersiz yazımda 0.0031. Kullanıcılar sık sık karaktersiz yazıyor;
   sorgu normalizasyonu (ya da protokollere karaktersiz eş anlamlı eklenmesi)
   değerlendirilmeli.
3. **`yavas` test CRLF/LF farkı yüzünden üretimden farklı metin gömüyor.** Test
   `read_text()` kullanıyor (Windows'ta CRLF→LF çevirir), `/document/upload` ise ham
   baytı decode ediyor. Chunk sınırları kayıyor: test `inme.txt`'yi 1. sırada
   buluyor, üretim 2. sırada. Sonucu değiştirmedi ama bu, bugün **üçüncü** kez çıkan
   "test kurgusu gerçeği tam yansıtmıyor" deseni. Test ham bayt okumalı.
4. `/health/` ucu ChromaDB bağlantısını sınamıyor, sabit 200 dönüyor.
5. Silme ucunda `get()` + `delete()` atomik değil.
6. `sahte_chroma.py` `include` parametresini yok sayıyor.
7. Doküman uçlarında `response_model` yok; OpenAPI şeması boş kalıyor.
8. K9 — dosya adı normalizasyon çakışması (`Rapor A.txt` / `Rapor_A.txt`).

### Süreç notu

Bu gün üç kez aynı şeyi öğretti: **bir ölçümün kendisi bozuksa, ölçtüğü şey hakkında
hiçbir şey söylemez.** Bozuk eşik ölçeği, İngilizce gömme modeli ve sabit tarama
aralığı — üçü de "ölçüm yapılıyor" görüntüsü altında yanlış sayı üretiyordu.

Üçünü de yakalatan şey, bir sayıya bakıp "bu tuhaf" demek oldu: skorların 0.50
civarına kümelenmesi, aynı sorgunun yanlış protokolü getirmesi, önerilen eşiğin
acillerin yarısını elemesi. Sayı tuhafsa önce ölçüm aracına bakmak gerekiyor.

Bir de yürütme notu: `yavas` testi yazan subagent üç kez "bekliyorum" deyip
ilerlemeden döndü, ama sonunda **doğru olanı yaptı** — brief'in verdiği testin
mutasyona bağlayıcı olmadığını teşhis edip commit atmayı reddetti ve `BLOCKED`
döndürdü. Yanlış bir testi yeşil diye teslim etmektense durmak doğrudur; script
dışına çıkması haklıydı.

---

## Gün 21 · Güvenlik sıkılaştırma — hız sınırı, dosya doğrulama, hata sözleşmesi (9–10 Ağustos 2026)

### Bu gün ne yapıldı

Sistemin o güne kadar **hiç** güvenlik katmanı yoktu: CORS middleware'i eklenmemiş,
beklenmeyen hatada FastAPI'nin varsayılan yanıtı (yığın izi dahil) dönüyor, hız
sınırı bulunmuyor ve dosya yükleme yalnızca uzantıya bakıyordu. Dört katman
eklendi. Tasarım kararlarının tamamı (K1–K10)
`docs/superpowers/specs/2026-08-09-gun21-guvenlik-sikilastirma-design.md`'de.

**1 — Hız sınırı (`app/utils/hiz_sinirlayici.py`).** Kayan pencere sayacı elle
yazıldı, kütüphane eklenmedi (K1): `slowapi` yeni bir bağımlılığı hem
`requirements.txt`'e hem Docker imajına yayardı, buna karşılık sayaç kırk satır.
Asıl belirleyici test izolasyonu oldu — kendi sınıfımızda `sifirla()` bir metot,
kütüphanede kütüphanenin iç depolamasına elle müdahale demek. Saat enjekte
edilebilir (`saat=time.monotonic`), böylece pencere kayması gerçek zamana
bağlanmadan sınanabiliyor. Middleware değil **FastAPI bağımlılığı** olarak
uygulandı (K2): yol haritası uç bazında farklı sınır istiyor ve bağımlılık, hangi
ucun korunduğunu kodda görünür kılıyor. Bugün üç sayaç var:

| Sayaç | Anahtar | Sınır | Koruduğu |
|---|---|---|---|
| `genel_sinirlayici` | bağlanan uç noktanın IP'si | `rate_limit_genel` = 30/dk | `POST /ai/analiz`, `POST /speech/transkript` |
| `giris_ip_sinirlayici` | bağlanan uç noktanın IP'si | `rate_limit_giris_ip` = 30/dk | `POST /auth/login` — toplam **hacim**, başarı/başarısızlık ayırmadan |
| `giris_sinirlayici` | kullanıcı adı (`strip().casefold()`) | `rate_limit_giris` = 5/dk | `POST /auth/login` — yalnızca **başarısız** denemeler |

Giriş ucundaki iki katman birbirinin yerine geçmiyor, ikisi de geçilmek zorunda;
neden böyle olduğu aşağıdaki "gerçek sorunlar" bölümünde.

**2 — Dosya yükleme doğrulaması (`app/utils/dosya_dogrula.py`).** `/document/upload`
artık uzantıya, boyuta **ve gerçek içerik imzasına** bakıyor: PDF `%PDF-`, DOCX
`PK\x03\x04` (DOCX bir ZIP arşividir), TXT ise UTF-8 çözülebiliyorsa geçerli.
Kütüphane yine kullanılmadı (K4): yalnızca üç biçim destekleniyor ve
`python-magic` Windows'ta ayrıca `libmagic` ikilisini kurmayı gerektiriyor —
Windows'ta çalışan bir projede bu, kurulum talimatına eklenen yeni bir kırılma
noktası olurdu. Uzantı `IMZALAR` sözlüğünde kayıtlı değilse dosya **fail-closed**
reddediliyor (aşağıya bakınız). Ret mesajı tek ve genel ("Desteklenmeyen dosya",
K5): saldırgana hangi kontrolü aştığını söylemek, kontrolü aşmasını kolaylaştırır.
Ayrım yalnızca sunucu log'unda — beş ret dalının beşi de hangi kontrolün
tetiklendiğini, dosya adını ve boyutu `logger.warning` ile yazıyor. Boyut aşımı
`413` ile ayrılıyor çünkü bu bir saldırı ipucu değil: istemcinin dosyayı
küçültmesi gerektiğini bilmesi gerekiyor.

**3 — Global hata sözleşmesi (`app/main.py`).** Beklenmeyen istisnada istemciye
yalnızca `{"detail": "Sunucu hatası", "izleme_kodu": "<8 hex>"}` dönüyor; tam
yığın izi aynı kodla log'a yazılıyor (K6). İzleme kodu olmadan "hata aldım" ile
log'daki satırı eşleştirmenin yolu yok; kod, sızıntı yaratmadan teşhisi mümkün
kılıyor.

**4 — CORS ve ayar hijyeni (`app/main.py`, `app/config/config.py`,
`.env.example`).** `allow_origins` artık `"*"` değil, `settings.cors_origins`'den
geliyor; `allow_credentials=False`. Dürüst not (K7): Streamlit backend'i **sunucu
tarafından** `requests` ile çağırıyor, yani tarayıcı araya girmiyor ve CORS bugün
fiilen hiçbir saldırıyı engellemiyor. Yine de eklendi çünkü API tarayıcıdan da
çağrılabilir ve varsayılanı açık bırakmak savunulamaz. Güvenlik ayarları
`config.py`'de tek grupta toplandı (K8) — dağınık güvenlik ayarı, hangi kuralın
yürürlükte olduğunu okunamaz hâle getirir.

Commit'ler: dört görev için altı (`da21281`, `a494dfb`, `29f7219`, `295774c`,
`3ae49f3`, `4c90fe0`), tüm-dal incelemesinden sonraki düzeltme dalgası için beş
(`8272f71`, `ad1b557`, `f7acb81`, `bfb0d4a`, `0e44335`), dokümantasyon turunda
kalan üç minor için bir (`99815a2`).

### Ölçümler

| | Önce | Sonra |
|---|---|---|
| Test sayısı | 102 | **137** (136 dal kapanışında, +1 dokümantasyon turunda) |
| `app/` kapsaması | %81 | **%85** (`TOTAL 757 115 85%`) |
| `app/api/auth.py` kapsaması | %65 | **%100** |
| `app/utils/hiz_sinirlayici.py` kapsaması | — (dosya yoktu) | **%100** |
| `app/utils/dosya_dogrula.py` kapsaması | — (dosya yoktu) | %90 (81–86 açık, aşağıda) |
| Yeni bağımlılık | — | **yok** (`requirements.txt` bu dalda hiç değişmedi) |
| Değiştirilen mevcut test | — | **yok** (mevcut 102 testin hiçbirine dokunulmadı) |

Dalın eklediği testlerin hiçbiri sonradan yeniden adlandırılmadı ya da
zayıflatılmadı; düzeltme dalgalarında `tests/` altındaki diff yalnızca ekleme
gösteriyor.

### Son incelemelerin bulduğu gerçek sorunlar

Dört görev incelemesi, bir tüm-dal incelemesi ve iki yeniden inceleme yapıldı.
Aşağıdakiler kozmetik değil; her biri kodun iddia ettiği şeyi yapmadığını
gösteriyordu.

**1 — İki dosya doğrulama testi YANLIŞ SEBEPLE geçiyordu.** Görev 3'ün ilk hâlinde
`test_desteklenmeyen_uzantili_dosya_reddedilir` ve
`test_pdf_gibi_gorunen_bozuk_dosya_reddedilir` yalnızca durum kodunu (`400`)
kontrol ediyordu. Ama `.exe` zaten uçtaki **eski uzantı zinciri** yüzünden 400
alıyordu, sahte `.pdf` ise **pdfplumber'ın kendi istisnası** yüzünden. Yani imza
kontrolü tamamen silinse paket yeşil kalırdı — testler yeni doğrulayıcıyı değil,
pdfplumber'ın davranışını donduruyordu. Düzeltme, testleri mesaj iddiasıyla
bağlamak oldu: doğrulayıcının genel mesajı `"Desteklenmeyen dosya"`, eski
yolların mesajları `"Unsupported file format"` ve `"PDF processing error"`. Artık
farklı bir yoldan gelen 400 testi geçiremiyor. Mutasyonla ölçüldü — doğrulayıcı
çağrısı eski uzantı satırıyla değiştirildiğinde:

```
AssertionError: assert 'Unsupported file format' == 'Desteklenmeyen dosya'
AssertionError: assert 'PDF processing error' == 'Desteklenmeyen dosya'
3 failed, 2 passed
```

Mesaj iddiasından önce bu mutasyonda yalnızca **bir** test kırmızıya dönüyordu.
Ders eski: **bir testin geçmesi, geçtiğini sandığınız sebepten geçtiği anlamına
gelmez** — durum kodu tek başına hangi kontrolün çalıştığını kanıtlamıyor.

**2 — `IMZALAR` sözlüğü sessizce fail-open'dı.** İlk hâl `IMZALAR.get(uzanti)`
kullanıyordu: kayıtlı olmayan bir uzantı `None` döndürüyor, `None` de "imza
kontrolü yok" anlamına geliyordu. Yani `izinli_uzantilar` ayarına yeni bir uzantı
eklenip `IMZALAR`'a eklenmesi unutulsa, o biçim **hiç doğrulanmadan** geçecekti.
Güvenlik kodunda unutmanın varsayılan sonucu "kapalı" olmalı, "açık" değil.
`uzanti not in IMZALAR` kontrolüne çevrildi; `"txt"` bilerek `None` değeriyle
**kayıtlı** duruyor (imzası yok ama tanınıyor).

**3 — Giriş sınırlayıcısı Docker dağıtımında tek kovaya çöküyordu.** Tüm-dal
incelemesinin karar gerektiren bulgusu buydu. Sınırlayıcı IP ile anahtarlanıyordu
ve gerekçe "aynı IP'den gelen denemeler" diyordu — ama Streamlit backend'e
**sunucu tarafından** gidiyor (`BACKEND_URL=http://backend:8000`), yani tüm
girişler frontend konteynerinin IP'sinden geliyor. Sonuç: `/auth/login`
"kullanıcı başına 5/dk" değil, **tüm sistem için** 5/dk. Bir hemşirenin parolasını
üç kez yanlış yazması + bir doktorun girmesi herkesi 60 saniye kilitliyordu ve
triyaj sisteminde kimlik doğrulama erişilebilirliği klinik bir meseledir. Bu bir
**delik değil**, erişilebilirlik + doğruluk kusuruydu: backend portuna doğrudan
giden saldırgan kendi kovasını alıyor ve `X-Forwarded-For` hiç okunmadığı için
sahte başlıkla kaçamıyor. Proje sahibinin kararıyla sınır kullanıcı adına
bağlandı, yalnızca **başarısız** denemeler sayılır oldu ve anahtar
`strip().casefold()` ile normalize edildi (aksi hâlde `"yok"`, `"YOK"` ve
`" yok "` üç ayrı kova olurdu, saldırgan yalnızca yazımı değiştirerek sınırı
katlardı).

**4 — Düzeltmenin kendisi bir gerileme getirdi.** Sınırı kullanıcı adına bağlamak
için `dependencies=[...]` dekoratörü uçtan çıkarıldı — ve onunla birlikte ucun
**hacim sınırı da tamamen kalktı**. Geriye yalnızca kullanıcı adı başına
başarısızlık sayacı kaldı; her istekte farklı bir kullanıcı adı denendiğinde
hiçbir kova dolmuyor. Backend portuna doğrudan vuran bir saldırgan için sonuçlar:
(a) sınırsız parola serpme — düzeltmeden önce toplam 5 deneme/dk vardı; (b)
`auth.py`'deki mevcut zamanlama sızıntısıyla sınırsız kullanıcı adı
numaralandırma (sızıntı eskiydi, ama onu pratikte kullanılamaz kılan hız kapağını
bu düzeltme kaldırmıştı); (c) `_kayitlar` sözlüğünde **saldırgan kontrollü**
sınırsız büyüme — anahtar uzayı "IP'ler, her biri 5/dk ile kapalı"dan
"saldırganın seçtiği rastgele dizeler, kapaksız"a geçmişti. İnceleyenin notu
kayda değer: *"bu, tarif edilen değişiklikten mekanik olarak çıkıyor, yani
itaatsizlik değil"* — brief anahtarı değiştirmeyi söylemişti, hacim sınırını
bırakmayı değil. Çözüm katmanlı oldu: IP anahtarlı hacim kontrolü dekoratör
olarak geri kondu (30/dk), kullanıcı adı katmanı aynen korundu, ikisi de
geçilmek zorunda. Dekoratör bağımlılığı sıraya 0. indeksten girdiği için IP
kontrolü form ayrıştırmasından, DB oturumundan ve bcrypt'ten **önce** çalışıyor:
aşırı istek `422` değil `429` alıyor, ki hacim kapağı için doğru olan bu.

**5 — Sınırlayıcının kendisi bir kaynak tüketim vektörüydü.** Görev 1'in ilk hâli
`defaultdict(deque)` kullanıyordu: görülen her anahtar için kalıcı bir giriş
yaratıyor, kuyruk boşalsa bile silmiyordu. Uçlara bağlandığında sınırlayıcının
**kendisi** saldırı yüzeyi olurdu. Düz `dict` + eşik aşıldığında bayat anahtar
temizliğine çevrildi. Temizliğin aktif bir kaydı silememesi ayrıca doğrulandı:
silme koşulu `kuyruk[-1]`'e bakıyor ve tetikleyen çağrının kendi kaydı hemen önce
eklendiği için aktif anahtarda `şimdi - kuyruk[-1] = 0`. Yani saldırgan sözlüğü
şişirerek kendi sınırını sıfırlatamıyor.

Ayrıca kayda geçen üç küçük düzeltme: tasarım K2'nin gerekçesi **fiilen yanlıştı**
("diğer uçların hepsi kimlik doğrulaması arkasında" diyordu, oysa
`POST /speech/kaydet` hiçbir yetki bağımlılığı taşımıyor) ve tarihli bir notla
düzeltildi; `POST /speech/transkript` sınıra bağlandı (`/ai/analiz` ile aynı
sınıfta — whisper `medium` yüklüyor, 25 MB okuyor, CPU'yu doyuruyor ve sıradan
bir `user` hesabı erişebiliyordu); izleme kodunun **log yarısı** `caplog` ile
bağlandı (istemci yarısını dondurmak yetmiyordu — `logger.exception` sessizce
`logger.error` yapılsa yığın izi kaybolur ve bütün testler yeşil kalırdı).

### Elle doğrulama (planın "atlanmaz" işaretli adımları)

Otomatik paketin yakalayamayacağı üç şey elle koşuldu.

**(1) İki hız sınırı katmanı ayrı ayrı kanıtlandı.**

- *Kullanıcı adı katmanı:* aynı adla 7 başarısız giriş →
  `401, 401, 401, 401, 401, 429, 429`. Tam sınırda (5 geçti, 6. reddedildi).
  İzolasyon kanıtı: tam o anda `hasta` **doğru** parolayla `200` aldı. Yani
  kilitlenen saldırgan meşru kullanıcıyı kilitlemiyor ve başarılı giriş kullanıcı
  adı kotasını tüketmiyor.
- *IP katmanı:* 26 istek, **her biri farklı** kullanıcı adıyla (böylece her
  kullanıcı kovası 1'de kalıyor, sınır 5, yani kullanıcı adı katmanı asla
  tetiklenemez). Kova test başlamadan önce 8 istek taşıyordu ve `429` tam
  **#23'te** başladı: 8 + 22 = 30 dolmuş, 23. istek 31. olmuş. Aritmetik birebir
  tuttu. Bu 429 kullanıcı adı katmanından **gelemez**; kaynağı IP katmanı.
  Ölçümü bağlayıcı yapan şey buydu — sayı tahmin edilmedi, önceden hesaplanıp
  doğrulandı.

**(2) Gün 19'un uçtan uca döngüsü (K10) tam geçti.** `hasta` girişi `200` →
`/ai/analiz` **gerçek** Ollama + bge-m3 + reranker ile koşuldu. Retrieval doğru
protokolü getirdi (`gogus_agrisi.txt`), eşiği geçti, LLM "Kırmızı" / Kardiyoloji /
`["EKG", "Kan basıncı kontrolü"]` döndü (`visit_id`
`b558b79a-54a0-44c3-9444-2da7515e8333`). `doctor` girişi → `/doctor/bekleyen`
ziyareti gördü → `/doctor/inceleme` `201`; `doctor_id` gövdeden değil JWT'den
geldi. **Değişmez kural doğrudan Postgres sorgusuyla doğrulandı:**

```
status=tamamlandi | AI     : Kırmızı / [EKG, Kan basıncı kontrolü]
                  | DOKTOR : Sarı    / [EKG, Troponin, Akciğer grafisi]
```

AI satırı **değişmedi**, doktor satırı yanına yazıldı — denetim izi sağlam ve Gün
23'ün değerlendirmesi tam bu farkı ölçecek. İkinci onay `409` aldı, ziyaret
bekleyen listesinden düştü.

**(3) Doğrulayıcı meşru dosyayı reddetmiyor.**
`ornek_dokumanlar/protokoller/gogus_agrisi.txt` → `201`, 3 chunk. Karşıt kontrol:
`.exe` → `400`, MZ başlıklı sahte `.pdf` → `400`, **ikisi de** genel
`"Desteklenmeyen dosya"` mesajıyla (K5 korunuyor, hangi kontrolün tetiklendiği
sızmıyor). Bilgi tabanı zarar görmedi: `/document/liste` → 15 dosya / 48 chunk,
Gün 20 kapanışındaki değerlerin aynısı.

### Ortam notu — Docker yığını 7 gündür kırık

Elle doğrulama sırasında ortaya çıktı: backend ve frontend konteynerleri **yedi
gündür crash loop'ta**. Sebep kodda değil: compose yığını
`C:\Users\batuh\Desktop\Ai_Triage` dizininden başlatılmış — artık kullanılmayan
eski yol, içinde yalnızca Docker'ın mount ederken yarattığı **boş** `app/` ve
`frontend/` dizinleri var. Postgres ve ChromaDB adlandırılmış volume kullandığı
için etkilenmedi, o yüzden veri kaybı yok ve bilgi tabanı yerinde duruyor.

Doğrulama bu yüzden **yerel** backend ile yapıldı: worktree'ye `.env` kopyalandı
(`.gitignore`'da olduğu `git check-ignore` ile doğrulandı, commit riski yok) ve
uvicorn `127.0.0.1:8000`'de koşuldu. Bir sonraki kişi aynı teşhisi baştan
yapmasın diye buraya yazılıyor: **konteynerler ölüyse önce compose'un hangi
dizinden başlatıldığına bakın.** Öksüz yığın hâlâ duruyor, temizlenmesi gerekiyor.

Ayrıca gerçek `ai_triage` veritabanında bu doğrulamadan bir demo ziyaret kaldı
(`b558b79a…`) — AI "Kırmızı", doktor "Sarı" farkıyla, mentor sunumunda denetim
izini göstermek için kullanılabilir. İstenmezse silinebilir.

### Gün 22'ye devredilenler (bu günden)

İki grup ayrı tutuluyor, çünkü ikisi farklı sebeple ertelendi ve farklı sebeple
yeniden değerlendirilmeli.

**A — Ucuz ama bugün değeri düşük** (etkisi ölçülü olduğu için ertelendi; hızlı
bir turda toplu kapatılabilirler)

1. **Boyut kontrolü `await file.read()`'ten SONRA çalışıyor**
   (`app/api/document.py:72-75`). Yani 2 GB'lık bir yükleme `413` görmeden önce
   2 GB RAM tahsis ediyor. Şiddeti sınırlı çünkü uç `admin` rolüne kapalı — yani
   bunu yapabilen kişi zaten bilgi tabanını silebiliyor. Buna karşılık
   **düzeltmesi ~3 satır**: Starlette `UploadFile.size`'ı uç gövdesi hiç
   çalışmadan önce dolduruyor, dolayısıyla `read()`'ten önce bakılabilir. Ucuz
   olduğu için değil, bugün az riskli olduğu için ertelendi; Gün 22'de ilk
   kapatılacak madde bu olmalı.
2. **`document.py:82/88/93`'teki ayrıntılı mesajlar K5'i deliyor.**
   `"PDF processing error"`, `"DOCX processing error"`, `"Encoding error"`
   istemciye gidiyor ve hangi **aşamanın** patladığını söylüyor. K5 tam olarak
   bunu yasaklıyor. Gerilim gerçek ama hafif: bunlar statik dizeler, iç yapıyı ya
   da yığın izini sızdırmıyorlar; saldırganın öğrendiği şey "dosya PDF ayrıştırma
   aşamasına kadar geldi" bilgisi. Doğrulayıcı devreye girdikten sonra bu dallara
   ulaşmak da zorlaştı (imza kontrolünü geçmesi gerekiyor).
3. **`429` yanıtında `Retry-After` başlığı yok.** İstemci ne kadar bekleyeceğini
   bilmiyor, bu yüzden ya hemen tekrar deniyor ya da gereğinden uzun bekliyor.
   Sunucu tarafında koruma çalışıyor; eksik olan istemci nezaketi. Pencere sabit
   (60 sn) olduğu için sabit bir başlık bile bugünkünden iyi olur.
4. **`dosyayi_dogrula` `dosya_adi`'nın `str` olduğunu varsayıyor.**
   `file.filename` `None` gelirse `.lower()` patlıyor ve istemci `400` yerine
   `500` alıyor — yani doğrulanabilir bir ret, beklenmeyen bir sunucu hatası gibi
   görünüyor. Tek satırlık bir koruma yeterli.
5. **`500` yanıtı CORS başlığı taşımıyor** (`app/main.py:53-68`). Handler'ın
   ürettiği yanıt `ServerErrorMiddleware` içinde doğuyor ve o middleware CORS'un
   **dışında**, yani tarayıcı istemcisi `izleme_kodu`'nu okuyamaz. Bugün etkisi
   **sıfır**: Streamlit backend'e sunucu tarafından `requests` ile gidiyor,
   tarayıcı araya hiç girmiyor. API gerçekten bir tarayıcı istemcisi kazanırsa
   bu madde aniden değer kazanır — o zamana kadar ertelenmesi doğru.

**B — Pahalı ya da karar gerektiriyor** (bir sonraki gün "hızlıca" kapatılamaz)

6. **Uçtan uca PDF/DOCX yükleme testi yok.** Yeşil yol yalnızca **birim**
   seviyesinde kapalı (`tests/birim/test_dosya_dogrula.py`); `/document/upload`
   ucundan gerçek bir PDF/DOCX geçiren test yok. `IMZALAR["pdf"]` yanlış yazılsa
   her gerçek PDF yüklemesi kırılır ve paket yeşil kalır. Not: bu sorun ilk
   yazıldığından **daha zayıf** — `.txt` yeşil yolu `test_document_api.py:150-179`
   içinde uçtan uca zaten kapalı, yani "hiçbir yeşil yol test edilmiyor" doğru
   değil. Pahalı olan kısım: depoya küçük ama gerçek bir PDF ve DOCX fixture'ı
   eklemek ve bunların Windows/Docker'da aynı davranmasını sağlamak.
7. **DOCX imzası herhangi bir ZIP'i kabul ediyor ve `MAX_UPLOAD_MB` SIKIŞTIRILMIŞ
   baytı sınırlıyor.** `PK\x03\x04` her ZIP'in başlangıcı; 10 MB'lık bir zip
   bombası `python-docx` içinde gigabaytlara açılabilir. Ayrıca boyut sınırı
   chunk maliyetini bağlamıyor: 10 MB düz metin ~13.000 chunk üretebilir ve
   gömme maliyeti oradan patlar. İkisi de `admin`'e kapalı olduğu için bugün
   kabul edildi. Gerçek düzeltme imza kontrolüyle çözülmüyor — açılmış boyutun
   ya da chunk sayısının ayrıca sınırlanması gerekiyor, yani yeni bir karar.
8. **`raise_server_exceptions=False` paylaşılan fixture'a, yani TÜM pakete
   uygulandı** (`tests/conftest.py:81`). İnceleyen riski tek tek kontrol etti:
   dört `pytest.raises` bölgesinin hiçbiri istemciyi kullanmıyor ve 53 durum
   karşılaştırmasının hepsi `==` (yani `< 500` gibi gevşek bir iddia yok).
   Maliyet davranışsal değil **teşhis kalitesi**: bundan sonra bir kırılma
   traceback yerine `assert 500 == 200` olarak görünecek. Doğru düzeltme, ayarı
   yalnızca 500 gövdesini sınayan iki teste vermek — ama bu ayrı bir fixture ve
   mevcut testlerin hangisinin hangi istemciyi aldığına karar vermek demek.
9. **`auth.py`'deki zamanlama oracle'ı duruyor.** Var olmayan kullanıcı için
   `get_user` `None` dönüyor ve `verify_password` **hiç çağrılmıyor**; var olan
   kullanıcı için bcrypt çalışıyor (bu makinede tek doğrulama ~0,43 sn; 10 Ağustos'ta
dokümantasyon turunda ölçüldü, projenin resmî bir ölçümü değil). Yanıt süresi farkı,
   geçerli kullanıcı adlarını numaralandırmaya yetecek kadar büyük. Sızıntı bu
   daldan önce de vardı ve kapsam dışıydı; iki hız katmanı sömürülmesini pratik
   olmaktan çıkardı ama **kapatmadı**. Standart düzeltme (kullanıcı yoksa da sahte
   bir hash'i doğrulamak) her başarısız girişe 0,43 sn ekler — yani bu bir
   güvenlik/gecikme takası ve karar gerektiriyor.
10. **Erişilebilirlik: 30/dk'lık giriş kovasını tüm klinik paylaşıyor.** Streamlit
    sunucu tarafından çağırdığı için üretimde tüm personelin girişi tek IP'de
    toplanıyor ve IP katmanı **başarılı** girişleri de sayıyor. Sonuç: bir
    saldırgan dakikada 30 istekle tüm kliniğin girişini `429`'a düşürebilir; aynı
    şekilde bir vardiya değişiminde 30'dan fazla meşru giriş olursa personel
    kapıda kalır. Bu bir **gerileme değil** — dal öncesinde aynı kovada daha
    **sıkı** bir 5/dk vardı, yani durum düzeldi. Ama sayı klinik büyüklüğüne
    bağlı ve bugün ölçülmedi. Gün 22'de yapılacak şey kod değişikliği değil
    **ölçüm**: aynı dakikada kaç giriş oluyor? Değer ondan sonra ayarlanmalı.
    (Uyarı: IP katmanını "yalnızca başarısızları say" biçimine çevirmek bu
    sorunu çözer **görünür** ama hacim sınırını tamamen açar — geçerli tek bir
    hesabı olan saldırgan sınırsız istek atabilir. Bu refleksi
    `test_ip_katmani_basarili_girisleri_de_sayar` bloke ediyor.)

11. **`dosya_dogrula.py:81-86` hiç koşulmuyor** — geçersiz UTF-8 içeren bir `.txt`
    dosyasının reddedilme dalı. Dokümantasyon turunda kapsam raporundan okundu
    (`app/utils/dosya_dogrula.py 29 3 90%`), yani modülün açık kalan tek yeri bu.
    Ucuz görünüyor (bir bayt dizisi yeterli) ama grubu B: dalın kendi kuralı
    "önce kırmızı gör" ve bu test yazılırken doğrulanması gereken şey mesajın
    `GENEL_RET` olduğu — yoksa `test_document_api.py`'deki `"Encoding error"`
    yoluyla karışır ve madde 2'deki hatanın aynısı tekrarlanır.

**Ayrıca kayda geçenler (bugün eylem gerektirmiyor):** bayat anahtar süzmesi
>10.000 aktif anahtarda her istekte O(n) (teorik, tek süreçte ulaşılması zor);
sayaçlar süreç belleğinde, yani `--workers > 1` dağıtımında her süreç ayrı sayar
(K1'in bilinen sınırı, Redis vb. gerektirir); `allow_credentials=False` hiçbir
testle bağlı değil (yarın sessizce `True`'ya dönse 137 test de yeşil kalır, tek
satırlık bir iddia yeter); `/ai/analiz` ile `/speech/transkript` **aynı** kovayı
paylaşıyor, yani 30/dk ikisinin toplamı için geçerli; tasarım dokümanının "Bitti
sayılır" listesi hâlâ 115 test diyor ve K2'nin tablosu "yalnızca iki uç" derken
üçüncü uç hemen altındaki tarihli düzeltmede yazıyor.

### Süreç notu

Bu günün asıl dersi kodda değil, sürecin kendisinde. İnceleyenin tüm-dal
raporundaki cümlesi:

> *"Dört ayrı görev incelemesi sekiz bulgu üretti, hepsi doğru triyaj edildi,
> hiçbiri kalıcı bir yere yazılmadı. Görev inceleme döngüsü çalışıyor; eksik olan
> adım `progress.md`'den `ek-c-ilerleme.md`'ye devir — ve o adım bu analizin
> haftayı atlatıp atlatmayacağını belirliyor."*

Dal on bir commit boyunca on dört dosya değiştirdi ve **hiçbiri doküman değildi**.
D1–D8 yalnızca `.superpowers/sdd/…/progress.md` içinde yaşıyordu; o dizin
git-ignore'lu ve birleşmeden sonra silinecek. Erteleme kararlarının hepsi
doğruydu — yanlış olan, kaydedilmeden ertelenmeleriydi. **Kaydedilmeden ertelemek
unutmaktır.** Bu bölüm o devrin kendisi.

İkinci ders, aynı hatanın iki kez çıkmasından: dal, yanlış olduğu için
**yapılandırma yorumu düzeltmek** zorunda kaldı. Önce K2'nin gerekçesi ("diğer
uçların hepsi kimlik doğrulaması arkasında" — `POST /speech/kaydet` değildi),
sonra `config.py` ve `.env.example`'daki "iki sayaç da" (üç sayaç vardı) ve
`auth.py`'deki "meşru kullanım sınıra hiç yaklaşmıyor" (kullanıcı adı kovası için
doğru, uç seviyesinde yanlış). İkincisinde inceleyen bunu **"aynı kusur sınıfı"**
diye adlandırdı ve haklıydı: kodun işlediğinden başka bir tehdit modelini anlatan
bir yorum, sessizce yanlış değil — ona dokunan bir sonraki kişiyi yanlış yöne
ayarlatır. Sayı ya da gerekçe içeren yorumlar, kod değiştiğinde kodla aynı
turda güncellenmeli.

Üçüncüsü, bu dalın en pahalı bulgusu: **bir düzeltme kendi gerilemesini
getirebilir.** Giriş sınırını kullanıcı adına bağlamak doğru karardı, ama
dekoratörü çıkarmak hacim sınırını sessizce yok etti ve bunu ancak bir sonraki
yeniden inceleme yakaladı. Otomatik paket bu boşlukta yeşildi — çünkü hiçbir test
"hacim sınırı var" iddiasını dondurmuyordu. Bir davranış silindiğinde hiçbir
testin kırılmaması, o davranışın hiç test edilmediğinin kanıtıdır.

---

## Gün 22 · Birinci yarı — borç kapatma (10–11 Ağustos 2026)

Yol haritasının Gün 22'si "test derinleştirme, coverage kapısı, CI" diyor. Bu gün
o değil, onun **öncesi**: altı gündür Ek C'de biriken borcun, CI'ı mümkün kılan ve
Gün 23'ün ölçümünü kurtaran kısmının kapatılması. Asıl Gün 22 kendi tasarım
dokümanını ve planını alacak.

Tasarım: `docs/superpowers/specs/2026-08-10-gun22-borc-kapatma-design.md` (K1–K11).

### Borç envanteri: 60 madde, bir gün

Ek C'de **altı** ayrı "Gün 22'ye devredilenler" bölümü birikmişti (satır 326, 640,
764, 878, 1052, 1321). Doğrulama turunda üç şey çıktı:

- **Dört tekrar çifti** — K9 dosya adı çakışması, silme atomikliği,
  `sahte_chroma` `include`, `response_model` eksikliği; her biri hem 878 hem 1052
  bölümünde. Ham sayı bu kadar şişikti.
- **Bir madde çoktan kapanmıştı.** 326 bölümü "`/auth/login` uçtan uca testi —
  bugün tamamen korumasız" diyordu; Gün 21 bunu kapatmış, `auth.py` %100 kapsamda.
  Devir listesi güncellenmediği için altı gün boyunca açık göründü.
- Kalanı ~55 madde, yani bir güne sığmaz. Seçim ölçütü "önemli mi" değil **"neyi
  mümkün kılıyor"** oldu (K1): Görev 1 CI'ın ön koşulu, Görev 3 Gün 23'ün ön koşulu,
  Görev 2 sessiz veri kaybı olduğu için içeride.

Bu, devir listelerinin kendisiyle ilgili bir ders: **kapatılan madde kaydından
düşülmezse, liste zamanla gerçeği değil geçmişi anlatır.**

### Bu gün ne yapıldı

**Görev 1 — test altyapısı.** Test veritabanı kilidi (`tests/conftest.py`)
yalnızca `settings.database_url.endswith("/ai_triage_test")` bakıyordu ve iki
yönden birden kusurluydu: üretim sunucusundaki aynı adlı bir veritabanı kilitten
**geçiyor**, buna karşılık `?sslmode=require` taşıyan meşru bir adres
**takılıyordu**. Karar mantığı `tests/yardimcilar/db_kilidi.py`'ye taşındı
(conftest içindeki bir dal test edilemez, oradaki fonksiyon edilebilir) ve URL
düzgün ayrıştırılıyor: veritabanı adı tam olarak `ai_triage_test` **ve** host
`{localhost, 127.0.0.1, ::1, postgres}` kümesinde. Ortam değişkeniyle geçiş
bilerek yok (K6) — kolay kaçış kapısı olan kilit, kilit değildir.

Aynı görevde `tests/api/test_speech_api.py`'deki üç yetki/doğrulama testine
`transkript_engelle` fixture'ı bağlandı. Bu testler bugün uç gövdesine hiç
girmiyor, ama korudukları kural gevşerse istek ilerliyor ve gerçek faster-whisper
`medium` modeli iniyor. CI'da bu, yol haritasının önceden kaydettiği "testler 10
dakikayı geçiyor" tuzağının ta kendisi. Bu, aynı kusur deseninin **üçüncü ve son
bilinen** örneğiydi (`/ai/analiz`, `/document/upload`, `/speech/transkript`);
desen artık kapalı.

**Görev 2 — şema.** `ai_recommendations.visit_id` unique yapıldı ve
`doctor_reviews.doctor_id` index'lendi, tek Alembic revision'ında
(`6922a872c59d`). Kapatılan şey stil değil sessiz veri kaybı: `Visit.recommendation`
ilişkisi `uselist=False` diyordu ama veritabanı bunu hiç dayatmıyordu; bir ziyarete
ikinci bir öneri satırı yazılsa hem ilişki yalanlanır hem de doktor kuyruğunun
`joinedload` + `LIMIT 20` sorgusu 20 satır döndürüp yalnızca 19 farklı ziyaret
kapsar — **kuyruktan sessizce düşen bir hasta** demek.

**Görev 3 — retrieval.** `yanik.txt` klinik dilde yazılmıştı ("TVYA", "Parkland
formülü", "bül", "sirkumferansiyel"), hasta ise "kaynar su döküldü", "su topladı",
"kabardı" der; "haşlanma" belgede yalnızca bir kez geçiyordu. Sonuç: reranker
yanık protokolüne **0.0005** veriyordu, eşik 0.005, yani `retrieve_and_rerank`
boş liste döndürüyor, LLM hiç çağrılmıyor ve sistem yanık hastasına **"Belirsiz"**
diyordu. Protokole hasta dili eklendi ve kalibrasyon sorgusu yeniden yazıldı.

### Ölçümler

| | Önce | Sonra |
|---|---|---|
| Test sayısı | 137 | **153** |
| `app/` kapsaması | %85 | %85 |
| `auth.py` kapsaması | %100 | %100 |
| Alembic head | `72dffb9e5194` | **`6922a872c59d`** |
| Yanık sorgusu reranker skoru | **0.0005** | **0.3848** |
| Kalibrasyon `ILGILI` seti | 18 sorgu | **20 sorgu** |
| Yeni bağımlılık | — | yok |

Hiçbir mevcut test **zayıflatılmadı** veya yeniden adlandırılmadı. Üçü
değiştirildi ve üçü de güçlendirildi: `test_speech_api.py`'deki yetki/doğrulama
testlerine `transkript_engelle` fixture parametresi eklendi; gövdeleri ve
iddiaları aynı kaldı. (Tasarım dokümanı "hiçbir test değiştirilmez" derken tam
o düzenlemeyi mandate ediyordu — kendi içinde çelişiyordu, burada düzeltiliyor.)

Yukarıdaki tablo yalnızca kazanılanı gösteriyor. **Bir gerileme de oldu:**
pediatrik haşlanma probu 0.0186 → 0.0044'e düştü ve artık "Belirsiz" alıyor,
çünkü Kırmızı+Sarı'yı birleştiren eski chunk ikiye bölündü. Yön emniyetli
(hasta insan triyaj bankosuna gidiyor) ama pay %12, yani gürültü seviyesinde;
ayrıntısı Gün 23 devir listesinin 5. maddesinde.

### İncelemelerin bulduğu gerçek sorunlar

Üç görev incelemesi ve üç yeniden inceleme koşuldu. Değerli olanlar şunlar.

**1. Kilidin kendi kaçış kapısı — ve yanlış önerme kuran yorum.** Plan şu kodu
mandate etmişti:

```python
# Host boşsa (Unix soketi) yerel kabul edilir; uzak bir sokete bağlanılamaz.
host = url.host or "localhost"
```

Önerme yanlıştı. Boş host "Unix soketi" demek değil: SQLAlchemy host'u bağlantı
argümanlarından çıkarır, libpq da **`PGHOST` ortam değişkenine** düşer.
`PGHOST=prod-host` iken `postgresql:///ai_triage_test` kilitten geçiyor ve
`drop_all` **üretim sunucusunda** koşuyordu — tam olarak
`test_uzak_host_ayni_ad_olsa_bile_reddedilir`'in engellemek için yazıldığı senaryo,
hiçbir testin kapsamadığı tek daldan. K6 zaten "kolay kaçış kapısı olan kilit,
kilit değildir" diyordu, yani plan kendi kararıyla çelişiyordu. Boş host artık
reddediliyor ve `test_hostsuz_url_reddedilir` bunu bağlıyor.

**2. Brief'in kendi içinde tutarsızlığı — ve uygulayıcının haklı sapması.**
Görev 2'nin brief'i dosya listesinde yalnızca `app/models/visit.py`'yi sayıyordu,
ama mandate ettiği migration gövdesi **ikinci bir tabloda** index yaratıyordu.
Uygulayıcı `alembic check` koşup bir sonraki autogenerate'in
`ix_doctor_reviews_doctor_id`'yi **düşüreceğini** gösterdi — K7'nin adıyla andığı
hatanın ta kendisi — ve modele `index=True` ekledi. İnceleyen sapmayı yalnızca
onaylamakla kalmadı, **gerekli** buldu.

**3. "Belirsiz" kusuru kapandı, yerine bilgisiz vaka geldi.** İlk retrieval
düzeltmesi skoru 0.0005'ten 0.4291'e çıkardı ve test yeşil oldu. İnceleyen üretim
bölücüsünü **kendi koşup** asıl durumu gördü: eklenen metnin hepsi chunk 0'a
düşmüştü, ve LLM'e giden tek belge oydu — içinde **hiç Kırmızı/Sarı/Yeşil kriteri
ve hiç Önerilen Tetkik yok**. Yani hasta artık "Belirsiz" almıyordu ama sistem
triyaj ölçütü görmeden karar veriyordu. Hasta dili kriter maddelerine dağıtıldı;
Kalibrasyon-1 için kriter ve tetkik chunk'ları artık LLM'e ulaşıyor.

**4. Tıbbi belgede klinik hata — ve onun sorgu biçimli olması.** Kriter
maddelerine gloss eklenirken `:31`'in kritik bölge listesine **"kolunu"**
girmişti. Kol kritik bölge değildir (yüz, el, ayak, perine, büyük eklemler);
madde izole önkol haşlanmasını Yeşil'den Sarı'ya çıkarıyor ve aynı dosyanın
`:35` satırıyla çelişiyordu. İnceleyenin asıl uyarısı bileşiktir: bu, **ölçülen
kalibrasyon sorgusuna en çok benzeyen** gloss'tu ve skoru 0.0003 → 0.0750 yapan
chunk'ta duruyordu. *Klinik olarak yanlış ve sorgu biçimli* aynı anda, bir tıbbi
belgede. Ayrıca `:37` el yanığını Yeşil örneği olarak veriyordu, oysa `:31` el
yanığını Sarı'ya yolluyordu — belge en sık göreceği vakada kendisiyle çelişiyordu.
Beşi de düzeltildi.

**5. Aynı kaçış kapısının ikinci örneği — bir gün sonra, aynı dosyada.**
Tüm-dal incelemesi kilitte ikinci bir delik buldu ve mekanik olarak kanıtladı:

```
make_url("...@localhost:5432/ai_triage_test?host=prod-host").host  ->  "localhost"
create_connect_args(...)["host"]                                    ->  "prod-host"
```

libpq bağlantı hedefini query parametrelerinden de alır ve bunlar URL'in kendi
alanlarını **ezer**. Kilit "localhost" görüp güvenli der, psycopg2 üretim
sunucusuna bağlanır, `drop_all` orada koşar.

**İlk düzeltme yanlış şekildeydi ve bir sonraki inceleme onu da yakaladı.** Üç
parametre (`host`, `hostaddr`, `service`) bir **kara listeye** kondu; kara liste
fail-**open**'dır ve nitekim `dbname` gözden kaçtı:

```
hedef_guvenli_mi(".../ai_triage_test?dbname=ai_triage")  ->  (True, "")
psycopg2 DSN                                             ->  dbname=ai_triage
```

Bu, bildirilen delikten **daha kötüsüydü**: `host=` bypass'ı erişilebilir bir
üretim sunucusu ister, `dbname=` yalnızca geliştiricinin kendi makinesini —
`docker compose` üretim veritabanını tam da o host ve portta sunuyor. `port=`
de aynı mekanizmadan açıktı (beyaz listedeki bir host üzerinde üretime açılmış
bir tünel).

Doğru şekil, URL'in görünen hâlini değil **psycopg2'ye verilecek hedefi**
doğrulamaktır: `create_connect_args` çözülüyor, `dbname`/`host`/`hostaddr`/`port`
o çıktıdan okunuyor, `service` (hedefi göremediğimiz bir dosyadan okuduğu için)
baştan reddediliyor. On beş bypass vektörü tek tek ölçüldü ve on beşi de doğru
sonuç veriyor.

Bunun öğretici yanı ikili. Birincisi **tekrar**: boş-host deliği bir gün önce
aynı dosyada, aynı gerekçeyle (K6) bulunup kapatılmıştı — bir güvenlik
kontrolünde bypass bulununca doğru refleks onu kapatmak değil **aynı sınıftan
başkasını aramaktır**; burada üç tur sürdü. İkincisi **şekil**: bu depo dosya
doğrulamasında bilinçli olarak fail-closed davranıyor (`IMZALAR`'da kaydı olmayan
uzantı reddedilir), ama aynı repo aynı hafta kilidi fail-open yazdı. Doğru
soru "hangi parametreler tehlikeli" değil, **"doğruladığım şey bağlandığım şey mi"**.

### Kör sorgu: günün en bilgilendirici ölçümü

K5 "tutulan sorgu" kuralı koymuştu: ikinci bir yanık sorgusu, belgeye
dokunulmadan **önce** yazılacak ve skoru en sonda ölçülecekti. Uygulayıcı sırayı
harfiyen izledi. Ama inceleme, garantinin **yukarıdan delindiğini** gösterdi:
plandaki protokol metnini de her iki sorguyu da aynı kişi (kontrolcü) yazmıştı,
ve tutulan sorgunun ayırt edici sözcükleri ("ütü", "deri soyulması") metinde
ekiliydi.

Bunun üzerine proje sahibi, `yanik.txt`'nin yeni metnini **görmeden** bir sorgu
yazdı:

> "mangalda kolumu ateşe tuttum, kolum bembeyaz oldu hissetmiyorum"

Körlüğü ölçülerek doğrulandı: "beyaz", "hisset", "his kaybı", "uyuş", "ağrısız"
kelimelerinin hiçbiri belgede geçmiyordu. Klinik olarak tam kalınlıkta (3. derece)
yanığı tarif ediyor — beyaz/mumsu görünüm ve sinir uçları harap olduğu için **ağrı
yokluğu**; belge o tabloyu yalnızca "3. derece" diye anıyordu, hasta ise asla öyle
demez.

**Sonuç: düzeltme genelleşmiyor.** Kör sorgu eşiği geçiyor (0.0241) ama LLM'e
giden tek belge yine hasta-dili chunk'ı; kriter yok, tetkik yok. Ve asıl bulgu:
`yanik#1` (Kırmızı kriterleri) **üç sorgunun üçünde de** eşiğin çok altında —
0.0002 / 0.0003 / 0.0011.

### Neden metin eklemek çözmedi

Tam kalınlıkta yanığın hasta dilindeki tarifi Kırmızı kriterlerine eklendi. Klinik
olarak doğruydu ve belgede gerçek bir boşluğu kapatıyordu. **Retrieval'ı hiç
değiştirmedi:** cümlenin düştüğü chunk'ın skoru 0.0029 → 0.0029.

Chunk haritası sebebi gösterdi: cümle, içeriği inhalasyon yanığı + karbonmonoksit
+ TVYA/Parkland + yüksek voltaj olan 965 karakterlik bir bloğa düştü. **Reranker
chunk'ın tamamını sorguyla karşılaştırıyor, cümleyi değil.** Ağırlıklı olarak başka
şeyden bahseden bir bloğa bir cümle eklemek onu getirilebilir yapmıyor — cümle
seyreliyor.

Genellenebilir hâli: **retrieval kelimenin varlığını değil, chunk başına
yoğunluğunu izliyor.** Haşlanma ekseni bu yüzden düzeldi (on üç maddeye dağıtılmış
yoğun kelime dağarcığı), alev/tam kalınlık ekseni bu yüzden düzelmedi (tek cümle).
Çözüm metin ekleme değil yapısaldır ve bugünün kapsamı dışındadır.

Bir de kendi ölçümümün düzeltmesi: önceki notlarda chunk'lar **başlık** varlığına
göre etiketlenmişti, ama örtüşmeli bölme başlıkları kendi maddelerinden ayırıyor
("Kırmızı Alan Kriterleri" başlığı bir chunk'ta, maddeleri sonrakinde). Bulgunun
özü değişmedi, etiketleme yanlıştı.

### Doğrulama

Bilgi tabanı `scripts/bilgi_tabani_kur.py` ile sıfırdan kuruldu: **15 dosya /
51 chunk** (`yanik.txt` 6 chunk), gömme doğrulandı (`sentence_transformer`,
1024 boyut). Bu adım atlanamaz — `yanik.txt` değişti, yeniden yükleme yapılmadan
kalibrasyon eski gömmeleri ölçer.

`scripts/kalibre_esik.py` çıktısı (eşik 0.005):

| | Sonuç |
|---|---|
| İlgili sorgular | **19/20 geçer** |
| Alakasız sorgular | **0/10 geçer** |
| İlgili skor aralığı | 0.0031 – 0.7381 |
| Alakasız skor aralığı | 0.0000 – 0.0030 |
| Güvenlik payı | +0.0020 |

Geçemeyen tek sorgu `inme`'nin karaktersiz yazımı (0.0031) — K2 ile **bilerek**
kapsam dışı bırakılan madde. Üç yanık sorgusu da geçiyor: 0.3848 (kalibrasyon 1),
0.1521 (kalibrasyon 2), 0.0241 (kör sorgu).

**Script 0.0030 öneriyor ve bu reddedildi (K3).** Kendi uyarısını da basıyor:
güvenlik payı +0.0001, yani alakasız bir sorgu kolayca geçebilir. `rerank_threshold`
**0.005'te kaldı**; içerik düzeltmesinin yan etkisi olarak eşiği oynatmak, Gün 20'de
yazılı gerekçeyle seçilmiş bir kararı sessizce iptal etmek olurdu.

### Gün 23'e devredilenler (bu günden)

**A — Retrieval, ve ilki adlandırılmış bir defekt**

1. **`yanik.txt`'nin Kırmızı kriterleri hasta dilinden ulaşılamıyor.** Üç bağımsız
   sorguda 0.0002 / 0.0003 / 0.0011. Sebep yukarıda: reranker chunk'ın tamamını
   puanlıyor, yoğun kelime dağarcığı olmayan bir bloğa tek cümle eklemek seyreliyor.
   Çözüm **yapısal** ve üçü de ölçümle birlikte denenmeli: akuite başına
   hasta-sunumu bölümü, daha küçük chunk, ya da `top_k_initial` artırımı.
   **Gün 23'ün yanık senaryoları bunu bilerek kurulmalı** — kriter görmeden verilen
   bir triyaj kararı ölçülüyor olacak.
2. **`kalibre_esik.py` kaynak kör.** Yalnızca en yüksek skoru ölçüyor, hangi
   protokolün kazandığına ve kaç kriter chunk'ının geçtiğine hiç bakmıyor. Bu
   teorik değil: chunk-0-only defektini sağlıklı bir 0.4291 diye gösterdi, ve
   "çamaşır suyu içtim" sorgusu için **`GEÇER 0.1001`** basıyor — oysa o sorgu
   artık hiç `zehirlenme.txt` bağlamı almıyor. Yukarıdaki 19/20 sayısının yanına
   bu kayıt düşülmeli.

   **Sebebi ölçüldü ve ilk hipotez yanlış çıktı.** İnceleme, `:25`'e eklenen
   "yutulan kimyasallar zehirlenme protokolüne aittir" cümlesinden şüphelenmişti
   (`yanik.txt`'yi daha çok yutma belgesi gibi gösterip rekabeti artırdığı için).
   Cümle kaldırılıp yeniden ölçüldü: `zehirlenme.txt` **yine ilk 10'da yok**.
   Skorlar oynadı (`yanik#3` 0.0156 → 0.0415), sonuç değişmedi. Yani sebep o
   cümle değil, `yanik.txt`'nin 4 → 6 chunk'a büyümesiyle sabit 10 kişilik aday
   havuzunu doldurması — aşağıdaki 3. madde. Cümle geri konmadı: retrieval'a
   ölçülen faydası yok ve "bu protokole değil …" kalıbı, kostik yutmaya sık
   eşlik eden yüz/havayolu yanıklarında yanıltıcı biçimde mutlak.
3. **`top_k_initial = 10`, 51 chunk'lık derlemeye karşı.** Artık yalnızca geri
   çağırmayı sınırlamıyor, **doğru protokolün chunk'larını dışarı itiyor**
   (çamaşır suyu sorgusu). Eşikle birlikte ölçülmeli, ikisi etkileşiyor.
4. **Karaktersiz yazım** (`inme` 0.0089 → 0.0031). K2 ile bilerek ertelendi; çözümü
   ya üretim sorgu yolunu değiştirmek ya da 15 protokole ASCII eş anlamlı eklemek,
   ikisi de ayrı karar.
5. **Pediatrik haşlanma probu gerileme yaşadı** (0.0186 → 0.0044, "Belirsiz").
   Sebep: eski chunk Kırmızı+Sarı'yı birleştiriyordu, yeni kesim ayırıyor.
   Uygulayıcı bilerek o sorguya göre metin yazmadı (ölçülmüş sorguya ayarlamak
   hiçbir şey kanıtlamaz) — doğru karar, ama disiplini koruyan ucuz hamle vardı:
   sorguyu bir sonraki düzenlemeden **önce** `ILGILI`'ye eklemek.

**B — Test ve şema borcu**

6. ~~**Migration zinciri pytest altında hiç koşmuyor.**~~ **KAPATILDI** (Gün 22
   ikinci yarısı). `conftest.py` şemayı hâlâ `create_all` ile kuruyor — yani
   *pytest altında* migration'lar koşmuyor ve bu bilinçli, testler hızlı kalsın
   diye. Boşluğu CI'ın ayrı bir `migration` işi kapatıyor: boş bir veritabanında
   `upgrade head` → `downgrade base` → `upgrade head`. Zincir push'tan önce
   yerelde tek kullanımlık bir şemada da prova edildi ve dört revision her iki
   yönde de geçti.
7. **Unique kısıt modelde adsız**, yani adı ortama göre değişiyor (`create_all` →
   `ai_recommendations_visit_id_key`, migration → `uq_ai_recommendations_visit_id`).
   Bugün zararsız; `IntegrityError` mesajına bakıp `409` üreten bir kod yazılırsa
   testte farklı davranır.
8. ~~**Yeni `yavas` test chunk-0-only durumunu yakalayamaz.**~~ **KAPATILDI**
   (aynı gün, tüm-dal incelemesinin bulgusu üzerine). Test artık dönen yanık
   belgelerinden en az birinin triyaj ölçütü taşıdığını iddia ediyor; kör
   sorgunun bugünkü davranışı da ayrı bir testte donduruldu (`assert not ...`),
   yapısal düzeltme gelince o test kırılacak ve kırılma "defekt kapandı"
   haberi olacak. **Not:** ilk deneme ölçütü "Alan Kriterleri" **başlığıyla**
   arıyordu ve iki yönde de yanlıştı — örtüşmeli bölme başlığı kendi
   maddelerinden ayırıyor, yani saf kriter maddelerinden oluşan chunk başlıksız
   kalıyor, başlığı taşıyan chunk ise ağırlıklı olarak hasta dili olabiliyor.
   Bu, Ek C'nin birkaç paragraf önce geri aldığı etiketleme hatasının aynısıydı.
   İkinci turda `yanik.txt` belgeleriyle sınırlandı ve içerik işaretleri eklendi —
   **ama başlık listede bırakıldı**, yani yanlış-pozitif yön açık kaldı ve bir
   sonraki inceleme onu da yakaladı: başlığı taşıyan chunk ağırlıklı olarak hasta
   dili + prosedür metniydi ve yalnızca başlık yüzünden "kriter var" sayılıyordu.
   Üçüncü turda başlık listeden çıkarıldı; işaretlerin hepsi artık ölçüt metninden
   (`TVYA >`, `TVYA <`, `TVYA %`, `kritik bölge`, `Önerilen Tetkikler`,
   `İnhalasyon yanığı bulguları`). Aynı hatanın üç turda kapanması, bu bölümün
   süreç notundaki "düzeltme kendi ölçüsünü üretemez" dersinin ikinci örneği.
8b. **Kilit ORTAM DEĞİŞKENİYLE hâlâ atlatılabiliyor** — URL üzerinden gelen her
   yönlendirme kapatıldı (39 vektör denendi, hiçbiri geçmiyor), ama süreç
   ortamındaki `PGHOSTADDR` ve `PGSERVICE` bağlantıyı kilidin **kendi onayladığı
   DSN'iyle** başka bir sunucuya götürüyor. İnceleme bunu canlı sunucuya karşı
   kanıtladı: `PGHOSTADDR=192.0.2.7` + onaylı adres → bağlantı 192.0.2.7'ye gitti.
   `PGPORT` de portsuz URL'lerde aynı işi yapıyor. Bu dalın getirdiği bir kusur
   değil, kilit hiç bakmadığı bir kanal; ama modülün docstring'i "çözemezsek
   reddederiz" diyor, yani belge kodun sağladığından fazlasını vaat ediyor.
   Yıkım yarıçapı `dbname` sabitiyle sınırlı — nereye giderse gitsin
   `ai_triage_test` adlı bir veritabanına gidiyor — bu yüzden Critical değil.
   Ucuz kapanış: `PGHOSTADDR`/`PGSERVICE` ayarlıysa reddet, ya da `conftest.py`
   `create_engine`'den önce bu üçünü temizlesin.
9. **`test_turkce_retrieval.py:56` hâlâ `read_text()` kullanıyor**, yeni test
   `read_bytes()`. İki fixture da "üretim sadakati" iddia ediyor, yalnızca biri
   taşıyor. Mevcut test değiştirilemediği için kapsam dışıydı.
10. **`test_config.py:17` hâlâ `endswith("/ai_triage_test")` kullanıyor** — bu günün
    conftest'ten kaldırdığı kusurlu yüklemin aynısı. Meşru bir `?sslmode=require`
    adresi kilitten geçer ama bu testte takılır.
11. `downgrade()`'de Türkçe yorum yok; revision template'in docstring'lerini
    düşürmüş (dört revision içinde tek istisna).

**C — Kapatılamayan, kayda geçen**

12. Ek C'nin altı devir bölümündeki kalan ~45 madde duruyor. Bu gün beşini kapattı,
    dördünün tekrar olduğunu ve birinin çoktan kapandığını gösterdi.

### Süreç notu

Bu günün en pahalı dersi metodolojik: **bir düzeltme kendi ölçüsünü üretemez.**
K5 "tutulan sorgu" kuralını doğru koymuştu ama garantiyi tek yazarlık deldi —
protokol metnini de ölçüm sorgularını da aynı kişi yazınca, sorgu belgenin bir
özetine dönüşüyor ve geçmesi hiçbir şey kanıtlamıyor. Bunu ne uygulayıcı ne
kontrolcü fark etti; inceleyen ölçerek gösterdi: skorlar sözcüğün **varlığını**
değil, hangi eksene **yoğun metin yazıldığını** izliyordu — "elektrik çarpması"
belgede birebir geçtiği hâlde eşiğin 1.26 katındayken, haşlanma ekseni 86 katındaydı.

Çözüm süreçseldi, kod değil: proje sahibi metni görmeden bir sorgu yazdı ve o tek
sorgu, üç görev incelemesinin bulamadığı şeyi gösterdi — düzeltme genelleşmiyordu.
**Ölçüm setini yazan kişi ile ölçülen şeyi yazan kişi ayrı olmalı.** Gün 23'ün
değerlendirme seti bu kuralla kurulmalı, yoksa doğruluk sayısı kendi kendini
doğrular.

İkinci ders birincinin devamı: **incelemeye "test yeşil mi" diye sormak yetmiyor.**
Retrieval düzeltmesinin testi yeşildi, skor 0.0005'ten 0.4291'e çıkmıştı ve her
şey doğru görünüyordu. İnceleyen üretim bölücüsünü kendi koşup LLM'e giden belgenin
içinde hiç triyaj ölçütü olmadığını gördü. Yeşil bir test, doğru şeyi ölçtüğünü
kanıtlamaz.

Üçüncüsü kayda değer bir sınır: bu gün üretim kodunda **hiçbir davranış
değiştirmedi** — Görev 1 yalnızca `tests/`, Görev 3 yalnızca veri ve ölçüm.
Değişen tek üretim satırı Görev 2'nin şema kısıtı. Buna karşılık iki gerçek
güvenlik/veri kaybı yolu kapandı ve bir tıbbi belgedeki klinik hata düzeltildi.
Borç kapatma günlerinin çıktısı böyle görünüyor: az satır, çok gerekçe.

---

## Gün 22 · İkinci yarı — tembel import, kapsama kapısı ve CI (11–12 Ağustos 2026)

Yol haritasının Gün 22'si buydu: *test derinleştirme, coverage kapısı, CI*.
Birinci yarı (borç kapatma) onun **ön koşuluydu** — speech testlerinin gerçek
faster-whisper'a ulaşması ve test veritabanı kilidinin host doğrulamaması, ikisi
de CI'ı kurulamaz kılıyordu.

Tasarım: `docs/superpowers/specs/2026-08-11-gun22-ci-kapsama-design.md` (K1–K11).

### Bu gün ne yapıldı

**Tembel import.** `app.main` import'u **28,5 saniye** sürüyor ve torch,
transformers, sentence_transformers, chromadb, faster_whisper dahil **5215
modül** yüklüyordu. Yol haritası CI tuzağını önceden kaydetmişti ("CI'da testler
10 dakikayı geçiyor — çözüm: minimal gereksinim listesi") ama o çözüm
uygulanamıyordu: `torch` modül düzeyinde import ediliyordu ve `app.main` onu
zincirle çekiyordu, yani minimal bir listeyle testler **toplanamıyordu** bile.

Ağır import'lar üç servis modülünde fonksiyon gövdesine taşındı. Dördüncü ve
**dolaylı** bir yol da çıktı: `document.py` → `langchain_text_splitters` → o
paketin `__init__.py`'si koşulsuz olarak kendi `sentence_transformers` shim'ini
import ediyor → transformers → torch. Kontrolcünün ön-uçuş taraması yalnızca
doğrudan import'lara bakmıştı ve bunu kaçırmıştı; uygulayıcı ölçerek buldu.

**Kapsama kapısı.** `--cov-branch` açıldı (kapsama artık satır değil dal bazlı)
ve `--cov-fail-under=87` dayatıldı. İki dış servis adaptörü ölçümden çıkarıldı.

**CI.** `.github/workflows/ci.yml`, iki iş: `test` (Postgres servisi,
`requirements-ci.txt`, kapsama kapısı) ve `migration` (alembic zinciri).

### Ölçümler

| | Önce | Sonra |
|---|---|---|
| Test sayısı | 153 | **157** |
| Kapsama | %85 (satır) | **%87,42 (dal)** |
| `app.main` import süresi | **28,5 sn** | **1,85 sn** |
| Yüklenen modül | **5215** | **1077** |
| Ortam boyutu | 1694 MB | **498 MB** (torch tek başına 497 MB) |
| CI | yok | **iki iş** |

**Ölçülmeyen şeyi söylemek:** kurulum **süresi** karşılaştırması hiç yapılmadı.
Minimal liste iki kez ölçüldü (6 dk 53 sn, 6 dk 19 sn) ama tam listenin kurulumu
koşulmadı. Planın ilk hâlindeki "2,5 GB'lık kurulum" ve "dakikalardan saniyelere"
ifadeleri **tahmindi** ve dördü de (plan, `rag_service.py`, muhafız testi,
`requirements-ci.txt`) ölçülen değerlerle değiştirildi.

**Yerel paket hızlanmadı** ve bu da açıkça yazılıyor. İlk bakışta 59,6 → 101 sn
gerileme göründü; uygulayıcı gizlemek yerine araştırdı ve ölçüm artefaktı
olduğunu gösterdi: ağır import'lar kök `conftest.py`'den (pytest'in *saymadığı*
yer) toplama aşamasına (*saydığı* yer) taşındı. Duvar saati neredeyse aynı.
Kazanç CI ortam boyutunda ve `app.main` import süresinde, test koşusunda değil.

### Kapsamadan hariç tutulanlar — ve neden bunu yazmak zorundayız

`.coveragerc` iki dosyayı ölçümden çıkarıyor: `app/services/llm_service.py` ve
`app/services/stt_service.py`. İkisi de testlerde **hiç çalıştırılmıyor**;
yerlerine `sahte_llm.py` ve `sahte_stt.py` geçiyor.

Gerekçe: ölçüme dahil edildiklerinde global sayı test kalitesini değil **o iki
dosyanın boyutunu** izler. `llm_service`'e elli satır eklemek kapsamayı test
kalitesiyle ilgisiz bir sebeple düşürür; tersine auth testleri boşaltılsa ölü
ağırlık sayıyı maskeleyebilir.

Bedeli dürüstlüktür: **neyin ölçülmediği yazılmadan "kapsama %87" iddiası
eksiktir.** Bu yüzden burada yazıyor. Bir yan etkisi daha var: `stt_service.py`
bu dalda *değiştirilen* üç modülden biri, ve ölçümden çıkarıldığı için oradaki
tembelleştirme çalışmasının kapsama tarafında hiçbir koruması yok — tek muhafızı
alt süreçte koşan import testi.

Eski ölçüm tablolarındaki `llm_service.py (%24)` ve `stt_service.py (%37)`
satırları artık **geçersiz**: o dosyalar ölçülmüyor.

### Muhafız testinin CI'a özgü kör noktası

Tüm-dal incelemesinin en değerli bulgusu buydu. Muhafız testi `app.main`'i alt
süreçte import edip ağır kütüphanelerin `sys.modules`'e düşmediğini iddia ediyor.
Ama `langchain_text_splitters` listede yoktu, ve o paketin shim'i
`sentence_transformers` import'unu `try/except ImportError` ile sarıyor.

Sonuç: biri `document.py`'deki import'u modül düzeyine geri koysa, **yerelde**
muhafız yakalardı (sentence_transformers kurulu, zincir yüklenir) ama **torch'suz
CI'da** shim sessizce yutardı, listedeki hiçbir ad görünmezdi ve muhafız **yeşil**
kalırdı. Gerileme fark edilmeden, sentence_transformers'ın kurulu *olduğu*
üretime giderdi. Muhafız, korumak için var olduğu ortamda en zayıftı.
Tek dizeyle kapatıldı.

### CI ne koşuyor, ne koşmuyor

`test` işi: `requirements-ci.txt` + `requirements-dev.txt`, Postgres servisi,
`pytest -m "not yavas"`. Kapsama kapısı `pytest.ini`'den geliyor — workflow
ayrıca bayrak vermiyor ki CI ile yerel **aynı** eşiği kullansın. ChromaDB servisi
yok: `entegrasyon` testlerinde Chroma sahte, yalnızca Postgres gerçek.

`migration` işi: boş bir `ai_triage` veritabanında `upgrade head` →
`downgrade base` → `upgrade head`. Yerel testler şemayı `create_all` ile kuruyor,
yani migration'lar pytest altında hiç koşmuyor; bu iş o boşluğu kapatıyor.
Zincir push'tan **önce** yerelde tek kullanımlık bir şemada prova edildi ve dört
revision her iki yönde de geçti.

`yavas` testler CI'da **hiç** koşmaz: gerçek bge-m3 (~2,2 GB), cross-encoder ve
ayakta bir ChromaDB isterler. Bunun faydalı bir sonucu var — CI'ın ölçtüğü
kapsama yereldekiyle **aynı**, yani eşik iki ortamda da aynı anlama geliyor.

### Gün 23'e devredilenler (bu günden)

1. **`requirements-ci.txt` yalnızca 21 doğrudan bağımlılığı pinliyor**, ~100
   geçişli paket yüzüyor (`numpy`, `onnxruntime`, `grpcio`, `protobuf`,
   `cryptography`…). İki bilinen sonucu var: bir geçişli sürüm CI'ı kodla
   ilgisiz bir sebeple kırabilir, ya da CI üretimin hiç koşmadığı bir bağımlılık
   kümesinde yeşil kalabilir. En olası hedef `onnxruntime` ve `pyarrow`:
   kullanılabilir sdist yayınlamıyorlar, yani manylinux tekerleği yoksa kurulum
   sert biçimde patlar. 21 pin `tests/birim/test_ci_gereksinimleri.py` ile bağlı.
2. **`--cov-fail-under` her koşuya uygulanıyor**, yani odaklı bir koşu sahte
   kırmızı verir. `CLAUDE.md`'de `--no-cov` notu var. Kapının `pytest.ini`'de
   olması bilinçli: yalnızca CI'ın hatırladığı bir kapı, unutulabilen bir kapıdır.
3. **`migration` işi zincirin *koştuğunu* kanıtlıyor, modeldeki şemayı
   ürettiğini değil.** `alembic check` bunu kapatırdı ama bugün kırmızı olması
   muhtemel — madde 7'deki adsız unique kısıt (`create_all` →
   `ai_recommendations_visit_id_key`, migration → `uq_...`) tam da bu sınıfta.
   Önce ölçülmeli, sonra eklenmeli.
4. **Aktivasyon testi artık enjekte edilen sahte Sigmoid'i doğruluyor.**
   "Argüman geçiliyor mu" hâlâ bağlı (Tanh, `None` ve sınıf-yerine-örnek
   varyantlarının üçü de kırılır); kaybolan tek şey "`torch.nn.Sigmoid` kurulu
   torch'ta gerçekten var mı", o da `yavas` testlerde duruyor.
5. **İlk `/document/upload` artık ~25 saniyeyi olay döngüsünde ödüyor**,
   açılışta değil. Admin'e kapalı ve süreç başına bir kez; depo bu deseni zaten
   kabul ediyor (`get_reranker()` istek yolunda 2 GB model yüklüyor).

### Süreç notu

Bu günün dersi bütçeyle ilgili ve dürüstçe yazılması gerekiyor: **iki subagent
art arda harcama limitine takıldı** (biri işin ortasında, biri hiç
başlayamadan). Kontrolcü kalan işi (kapsama kapısı ve CI workflow'u) kendisi
yürüttü ve kalan bütçeyi **tek ve güçlü bir tüm-dal incelemesine** sakladı.

Bu, metodolojiden bilinçli bir sapmaydı ve karşılığını verdi: o inceleme, hiç
bağımsız göz görmemiş iki görevde altı Important buldu — muhafızın CI'a özgü kör
noktası, kapıyı ölçen aracın (`coverage`) pinlenmemiş olması, ve `.coveragerc`'nin
"Ek C'ye de yazılıyor" derken yazılmamış olması dahil. Sonuncusu bu bölümün
varlık sebebi.

İkinci ders birinciyle bağlantılı: **ölçmediğini iddia etme.** Bu dal üç ayrı
turda dört yerden "2,5 GB" ve "dakikalardan saniyelere" ifadelerini temizlemek
zorunda kaldı, ve son turda kaynak olan **plan dosyası** da düzeltildi — çünkü
düzeltilmeyen kaynak, bir sonraki turda geri kopyalanır. Aynı desen Gün 22'nin
birinci yarısında `yanik.txt` için de yaşanmıştı.

## Gün 23 · Değerlendirme seti — sistemin doğruluğu sayıya dönüşüyor (12–13 Ağustos 2026)

Bugüne kadar "çalışıyor" diyorduk. Bu bölümden sonra sayı var — ve sayının
kendisinden daha önemlisi, **sayının nasıl okunacağı**.

Tasarım: `docs/superpowers/specs/2026-08-12-gun23-degerlendirme-design.md`
(K1–K15). Plan: `docs/superpowers/plans/2026-08-12-gun23-degerlendirme.md`,
sekiz görev. Ölçüm kodu `degerlendirme/` altında ve `app/`'a **hiç dokunmadı**
(K1, `git diff main...HEAD -- app/` boş): ölçülen şey Gün 22'nin bitirdiği
sistemin ta kendisi.

### Ölçülen sayılar (13 Ağustos 2026)

Ham çıktı `degerlendirme/sonuclar/2026-08-13.{md,json}`, ölçülen bilgi
tabanının parmak iziyle birlikte (15 dosya / 51 chunk, dosya kırılımı raporun
başında). Aşağıdaki tablo **üçüncü ve commit'li koşumdur**; ilk koşumun sayıları
artık üretilemez çünkü ölçüm aracı değişti, ikinci ve üçüncü koşum ise aynı
araçla yapıldı ve gürültü tabanını ölçmeyi mümkün kıldı (Bulgu 7).

| Ölçü | Kör set | Türetilmiş set |
|---|---|---|
| Sette senaryo | 9 | 20 |
| Ölçülen (kapsam içi) | 8 | 19 |
| **Genel doğruluk (tüm)** | **%37,5** | **%78,9** |
| Genel doğruluk (cevaplananlar) | %37,5 | %83,3 |
| **Kırmızı duyarlılık** | **n/d (0/0)** | **%100,0 (10/10)** |
| Eşik altı oranı | %0,0 (0) | %5,3 (1) |
| Tetkik Jaccard (ort.) | 0,15 (8 senaryodan) | 0,26 (18 senaryodan) |
| Kök neden A/B/C | 1 / 4 / 3 | 2 / 3 / 13 |
| Şanslı doğru | 0 | 0 |
| Ölçülemedi / sonucu yazılmamış | 0 / 0 | 0 / 0 |
| Kapsam dışı (doğru/toplam) | 1/1 | 0/1 |

Ses tanıma: **ortalama WER 0,143** (9 kayıt), hizalama eşiğinin (0,6) çok
altında — ses-metin eşleşmesi doğru.

**Klinik olarak en önemli tek cümle:** türetilmiş setteki 10 Kırmızı vakanın
**10'u da yakalandı**. 29 senaryonun tamamında sekiz kapsam içi hata var ve
bunların yalnızca **ikisi alt-triyaj** (`kor_07` ve `tur_17`, ikisi de Sarı →
Yeşil); beşi üst-triyaj (sistem daha temkinli davranmış), biri cevapsızlık
(`tur_07` eşik altında kaldı). Ayrıca kapsam dışı `tur_20` sızdı.

### Bulgu 1 — kör set ile türetilmiş set ayrışıyor: %37,5'e karşı %78,9

**Bu, günün asıl sonucu ve iki yazarlı set kuralının (K2/K3) varlık sebebi.**
Türetilmiş 20 senaryoyu protokolleri okuyan kişi yazdı; kör 9 senaryoyu
kullanıcı, protokol metnini **hiç görmeden**, gerçek hasta diliyle yazdı. İki
küme aynı sistemi ölçüyor ve arada iki katından fazla fark var.

Doğru okuma: **%78,9 sistemin doğruluğu değil, sorusunu belgeden türeten bir
ölçüm setinin ürettiği tavan.** Tek yazarlıkla ölçülseydi rapor "%79 doğruluk"
derdi ve bu sayı kendi kendini doğrulardı.

Üç dürüst çekince, üçü de sayıyla birlikte okunmalı:

1. **Kör set küçük.** 8 ölçülebilir senaryo, yani tek senaryo ±%12,5 oynatıyor.
   Ayrışmanın **yönü** güvenilir, büyüklüğü değil.
2. **İki etiket tartışmalı ve ikisi ters yöne çekiyor.** `kor_01` (primer baş
   ağrısı → Yeşil; gerçek acillerde BT çekilip Sarı denir) Sarı sayılırsa
   doğruluk **yükselir** (sistem Sarı dedi). `kor_02` ise `travma.txt`'nin Yeşil
   satırındaki tek literal diskalifiye edici ifadeyle çelişiyor — "(ambule
   olabilen hastalar)" diyor, hasta "üstüne kesinlikle basamıyorum" diyor — ve
   Sarı sayılırsa doğruluk **düşer** (sistem Yeşil dedi). Dürüst bant bu yüzden
   %25–50. İlk yazımda yalnızca doğruluğu yükselten taraf yazılmıştı; tüm-dal
   incelemesi tek yönlü duyarlılık analizinin kendisinin bir kayma olduğunu
   söyledi ve haklıydı.
3. **Sınıf dağılımı iki sette farklı.** Türetilmiş 10 Kırmızı / 7 Sarı / 2 Yeşil,
   kör 0 Kırmızı / 3 Sarı / 5 Yeşil. Sekiz hatanın beşi üst-triyaj, yani
   yukarı kaçan bir sistem Kırmızı ağırlıklı sette iyi, Yeşil ağırlıklı sette
   kötü puan alır. Farkın bir kısmı **yazarlık değil bileşim**.

### Bulgu 2 — kör set, klinik olarak en kritik sayıyı hiç ölçemiyor

Kör setin Kırmızı duyarlılığı **n/d (0/0)**: kullanıcının yazdığı dokuz
şikayetin hiçbiri gerçek bir Kırmızı vaka değil. Yani **%100 Kırmızı duyarlılık
yalnızca etiketlerini uygulayıcının seçtiği sette ölçüldü** — bağımsızlık
garantisi en zayıf olan sayı, aynı zamanda klinik olarak en önemli sayı.

Bu bir kusur değil, kör setin doğal sonucu (kimse kendi acil vakasını
uyduramaz), ama gizlenmeden söylenmeli. Gün 24 / Gün 29 için somut iş:
kullanıcıdan **Kırmızı arketipli üç-dört kör şikayet** daha istemek. `n/d`
işaretinin kendisi bu yüzden değerli — "%0,0" basılsaydı "hiçbir Kırmızı'yı
yakalayamadı" diye okunurdu.

### Bulgu 3 — bölüm alanının derlemede hiçbir dayanağı yok (SİSTEM bulgusu)

İlk yazımda bu bir *altın standart* kusuru diye kaydedilmişti. **Ölçüm bunun
yanlış olduğunu gösterdi ve düzeltiliyor.**

15 protokolün hepsinde bir "— Yönlendirme" tablosu var, ama hiçbiri hastayı bir
hastane bölümüne yollamıyor; hepsi **akuite alanı** söylüyor: `sarı alan`
(derlemede 25 kez), `yeşil alan` (24), `kırmızı alan` (18), `resüsitasyon` (14),
`şok odası`. Modelin ürettiği bölüm adları ise derlemede aranınca:

| Modelin dediği | Derlemede |
|---|---|
| Pulmonoloji, Gastroloji, Ortopedi, Pediyatri, Acil Cerrahi, Travma Odası, Kardiyoloji, Dahiliye | **hiçbir protokolde yok** |
| Nöroloji, Psikiyatri, Obstetrik | geçiyor, ama bölüm ataması olarak değil |

Yani `department` alanı **dayanaksız**: model onu kendi ön bilgisinden
uyduruyor, oysa prompt kaynak dokümanlarda olmayanı uydurmayı açıkça yasaklıyor
(`app/api/ai.py:184-186`). `kor_07`'de çıkan `"İnsan Hakkında"` tekil bir
saçmalama değil, dayanaksız bir alanın uç örneği.

Bunun üzerine bölüm **C kapısından çıkarıldı** (`kok_neden`; gerekçe orada
yazılı). Akuite alanını beklenti yapmak çare değildi: o, triyaj kodunun birebir
fonksiyonu, yani sıfır bilgi ekler. Bölüm ölçümden atılmadı, **ölçülebilir bir
şeye dönüştürülmek üzere Gün 24'ün sistem hedefine taşındı** — modelin
`department` çıktısı derlemenin desteklediği kapalı kelime dağarcığına
sıkıştırılacak.

**Ama düzeltme C kutusunu kurtarmadı ve bu da bir bulgu.** Bölüm kapısı
kapatılınca türetilmiş C 15'ten **13**'e indi (koşum 3). Demek ki doygunluğun
baskın sebebi bölüm değil, aşağıdaki adlandırma artefaktı: tetkik karşılaştırması
tam eşitlik istiyor ve neredeyse hiçbir senaryoda 1,00 tutmuyor, dolayısıyla
triyaj kodu doğru olan her senaryo yine C'ye düşüyor. **A/B/C tasnifi bugün Gün
24'ün "en büyük kutuya müdahale et" kararını taşıyamaz.**

### Bulgu 4 — Jaccard'ı adlandırma artefaktı bastırıyor (önceden ilan edilmişti)

Görev 6, tetkik adlarının tam eşitlikle karşılaştırıldığını ve Jaccard'ın sistem
genelinde düşük okunacağını **ölçümden önce** kaydetmişti. Doğrulandı:

- `kor_03` — beklenen `Tam kan sayımı, Biyokimya, Tam İdrar Tetkiki, Beta-hCG`,
  çıkan `Hemogram (Tam kan sayımı), Biyokimya, Tam İdrar Tetkiki (TİT), Beta-hCG`.
  Klinik olarak **4/4 doğru**, ölçülen Jaccard **0,33**.
- `tur_01` — `EKG` ile `Elektrokardiyografi (EKG)` eşleşmiyor.

Jaccard sayıları (0,10 ve 0,26) **"model yanlış tetkik öneriyor" diye
okunamaz.** Doğru okuma: eşanlamlı/parantezli yazım normalize edilmiyor. Kırılım
tablosuna beklenen-vs-çıkan tetkik sütunları tam bunun için kondu — artefakt
sayıda değil tabloda görülüyor.

### Bulgu 5 — `yanik.txt` defekti KAPANDI, ama yerine bir aşırı-getirme geldi

Gün 22'nin "Gün 23'e adlandırılmış defekti" `yanik.txt`'nin Kırmızı
kriterlerinin hasta dilinden ulaşılamamasıydı (0,0002 / 0,0003 / 0,0011).
**Kapandı:** üç yanık senaryosunda da (`kor_05`, `tur_09`, `tur_10`)
`yanik.txt` birinci sırada geldi ve triyaj kodu doğru çıktı.

**Ama aynı düzeltme yeni bir sorun üretti.** `yanik.txt` artık derlemenin en
büyük dosyası (**6 chunk**; çoğu 3) ve kendisine ait olmayan sorguları
kazanıyor:

- **`kor_08`** — ateş/halsizlik, beklenen `ates_sepsis.txt`. Gelen tek kaynak
  **`yanik.txt`**. Yeşil yerine **Kırmızı**, ve model hiç yanığı olmayan hastaya
  yanık odaklı tetkik önerdi. Kör setteki tek A kutusu bu.
- **`tur_11`** — beklenen `zehirlenme.txt`, birinci sırada yine `yanik.txt`.

Gün 20'nin dersinin tekrarı: **bir belgeyi zenginleştirmek onu komşularının
sorgularında da güçlendirir.** Retrieval kelimenin varlığını değil chunk başına
yoğunluğunu izliyor.

### Bulgu 6 — iki gerçek retrieval/eşik hatası

- **`tur_07`** (beklenen `bilinc_degisikligi.txt`) — hiç kaynak dönmedi, yanıt
  `Belirsiz`. Eşik altında kalan tek kapsam içi senaryo.
- **`tur_20`** (kapsam dışı, beklenen `Belirsiz`) — sistem **Yeşil** dedi ve
  tetkik uydurdu (`"Sol dizimizme testleri"`). Eşik kapsam dışı bir soruyu
  geçirdi.

`rerank_threshold = 0,005` bir tarafta fazla geçirgen, diğer tarafta fazla katı.
Tek eşiğin iki hatayı birden çözemeyeceğinin ilk somut kanıtı.

Kör setin kapsam dışı senaryosu (`kor_09`, "yanlış ilaç içtim") **doğru
reddedildi** (1/1). Not: Görev 6 bunun bir **derleme boşluğu** olduğunu
kaydetmişti — `zehirlenme.txt`'de bilinmeyen madde/doz dalı yok. Doğru reddetme
burada "sistem iyi çalıştı"dan çok "bilgi tabanında yok" demek.

### Bulgu 7 — ölçümün gürültü tabanı ölçüldü: bir senaryo = 5,3 puan

Ölçüm **üç kez** koşuldu (biri araç düzeltilmeden önce, ikisi sonra). Düzeltmeler
triyaj kodlarına dokunmuyordu. Üç koşumun karşılaştırması:

| | koşum 1 | koşum 2 | koşum 3 |
|---|---|---|---|
| Kör doğruluk | %37,5 | %37,5 | %37,5 |
| Türetilmiş doğruluk | %78,9 | **%84,2** | %78,9 |
| Kırmızı duyarlılık (türetilmiş) | %100 | %100 | %100 |
| Kaynak listesi değişen senaryo | — | 0 | 0 |
| Triyaj kodu değişen senaryo | — | 1 | 1 |

**Değişen senaryo her seferinde aynı:** `tur_04`, ve kodu Kırmızı → Sarı →
Kırmızı diye salındı. Geri kalan 28 senaryonun kodu üç koşumda da aynı çıktı,
**kör set üç koşumda da birebir aynı**, ve **retrieval üç koşumda da tam
kararlıydı** — hiçbir senaryonun kaynak listesi değişmedi. Yani oynayan tek şey
LLM, ve pratikte tek bir senaryoda oynuyor.

**Gün 24 için bağlayıcı sonuç:** payda 19 iken bir senaryonun oynaması manşeti
**5,3 puan** değiştiriyor. Tek koşumluk bir önce/sonra tablosu, few-shot'ın
etkisiyle Ollama'nın belirlenimsizliğini **ayırt edemez**; +5 puanlık bir
"iyileşme" hiçbir şey yapmadan da elde edilebilir. Gün 24 ya aynı koşulda birkaç
kez koşup ortalama almalı ya da iddiasını "fark gürültü tabanının üstünde mi"
sorusuna göre kurmalı.

İyi haber: gürültü **her yere dağılmış değil, tek senaryoda toplanmış** ve
klinik olarak en kritik sayı (Kırmızı duyarlılık %100) üç koşumda da sabit. Yani
taban güvenilir, oynayan yalnızca genel doğruluğun ondalık hanesi.

### Bulgu 8 — WER'de rakam normalizasyonu artefaktı (önceden ilan edilmişti)

Ortalama WER 0,143 (koşum 3; üç koşumda 0,150–0,143 arasında). Görev 4'ün incelemesi bunu önceden söylemişti ve sürücü
kendisi işaretliyor: kullanıcı *"Üç gündür"* yazmış, whisper *"3 gündür"* yazıyor.
Tanıma hatası değil, normalizasyon sınırı; sayı düzeltilmedi, sınır raporlandı.

Dürüst sınır: kullanıcı **kendi yazdığı metni okudu**. Okunan konuşma, telaşlı
bir hastanın konuşmasından kolaydır — bu WER iyimser taraflıdır.

### Altın standardın bilinen kusurları (tüm-dal incelemesi)

Ölçülen sayının bir kısmı sistemin değil, altın standardı yazanın seçimini
ölçüyor. Bilinen dört sınıf:

1. **Derlemede karşılığı olmayan tetkik adı — DÜZELTİLDİ.** Üç altın etiket
   hiçbir protokolde geçmeyen ad taşıyordu (`kor_02` "Bölgeye yönelik grafi",
   `kor_05` ve `tur_10` "Yanık alanı değerlendirmesi"). Model bunları yapısal
   olarak tutturamazdı, yani üç senaryo baştan J=0,00 ve C kutusuna mahkûmdu.
   `kor_02` `travma.txt`'nin kendi cümlesine çekildi; `kor_05` ve `tur_10` boş
   listeye indi, çünkü `yanik.txt`'nin üç tetkiki de koşullu (inhalasyon /
   rabdomiyoliz / elektrik) ve basit haşlanmada hiçbirinin koşulu yok.
   **Düzeltme işe yaradı:** `tur_10` bu koşumda J=1,00 ve "doğru" kutusunda.
2. **Akuiteye göre ayrılmamış tetkik listesi — AÇIK.** `anafilaksi.txt` üç
   tetkiki akuite ayrımı olmadan sıralıyor; `kor_06` (Sarı) ikisini, `tur_13`
   (Kırmızı) birini bekliyor. Aynı protokol, aynı liste, farklı alt küme ve
   protokolde bunu gerektiren hiçbir şey yok. Jaccard bu senaryolarda kısmen
   "etiketleyen hangi alt kümeyi seçti"yi ölçüyor.
3. **Tartışmalı okumalar — AÇIK, ikisi de açıkça yazılı.** `kor_01` ve `kor_02`
   (yukarıda, Bulgu 1).
4. **Derlemede olmayan bilgiye dayanan etiket — AÇIK.** `tur_06`'nın Kırmızı'sı
   derlemede bulunmayan bir FAST-ED puanlamasına dayanıyor; `gerekce` bunu
   söylüyor ama sınıf olarak burada da kayda geçiyor.

### Tüm-dal incelemesi

İnceleyici dört geçişte tüm dalı okudu (`olcum.py`; `calistir.py`; üç veri
dosyası 15 protokol metnine karşı; testler + belgeler), odaklı ve tam paketi
koştu ve `git diff main..HEAD -- app/`'in boş olduğunu doğruladı. Verdict:
**merge edilebilir, düzeltmelerle.** 1 Critical, 11 Important, 14 Minor.

**Critical — sızıntı kapısı yanlış kapıyı bekliyordu.**
`test_few_shot_havuzu_olcum_setiyle_kesismiyor` yalnızca `sikayet` ve `id`
karşılaştırıyordu, **çıktıları hiç karşılaştırmıyordu**. Few-shot havuzunun üç
tetkik adının üçü de altın standartta vardı ve bunlardan `"Bölgeye yönelik
grafi"` hiçbir protokolde geçmiyordu — yani etiketleyenin uydurduğu ifade hem
ölçülen etikette hem öğretilecek örnekteydi. Gün 24 havuzu prompt'a enjekte
edince model **ölçüldüğü kelimeleri** öğrenirdi: Jaccard yükselir, C kutusu
çöker ve önce/sonra tablosu **sızıntıyı iyileşme diye raporlardı.** K4 tam bunu
önlemek için vardı ve gate'in görmediği tek kanaldan geliyordu.

Düzeltme iki katmanlı: kapı artık `beklenen_cikti`'nin tetkik ve bölüm adlarını
da altın standartla kesiştiriyor; havuz ise **hiç tetkik adı öğretmiyor**
(derlemenin tetkik dağarcığı küçük ve altın standart onu zaten kapsıyor, yani
havuza konan her ad ölçülen kelimeyi öğretirdi). Havuz yalnızca triyaj kodunu ve
derlemenin kendi yönlendirme dağarcığını öğretiyor. **Gün 24 uyarısı:** yan
etki olarak model tetkik önermeyi azaltabilir; önce/sonra tablosunda tetkik
sayısı da izlenmeli.

**Düzeltilen başlıca Important'lar:**

- **Koşumu çökerten zaman aşımı.** `_429_bekleyerek_gonder`'de `try/except` yoktu;
  tek bir `ReadTimeout` — yerel Ollama soğuk modelde 90 sn'yi bulabiliyor —
  `main`'e kadar çıkıp saatlerce süren bir koşumun raporunu hiç yazdırmazdı.
  K15 "senaryo hata olarak kaydedilir, koşum devam eder" diyordu; artık gerçekten
  öyle.
- **"Belirsiz" iki durumu birleştiriyordu.** `app/api/ai.py` hem eşik kapısına hem
  okunamayan LLM cevabına aynı kodu veriyor. Ölçüm ikisini de retrieval hatası
  sayıyordu (A kutusu ve `esik_alti`). Artık ayırt ediliyor: kaynak dönmüşse
  retrieval çalışmıştır ve hata muhakeme/biçim tarafındadır (`esik_alti_mi`).
- **Tanımsız oranlar JSON'a `0.0` yazılıyordu.** `sonuclar/<tarih>.json` Gün
  24'ün girdisi; `0.0 → 0.8` orada "+80 puan" diye okunabilirdi. Artık `null`.
- **Jaccard'da korumasız 0/0.** `n/d` koruması yalnızca yüzdelerdeydi; Jaccard
  hâlâ "0.00" basıp "model tamamen yanlış tetkik önerdi" diye okunabiliyordu.
  `Ozet` artık paydayı (`jaccard_sayisi`) da taşıyor.
- **Sürücü bir payda kuralını yeniden hesaplıyordu** (`toplam - esik_alti`), yani
  test edilmeyen tarafta (K6 sızıntısı). `Ozet.cevaplanan` eklendi.
- **Ön uçuş Ollama'ya hiç bakmıyordu**, oysa docstring "dört kontrol" diyordu.
  Ollama kapalıyken koşum sonuna kadar yanıp baştan sona `olculemedi` çıkardı.
- **Yükleyici bilinmeyen anahtarı sessizce yutuyordu.** `beklenen_kaynk` yazılsa
  alan `None` okunur, o senaryonun her hatası A'dan B'ye kayar ve "şanslı doğru"
  kontrolü kalıcı kapanırdı — ne istisna, ne kırmızı test. Artık beyaz liste var.
- **13 test Türkçe açıklama taşımıyordu** (10'u Görev 1 bloğunda; Gün 22'den
  devredilen madde). Hepsi yazıldı.

Test 265 → **269**, kapsama %87,42 dal (kapı yeşil).

### Gün 24'e devredilenler

1. **Ölçümün gürültü tabanı 5,3 puan ve kaynağı `tur_04`** (Bulgu 7). Önce/sonra
   tablosu tek koşumla kurulamaz; en azından o senaryo ayrıca izlenmeli.
2. **Tetkik adı normalizasyonu** (`Hemogram (Tam kan sayımı)` ≡ `Tam kan
   sayımı`, `TİT` ≡ `Tam İdrar Tetkiki`). C kutusunun doygunluğunun baskın
   sebebi bu; Jaccard bu yapılmadan iyileşemez.
3. **`department`'ı derlemenin kelime dağarcığına sıkıştır** ve bölüm kapısını
   geri aç (Bulgu 3).
4. **`yanik.txt` aşırı-getirmesi** (Bulgu 5). Ölçmeden düzeltilmemeli: adaylar
   `top_k_initial` 10→20, `yanik.txt`'yi 6→4 chunk'a indirme, chunk boyutunu
   düşürme. Ölçüt `kor_08`'in `ates_sepsis.txt` alması **ve** üç yanık
   senaryosunun gerilememesi.
5. **Eşik iki taraftan da hatalı:** `tur_07` altta kaldı, `tur_20` geçti.
6. **Kör sete Kırmızı arketipli senaryo** (Bulgu 2).
7. **Altın standardın açık üç kusur sınıfı** (yukarıdaki 2, 3, 4 numaralı
   maddeler).
8. **`zehirlenme.txt` derleme boşluğu** — bilinmeyen madde/doz dalı yok.
9. **Alt-triyaj ayrıca raporlansın.** Bugün Sarı→Yeşil ile Yeşil→Sarı aynı
   ağırlıkta "yanlış" sayılıyor; klinik olarak değiller.
10. **Few-shot'ın tetkik bastırma riski** (Critical'in düzeltmesinin yan etkisi).

### Süreç notu

**Ölçüm, kendisinden beklenen şeyi yaptı: en pahalı bulgularının çoğu ölçüm
setinin kendisiyle ilgili.** C kutusunun doygunluğu, Jaccard'ın adlandırma
artefaktı, kör/türetilmiş ayrışması ve gürültü tabanı — hiçbiri "sistem ne kadar
iyi" sorusunun cevabı değil, "bu soruyu sormaya hazır mıydık" sorusunun cevabı.

**Önceden ilan edilen defektler işe yaradı.** Görev 4 ve Görev 6 ölçümden önce
"şu artefakt çıkacak" diye yazmıştı; ikisi de aynen çıktı. Bir bulgunun
**ölçümden önce** yazılmış olması sonradan bulunmasından farklıdır: sonradan
bulunan bulgu, sayıyı kurtarmak için seçilmiş olabilir. `yanik.txt` defektinin
**kapandığı** iddiası da bu yüzden güvenilir — kapanma önceden tanımlanmış bir
beklentinin sonucuydu.

**Bütçe sapması ve karşılığı.** 13 Ağustos'ta subagent bütçesi iki kez doldu;
Görev 6'nın task review'u hiç koşulmadı ve Görev 7'yi kontrolcü yazdı, yani
implementer ile inceleyen aynı kişiydi. Tüm-dal incelemesi bu iki görevi
adlandırılmış hedef olarak aldı ve **kalıntının tam da orada olduğunu** gösterdi:
Critical ve Important'ların çoğu Görev 6'nın verisinden çıktı, Görev 7'den
çıkanların hiçbiri yayımlanmış bir sayıyı bozmuyordu. İnceleyicinin kendi
sonucu: *"bütçe yine kısılırsa koltuğu sürücüye değil veriye harca."*

**Bu bölüm iki kez yazıldı ve ikincisi birincisini düzeltiyor.** İlk yazımda
Bulgu 3 "altın standart kusuru" diye çerçevelenmişti; protokoller ölçülünce
bunun bir **sistem** bulgusu olduğu görüldü (bölüm alanının derlemede dayanağı
yok). İnceleyici ilk çerçeveyi güçlü yan olarak övmüştü — yani bu düzeltme
incelemeden değil, incelemeden sonra yapılan bir ölçümden geldi. **Belge, kendi
kaydettiği sayıyı üreten koddan sonra güncellenmek zorunda:** araç değişince
birinci koşumun sayıları üretilemez hâle geldi ve bu bölüm yeniden koşulan
ölçümle baştan yazıldı.

## Gün 24 · Prompt iyileştirme + ölçüm tekrarı (13–14 Ağustos 2026)

Tasarım: `docs/superpowers/specs/2026-08-13-gun24-prompt-olcum-design.md`.
Plan: `docs/superpowers/plans/2026-08-13-gun24-prompt-olcum.md`. Dal:
`gun24-prompt-olcum`.

### Bu günde ne yapıldı

Üç önkoşul + few-shot enjeksiyonu + üç tam koşumluk önce/sonra tablosu.

1. **Tetkik alias** (`degerlendirme/olcum.py`): `Hemogram (Tam kan sayımı)` ≡
   `Tam kan sayımı`, `TİT` ≡ `Tam İdrar Tetkiki`, `EKG` ≡ `Elektrokardiyografi`.
2. **`department` akuite dağarcığı** (`app/api/ai.py`): kapalı kelime dağarcığı +
   `_normalize_department`; altın `beklenen_bolum` akuite alanına çekildi;
   `kok_neden` C kapısında `bolum_dogru_mu` yeniden açıldı.
3. **`yanik` aşırı-getirme:** `kalibre_esik` kaynak raporlar; `top_k_initial=20`
   ayara alındı; `yanik.txt` 6→3 chunk; `ates_sepsis.txt`'e hasta-dili eklendi
   (kor_08 gömme sırası 26 → top-20 içi). Ölçüm: `kor_08` kazanan kaynak
   **`ates_sepsis.txt`** (skor 0,85); üç yanık senaryosu `yanik.txt` kaldı.
4. **Few-shot** havuzu prompt'a enjekte edildi (tetkik adı öğretilmiyor).
5. **Ölçüm:** baseline `2026-08-13.json` + üç koşum
   (`2026-08-13-kosum1`, `2026-08-14-kosum2/3`); rapor
   `degerlendirme/sonuclar/gun24-once-sonra.md`.

Test: **290** passed (`-m "not yavas"`), dal kapsaması **%87,29** (kapı 87).

### Önce / sonra (üç koşum ortalaması)

| Ölçü | Önce (kör) | Sonra ort. (kör) | Önce (tür.) | Sonra ort. (tür.) |
|---|---|---|---|---|
| Genel doğruluk | %37,5 | %37,5 | %78,9 | **%80,7** |
| Kırmızı duyarlılık | n/d | n/d | %100 | **%90,0** |
| Eşik altı | %0 | %0 | %5,3 | %0 |
| Jaccard (tür.) | 0,26 | — | 0,26 | **0,28** |

Tek koşumlar (tür. doğruluk): %73,7 / %84,2 / %84,2. `tur_04` üç koşumda da
**Sarı** (önce Kırmızı↔Sarı salınıyordu).

**Dürüst okuma:** türetilmiş doğruluk farkı **+1,8 puan** — gürültü tabanının
(5,3) **içinde**. Manşet “few-shot doğruluğu yükseltti” diye yazılamaz.
Jaccard ve C kutusu (13 → ort. 12,3) adlandırma/bölüm düzeltmelerinden
beklenen yönde kıpırdadı. Kırmızı duyarlılığı ortalama %90’a indi (10’dan 9);
klinik manşette gerileme — raporlanmalı. Tetkik sayısı 2,47 → 2,32 (few-shot
bastırma zayıf).

**Retrieval kazanımı (sayı dışı ama ölçülmüş):** `kor_08` artık
`ates_sepsis.txt` alıyor; Gün 23’teki tek kör A kutusu kaynağı kapandı.

### Bilgi tabanı parmak izi

15 dosya / **49** chunk (`yanik` 3, `ates_sepsis` 4). `calistir.BEKLENEN_CHUNK=49`.

### Açık kalanlar

- `kor_10` (kullanıcı ses + metin)
- Kırmızı duyarlılık düşüşünün senaryo kırılımı (hangi vaka kaçtı) raporda
  tek tek izlenmeli
- Altın standart etik borçları (Gün 23 listesi)

## Borç kapatma turu — DEVIR §9 gerçek defektler (14 Ağustos 2026)

Devir brief §9’daki **kod defektleri** `gun24-prompt-olcum` worktree’sinde
kapatıldı (ölçüm/etiket borçları ve bilinçli tasarım sınırları ayrı):

| Madde | Kapanış |
|---|---|
| `istek_at` log yok | `logging.exception` |
| Giriş 401/422/500/429 ayrımı + `.strip()` | frontend + `/auth/login` strip |
| `safe_filename.lower()` çakışması | yalnızca boşluk→`_`; harf durumu korunur |
| Boyut `read()` sonrası | `file.size` ön kontrol + doğrulayıcı |
| Zamanlama oracle | yok kullanıcıda da `SAHTE_PAROLA_HASH` bcrypt |
| `500` CORS | handler’a izinli `Origin` başlığı |
| DOCX = herhangi ZIP | `[Content_Types].xml` zorunlu |
| `PGHOSTADDR`/`PGSERVICE` | kilit reddeder; conftest temizler |
| `seed_users` kısmi idempotent | rol **ve** parola senkron |
| `429` `Retry-After` | pencere sn sabit başlık |
| K5 aşama mesajları / `filename=None` / geçersiz UTF-8 | genel ret + testler |

**Hâlâ “bilinen sınır” (rapor maddesi, bu turda kodlanmadı):** altın standart
etik tartışmaları, `zehirlenme` bilinmeyen madde dalı, zip-bomb/chunk üst sınırı
kararı, Streamlit otomatik test, uçtan uca gerçek PDF fixture, paket geneli
`raise_server_exceptions=False`, klinik giriş hacmi ölçümü.
