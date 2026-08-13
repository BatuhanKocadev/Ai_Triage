# Gün 24 uygulama planı — Prompt + ölçüm tekrarı

**Tarih:** 13 Ağustos 2026
**Spec:** `docs/superpowers/specs/2026-08-13-gun24-prompt-olcum-design.md`
**Dal / worktree:** `gun24-prompt-olcum` / `.worktrees/gun24-prompt-olcum`

## Görevler

### G0 — Altyapı
- [x] Spec + bu plan commit’e aday
- [x] Worktree doğrulandı (`main...HEAD` sağ = 0 başlangıçta)

### G1 — Tetkik alias (TDD)
- [x] Kırmızı testler: Hemogram≡Tam kan sayımı, TİT≡Tam İdrar Tetkiki, EKG≡Elektrokardiyografi
- [x] `degerlendirme/olcum.py` kanonikleştirme
- [x] Yeşil doğrulama `--no-cov`

### G2 — Department akuite (TDD)
- [x] `_normalize_department` + birim testleri
- [x] Prompt kuralı kapalı dağarcık
- [x] Senaryo JSON `beklenen_bolum` güncelle
- [x] `kok_neden` C kapısında `bolum_dogru_mu`
- [x] API / ölçüm testleri yeşil

### G3 — yanik aşırı-getirme
- [x] `kalibre_esik.py` kazanan `source` + skor
- [x] `top_k_initial` settings, varsayılan 20
- [x] Ölç: ateş → ates_sepsis? yanık üçlüsü bozulmadı mı?
- [x] Gerekirse `yanik.txt` sıkıştır + yeniden upload (+ `ates_sepsis` hasta dili)

### G4 — Few-shot enjeksiyon
- [x] Havuz loader + prompt enjekte
- [x] API testi: system_prompt örnek şikayet içeriyor
- [x] Sızıntı kapısı hâlâ yeşil

### G5 — Ölçüm tekrarı
- [x] ≥3 koşum
- [x] `karsilastir` / önce-sonra markdown
- [x] Ek C Gün 24 bölümü
- [x] Tam paket `pytest -m "not yavas"`

## Doğrulama komutları

```bash
.venv\Scripts\python.exe -m pytest tests/birim/test_degerlendirme_araci.py --no-cov
.venv\Scripts\python.exe -m pytest -m "not yavas"
.venv\Scripts\python.exe -m degerlendirme.calistir
```
