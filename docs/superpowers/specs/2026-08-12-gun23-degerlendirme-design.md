# Gün 23 — Değerlendirme Seti ve Doğruluk Ölçümü Tasarım Dokümanı

**Tarih:** 12 Ağustos 2026
**Durum:** onaylandı, plan yazılacak
**Öncesi:** Gün 22'nin ikinci yarısı (CI) `main`'e birleşti ve push'landı (`5b5d25c`, 157 test, %87,42 dal kapsaması, CI iki işte yeşil)

## Hedef

Bugüne kadar "çalışıyor" diyorduk. Bugünden sonra ölçülmüş bir cümle kuracağız:
*"24 senaryonun N'inde doğru triyaj kodu üretti, gerçek Kırmızı vakaların
%M'ini yakaladı, %K'sında eşiğin altında kalıp cevap vermedi."*

Bu, staj raporunun ve video sunumunun en değerli tek sayfası ve Gün 24'ün
önce/sonra tablosunun **önce** sütunudur.

## Kapsam

**İçeride:**

1. İki yazarlı değerlendirme seti (kör set + türetilmiş set) ve ayrı tutulan
   few-shot havuzu
2. `degerlendirme/olcum.py` — saf ölçüm fonksiyonları ve birim testleri
3. `degerlendirme/calistir.py` — HTTP sürücüsü, ön uçuş kontrolü, kısmi sonuç
   koruması
4. Ses kayıtları üzerinden WER ölçümü
5. `degerlendirme/sonuclar/YYYY-AA-GG.{md,json}` — insan raporu ve Gün 24'ün
   okuyacağı ham kayıt

**Dışarıda, bilinçli olarak:** `top_k_initial`'ın düzeltilmesi; `yanik.txt`'nin
Kırmızı erişilebilirliği; prompt'a few-shot enjeksiyonu; karaktersiz yazım
sorunu. Dördü de **Gün 24'ün işi** — bugünün amacı onların bedelini sayıya
çevirmek. Ek C'nin kalan ~50 maddelik borcu da dışarıda.

**Kırmızı çizgi:** `app/` altında **hiçbir dosya değişmez.**
`ornek_dokumanlar/` altındaki protokol metinleri, `rerank_threshold` (0.005) ve
mevcut 157 testin hiçbiri değişmez. Depoda değişen tek mevcut dosya
`.gitignore`'dur (`degerlendirme/ses/` eklenir).

## Bağlam — bugünkü durum, ölçülmüş

| | Değer | Kaynak |
|---|---|---|
| Test / kapsama | 157 passed, %87,42 dal | Gün 22 ikinci yarı |
| Bilgi tabanı | 15 protokol dosyası / **51 chunk**, bge-m3, 1024 boyut | Gün 22 birinci yarı doğrulaması |
| `rerank_threshold` | **0.005** | `app/config/config.py:91` |
| `top_k_initial` | **10** (ayar değil, fonksiyon varsayılanı) | `app/services/rag_service.py:47` |
| `degerlendirme/` | **yok** | depo |
| Etiketli vaka verisi | **hiç gelmedi** — `veri/` klasörü yok | depo |
| Ses kaydı | **1 adet** (`ornek_dokumanlar/ses_ornek.m4a`) | depo |
| `symptom_text` sınırı | 10–500 karakter | `app/api/ai.py:42` |
| `vitals` alanları | yalnızca `fever`, `pulse` | `app/api/ai.py:35` |
| `AnalysisResponse.sources` | dönüyor | `app/api/ai.py:56` |
| `/ai/analiz` hız sınırı | `genel_sinirlayici`, **30/dk**, `/speech/transkript` ile **ortak** | `app/api/ai.py`, `app/api/speech.py:48` |

İki gerçeklik bugünün şeklini belirledi. Birincisi: **staj yerinden etiketli vaka
gelmedi**, yani senaryolar sıfırdan yazılacak. İkincisi: yol haritası "10 kayıt
için WER" diyor ama depoda tek bir ses dosyası var.

## Bilinen ve önceden ilan edilen defektler

Aşağıdaki üçü Gün 22'de **ölçülerek** bulundu ve bugün düzeltilmiyor. Rapor
bunları "ölçüm keşfetti" diye sunmayacak; beklenen çıktı olarak önceden yazılıyor.

1. **`yanik.txt`'nin Kırmızı kriterleri hasta dilinden ulaşılamıyor.** Üç bağımsız
   sorguda 0.0002 / 0.0003 / 0.0011. Sebep yapısal: reranker chunk'ın tamamını
   puanlıyor, yoğun kelime dağarcığı olmayan bloğa tek cümle eklemek seyreliyor.
   **Beklenti:** yanık senaryoları A kutusuna düşecek.
2. **`top_k_initial = 10`, 51 chunk'lık derlemeye karşı.** Artık yalnızca geri
   çağırmayı sınırlamıyor, doğru protokolün chunk'larını aday havuzundan dışarı
   itiyor ("çamaşır suyu içtim" sorgusu `zehirlenme.txt` bağlamı hiç almıyor).
   **Beklenti:** zehirlenme senaryosu A kutusuna düşecek.
3. **Karaktersiz yazım skorları düşürüyor** (`inme` 0.0089 → 0.0031). Kör
   metinlerde Türkçe karakter kullanılacak; aksi hâlde ölçüme ikinci bir değişken
   girer ve hangi etkinin kimden geldiği ayrılamaz.

## Tasarım kararları

**K1 — Bugün ölçüm günüdür, düzeltme günü değil.** Sistem olduğu gibi ölçülür.
Gerekçe: Gün 24'ün önce/sonra tablosu raporun yöntem bölümünü tek başına taşıyor
ve gerçek bir fark göstermesi gerekiyor. Bugün düzeltirsek yarın ölçecek bir fark
kalmaz. `app/` altına dokunulmaması bu kararın uygulanabilir hâlidir.

**K2 — Ölçüm seti iki yazarlıdır: kör set ve türetilmiş set, fiziksel olarak ayrı
dosyalarda, her sayıda ayrı raporlanır.** Bu günün en önemli kararı ve bedeli
zaten ödenmiş bir dersten geliyor: Gün 22'nin birinci yarısında protokol metnini
de kalibrasyon sorgularını da aynı kişi (uygulayıcı) yazınca sorgu belgenin
özetine dönüştü, ve K5'in "tutulan sorgu" kuralı bunu **delemedi**. Kullanıcının
metni görmeden yazdığı tek sorgu ("mangalda kolumu ateşe tuttum, kolum bembeyaz
oldu hissetmiyorum") üç görev incelemesinin bulamadığını gösterdi: düzeltme
genelleşmiyordu. Tek yazarlı bir doğruluk sayısı kendi kendini doğrular.

- `degerlendirme/kor_senaryolar.json` — 6-8 senaryo, **kullanıcı yazar**,
  `ornek_dokumanlar/protokoller/` klasörünü açmadan.
- `degerlendirme/senaryolar.json` — ~18 senaryo, uygulayıcı protokollerden türetir.
- İki setin sayıları **hiçbir yerde toplanıp tek sayıya indirgenmez.** Ayrışma
  çıkarsa bulgu odur.

**K3 — Sorguyu yazmak ile etiketi atamak ayrı işlerdir.** Kullanıcı yalnızca
`sikayet` alanını (ve isterse `yas`/`cinsiyet`) yazar; `beklenen_triage_code`,
`beklenen_bolum`, `beklenen_tetkikler`, `beklenen_kaynak` alanlarını uygulayıcı
protokol kriterlerine bakarak doldurur. Kirlenen şey sorgunun dilidir, etiketin
kaynağı değil — kullanıcı klinisyen olmadığı için altın standardı o üretemez.
Körlük tek yönlüdür: kullanıcı protokolleri görmemelidir, uygulayıcının kullanıcı
metinlerini görmesi sorun değildir.

**K4 — Sızıntı kuralı testle dayatılır, dosya başlığındaki uyarı yazısıyla değil.**
`degerlendirme/few_shot_havuzu.json` bugün 3-5 örnekle doğar ve **asla ölçülmez**.
`test_few_shot_havuzu_olcum_setiyle_kesismiyor` iki setin kesişiminin boş olduğunu
doğrular. Gerekçe: yol haritası sızıntı kuralını "dosya başlıklarına bu kural
yazılır" diye tarif ediyor, ama Gün 21 aynı sınıfta bir ders verdi — kodun
işlediği kuraldan başka bir şey anlatan yorum, ona sonra dokunan kişi tarafından
yanlış ayarlanır. Havuzun bugün doğması Gün 24'ü yazma baskısından kurtarır.

**K5 — `degerlendirme/` paketi `app`'i hiç import etmez; yalnızca HTTP konuşur.**
İki kazancı var: ölçüm gerçek kullanım yolunu ölçmüş olur (yol haritasının
REFACTOR notu bunu istiyor), ve `scripts/*.py`'yi ısıran `PYTHONPATH` tuzağına
hiç girmez. Sürücünün tek bağımlılığı `requests`.

**K6 — Saf çekirdek / sürücü ayrımı.** `olcum.py` ağ ve model görmeyen saf
fonksiyonlar taşır; `calistir.py` yalnızca sürücüdür ve test edilmez. Birim
testleri Ollama'sız, backend'siz koşar. Bu ayrım olmadan yol haritasının istediği
beş test yazılamaz.

**K7 — Genel doğruluk iki kez basılır.** Biri tüm senaryolar üzerinden, biri
yalnızca cevap verilen ("Belirsiz" olmayan) senaryolar üzerinden. Gerekçe: tek
sayı basılırsa "Belirsiz"leri paydadan düşürerek doğruluğu şişirmek mümkün olur;
iki sayı bunu imkânsız kılar ve aradaki fark eşik altı oranını okunur hâle getirir.

**K8 — "Belirsiz" bir yanlış cevap değildir, ama kök nedende A sayılır.** Rapor
onu "cevap vermedim" olarak kendi oranıyla basar (yol haritasının kuralı). Kök
neden tasnifinde ise retrieval kutusuna girer, çünkü eşik altında kalmak
retrieval'ın başarısız olmasının başka bir adıdır.

**K9 — Kök neden otomatik tasnif edilir, elle değil.** Her yanlış üç kutudan
birine düşer:

| Kutu | Koşul | Gün 24'teki çözüm sınıfı |
|---|---|---|
| **A — retrieval** | `beklenen_kaynak` dönen `sources` içinde yok (veya cevap "Belirsiz") | chunk boyutu, `top_k_initial`, eşik, protokol metni |
| **B — muhakeme** | Doğru protokol geldi ama triyaj kodu yanlış | few-shot, prompt |
| **C — biçim** | Triyaj kodu doğru, bölüm veya tetkikler yanlış | normalizasyon, şema |

Gerekçe: yol haritasının Gün 24'ü "en büyük kutuya müdahale et" diyor. Ölçülmezse
o tasnif senaryo senaryo elle kazılarak yapılır — 3 iş günü kalmışken en pahalı
yer orasıdır. Veri zaten yanıtta geliyor (`AnalysisResponse.sources`), maliyeti
sıfıra yakın.

**K10 — Hız sınırı ölçüm için kapatılmaz.** `genel_sinirlayici` `/ai/analiz` ve
`/speech/transkript` için ortaktır ve 30/dk'dır; ~24 senaryo + 6-8 ses çağrısı bu
sınıra değebilir. Sürücü 429 görünce bekler, yeniden dener **ve bunu rapora
kaydeder.** Sınırı kapatmak, üretimde olmayan bir sistemi ölçmek olurdu.

**K11 — WER kendi içimizde yazılır, yeni bağımlılık eklenmez.** ~15 satırlık
standart düzenleme-mesafesi. Gerekçe: `jiwer` eklemek `requirements.txt` **ve**
`requirements-ci.txt`'in ikisini birden güncellemeyi gerektirir
(`tests/birim/test_ci_gereksinimleri.py` pariteyi dayatıyor) — ölçüm gününde
gereksiz bir CI riski.

**K12 — WER normalizasyonu Türkçe karakteri ASCII'ye katlamaz.** Küçük harfe
indirme ve noktalama temizliği yapılır, katlama yapılmaz. Katlarsak gerçek tanıma
hatalarını (ör. "şiddetli" → "siddetli") doğru saymış oluruz ve WER olduğundan iyi
çıkar.

**K13 — Kapsama kapısına dokunulmaz.** `pytest.ini` `--cov=app` diyor,
`degerlendirme/` onun dışında kalır ve `--cov-fail-under=87` etkilenmez. Aracın
kendisi kendi birim testleriyle korunur. Ölçüm gününde kapıyı oynatmak, kapının
anlamını ölçümle karıştırmak olurdu.

**K14 — Koşumun yarattığı ziyaretler silinmez.** Her `/ai/analiz` çağrısı gerçek
`ai_triage` veritabanına bir `Visit` + `AIRecommendation` yazıyor; koşum sonunda
doktor kuyruğunda ~24 gerçek vaka birikir. Bunlar **video sunumundaki doktor
paneli demosu için hazır ve gerçekçi içeriktir.** `visit_id`'ler ham sonuç
dosyasına yazılır, böylece istenirse toplu silinebilir. Sessiz bir yan etkiyi
sessiz bırakmamak için burada kayda geçiyor.

**K15 — Kısmi sonuç korunur.** Her senaryo tamamlandığında ham sonuç dosyasına
yazılır. 20. senaryoda çöken bir koşum 19 ölçümü kaybetmez. Tek senaryonun hatası
(500, timeout, 429 tükenmesi) kaydedilir ve koşumu durdurmaz.

## Mimari

```
degerlendirme/
  __init__.py
  olcum.py               # saf fonksiyonlar — ağ yok, model yok
  calistir.py            # sürücü — HTTP, ön uçuş, raporlama
  senaryolar.json        # ~18 türetilmiş senaryo
  kor_senaryolar.json    # 6-8 kör senaryo (kullanıcı yazar)
  few_shot_havuzu.json   # 3-5 örnek — ASLA ölçülmez
  ses/                   # .gitignore — kullanıcının kayıtları
  sonuclar/
    YYYY-AA-GG.md        # insan için tablo
    YYYY-AA-GG.json      # ham per-senaryo kayıt — Gün 24 buradan okur
tests/birim/
  test_degerlendirme_araci.py
```

### Senaryo şeması

```json
{
  "id": "kor_03",
  "sikayet": "iki saattir göğsümde baskı var, sol kolum uyuşuyor, terledim",
  "yas": 58,
  "cinsiyet": "Erkek",
  "kronik_hastalik": "hipertansiyon",
  "vitals": {"fever": null, "pulse": 104},
  "beklenen_triage_code": "Kırmızı",
  "beklenen_bolum": "Acil Servis",
  "beklenen_tetkikler": ["EKG", "Troponin"],
  "beklenen_kaynak": "gogus_agrisi.txt",
  "ses_dosyasi": "ses/kor_03.m4a"
}
```

`vitals` yalnızca `fever` ve `pulse` taşır çünkü `app/api/ai.py:35` bundan
fazlasını kabul etmiyor — şema uydurulmaz. `sikayet` 10-500 karakter aralığına
uyar. `ses_dosyasi` yalnızca kör senaryolarda bulunur; yoksa o senaryo WER'e
girmez. `beklenen_kaynak` izlenebilirlik için değil, **K9'un kök neden ayrımı
için** vardır.

### `olcum.py` — saf fonksiyonlar

| Fonksiyon | Girdi → Çıktı |
|---|---|
| `senaryolari_yukle(yol)` | dosya yolu → senaryo listesi; eksik/geçersiz alan varsa hata |
| `triyaj_dogru_mu(beklenen, cikan)` | iki kod → bool |
| `tetkik_ortusmesi(beklenen, cikan)` | iki liste → Jaccard [0,1] |
| `kok_neden(senaryo, yanit)` | senaryo + yanıt → `"A"` / `"B"` / `"C"` / `None` (doğruysa) |
| `wer(referans, hipotez)` | iki metin → [0,1] |
| `ozet(sonuclar)` | sonuç listesi → aşağıdaki tablo |

### Raporlanan sayılar

| Ölçü | Tanım |
|---|---|
| Genel doğruluk (tüm) | doğru triyaj kodu / toplam senaryo |
| Genel doğruluk (cevaplananlar) | doğru triyaj kodu / "Belirsiz" olmayan senaryo |
| **Kırmızı duyarlılık** | gerçek Kırmızı senaryolardan sistemin de Kırmızı dediği oran |
| Eşik altı oranı | "Belirsiz" / toplam |
| Tetkik Jaccard | ortalama örtüşme, yalnızca cevap verilenlerde |
| Kök neden dağılımı | A / B / C sayıları |
| WER | ortalama, ses kaydı olan senaryolarda |

Her sayı **kör set ve türetilmiş set için ayrı ayrı** basılır (K2).

Kırmızı duyarlılık klinik olarak tek kritik sayıdır: gerçek Kırmızı bir hastaya
Yeşil demek ile gerçek Yeşil bir hastaya Kırmızı demek aynı ağırlıkta hata
değildir.

### Veri akışı

```
kor_senaryolar.json ─┐
senaryolar.json ─────┼─→ calistir.py ─→ POST /ai/analiz ─→ yanıt (+sources)
                     │        │
      ses/*.m4a ─────┘        ├─→ POST /speech/transkript ─→ metin ─→ wer()
                              │
                              └─→ olcum.py ─→ sonuclar/YYYY-AA-GG.{md,json}
```

## Hata yönetimi

**Ön uçuş kontrolü, koşumdan önce, fail-fast:** backend ayakta mı; `hasta`
hesabıyla jeton alınıyor mu; ChromaDB koleksiyonunda 51 chunk var mı; Ollama
cevap veriyor mu. Gerekçe Gün 20'nin dersi: `/health/` 200 dönmesi kimlik
doğrulamasının çalıştığını kanıtlamaz — `bilgi_tabani_kur.py` tam bu yüzden
bilgi tabanını boşaltacaktı. Bir ön uçuş adımı düşerse koşum hiç başlamaz.

| Durum | Davranış |
|---|---|
| 429 (hız sınırı) | Bekle, yeniden dene; olay rapora yazılır (K10) |
| 500 / timeout | Senaryo "hata" olarak kaydedilir, koşum devam eder (K15) |
| Ses dosyası yok | O senaryo WER'e girmez, triyaj ölçümü etkilenmez |
| Ön uçuş düşerse | Koşum hiç başlamaz, sebep ekrana yazılır |

## Test stratejisi

`tests/birim/test_degerlendirme_araci.py` — yol haritasının beşi artı üç tanesi:

1. `test_senaryo_dosyasi_okunur_ve_dogrulanir` — eksik alanlı senaryo hata verir
2. `test_dogruluk_hesaplanir` — 4 senaryodan 3 doğru → %75
3. `test_kirmizi_kacirma_ayri_raporlanir` — gerçek Kırmızı iken Yeşil denmesi ayrı ve daha ağır sayılır
4. `test_tetkik_ortusme_orani_hesaplanir` — Jaccard
5. `test_esik_alti_yanitlar_ayri_sayilir` — "Belirsiz" yanlış değil, cevapsız
6. `test_kok_neden_retrieval_ve_muhakeme_ayrilir` — K9
7. `test_few_shot_havuzu_olcum_setiyle_kesismiyor` — K4
8. `test_wer_hesaplanir` — K11

Hepsi saf; Ollama, backend, ChromaDB hiçbirinde çağrılmaz. TDD zorunlu: her test
önce yazılır ve kırmızı görüldüğü rapor edilir.

## Doğrulama

1. `.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py -v --no-cov`
   (`--no-cov` zorunlu, yoksa kapsama kapısı sahte kırmızı verir)
2. `.venv\Scripts\python.exe -m pytest -m "not yavas"` — 157 + 8 test, regresyon yok
3. `.venv\Scripts\python.exe degerlendirme/calistir.py` — gerçek Ollama ve
   Postgres ile, `main` checkout'undan (`.env` orada)
4. Çıkan sayılar Ek C'nin "Gün 23" bölümüne yazılır

## Bitti sayılır

- [ ] 24+ senaryo hazır; 6-8'i kör, hepsi yüklenen protokollerle konu olarak örtüşüyor
- [ ] Koşum aracı testli ve çalışıyor (8 birim testi yeşil)
- [ ] Genel doğruluk (iki hâliyle), Kırmızı duyarlılık, eşik altı oranı, Jaccard ve kök neden dağılımı ölçüldü ve kaydedildi
- [ ] Kör set ile türetilmiş setin sayıları ayrı basıldı ve ayrışma yorumlandı
- [ ] Ses kayıtları için WER hesaplandı
- [ ] Hiçbir ölçüm senaryosu few-shot havuzunda yok ve bu **testle** doğrulandı
- [ ] `app/` altında hiçbir dosya değişmedi
- [ ] Mevcut 157 test yeşil, kapsama kapısı geçiyor
- [ ] Ek C'ye "Gün 23" bölümü yazıldı
- [ ] Dal `main`'e birleşti

## Riskler

**Kör setin küçüklüğü.** 6-8 senaryo istatistiksel bir örneklem değil. Rapor bunu
oran olarak değil, **gözlem** olarak sunacak: "kör setin N senaryosundan M'i
başarısız oldu ve hepsi A kutusuna düştü" gibi. Gün 22'de tek bir kör sorgu üç
incelemenin bulamadığını gösterdi — değeri örneklem büyüklüğünde değil,
yazarlığın bağımsızlığında.

**Okunan konuşma, telaşlı konuşmadan kolaydır.** Kullanıcı kendi yazdığı metni
okuyacağı için WER iyimser taraflıdır. Rapora bu cümleyle yazılır.

**Ollama'nın belirlenimsizliği.** Aynı senaryo iki koşumda farklı sonuç verebilir.
Bugün tek koşum yapılır ve sayılar "tek koşum" etiketiyle kaydedilir; Gün 24'ün
karşılaştırması aynı etiketi taşıyacak.

**`degerlendirme` paketinin `sys.path`'te bulunması.** `tests/` altında
`__init__.py` olduğu için pytest depo kökünü `sys.path`'e ekler ve
`import degerlendirme.olcum` çalışır. Plan bunu ilk testte doğrulayacak; çalışmazsa
çözüm `pytest.ini`'ye `pythonpath = .` eklemektir.
