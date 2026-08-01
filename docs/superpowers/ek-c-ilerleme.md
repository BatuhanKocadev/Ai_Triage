# Ek C — İlerleme Çizelgesi

## Gün 11–16 · Test ağı günü (31 Temmuz – 1 Ağustos 2026)

### Bu gün ne yapıldı

Gün 1–16 arasında yazılan üretim kodunun **hiç testi yoktu**. Bu gün geriye
dönük bir test ağı örüldü: `pytest` çatısı kuruldu, gerçek Postgres üzerinde
işlem-bazlı izolasyon veren fixture'lar yazıldı, dış servisler (Ollama,
faster-whisper, ChromaDB, cross-encoder) sahtelerle değiştirildi ve dokuz
görevde toplam 68 test eklendi.

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
| Toplam test sayısı | **68** (`pytest --collect-only` → 68 tests collected) |
| Geçen / kalan | **68 passed / 0 failed** (`pytest -m "not yavas"`, 19.41 sn) |
| Kapsama (`app/`) | **%72** (536 ifadenin 149'u kapsanmıyor) |
| Test dosyası sayısı | 8 (`tests/api/` 4, `tests/birim/` 4) |
| Uyarı | 2 (ikisi de üçüncü parti kütüphane, aşağıda açıklandı) |
| Hiç test görmeyen modüller | **Yok** — `app/` altındaki 21 modülün hepsi kapsama raporunda görünüyor. Ancak dört modül yalnızca *import* seviyesinde kapsanıyor (aşağıya bakınız). |

`-m "not yavas"` bugün **hiçbir testi elemiyor**: `yavas` işaretli test yok
(`grep -rn "mark.yavas" tests/` boş döner). 68 sayısı paketin tamamıdır.
İşaret ileride Ollama/Whisper modeli gerektiren testler eklenirse diye
`pytest.ini` içinde hazır bekletiliyor.

#### Test dosyası başına dağılım

| Dosya | Test | Neyi donduruyor |
|---|---|---|
| `tests/birim/test_triyaj_normalizasyon.py` | 22 | `_sadelestir`, `_normalize_triage_code`, `_normalize_tetkikler` |
| `tests/api/test_ai_analiz_api.py` | 11 | `/ai/analiz` sözleşmesi: 401/422/200, eşik altı yolu, DB yazımı |
| `tests/api/test_speech_api.py` | 11 | `/speech/transkript` sözleşmesi (Whisper modeli yüklenmeden) |
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
var. Bu girdi yukarıdaki uyarıyı **hiçbir zaman yakalayamazdı**:
`StarletteDeprecationWarning`, `DeprecationWarning`'den değil **`UserWarning`**'den
türüyor (`starlette/exceptions.py:36`). Filtreyi genişletmek çözüm değildir;
yalnızca `error::UserWarning` ya da çıplak `error` bunu hataya çevirir — ikisi de
üçüncü parti gürültüsünü de hataya çevireceği için bugün tercih edilmedi.
Bu, "uyarı filtrem var, demek ki korunuyorum" varsayımının yanlış olabileceğinin
somut örneğidir.

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
demek: o satır silinse ya da bozulsa paket yine 68/68 yeşil verir.

| Dosya:satır | Korumasız davranış | Neden önemli |
|---|---|---|
| `app/api/ai.py:141-143` | `except Exception` → `relevant_documents = []`. RAG çökerse hasta sessizce "Belirsiz / Triyaj Bankosu"na düşüyor — meşru eşik-altı sonucuyla **aynı** kod yolundan. | Doktor "bu şikayete uygun protokol yok" ile "getirme sistemi bozuk"u ayırt edemiyor. Davranışsal olarak dosyadaki en önemli kapsanmamış dal. Kapsama raporunda da tek eksik satır grubu (`ai.py` %97). |
| `app/api/auth.py:26-38` | **`/auth/login` ucu hiçbir testten geçmiyor.** Yanlış parolada 401 dönen dal, `verify_password`'ün gerçek kullanıcıya karşı çalışması ve jetonun `ACCESS_TOKEN_EXPIRE_MINUTES` ile dağıtılması korumasız. | Testler jetonu `jeton_uret` fixture'ıyla doğrudan üretiyor, giriş ucundan geçmiyor. Yani "yanlış parolayla giriş yapılamaz" iddiası bugün **hiçbir test tarafından savunulmuyor** — uygulamanın en temel güvenlik iddiası. Bu, bugünkü ölçümde ortaya çıkan yeni bulgudur. |
| `app/services/rag_service.py:82` | `if score >= threshold` filtresi tamamen silinse hiçbir test yakalamaz. Sınır operatörü pinli, maddenin varlığı değil. | Yakalanmayan senaryo üretimde tipik: en iyi doküman eşiği geçerken `[:top_k_final]` içindeki alttaki geçmiyor (`config.py:31-34`'e göre ilgili skorlar 0.502-0.664, eşik 0.52). Yani egzotik değil, olağan durum. |
| `app/services/auth_service.py:83` | `require_admin_role`'ün **izin veren** dalı (`return current_user`) hiçbir testten geçmiyor. Bugün yalnızca reddeden dal (403) test edildi. | "Admin doküman yükleyebilir" iddiası korumasız. Test etmek gerçek ChromaDB gerektirdiği için bugün yapılamadı; koleksiyonu sahtelemek ya da CI'da Chroma ayağa kaldırmak gerekir. |
| `app/api/document.py:70-143` | `/document/upload` gövdesinin tamamı (PDF/DOCX/TXT ayrıştırma, chunk'lama, deterministik chunk ID üretimi, ChromaDB upsert) test edilmiyor — modül %17. | Aynı dosyanın tekrar yüklenince çoğaltmak yerine üzerine yazması (`<dosyaadi>_chunk_<n>`) belgelenmiş bir davranış ama pinli değil. ChromaDB bağımlılığı yüzünden ertelendi. |
| `app/api/document.py:139-143` | Geniş `except Exception` → 500 "Upload error". Altyapı arızası (ChromaDB kapalı) ile bozuk dosya aynı jenerik 500'e düşüyor; çağıran ikisini ayırt edemiyor. | Görev 9'un 1. mutasyonu sırasında gözlemlendi: yetki kapısı devre dışı bırakılınca istek gövdeye ilerledi ve ChromaDB'ye ulaşamayıp bu dala düştü (`Upload error: Could not connect to a Chroma server`). `ai.py:141-143`'teki desenin aynısı: gerçek arıza, olağan bir sonuç gibi görünüyor. Kayıt dışı kalmasın diye buraya yazıldı. |
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
| 3 | Testin ağır uca bağlanması | `test_auth_api.py`'deki 4 API testi auth kapısını `/ai/analiz` üzerinden yokluyor — uygulamanın en ağır ucu. Bugün güvenli (hepsi auth katmanında kısa devre yapıyor) ama tek satırlık bir üretim değişikliği onları RAG/LLM hattına sürükleyebilir. |
| 4 | Sahte servis kapsamı | `esik_alti` yaması `get_structured_completion`'ı yamalamıyor; dört test Ollama'dan yalnızca eşik kapısı (`ai.py:145`) da sağlam kaldığı sürece uzak duruyor. Doğrulama **ve** kapı birlikte bozulursa testler gerçek LLM'e gider. |
| 5 | Yamalanmayan sahte | `test_speech_api.py`'deki 2. ve 3. test (`.txt` reddi, boyut sınırı) `transcribe`'ı yamalamıyor; yorum "STT hiç çağrılmadan reddedilmeli" diyor ama bunu hiçbir şey ayırt etmiyor. Yamalanırsa hem iddia pinlenir hem `WHISPER_MODEL_SIZE` geçici çözümüne gerek kalmaz. |
| 6 | Görünenden dar kapsam | `test_string_olmayan_triyaj_kodu_belirsiz_doner`'de 4 tip vakasının 3'ü mutasyon altında aynı şekilde patlıyor (`AttributeError: translate`) — dört ayrı vaka gibi görünüp tek bir mekanizmayı ölçüyor. |
| 7 | Eksik assert | `test_dokumanlar_skora_gore_siralanir` yalnızca `sonuc[0]`'ı assert ediyor. `len(sonuc) == 2` + `sonuc[1]` eklenirse tam sıralama bedavaya pinlenir. |
| 8 | Eksik assert | Mutlu yol testi `AnalysisResponse.status` alanını hiç assert etmiyor; eşik altı testi `sources == []` ve açıklayıcı `ai_note`'u pinlemiyor. |
| 9 | Kısmi mutasyon kanıtı | Görev 4'ün 4. mutasyonu `test_jeton_kullanici_adi_ve_rol_tasir`'ın yalnızca `sub` yarısını yanlışlıyor; `role` assert'i için bağımsız kırmızı kanıtı yok. |
| 10 | Tekrar eden test | `test_jetonsuz_istek_401_doner` hem `tests/api/test_auth_api.py:9` hem `tests/api/test_ai_analiz_api.py` içinde birebir aynı. İkisi de kendi görev brief'lerinden geldi; doğru evi `test_auth_api.py`. |
| 11 | Örtük assert | `test_saglik.py`'deki iki izolasyon testinde açık assert yok; pass/fail `db_oturum.commit()` patlar mı diye örtülüyor. Tripwire için meşru ama paketin geri kalanındaki açık-assert üslubundan sapıyor. |
| 12 | Ölü import | `tests/birim/test_rag_esik_kapisi.py`'de `import pytest` kullanılmıyor (yalnızca `monkeypatch` fixture'ı var, o import gerektirmez). Plandan birebir korunmuş; silinmeli. |
| 13 | Eksik yorum | `tests/conftest.py`'deki `join_transaction_mode` yorumu, connection pool'un `reset_on_return="rollback"` varsayılanının `islem.rollback()`'i bağımsız olarak yedeklediğini söylemiyor. İleride bakan biri `rollback`'i silince testlerin kırmızı olmamasına şaşırabilir. |
| 14 | Fixture teardown'u fazla geniş | `istemci` fixture'ının teardown'u `app.dependency_overrides.clear()` kullanıyor, yalnızca `get_db` anahtarını silmiyor. Bugün tek override o, ama ileride başka override eklenirse sessizce silinir. |
| 15 | `asyncio_mode` ayarsız | `pytest-asyncio` kurulu ama `pytest.ini`'de `asyncio_mode` yok. Bugün etkisiz: pakette hiç `async def test_` yok (`/speech/transkript` async ama `TestClient` onu kendi sürüyor). İlk async test eklendiğinde ayarlanmalı. |

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
zayıflıkları" tablosundaki 15 maddenin tamamı. Hiçbiri paketin doğruluğunu
bozmuyor, hepsi güç/netlik kaybı.

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

```
$ .venv\Scripts\python.exe -m pytest -m "not yavas" --override-ini="addopts=" -v --no-header

============================= test session starts =============================
collected 68 items

tests/api/test_ai_analiz_api.py::test_jetonsuz_istek_401_doner PASSED    [  1%]
tests/api/test_ai_analiz_api.py::test_kisa_sikayet_422_doner PASSED      [  2%]
tests/api/test_ai_analiz_api.py::test_gecersiz_yas_422_doner PASSED      [  4%]
tests/api/test_ai_analiz_api.py::test_gecersiz_giris_tipi_422_doner PASSED [  5%]
tests/api/test_ai_analiz_api.py::test_basarili_analiz_200_ve_sema_alanlari PASSED [  7%]
tests/api/test_ai_analiz_api.py::test_klinik_uyari_nota_eklenir PASSED   [  8%]
tests/api/test_ai_analiz_api.py::test_esik_altinda_llm_cagrilmaz_ve_belirsiz_doner PASSED [ 10%]
tests/api/test_ai_analiz_api.py::test_llm_hatasi_502_doner PASSED        [ 11%]
tests/api/test_ai_analiz_api.py::test_ziyaret_ve_oneri_veritabanina_yazilir PASSED [ 13%]
tests/api/test_ai_analiz_api.py::test_ses_kaynakli_basvuru_giris_tipi_ses_kaydedilir PASSED [ 14%]
tests/api/test_ai_analiz_api.py::test_varsayilan_giris_tipi_metindir PASSED [ 16%]
tests/api/test_auth_api.py::test_jetonsuz_istek_401_doner PASSED         [ 17%]
tests/api/test_auth_api.py::test_bozuk_jeton_401_doner PASSED            [ 19%]
tests/api/test_auth_api.py::test_tanimsiz_rol_403_doner PASSED           [ 20%]
tests/api/test_auth_api.py::test_veritabaninda_olmayan_kullanicinin_jetonu_401_doner PASSED [ 22%]
tests/api/test_auth_api.py::test_admin_olmayan_dokuman_yukleyemez PASSED [ 23%]
tests/api/test_auth_api.py::test_dokuman_yukleme_jetonsuz_401_doner PASSED [ 25%]
tests/api/test_saglik.py::test_saglik_ucu_200_doner PASSED               [ 26%]
tests/api/test_saglik.py::test_izolasyon_denegi_ilk_testte_commit_edilir PASSED [ 27%]
tests/api/test_saglik.py::test_izolasyon_denegi_ikinci_testte_hala_yaratilabilir PASSED [ 29%]
tests/api/test_speech_api.py::test_jetonsuz_istek_401_doner PASSED       [ 30%]
tests/api/test_speech_api.py::test_desteklenmeyen_format_400_doner PASSED [ 32%]
tests/api/test_speech_api.py::test_cok_buyuk_dosya_400_doner PASSED      [ 33%]
tests/api/test_speech_api.py::test_basarili_transkript_metin_sure_ve_model_doner PASSED [ 35%]
tests/api/test_speech_api.py::test_stt_hatasi_422_doner PASSED           [ 36%]
tests/api/test_speech_api.py::test_bos_transkript_422_doner PASSED       [ 38%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.wav] PASSED [ 39%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.mp3] PASSED [ 41%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.m4a] PASSED [ 42%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.ogg] PASSED [ 44%]
tests/api/test_speech_api.py::test_desteklenen_formatlarin_hepsi_kabul_edilir[.webm] PASSED [ 45%]
tests/birim/test_auth_service.py::test_parola_hashlenir_ve_dogrulanir PASSED [ 47%]
tests/birim/test_auth_service.py::test_gecersiz_parola_reddedilir PASSED [ 48%]
tests/birim/test_auth_service.py::test_ayni_parola_farkli_hash_uretir PASSED [ 50%]
tests/birim/test_auth_service.py::test_jeton_kullanici_adi_ve_rol_tasir PASSED [ 51%]
tests/birim/test_auth_service.py::test_suresi_dolmus_jeton_reddedilir PASSED [ 52%]
tests/birim/test_config.py::test_ayarlar_env_dosyasindan_okunur PASSED   [ 54%]
tests/birim/test_config.py::test_veritabani_url_test_veritabanini_gosterir PASSED [ 55%]
tests/birim/test_rag_esik_kapisi.py::test_koleksiyon_yoksa_bos_liste_doner PASSED [ 57%]
tests/birim/test_rag_esik_kapisi.py::test_esik_altinda_bos_liste_doner PASSED [ 58%]
tests/birim/test_rag_esik_kapisi.py::test_esik_ustunde_dokuman_doner PASSED [ 60%]
tests/birim/test_rag_esik_kapisi.py::test_tam_esik_degeri_dahil_edilir PASSED [ 61%]
tests/birim/test_rag_esik_kapisi.py::test_dokuman_kaynagi_ciktiya_eklenir PASSED [ 63%]
tests/birim/test_rag_esik_kapisi.py::test_dokumanlar_skora_gore_siralanir PASSED [ 64%]
tests/birim/test_rag_esik_kapisi.py::test_metadata_filtresi_koleksiyona_gecirilir PASSED [ 66%]
tests/birim/test_rag_esik_kapisi.py::test_bos_koleksiyon_sonucu_bos_liste_doner PASSED [ 67%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[Kırmızı-kirmizi] PASSED [ 69%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[KIRMIZI-kirmizi] PASSED [ 70%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[Yeşil-yesil] PASSED [ 72%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[  Sarı  -sari] PASSED [ 73%]
tests/birim/test_triyaj_normalizasyon.py::test_sadelestir_turkce_karakterleri_ascii_yapar[ŞİĞÜÖÇ-siguoc] PASSED [ 75%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[Kırmızı-Kırmızı] PASSED [ 76%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[kirmizi-Kırmızı] PASSED [ 77%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[KIRMIZI-Kırmızı] PASSED [ 79%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[  sari  -Sarı] PASSED [ 80%]
tests/birim/test_triyaj_normalizasyon.py::test_triyaj_kodu_gecerli_kumeye_indirgenir[yesil-Yeşil] PASSED [ 82%]
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
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.

..\..\..\.venv\Lib\site-packages\chromadb\telemetry\opentelemetry\__init__.py:128
  DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16

======================= 68 passed, 2 warnings in 19.41s =======================
```

Ortam: Windows 11, Python 3.14.6, pytest 8.4.2, gerçek PostgreSQL
(`ai_triage_test` veritabanı). Ollama, faster-whisper, ChromaDB ve cross-encoder
**hiçbir testte çalıştırılmadı** — `tests/yardimcilar/` altındaki sahtelerle
değiştirildiler.
