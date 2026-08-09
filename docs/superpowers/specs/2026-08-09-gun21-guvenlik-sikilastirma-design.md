# Gün 21 — Güvenlik Sıkılaştırma Tasarım Dokümanı

**Tarih:** 9 Ağustos 2026
**Kapsam:** İstek hız sınırı, dosya yükleme doğrulaması, hata mesajlarında bilgi
sızıntısının kapatılması, CORS ve gizli anahtar yönetimi.

## Hedef

Tıbbi veri işleyen bir sistemin savunulabilir olması için gereken minimum güvenlik
katmanını kurmak. Bugün bu katmanın **hiçbiri yok**: CORS middleware'i eklenmemiş,
beklenmeyen hatada FastAPI'nin varsayılan yanıtı dönüyor, hız sınırı bulunmuyor ve
dosya yükleme yalnızca uzantıya bakıyor.

## Kapsam

**İçinde:** hız sınırı, dosya içerik doğrulaması, global hata gövdesi, CORS,
`.env.example` uyarıları, güvenlik ayarlarının tek grupta toplanması, sekiz
güvenlik testi.

**Dışında:** kimlik doğrulama mimarisinin değiştirilmesi (JWT akışı olduğu gibi
kalıyor), HTTPS/TLS (dağıtım konusu), veritabanı erişim kontrolü, denetim günlüğü.

## Bağlam — bugünkü durum

| | Durum |
|---|---|
| CORS | `app/main.py`'de middleware hiç eklenmemiş |
| Exception handler | Yok; beklenmeyen istisnada FastAPI varsayılanı |
| Hız sınırı | Yok |
| Dosya doğrulama | Yalnızca uzantı (`app/api/document.py:73`) |
| JWT ayarları | `config.py`'de mevcut (`jwt_secret_key`, `access_token_expire_minutes`) |
| Güvenlik kütüphaneleri | `slowapi`, `python-magic`, `filetype` — hiçbiri kurulu değil |

## Tasarım kararları

**K1 — Hız sınırı kendi sayacımızla yazılır, kütüphane eklenmez.**
`app/utils/hiz_sinirlayici.py` içinde kayan pencere sayacı. Gerekçe: yeni bağımlılık
`requirements.txt` ve Docker imajına yayılır; buna karşılık sınırlayıcı ~40 satır ve
davranışı tam kontrolümüzde. Asıl belirleyici test izolasyonu (K3): kendi sınıfımızda
`sifirla()` bir metot, `slowapi`'de kütüphanenin iç depolamasına elle müdahale.

Saat enjekte edilebilir (`saat=time.monotonic` varsayılan) — testler gerçek zamana
bağlı kalmasın, pencere kayması deterministik sınanabilsin.

**K2 — Sınırlayıcı FastAPI bağımlılığı olarak uygulanır, middleware olarak değil.**
Yol haritası uç bazında farklı sınır istiyor: `/auth/login` sıkı (parola deneme
saldırısı), `/ai/analiz` orta. Middleware tüm uçlara aynı kuralı uygular; bağımlılık
uç bazında ayar verir ve hangi ucun korunduğu kodda görünür olur.

Bu günün kapsamında **yalnızca iki uç** sınırlanır:

| Uç | Sınır | Gerekçe |
|---|---|---|
| `POST /auth/login` | `rate_limit_giris` (sıkı) | Kimlik doğrulaması olmadan çağrılabilen tek yazma ucu; parola deneme saldırısının hedefi |
| `POST /ai/analiz` | `rate_limit_genel` (orta) | Yerel LLM'i çalıştırıyor, en pahalı uç; kötüye kullanım servisi tüketir |

Diğer uçlar bilerek dışarıda: hepsi kimlik doğrulaması ve rol kapısının arkasında,
yani anonim bir saldırgan onlara zaten ulaşamıyor. Her uca sınır koymak, koruduğu
şeyi netleştirmeden yüzey genişletmek olurdu (YAGNI). `/document/upload` pahalı ama
`admin` rolüne kapalı; ihtiyaç görülürse aynı bağımlılık tek satırla eklenir.

**K3 — Test izolasyonu tasarımın parçasıdır, sonradan eklenecek bir detay değil.**
`TestClient` her istekte aynı IP'yi kullanır. Sınırlayıcı sıfırlanmazsa bir testin
tükettiği kota diğerini `429`a düşürür ve hata "güvenlik çalışıyor" değil "test
altyapısı bozuldu" biçiminde görünür — teşhisi zor, sinir bozucu bir sınıf.
`tests/conftest.py`'ye **autouse** fixture eklenir; her testten önce sınırlayıcıyı
sıfırlar. Mevcut 102 testin hiçbiri değişmeden yeşil kalmalıdır.

**K4 — Dosya içeriği elle imza kontrolüyle doğrulanır.**
Yalnızca üç biçim destekleniyor: PDF `%PDF-` ile, DOCX bir ZIP olduğu için
`PK\x03\x04` ile başlar, TXT ise UTF-8 çözülebiliyorsa geçerlidir. ~15 satır, sıfır
bağımlılık, Windows ve Docker'da aynı davranır. `python-magic` Windows'ta `libmagic`
ikilisini ayrıca kurmayı gerektirdiği için elenmiştir.

**K5 — Boyut aşımı `413`, biçim/imza reddi `400`; mesajlar geneldir.**
Reddetme mesajı hangi kontrolün tetiklendiğini dışarı vermez ("Desteklenmeyen dosya"
gibi); ayrıntı log'a yazılır. Saldırgana hangi kontrolü aştığını söylemek, kontrolü
aşmasını kolaylaştırır.

**K6 — Beklenmeyen istisnada istemciye genel mesaj + korelasyon kimliği döner.**
`app/main.py`'de global exception handler: tam yığın izi ve istek bağlamı log'a,
istemciye yalnızca `{"detail": "Sunucu hatası", "izleme_kodu": "<kısa-uuid>"}`.
Kimlik olmadan "hata aldım" ile log'daki satırı eşleştirmenin yolu yok; kimlik,
sızıntı yaratmadan teşhisi mümkün kılar.

**K7 — CORS ayardan okunur; bugünkü mimaride tarayıcı yolunu korumaz.**
`allow_origins` artık `"*"` değil, `settings.cors_origins`'den geliyor. Dürüst not:
Streamlit backend'i **sunucu tarafından** `requests` ile çağırıyor, yani tarayıcı
araya girmiyor ve CORS bugün fiilen hiçbir saldırıyı engellemiyor. Yine de ekleniyor
çünkü API tarayıcıdan da çağrılabilir ve varsayılanı açık bırakmak savunulamaz.
Raporda "eklendi" denirken bu sınır belirtilmeli.

**K8 — Güvenlik ayarları `config.py`'de tek grupta toplanır.**
`rate_limit_genel`, `rate_limit_giris`, `rate_limit_pencere_sn`, `max_upload_mb`,
`izinli_uzantilar`, `cors_origins`. Yol haritasının REFACTOR maddesi; dağınık
güvenlik ayarı, hangi kuralın yürürlükte olduğunu okunamaz hâle getirir.

**K9 — Yol haritasındaki `/auth/token`, bu depoda `/auth/login`'dir.**
Testler gerçek yola yazılır. Test adları yol haritasından birebir korunur.

**K10 — Gün 19'un uçtan uca döngüsü tekrarlanır; bu adım atlanamaz.**
Yol haritası bunu açıkça "atlanmaz" diye işaretliyor. Güvenlik eklemeleri
hasta→analiz→doktor→onay akışını bozmamalı; hız sınırı ya da dosya doğrulaması
yanlış ayarlanırsa akış sessizce kırılır.

## Uç sözleşmeleri (değişen davranışlar)

| Durum | Önce | Sonra |
|---|---|---|
| Dakikada N'i aşan istek | işlenir | `429` |
| `/auth/login`'e art arda deneme | işlenir | `429` (daha sıkı sınır) |
| `.exe` yükleme | `400` "Unsupported file format" | `400`, genel mesaj |
| Boyut sınırını aşan dosya | işlenir | `413` |
| `.pdf` uzantılı ama içeriği PDF olmayan dosya | işlenir, çöp metin çıkarılır | `400` |
| Beklenmeyen istisna | FastAPI varsayılanı | `500` + genel mesaj + izleme kodu |
| İzinsiz origin'den tarayıcı isteği | CORS başlığı yok (varsayılan) | açıkça reddedilir |

Mevcut başarılı akışların sözleşmesi değişmez.

## Test mimarisi

`tests/api/test_guvenlik.py` (yeni) — sekiz test, her biri bir saldırıyı taklit eder:

| Test | Neyi donduruyor |
|---|---|
| `test_ardarda_istek_hiz_sinirina_takilir` | N istekten sonra `429` |
| `test_giris_denemesi_hiz_sinirli` | `/auth/login` için ayrı ve daha sıkı sınır |
| `test_desteklenmeyen_uzantili_dosya_reddedilir` | `.exe` reddedilir |
| `test_cok_buyuk_dosya_reddedilir` | Boyut sınırı, `413` |
| `test_pdf_gibi_gorunen_bozuk_dosya_reddedilir` | Uzantı değil içerik kontrolü |
| `test_hata_mesajinda_yigin_izi_yok` | `500` yanıtında traceback/dosya yolu yok |
| `test_gecersiz_jwt_ile_401_ve_detay_sizmaz` | Kullanıcı/parola ayrımı dışarı verilmez |
| `test_cors_sadece_izinli_kaynaga_acik` | İzinsiz origin'e açık değil |

Ayrıca `tests/birim/test_hiz_sinirlayici.py` (yeni) — sınırlayıcının kendisi enjekte
edilmiş saatle sınanır: pencere dolunca reddeder, pencere kayınca yeniden izin verir.
Uç testleri sınırlayıcının *kullanıldığını*, birim testleri *doğru çalıştığını*
gösterir; ikisi birbirinin yerine geçmez — bu ayrımın atlanması Gün 17+18'de
mutasyonla ölçülen kusurdu.

`tests/conftest.py`'ye autouse sıfırlama fixture'ı (K3).

## Bitti sayılır

- [ ] Sekiz güvenlik testi yeşil, her biri önce kırmızı görüldü
- [ ] Sınırlayıcının birim testleri yeşil (enjekte edilmiş saatle)
- [ ] Mevcut 102 test hâlâ yeşil, hiçbiri değiştirilmeden
- [ ] Hız sınırı elle görüldü: aynı uca art arda istek, `429` alındı
- [ ] Gün 19'un uçtan uca döngüsü tekrarlandı ve bozulmadı (K10)
- [ ] `.env.example` JWT uyarısını ve yeni ayarları içeriyor
- [ ] Güvenlik ayarları `config.py`'de tek grupta
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
