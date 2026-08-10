# Gün 22 (birinci yarı) — Borç Kapatma Tasarım Dokümanı

**Tarih:** 10 Ağustos 2026
**Durum:** onaylandı, plan yazılacak
**Öncesi:** Gün 21 güvenlik sıkılaştırması `main`'e birleşti (`88cc8f9`, 137 test, kapsama %85)

## Hedef

Altı gün boyunca Ek C'de biriken teknik borcun, bugün gerçekten değeri olan
kısmını kapatmak. Amaç listeyi tüketmek değil — liste ~60 madde, gün bir tane.
Amaç, **Gün 22'nin ikinci yarısını (CI) mümkün kılan** ve **Gün 23'ün ölçümünü
kurtaran** maddeleri seçip kapatmak.

## Kapsam

**İçeride, beş madde:**

1. `tests/conftest.py` test veritabanı kilidi — host doğrulaması ve düzgün URL ayrıştırma
2. `tests/api/test_speech_api.py` — `transcribe` yamalamayan üç test
3. `ai_recommendations.visit_id` — unique kısıtı
4. `doctor_reviews.doctor_id` — index
5. `ornek_dokumanlar/protokoller/yanik.txt` — hasta dili + kalibrasyon sorgusunun yeniden yazılması

**Dışarıda, bilinçli olarak:** karaktersiz yazım sorunu (K2); `response_model`
eksikliği; `429`'da `Retry-After`; `sahte_chroma.py`'nin `include` parametresini
yok sayması; `get_current_user` sertleştirmesi; `_sadelestir` parametrize vakası;
K9 dosya adı normalizasyon çakışması; silme ucunun atomik olmaması; kalıcılık
(durability) testi; ve Ek C'nin altı devir bölümündeki kalan maddeler. Hiçbiri
silinmiyor, Ek C'de duruyorlar.

**Ayrıca dışarıda:** asıl Gün 22 — test derinleştirme, kapsama kapısı, CI (K11).

## Bağlam — bugünkü durum

Ek C'de **altı** ayrı "Gün 22'ye devredilenler" bölümü var (satır 326, 640, 764,
878, 1052, 1321). Toplam ~60 madde, ve aralarında dört tekrar çifti bulunuyor
(K9 dosya adı çakışması, silme atomikliği, `sahte_chroma` `include`,
`response_model` — her biri hem 878 hem 1052 bölümünde).

Doğrulama turunda **bir madde kapanmış çıktı:** 326 bölümündeki "`/auth/login`
uçtan uca testi — bugün tamamen korumasız". Gün 21 bunu kapattı;
`test_ip_katmani_basarili_girisleri_de_sayar` doğru parolayla 200,
`test_giris_denemesi_hiz_sinirli` yanlış parolayla 401 alıyor ve `auth.py`
%100 kapsamda.

Retrieval tarafında Gün 20 kapanışı **16/18 ilgili sorgu** ölçmüştü. Açık kalan
ikisi: `yanik` (0.0005) ve `inme`'nin karaktersiz yazımı (0.0031). Eşik 0.005.

## Tasarım kararları

**K1 — Kapsam beş maddeyle sınırlı; seçim ölçütü "neyi mümkün kılıyor".**
Maddeler tek tek önemli oldukları için değil, iki şeyi kilitledikleri için
seçildi. Madde 1 ve 2 Gün 22'nin ikinci yarısının (CI) ön koşulu: yamalanmamış
speech testleri CI'da gerçek faster-whisper `medium` modelini indirmeye kalkar
(yol haritasının önceden kaydettiği "CI'da testler 10 dakikayı geçiyor"
tuzağının ta kendisi), ve kilit host bakmadığı için CI'ın ortam değişkeninden
gelen veritabanı adresine güvenilemez. Madde 5 Gün 23'ün ön koşulu: yanık
senaryolarında sistem bugün "Belirsiz" diyor, yani doğruluk ölçümü baştan
bozuk çıkardı. Madde 3 ne birine ne ötekine hizmet ediyor; sessiz veri kaybı
olduğu için içeride.

**K2 — Retrieval hedefi 18/19, tam kapsama değil.**
(Sayının paydası K5 ikinci yanık sorgusunu eklediği için 18'den 19'a çıkar;
Gün 20'nin ölçümü 16/18'di. Açık kalan tek sorgu `inme`'nin karaktersiz yazımı.)
Karaktersiz yazım bilinçli olarak açık bırakılıyor. Sebep türsel: `yanik` bir
**içerik** boşluğu (protokol klinik dilde yazılmış, hasta dili yok), karaktersiz
yazım ise bir **girdi normalizasyonu** sorunu ve çözümü ya üretim sorgu yolunu
değiştirmeyi ya da 15 protokole ASCII eş anlamlı eklemeyi gerektiriyor. İkisi
ayrı karar; birini ötekinin arkasına saklamak ikisini de kötü çözer.
`yanik` klinik bir açık, karaktersiz yazım konfor sorunu — sıralama buradan.

**K3 — `rerank_threshold = 0.005` sabittir; düzeltme onu geçmek zorunda.**
Eşik Gün 20'de yazılı gerekçeyle seçildi: alakasız maksimumun (0.0030) 1.7 katı,
güvenlik payı bilinçli olarak bir basamak yukarı alınmış ("triyajda yanlış kabul,
kaçırılan bir vakadan tehlikelidir"). Bir içerik düzeltmesinin **yan etkisi**
olarak değişmesi, o gerekçeyi sessizce iptal etmek olur. Kalibrasyon yine
koşulacak ama iki şeyi doğrulamak için: yanık sorgusunun geçtiği ve diğer 17'nin
gerilemediği. Eklenen metin sorguyu 0.005'in üstüne çıkaramıyorsa **düzeltme
yetersizdir**, eşik yanlış değil.

**K4 — Sızıntı sınırı: belge protokolün bakış açısından zenginleştirilir,
kalibrasyon sorgusuna bakılarak değil.**
Meşru olan, yanık protokolünü hastaların bu tabloyu genel olarak nasıl tarif
ettiğiyle zenginleştirmek. Sızıntı olan, ölçüm sorgusunu belgeye kopyalamak.
Gün 20'de `inme.txt`'ye eklenen FAST cümlesi kalibrasyon sorgusunun üç öbeğini
neredeyse birebir tekrarlıyordu ve eşik şişirilmiş bir skorla seçiliyordu;
incelemede yakalandı, sorgu yeniden yazıldı. Aynı emsal burada uygulanıyor:
`yanik.txt` zenginleştirilir, ardından kalibrasyon sorgusu **aynı klinik tabloyu
protokolün kelimelerini kullanmadan** anlatacak biçimde yeniden yazılır.
Bugünkü sorgu ("Kaynar su elimin üstüne döküldü, hemen su toplamaya başladı.")
değişecektir.

**K5 — İkinci, tutulan bir yanık sorgusu eklenir.**
K4 tek başına şunu açıkta bırakıyor: sorguyu yeniden yazsak bile, belgeyi o
sorgu geçene kadar ayarlarsak yine tek bir cümleye aşırı uydurmuş oluruz.
Bu yüzden `ILGILI` listesine ikinci bir yanık sorgusu konur. **Sıra bağlayıcıdır
ve garantiyi veren şey sıradır:** ikinci sorgu `yanik.txt`'ye dokunulmadan
**önce** yazılır ve dosyaya kilitlenir; belge yalnızca birinci sorguya bakılarak
düzenlenir; ikinci sorgunun skoru **ilk kez en sonda**, düzeltme bittikten sonra
ölçülür. Sonradan yazılan bir "tutulan" sorgu tutulmuş sayılmaz — o noktada
belgeyi zaten görmüş olursunuz.

İkisi de 0.005'i geçerse düzeltme genelleşmiş demektir; yalnızca ayarlanan
geçerse ezberlenmiş demektir ve düzeltme **yetersizdir** (K3 gereği çözüm eşiği
indirmek değil, metni güçlendirmektir). Maliyeti bir liste satırı, kazancı
ölçümün anlamı.

**K6 — Test veritabanı kilidi: beyaz liste, kaçış kapısı yok.**
Kilit `Base.metadata.drop_all` çağıran bir fixture'ı koruyor, yani bütün bir
şemayı siliyor. Bugünkü kontrol yalnızca `settings.database_url.endswith(
"/ai_triage_test")` — iki yönden kusurlu: üretim sunucusundaki aynı adlı bir
veritabanı kilitten geçiyor, ve `?sslmode=require` gibi bir query string
sonek testini geçemediği için **meşru** bir koşuyu durduruyor. Yeni kural: URL
düzgün ayrıştırılır; veritabanı adı tam olarak `ai_triage_test` **ve** host şu
kümede olmalı — `localhost`, `127.0.0.1`, `::1`, `postgres`. Sonuncusu Docker
Compose ve CI servis konteynerinin adı. Ortam değişkeniyle geçiş **yoktur**:
kolay kaçış kapısı olan kilit kilit değildir ve kaza en çok o kapıdan girer.
Başka bir host gerekirse kilit bilinçli olarak düzenlenir.

**K7 — İki şema değişikliği tek Alembic revision'ında toplanır.**
`ai_recommendations.visit_id` unique ve `doctor_reviews.doctor_id` index aynı
alanı ilgilendiriyor ve aynı gün doğuyor; iki ayrı revision hem fazladan iş hem
daha zor okunan bir geçmiş. `downgrade()` ikisini de geri alır. Model tarafı
(`app/models/visit.py`) ve migration **birlikte** değişir, yoksa bir sonraki
`autogenerate` farkı yeniden üretir.

`visit_id`'nin unique olmaması bugün gerçek bir kayıp yolu: `Visit.recommendation`
ilişkisi `uselist=False` diyor, yani bir ziyarete iki öneri satırı yazılırsa hem
ilişki yalanlanır hem de doktor kuyruğundaki `joinedload` + `LIMIT 20` sorgusu
19 farklı ziyaret döndürüp bekleyen bir vakayı **sessizce düşürür**. Canlı veri
ölçüldü (10 Ağustos 2026): 12 öneri / 12 tekil ziyaret, yineleme yok, kısıt veri
taşımadan eklenir.

**K8 — `doctor_id` index'i için test yazılmaz.**
Index davranış değiştirmez, yalnızca sorgu planını etkiler. Varlığını sınayan bir
test, veritabanı iç yapısını teste sabitler ve karşılığında hiçbir hata
yakalamaz. Migration'ın uygulandığı `alembic upgrade head` ile doğrulanır.

**K9 — Speech yamalamasının bağlayıcılığı mutasyonla kanıtlanır; TDD uymaz.**
`test_jetonsuz_istek_401_doner`, `test_desteklenmeyen_format_400_doner` ve
`test_cok_buyuk_dosya_400_doner` yeni davranış istemiyor — üçü de bugün doğru
sonucu veriyor. Kusur şurada: `transcribe` yamalanmadığı için, uçtaki uzantı
beyaz listesi ya da boyut sınırı gevşerse istek gövdeye ilerler ve gerçek
faster-whisper `medium` modeli yüklenir (yüzlerce MB indirme, dakikalarca CPU).
"Önce kırmızı gör" burada anlamsız; bağlayıcılık, uçtaki korumayı gevşetip
testin **gerçek servise gitmek yerine temiz kırmızı verdiğini** göstererek
kanıtlanır. Çözüm `dokuman_yazmayi_engelle` fixture'ının birebir muadili;
desen aynı dosyadaki diğer testlerde zaten mevcut.

Bu, aynı kusur deseninin **üçüncü ve son bilinen** görünümü: `/ai/analiz` (Gün
11-16 incelemesinde Important sayılıp düzeltildi), `/document/upload` (Gün 20
birleştirmesinde son kontrolde bulundu) ve `/speech/transkript` — yani buradaki
üç test. Ek C'nin kaydettiği ders, ağırlık farkının teknik bir gerekçeye değil
hangi incelemede görüldüğüne dayandığıydı; bu madde kapandığında desenin bilinen
tüm örnekleri kapanmış olur.

**K10 — Yeni `yavas` test ham bayt okur, `read_text()` değil.**
Ek C (1052/3) mevcut `yavas` testin `read_text()` kullandığını, üretimin ise ham
baytı decode ettiğini kaydediyor: Windows'ta CRLF→LF çevrimi yüzünden test ile
üretim **farklı metin gömüyor** ve chunk sınırları kayıyor. Yeni test aynı
kusuru tekrarlamamalı. Bu, projede "test kurgusu gerçeği tam yansıtmıyor"
deseninin bilinen dördüncü tekrarı olurdu.

**K11 — Bu belge Gün 22'nin yalnızca birinci yarısıdır.**
Yol haritasının Gün 22'si "Test derinleştirme, coverage kapısı, CI". Bu belge
onu kapsamıyor; borç kapatma bittikten sonra ikinci yarı kendi tasarım
dokümanını ve planını alır. İkisini tek spec'e sıkıştırmak, ikisinin de kabul
ölçütünü bulanıklaştırırdı.

## Görev bölünmesi

Üç görev, türüne göre. Sıra bağlayıcıdır: retrieval en sona kalır ki
`kalibre_esik.py` koşulurken paket zaten yeşil olsun ve "acaba başka bir şey mi
bozdu" sorusu doğmasın.

| # | Görev | Dosyalar | Tür |
|---|---|---|---|
| 1 | Test altyapısı | `tests/conftest.py`, `tests/api/test_speech_api.py` | yalnız test |
| 2 | Şema | `app/models/visit.py`, yeni Alembic revision, ilgili test | üretim + şema |
| 3 | Retrieval | `ornek_dokumanlar/protokoller/yanik.txt`, `scripts/kalibre_esik.py`, yeni `yavas` test | veri + ölçüm |

## Test mimarisi

| Madde | Kırmızı nasıl görülür |
|---|---|
| conftest kilidi | Saf TDD. `postgresql://triage:triage@prod-host:5432/ai_triage_test` reddedilmeli diyen test bugün geçmiyor; ayrıca `.../ai_triage_test?sslmode=require` kabul edilmeli diyen test bugün geçmiyor |
| Speech yamalama | TDD uymaz (K9). Mutasyon kanıtı zorunlu, rapora birebir çıktısıyla girer |
| `visit_id` unique | Saf TDD. Aynı ziyarete iki `AIRecommendation` yazan test `IntegrityError` bekler; bugün hata almıyor |
| `doctor_id` index | Test yazılmaz (K8) |
| `yanik.txt` | Saf TDD. `yavas` işaretli test: yanık sorgusu `yanik.txt`'yi eşiğin üstünde getirmeli; bugün 0.0005 |

Mevcut 137 testin hiçbiri değiştirilmez, zayıflatılmaz veya yeniden adlandırılmaz.
Yeni bağımlılık eklenmez.

## İşletme zinciri (Görev 3)

Dosyayı değiştirmek tek başına hiçbir şey yapmaz; bilgi tabanı yeniden
yüklenmeden kalibrasyon **eski gömmeleri** ölçer. Sıra:

1. `yanik.txt` düzenlenir
2. Bilgi tabanı yeniden kurulur (`scripts/bilgi_tabani_kur.py`)
3. `scripts/kalibre_esik.py` koşulur ve çıktısı rapora birebir yazılır

Script'ler **`main` checkout'undan** çalıştırılır — `.env` orada, yani doğru
Chroma portu (8001) ve backend'le aynı JWT anahtarı gelir; worktree'lerde `.env`
yoktur. Backend her birleştirmeden sonra yeniden başlatılmalıdır; `/health/`
200 dönmesi hangi kodun koştuğunu kanıtlamaz.

**Ortam uyarısı (10 Ağustos 2026):** Docker backend ve frontend konteynerleri
crash loop'ta — compose yığını `C:\Users\batuh\Desktop\Ai_Triage` dizininden
başlatılmış (eski yol, içinde yalnızca Docker'ın mount ederken yarattığı boş
`app/` ve `frontend/` var). Postgres ve ChromaDB adlandırılmış volume
kullandığı için sağlam. Doğrulama yerel uvicorn ile yapılır.

## Bitti sayılır

- [ ] Test sayısı 137'den artmış; mevcut hiçbir test değişmemiş veya zayıflamamış
- [ ] conftest kilidi host doğruluyor, query string'li meşru URL'i durdurmuyor, kaçış kapısı yok
- [ ] Speech'in üç testi `transcribe` yamalıyor; mutasyon kanıtı raporda
- [ ] `ai_recommendations.visit_id` unique; aynı ziyarete ikinci öneri `IntegrityError` veriyor
- [ ] `doctor_reviews.doctor_id` index'li; `alembic upgrade head` ve `downgrade -1` sınandı
- [ ] `yanik.txt` hasta dilini kapsıyor; kalibrasyon sorgusu yeniden yazıldı (K4)
- [ ] İkinci, tutulan yanık sorgusu eklendi ve **o da** eşiği geçiyor (K5)
- [ ] Kalibrasyon **18/19** ilgili (tek başarısız: `inme` karaktersiz yazım), 0/10 alakasız; `rerank_threshold` hâlâ 0.005 (K3)
- [ ] Yeni `yavas` test ham bayt okuyor (K10)
- [ ] Kapatılan her madde Ek C'de **kapatıldı** olarak işaretlendi — açık listede asılı kalmıyor
- [ ] Yeni bağımlılık yok; `requirements.txt` değişmedi
- [ ] Her yeni fonksiyon/alan/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
