# Gün 22 (ikinci yarı) — Test Derinleştirme, Kapsama Kapısı ve CI Tasarım Dokümanı

**Tarih:** 11 Ağustos 2026
**Durum:** onaylandı, plan yazılacak
**Öncesi:** Gün 22 birinci yarısı (borç kapatma) `main`'e birleşti (`539df32`, 153 test, kapsama %85 satır / %83 dal)

## Hedef

Yol haritasının Gün 22'sini yapmak: **test derinleştirme, kapsama kapısı, CI.**
Bugün testler yalnızca elle koşuyor, kapsama yalnızca raporlanıyor (dayatılmıyor),
ve depoda hiçbir CI yapılandırması yok.

## Kapsam

**İçeride:**

1. Ağır import'ların tembelleştirilmesi (`rag_service`, `stt_service`, `chroma_service`)
   ve ölçümle yazılmış bir `requirements-ci.txt`
2. Dal kapsaması + `--cov-fail-under` kapısı (`.coveragerc`, `pytest.ini`)
3. GitHub Actions workflow'u: `test` işi ve `migration` işi

**Dışarıda, bilinçli olarak:** Ek C'nin kalan test-kalite borçları
(`test_config.py`'nin kusurlu `endswith` yüklemi, uçtan uca PDF/DOCX yükleme
testi, kalıcılık/durability testi); `top_k_initial` ve `yanik.txt`'nin Kırmızı
erişilebilirliği (Gün 23); lint/formatter yapılandırması.

**Kırmızı çizgi:** `rerank_threshold`, `ornek_dokumanlar/` altındaki protokol
metinleri ve mevcut 153 testin hiçbiri değişmez.

## Bağlam — bugünkü durum, ölçülmüş

| | Değer | Nasıl ölçüldü |
|---|---|---|
| Hızlı paket | 153 passed, 5 deselected, ~57 sn | `pytest -m "not yavas"` |
| Satır kapsaması | %85 | `--cov=app` |
| **Dal kapsaması** | **%83** | `--cov-branch` |
| Dal kapsaması, iki adaptör hariç | **%87** | geçici `.coveragerc` ile |
| **`app.main` import süresi** | **25,5 sn** | ayrı süreçte ölçüldü |
| Import'un çektiği ağır modüller | torch, transformers, sentence_transformers, chromadb, faster_whisper, pdfplumber, docx | `sys.modules` |
| Yüklenen toplam modül | 5214 | `len(sys.modules)` |
| CI | **yok** | `.github/workflows` dizini mevcut değil |

Yani 57 saniyelik paketin **yaklaşık yarısı** saf import. Yol haritası CI tuzağını
önceden kaydetmişti: *"CI'da testler 10 dakikayı geçiyor — kök neden:
torch/sentence-transformers CI'da kuruluyor. Çözüm: CI için minimal gereksinim
listesi; ağır bağımlılıklar yalnızca `yavas` testlerde."* O çözüm bugün
**uygulanamaz** çünkü `torch` modül düzeyinde import ediliyor ve `app.main` onu
zincirle çekiyor — minimal bir listeyle testler toplanamaz bile.

## Tasarım kararları

**K1 — Bu belge yol haritasının asıl Gün 22'sidir; birinci yarı ayrı bir gündü.**
10-11 Ağustos'ta kapatılan borç günü (`docs/superpowers/specs/2026-08-10-gun22-borc-kapatma-design.md`)
bu günün **ön koşuluydu**: speech testlerinin gerçek faster-whisper'a ulaşması ve
test veritabanı kilidinin host doğrulamaması, ikisi de CI'ı kurulamaz kılıyordu.
İkisi ayrı spec, ayrı plan, ayrı dal.

**K2 — Ağır import'lar tembelleştirilir; minimal CI listesi bunun sonucudur, sebebi değil.**
Sıra bağlayıcı: önce import'lar fonksiyon içine taşınır, sonra `requirements-ci.txt`
yazılır. Tersi sırada liste yazılırsa testler toplanamaz ve neyin eksik olduğu
anlaşılmaz. Tembelleştirilecek modüller ve sebepleri:

| Modül | Ağır import | Neden tembelleştirilebilir |
|---|---|---|
| `rag_service.py` | `torch`, `sentence_transformers` | Model zaten tembel (`get_reranker`); testler `sahte_rag` ile değiştiriyor |
| `stt_service.py` | `torch`, `faster_whisper` | Model zaten tembel (`_model`); testler `sahte_stt` ile değiştiriyor |
| `chroma_service.py` | `chromadb` | Bağlantı zaten tembel (`_collection`); testler `sahte_chroma` ile değiştiriyor |

`document.py`'nin `pdfplumber` / `python-docx` import'ları **bırakılıyor**: ikisi de
hafif ve tembelleştirmenin ölçülen bir kazancı yok. Bunun doğrudan sonucu şudur ve
K4'ün ölçümünde şaşırtıcı gelmemeli: `requirements-ci.txt` **pdfplumber ve
python-docx'i içerecek**, çünkü `app.main` onları import zinciriyle çekmeye devam
edecek. Minimal liste "hiçbir ağır şey yok" demek değil, "torch ailesi yok" demek.

**K3 — Modül düzeyindeki tip açıklamaları ayrı bir tuzaktır ve import'u taşımak tek başına yetmez.**
İki modülde şu desen var:

```python
_model: WhisperModel | None = None      # stt_service.py
_reranker: CrossEncoder | None = None   # rag_service.py
```

Modül düzeyindeki değişken açıklamaları çalışma zamanında değerlendirilir ve
`__annotations__` içine yazılır; import fonksiyona taşınınca bu satır `NameError`
verir. Çözüm dosya başına `from __future__ import annotations` (tercih edilen) ya
da açıklamayı tırnağa almak. Uygulayıcı bunu bilmezse "import'u taşıdım, oldu"
deyip patlayan bir modül bırakır — bu yüzden karar olarak yazılıyor.

**K4 — `requirements-ci.txt` ölçümle yazılır, `requirements.txt`'ten kopyalanmaz.**
Yöntem: minimal bir listeyle temiz bir sanal ortam kurulur, `-m "not yavas"`
koşulur, ne eksikse eklenir, yeşil olana kadar tekrarlanır. Her satırın yanında
**neden orada olduğu** yazılır. Tahminle yazılmış bir liste, ilk CI koşusunda
anlaşılmaz bir `ModuleNotFoundError` üretir ve o hata uzak bir makinede ayıklanır.

**K5 — Kapsama dal bazlıdır ve eşik 87'dir; ikisi de ölçüldü.**
`--cov-branch` açılır (bugün yok, yani %85 satır bazlı ve koşul dalları hiç
ölçülmüyor). `--cov-fail-under=87` konur. 87 sayısı ölçümden geliyor: hariç
tutmadan önce dal kapsaması %83, `llm_service.py` ve `stt_service.py` hariç
tutulunca %87.

Eşik bir **taban**dır, hedef değil. Bugünkü değere eşit konması bilinçli: amaç
sessiz erozyonu yakalamak, yani "kapsama düştü" durumunu kırmızıya çevirmek.

**K6 — Sahtelenen iki dış servis adaptörü ölçümden çıkarılır, ve bu Ek C'ye yazılır.**
`app/services/llm_service.py` (%22) ve `app/services/stt_service.py` (%30)
testlerde bilerek hiç çalıştırılmıyor — `sahte_llm.py` ve `sahte_stt.py` yerlerine
geçiyor. Ölçüme dahil edildiklerinde global sayı test kalitesini değil **o iki
dosyanın boyutunu** izler: `llm_service`'e elli satır eklemek kapsamayı test
kalitesiyle ilgisiz bir sebeple düşürür, tersine auth testleri boşaltılsa ölü
ağırlık sayıyı maskeleyebilir.

Hariç tutmanın bedeli dürüstlüktür: **neyin ölçülmediği yazılmadan "kapsama %87"
iddiası eksiktir.** Bu yüzden `.coveragerc` içindeki `omit` gerekçesini taşır ve
Ek C'ye ayrıca yazılır.

**K7 — CI iki iştir, her biri kendi Postgres servisiyle.**
`test` işi: `requirements-ci.txt` + `requirements-dev.txt`, `ai_triage_test`
veritabanı, `pytest -m "not yavas"` — kapsama kapısı burada dayatılır.
`migration` işi: boş veritabanına `alembic upgrade head` → `downgrade base` →
`upgrade head`.

**ChromaDB servisi gerekmiyor.** `entegrasyon` işaretli testlerde Chroma sahte,
yalnızca Postgres gerçek (Ek C bu işaretin fazla geniş olduğunu zaten kaydetmişti).

**K8 — `migration` işi `ai_triage` adını kullanır ve DB kilidi orada devrede değildir; ikisi de bilinçlidir.**
Ad seçimi: test işi `conftest` üzerinden `drop_all` çağırıyor; aynı veritabanı adını
paylaşmak iki işi birbirine bağlar. GitHub Actions'ta her iş kendi servis
konteynerini aldığı için bugün çakışma yok, ama bağımlılığı baştan kurmamak daha
ucuz. Üretimdeki adla koşmak ayrıca Gün 27'nin kurulum provasının provasıdır.

Kilit meselesi: `tests/yardimcilar/db_kilidi.py` yalnızca **test fixture'ının**
yolunda; alembic'i korumuyor. Migration işi kasıtlı olarak `ai_triage` adlı bir
veritabanına yazıyor. Bu yazılmazsa, sonra bakan biri "kilit burada neden devrede
değil" diye haklı olarak takılır.

**K9 — `yavas` testler CI'da hiç koşmaz.**
Gerçek bge-m3 (~2.2 GB), cross-encoder ve ayakta bir ChromaDB isterler. Sonucu:
CI'ın ölçtüğü kapsama, yerelde `-m "not yavas"` ile ölçülenle **aynı** olur, yani
eşik iki ortamda da aynı anlama gelir.

**K10 — Import testi alt süreçte koşar.**
`sys.modules`'te `torch` olup olmadığını sınayan test, pytest oturumunun kendi
içinde koşarsa anlamsızdır: başka testler torch'u zaten yüklemiş olur. Test bir
alt süreç açıp `app.main`'i orada import etmeli ve sonucu oradan okumalı.

**K11 — CI'ın kabul ölçütü GitHub'da yeşil koşmasıdır; yerelde kanıtlanamaz.**
Workflow YAML'ı okunabilir ve mantığı gözden geçirilebilir, ama gerçek kanıt
uzakta koşmasıdır. "Workflow yazıldı" bu günü bitirmez; "workflow koştu ve iki iş
de yeşil" bitirir. Bu, günün kapanışının bir push'a bağlı olduğu anlamına gelir.

## Görev bölünmesi

Sıra bağımlılığa göre: CI hem `requirements-ci.txt`'i hem `.coveragerc`'yi tüketir.

| # | Görev | Dosyalar | Tür |
|---|---|---|---|
| 1 | Tembel import + minimal liste | `app/services/{rag,stt,chroma}_service.py`, `requirements-ci.txt`, yeni test | üretim + test |
| 2 | Kapsama kapısı | `.coveragerc`, `pytest.ini` | yapılandırma |
| 3 | CI workflow | `.github/workflows/ci.yml` | yapılandırma |

Görev 1 başta çünkü üretim koduna dokunan tek iş; bir şeyi kıracaksa en erken
görülmeli ve kırılırsa kalan iki bacak zaten anlamsızlaşır.

## Test mimarisi

| İş | Kırmızı nasıl görülür |
|---|---|
| Tembel import | **Saf TDD, ve bu günün asıl kalıcı muhafızı.** Alt süreçte `app.main` import edilir, `sys.modules` içinde `torch`/`sentence_transformers`/`faster_whisper`/`chromadb` **bulunmadığı** iddia edilir. Bugün geçmiyor. |
| Kapsama kapısı | TDD uymaz. Bağlayıcılık ters yönden kanıtlanır: `--cov-fail-under` geçici olarak 95 yapılır, paketin kırıldığı görülür, geri alınır. |
| CI workflow | Yerelde kanıtlanamaz (K11). Kabul, uzakta yeşil koşmasıdır. |

Import testi olmadan, birinin `rag_service`'e modül düzeyinde bir `import torch`
geri koyması **hiçbir şeyi kırmaz** ve CI sessizce yavaşlar — yani tam olarak yol
haritasının uyardığı yere geri dönülür. Bu testin değeri, kapsama kapısınınkinden
yüksek.

## Bitti sayılır

- [ ] `app.main` import'u `torch`, `sentence_transformers`, `faster_whisper` ve `chromadb`'yi çekmiyor; bir test bunu alt süreçte bağlıyor
- [ ] Import süresi ve paket süresi önce/sonra ölçülüp raporlandı (taban: 25,5 sn import, ~57 sn paket)
- [ ] `requirements-ci.txt` ölçümle yazıldı; minimal listeyle kurulan temiz ortamda `-m "not yavas"` yeşil
- [ ] Her satırın yanında neden orada olduğu yazılı
- [ ] `.coveragerc` dal kapsamasını açıyor ve iki adaptörü gerekçesiyle hariç tutuyor
- [ ] `--cov-fail-under=87` aktif; 95'e çıkarılınca paketin kırıldığı görüldü
- [ ] `.github/workflows/ci.yml` iki iş içeriyor: `test` ve `migration`
- [ ] **CI GitHub'da koştu ve iki iş de yeşil** (K11)
- [ ] Ek C'ye kapsamadan hariç tutulan dosyalar ve gerekçesi yazıldı
- [ ] Mevcut 153 testin hiçbiri **zayıflatılmadı** veya yeniden adlandırılmadı; `rerank_threshold` ve protokol metinleri değişmedi. (Yeni test eklemek bu kısıtın dışındadır — Gün 22'nin birinci yarısında bu ifade "hiçbiri değiştirilmedi" diye yazılmış ve aynı belge üç testin fixture parametresi kazanmasını mandate ettiği için kendi kendisiyle çelişmişti; burada baştan ayrılıyor.)
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
