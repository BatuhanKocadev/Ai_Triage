# Gün 24 — Prompt iyileştirme ve ölçüm tekrarı

**Tarih:** 13 Ağustos 2026
**Durum:** onaylandı (kullanıcı: tam Gün 24)
**Öncesi:** Gün 23 değerlendirme seti `main`'de (`c4b3e80`); baseline
`degerlendirme/sonuclar/2026-08-13.{md,json}`

## Hedef

Staj raporunun yöntem bölümünü taşıyan **önce/sonra tablosu**: üç önkoşul
(tetkik adı normalizasyonu, `department` akuite dağarcığı, `yanik.txt`
aşırı-getirme) + few-shot prompt enjeksiyonu sonrası ölçümün, gürültü tabanının
üstünde olup olmadığını göstermek.

## Kapsam

**İçeride:**

1. Tetkik alias → kanonik ad (`degerlendirme/olcum.py`); Jaccard artefaktını kır
2. `department` kapalı kelime dağarcığı + `_normalize_department`; altın
   `beklenen_bolum` akuite alanına; `kok_neden` C kapısında `bolum_dogru_mu`
3. `kalibre_esik.py` kaynak raporlasın; `top_k_initial=20` ayara; gerekirse
   `yanik.txt` ~4 chunk; Chroma yeniden yükle
4. Few-shot havuzunu prompt’a enjekte et (tetkik adı öğretme)
5. ≥3 tam koşum; ortalama manşet; `tur_04` ve tetkik boşalma oranı izlenir

**Dışarıda:**

- `kor_10` (yalnızca kullanıcı)
- Altın standart etik tartışmaları (`kor_01`/`kor_02`, `tur_06` FAST-ED, …)
- Frontend / güvenlik borç listesi
- FHIR (Gün 25 feda)

## Tasarım kararları

**K1 — Önce üç önkoşul, sonra few-shot.** Aksi hâlde önce/sonra tablosu gürültü
ve adlandırma artefaktını “iyileşme” diye yazar.

**K2 — Tetkik normalizasyonu yalnızca ölçüm tarafında.** Üretim LLM çıktısını
yeniden adlandırmıyor; raporlanan Jaccard klinik eşanlamı yansıtır.

**K3 — `department` dağarcığı:** `Kırmızı Alan`, `Sarı Alan`, `Yeşil Alan`,
`Resüsitasyon`, `Şok Odası`, `Triyaj Bankosu`. Model hastane bölümü uydurursa
triyaj kodundan akuite alanına indirgenir; eşik altı zaten `Triyaj Bankosu`.

**K4 — C kapısı:** triyaj doğru ∧ bölüm doğru ∧ tetkik Jaccard == 1,0.

**K5 — `yanik` önce ölçülür.** Aday sırası: kaynaklı kalibrasyon →
`top_k_initial=20` → chunk sıkıştırma. Kabul: ateş sorgusu `ates_sepsis.txt`
**ve** üç yanık senaryosu gerilemez.

**K6 — Few-shot sızıntı yok.** Havuz tetkik adı öğretmez; kesişim kapısı durur.
Önce/sonrada ortalama tetkik sayısı izlenir (bastırma riski).

**K7 — Ölçüm ≥3 koşum.** Manşet ortalama; tek koşum +5,3 puan iddiası yasak.
Baseline `2026-08-13` dosyaları değiştirilmez.

**K8 — TDD + Türkçe yorum.** Her yeni fonksiyon/alana tek cümlelik Türkçe
açıklama.

## Başarı ölçütleri

- Odaklı ve tam paket (`pytest -m "not yavas"`) yeşil; kapsama ≥ %87
- Önce/sonra markdown: kör + türetilmiş ortalama doğruluk, Kırmızı duyarlılık,
  Jaccard, A/B/C, eşik altı, tetkik sayısı, `tur_04` salınımı
- İyileşme cümlesi gürültü tabanına göre dürüst (“üstünde” / “içinde”)
