# Gün 24 — Önce / sonra tablosu

Baseline: `2026-08-13` (Gün 23, değiştirilmedi).
Sonra koşum sayısı: **3** (manşet = ortalama).
Gürültü tabanı (Gün 23): **5.3 puan** (kaynak: `tur_04` salınımı).

## Manşet metrikler

| Ölçü | Önce (kör) | Sonra ort. (kör) | Önce (tür.) | Sonra ort. (tür.) |
|---|---|---|---|---|
| Genel doğruluk | %37.5 | %33.3 | %78.9 | %82.5 |
| Kırmızı duyarlılık | n/d | n/d | %100.0 | %100.0 |
| Eşik altı oranı | %0.0 | %0.0 | %5.3 | %0.0 |

Türetilmiş Jaccard önce: **0.2579365079365079**, sonra ort.: **0.27953216374269**.

## A/B/C (türetilmiş, ortalama sayılar)

- **A**: önce 2, sonra ort. 2.0
- **B**: önce 3, sonra ort. 2.3
- **C**: önce 13, sonra ort. 15.0

## Few-shot tetkik bastırma izi

Ortalama önerilen tetkik sayısı (türetilmiş, Belirsiz hariç): önce **2.47**, sonra ort. **2.33**.

## `tur_04` salınımı

Sonra koşumlarda `tur_04` kodları: Sarı, Kırmızı, Kırmızı
Önce: `Kırmızı`.

## Dürüst okuma

Türetilmiş doğruluk farkı **+3.5 puan** — gürültü tabanının (**5.3**) **içinde**. Few-shot / önkoşul etkisi tek başına manşet iyileşmesi diye raporlanamaz.

---

## Few-shot enjeksiyonu KAPALI — ölçümle alınan karar (14 Ağustos 2026)

Yukarıdaki "sonra" koşumları **few-shot kapalıyken** yapıldı
(`settings.few_shot_aktif = False`). Few-shot açık kolunun kendi tablosu
`gun24-fewshot-acik-kolu.md` dosyasında duruyor. Üçe üç karşılaştırma:

| | kör | türetilmiş | **Kırmızı duyarlılık** | Jaccard | kaçan Kırmızı |
|---|---|---|---|---|---|
| few-shot **açık** (3 koşum) | %37,5 | %80,7 | **%90,0** | 0,28 | `tur_11` (3/3) |
| few-shot **kapalı** (3 koşum) | %33,3 | %82,5 | **%100,0** | 0,28 | yok |

Doğruluk ve Jaccard farkları gürültü tabanının (5,3 puan) içinde. Gürültünün
dışında kalan tek fark **Kırmızı duyarlılığı** ve o kategorik: açıkken üç
koşumun üçünde de aynı vaka kaçıyor, kapalıyken hiç kaçmıyor.

### Kaçan vaka ve sebebi

`tur_11` — *"Oğlum mutfakta çamaşır suyunu su sanıp içmiş. Ağzının içi yanmış,
sürekli salyası akıyor ve yutkunamıyor."* Beklenen **Kırmızı**.

`zehirlenme.txt`'nin Kırmızı satırı birebir şunu diyor: *"Kostik madde
(**çamaşır suyu**, asit) içen ... vakalar."* Ve o belge retrieval'da **geliyor**
(dört koşumun dördünde de `sources = [yanik.txt, zehirlenme.txt]`). Yani model
kriteri önünde görüyor ve yine de Sarı diyor.

### İzole deney — tek değişken örnek bloğu

Aynı senaryo, aynı retrieval çıktısı, aynı prompt iskeleti:

| Kol | `tur_11` Kırmızı |
|---|---|
| A — few-shot açık | **0/6** |
| B — few-shot kapalı | **6/6** |
| C — açık + "örneklere bakarak seçme, referans doküman kazanır" uyarısı | **1/6** |

**C kolu kritik:** sorun ifade değil, örneklerin varlığı. Prompt açıkça
"referans doküman kazanır" dediğinde bile dört örnek getirilen kriteri eziyor.

### Mekanizma ve karar

Few-shot modeli akuite skalasında **aşağı** çekiyor. Bu kör sette işe
yarıyordu (model orada yukarı kaçıyor: `kor_02`, `kor_05`, `kor_08` kapalıyken
Kırmızı'ya fırlıyor) ve türetilmiş sette zarar veriyordu.

Karar doğruluk sayısına değil **yöne** dayanıyor: few-shot açıkken güvenli bir
üst-triyaj kazanılıyor, karşılığında **tehlikeli bir alt-triyaj** veriliyor.
Triyajda bu takas kabul edilemez — kör setin 4,2 puanı, kaçırılan bir kostik
madde vakasından ucuzdur.

Mekanizma silinmedi, ayara alındı: `settings.few_shot_aktif`. Yeniden açmadan
önce bu ölçümü çürütmek gerekiyor.
