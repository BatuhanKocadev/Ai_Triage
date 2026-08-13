# Gün 24 — Önce / sonra tablosu

Baseline: `2026-08-13` (Gün 23, değiştirilmedi).
Sonra koşum sayısı: **3** (manşet = ortalama).
Gürültü tabanı (Gün 23): **5.3 puan** (kaynak: `tur_04` salınımı).

## Manşet metrikler

| Ölçü | Önce (kör) | Sonra ort. (kör) | Önce (tür.) | Sonra ort. (tür.) |
|---|---|---|---|---|
| Genel doğruluk | %37.5 | %37.5 | %78.9 | %80.7 |
| Kırmızı duyarlılık | n/d | n/d | %100.0 | %90.0 |
| Eşik altı oranı | %0.0 | %0.0 | %5.3 | %0.0 |

Türetilmiş Jaccard önce: **0.2579365079365079**, sonra ort.: **0.27690058479532165**.

## A/B/C (türetilmiş, ortalama sayılar)

- **A**: önce 2, sonra ort. 2.0
- **B**: önce 3, sonra ort. 2.7
- **C**: önce 13, sonra ort. 12.3

## Few-shot tetkik bastırma izi

Ortalama önerilen tetkik sayısı (türetilmiş, Belirsiz hariç): önce **2.47**, sonra ort. **2.32**.

## `tur_04` salınımı

Sonra koşumlarda `tur_04` kodları: Sarı, Sarı, Sarı
Önce: `Kırmızı`.

## Dürüst okuma

Türetilmiş doğruluk farkı **+1.8 puan** — gürültü tabanının (**5.3**) **içinde**. Few-shot / önkoşul etkisi tek başına manşet iyileşmesi diye raporlanamaz.
