# Retrieval Boru Hattı Düzeltmesi — Tasarım Dokümanı

**Tarih:** 6 Ağustos 2026
**Kapsam:** Reranker skorlarındaki çift sigmoid ve ChromaDB'nin İngilizce gömme
modeli. İkisi de retrieval'ı sessizce bozuyor.

## Hedef

`/ai/analiz` boru hattının Türkçe sorgularda doğru protokolü getirmesini sağlamak
ve skor ölçeğini eşik kalibrasyonu yapılabilir hâle döndürmek.

## Bağlam — nasıl bulundu

Gün 20'de bilgi tabanı 4 chunk'tan (2 sahte dosya) 47 chunk'a (15 gerçek protokol)
çıkarıldı ve `scripts/kalibre_esik.py` koşuldu. Çıkan tablo şuydu: 18 ilgili
sorgunun 10'u eleniyor, ilgili skorların minimumu (0.5001) alakasız skorların
maksimumundan (0.5004) **düşük** — yani iki sınıf iç içe geçmiş. Önerilen eşik
gerçek acillerin %56'sını "Belirsiz"e düşürüyordu.

Bu, eşik seçimiyle çözülebilecek bir sorun değildi; ölçülen şeyin kendisi bozuktu.

### A — Çift sigmoid

`CrossEncoder.predict()` modelin kendi `activation_fn`'ini uyguluyor.
`BAAI/bge-reranker-v2-m3` için bu `Sigmoid()`, yani `predict()` zaten `[0,1]`
aralığında olasılık döndürüyor. `rag_service.py:67` bunu `calculate_sigmoid` ile
**ikinci kez** eziyor.

Sonuç: tüm skor uzayı `sigmoid(0)=0.500` ile `sigmoid(1)=0.731` arasına sıkışıyor.
Ayrım gücünün yaklaşık %77'si atılıyor. Ölçülen aralık (0.5000–0.6721) bu tahminle
birebir uyuşuyor.

Mevcut `rerank_threshold = 0.52` bu bozuk ölçekte kalibre edilmişti.

### B — Birinci aşama İngilizce gömme kullanıyor

ChromaDB koleksiyonu `DefaultEmbeddingFunction` ile kurulmuş; bu
`all-MiniLM-L6-v2`, yani yalnızca İngilizce. Türkçe sorguda ürettiği vektörler
sinyal taşımıyor:

| Sorgu | Beklenen | ChromaDB'nin ilk 5'i |
|---|---|---|
| "Kaynar su elimin üstüne döküldü" | `yanik.txt` | psikiyatrik, psikiyatrik, inme, travma, karın |
| "yüzü düştü, kolunu kaldıramıyor, konuşması bozuk" | `inme.txt` | psikiyatrik, anafilaksi, travma, psikiyatrik, baş ağrısı |

Mesafeler 1.21–1.34 aralığında sıkışık — vektörlerin ayırt edici bilgi taşımadığının
imzası.

`top_k_initial = 10` olduğu için 47 chunk'tan yalnızca 10'u reranker'a ulaşıyor ve
o 10'u seçen mekanizma bu. Reranker doğru dokümanı hiç görmüyor.

**Bu hata dün yoktu çünkü ölçülemiyordu:** 4 chunk varken `n_results=10` koleksiyonun
tamamını getiriyordu, dolayısıyla birinci aşamanın kalitesi sonucu hiç etkilemiyordu.
Derleme büyüyünce ortaya çıktı.

### Testler bunu neden yakalamadı

`tests/birim/test_rag_esik_kapisi.py` sahte reranker'a **logit ölçeğinde** değer
veriyor (`-10.0`, `10.0`, `1.0`, `9.0`). Gerçek `predict()` ise **olasılık**
döndürüyor. Sahte, gerçek sözleşmenin yanlışını kodlamış.

Sonucu şu: `-10 → eşik altı` ve `10 → eşik üstü` testleri, kodda sigmoid olsa da
olmasa da geçiyor — çift sigmoid hakkında hiçbir şey kanıtlamıyorlar. Bu, Gün 11–16
ve 17+18'de belgelenen desenin bir başka yüzü: **sahte servis gerçeği yanlış taklit
ederse, testler yeşil verip üretim bozulur.**

Ayrıca gerçek modelle Türkçe retrieval'ı sınayan hiçbir test yoktu; B'yi yakalayacak
olan test buydu.

## Kapsam

**İçinde:** A ve B'nin düzeltilmesi, sahte reranker'ın gerçek sözleşmeye
hizalanması, bilgi tabanını yeniden kuran script, üç yeni test.

**Dışında:**
- `rerank_threshold`'un yeni değeri — A ve B düzeltilmeden ölçülemez, bu spec bir
  sayı sabitlemez (K7).
- Derlemenin hasta diline yaklaştırılması ("C maddesi") — ölçümden sonra, yalnızca
  ölçümün zayıf gösterdiği başlıklara (K8).
- torch'un CUDA sürümüne geçilmesi. Makinede RTX 4060 var ama torch CPU-only
  kurulu; bu bir hız konusu, doğruluk konusu değil (K9).

## Tasarım kararları

**K1 — Reranker aktivasyonu açıkça kurulur.** `CrossEncoder` nesnesi
`activation_fn=torch.nn.Sigmoid()` ile yaratılır. Bugün `predict()` zaten sigmoid
uyguluyor ama bu, modelin *config dosyasından* geliyor — model değişirse ya da
kütüphane varsayılanı kayarsa `predict()` sessizce ham logit döndürür ve her eşik
anlamsızlaşır. Tam olarak bugün bulduğumuz hatanın türü bu; açık kurulum bağımlılığı
ortadan kaldırır.

**K2 — `calculate_sigmoid` silinir.** `rag_service.py:67` çağrısı kalkınca fonksiyonun
iki çağıranı da (burası ve `scripts/kalibre_esik.py`) kalmaz. Kullanılmayan bir
dönüşüm fonksiyonunu bırakmak, ileride birinin yeniden çağırmasına davetiyedir.

**K3 — Sahte reranker olasılık ölçeğine taşınır.** `sahte_reranker_uret` artık
`[0,1]` aralığında değer üretir ve `test_rag_esik_kapisi.py`'nin dört testi bu
ölçeğe göre yeniden yazılır. Sahte gerçek sözleşmeyi yansıtmak zorundadır; bu hata
tam da yansıtmadığı için hayatta kaldı.

**K4 — Gömme modeli ayardan okunur, varsayılanı `BAAI/bge-m3`.** Reranker ile aynı
aile olduğu için iki aşama aynı anlam uzayını paylaşır. Türkçesi güçlü ve
`multilingual-e5` ailesinin aksine `"query: "` / `"passage: "` öneki gerektirmez —
öneki unutmak sessiz kalite kaybı üreten yeni bir hata kaynağı olurdu.

**K5 — Koleksiyon düşürülüp yeniden kurulur.** Mevcut 47 vektör eski modelle
üretildi; farklı boyutta ve farklı anlam uzayında oldukları için yeni sorgu
vektörleriyle karşılaştırılamazlar. Kısmi güncelleme mümkün değil, koleksiyonun
tamamı yeniden gömülmeli.

**K6 — Yeniden kurma bir script'tir, elle adım değil.** `scripts/bilgi_tabani_kur.py`
koleksiyonu sıfırlar ve `ornek_dokumanlar/protokoller/` içeriğini gerçek API
üzerinden yükler. Model ya da derleme her değiştiğinde gerekecek; elle yapılan bir
sıra, unutulduğunda sessizce eski vektörlerle çalışan bir sistem bırakır.

**K7 — Bu spec `rerank_threshold` için sayı sabitlemez, ama yazılmasını kapsar.**
Düzeltmeler bittikten sonra `kalibre_esik.py` yeniden koşulur, değer ölçümden
türetilir ve `config.py`'ye yazılır. Spec'in sabitlemediği şey **sayının kendisi**;
sayıyı ölçüm belirler. Mevcut `0.52` geçersizdir: bozuk ölçekte ölçülmüştü ve yeni
ölçek tamamen farklı olacak. Bu adım Gün 20'nin üçüncü parçasını da kapatır.

Ölçüm ilgili ve alakasız sınıfları temiz ayıramazsa (yani hiçbir eşik yanlış kabul
olmadan makul sayıda ilgiliyi geçiremezse), eşik yazılmaz — bulgu kaydedilir ve
K8'deki "C maddesi" devreye girer. Kötü bir eşiği yazmak, kırık bir sistemi
sabitlemek olur.

**K8 — "C maddesi" ölçümden sonra kararlaştırılır.** Derleme klinik dilde yazılmış,
sorgular hasta dilinden geliyor (ham skorlar: "dudaklarım morardı, hırıltılı" →
`nefes_darligi` 0.717, çünkü metinde "siyanoz (morarma)" ve "hırıltılı solunum"
geçiyor; "kaynar su döküldü" → `yanik` 0.00023, çünkü metin "TVYA" ve "Parkland
formülü" diyor). Düzgün çok dilli gömme bu köprünün bir kısmını kendiliğinden
kurabilir. 15 dosyayı ölçüm yapmadan elden geçirmek, gereksiz olabilecek bir emek.

## Uygulanacak değişiklikler

### `app/services/rag_service.py`
- `get_reranker()`: `CrossEncoder(..., activation_fn=torch.nn.Sigmoid())`
- `retrieve_and_rerank()`: `normalized_scores` artık `predict()` çıktısının kendisi
- `calculate_sigmoid` silinir

### `app/config/config.py`
- `embedding_model: str = "BAAI/bge-m3"`

### `app/services/chroma_service.py`
- `get_collection()`, `settings.embedding_model`'den kurulan bir
  `SentenceTransformerEmbeddingFunction` ile koleksiyonu açar

### `scripts/kalibre_esik.py`
- `calculate_sigmoid` import'u ve kullanımı kalkar

### `scripts/bilgi_tabani_kur.py` (yeni)
- Koleksiyonu düşürür, `ornek_dokumanlar/protokoller/*.txt` dosyalarını
  `POST /document/upload` ile yükler, sonuç özetini basar

## Test mimarisi

| Test | Dosya | Neyi donduruyor |
|---|---|---|
| `test_reranker_skoru_ikinci_kez_ezilmez` | `tests/birim/test_rag_esik_kapisi.py` | Sahte reranker `0.9` döndürdüğünde skor `0.9` olmalı; eski kodda `0.711`e düşerdi |
| `test_gomme_modeli_ayarlardan_okunur` | `tests/birim/test_chroma_service.py` (yeni) | `get_collection()` gömme fonksiyonunu `settings.embedding_model`'den kurmalı |
| `test_turkce_sorgu_dogru_protokolu_getirir` | `tests/entegrasyon/test_turkce_retrieval.py` (yeni, `yavas`) | Gerçek bge-m3 ile "kaynar su döküldü" sorgusu `yanik.txt` getirmeli |

İlk ikisi gerçek model yüklemez, normal koşuda çalışır. Üçüncüsü `yavas` işaretlidir
ve `-m "not yavas"` ile atlanır — ama **B'yi yakalayacak olan test odur**, bu yüzden
yazılması şart.

Ayrıca `test_rag_esik_kapisi.py`'nin mevcut dört testi K3 gereği olasılık ölçeğine
taşınır. `test_tam_esik_degeri_dahil_edilir` düzeltmeyle birlikte kırmızıya dönecek
(bugün `0.0` → `sigmoid(0)=0.5` sayılıyor); bu beklenen ve doğru davranıştır.

## Bitti sayılır

- [ ] Üç yeni test yeşil; `test_rag_esik_kapisi.py` olasılık ölçeğinde yeniden yazıldı
- [ ] Mevcut 99 test hâlâ yeşil (`-m "not yavas"`)
- [ ] `calculate_sigmoid` depoda hiç geçmiyor
- [ ] `scripts/bilgi_tabani_kur.py` çalıştırıldı; koleksiyon bge-m3 ile yeniden kuruldu
- [ ] `GET /document/liste` 15 dosya / 48 chunk gösteriyor (`inme.txt`'ye FAST
      bulguları eklenince derleme 47'den 48 chunk'a çıktı; yukarıdaki metinde
      geçen 47 rakamları bu düzenlemeden önceki ölçümlerdir)
- [ ] "Kaynar su" ve FAST inme sorguları elle denendiğinde doğru protokolü getiriyor
- [ ] `kalibre_esik.py` yeniden koşuldu ve yeni skor dağılımı kaydedildi
- [ ] Ölçüm temiz ayrım veriyorsa yeni `rerank_threshold` `config.py`'ye yazıldı;
      vermiyorsa bulgu kaydedildi ve eşik değiştirilmedi (K7)
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
