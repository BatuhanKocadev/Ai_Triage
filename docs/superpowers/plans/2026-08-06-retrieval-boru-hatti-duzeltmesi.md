# Retrieval Boru Hattı Düzeltmesi — Uygulama Planı

> **Ajan çalışanlar için:** ZORUNLU ALT BECERİ: Bu planı görev görev uygulamak için
> superpowers:subagent-driven-development kullanın. Adımlar takip için checkbox
> (`- [ ]`) sözdizimi kullanır.

**Hedef:** Reranker skorlarındaki çift sigmoidi kaldırmak ve ChromaDB'yi Türkçe
anlayan bir gömme modeline geçirmek; böylece eşik kalibrasyonu anlamlı hâle gelsin.

**Mimari:** Üç görev. Görev 1 skor ölçeğini düzeltir (`rag_service`), Görev 2 gömme
modelini ayardan okunur hâle getirir (`chroma_service` + `config`) ve bilgi tabanını
yeniden kuran scripti ekler, Görev 3 gerçek modelle Türkçe retrieval'ı sınayan
`yavas` entegrasyon testini yazar.

**Teknoloji:** sentence-transformers 5.6.0, ChromaDB, BAAI/bge-m3, pytest.

**Tasarım dokümanı:** `docs/superpowers/specs/2026-08-06-retrieval-boru-hatti-duzeltmesi-design.md`
— çelişkide o belge kazanır, kararlar K1–K9 numaralarıyla oradadır.

## Global Constraints

- **Türkçe açıklama zorunlu.** Eklenen her fonksiyon ve blok yanına tek cümlelik
  Türkçe yorum.
- **Test adları birebir uygulanır.**
- **Saf TDD.** Önce test, ÇALIŞTIRARAK kırmızı görülür, sonra üretim kodu.
- **Mevcut 99 test yeşil kalmalı** (`-m "not yavas"`). Taban çizgisi `main` üzerinde
  ölçüldü: `99 passed`, kapsama %80.
- **Python:** `C:\Users\batuh\Desktop\Ai_Triage-myself\.venv\Scripts\python.exe`
- **Normal koşuda gerçek model YÜKLENMEZ.** Yalnızca `yavas` işaretli testler
  gerçek bge-m3'ü yükleyebilir.
- **PostgreSQL ve ChromaDB ayakta.** Konteynerler `ai_triage_postgres`,
  `ai_triage_chromadb` (host portu **8001**).
- **Commit mesajları ASCII.**
- **DİKKAT — iki farklı `SahteKoleksiyon` var.** `tests/yardimcilar/sahte_rag.py`
  içindeki `collection.query()` taklit eder (RAG testleri);
  `tests/yardimcilar/sahte_chroma.py` içindeki `upsert/get/delete` taklit eder
  (doküman uçları). Karıştırmayın, birleştirmeyin.

---

## Dosya Yapısı

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `tests/yardimcilar/sahte_rag.py` | sahte reranker olasılık ölçeğine taşınır | 1 |
| `tests/birim/test_rag_esik_kapisi.py` | 4 test yeniden yazılır + 1 yeni | 1 |
| `app/services/rag_service.py` | açık aktivasyon, çift sigmoid kalkar | 1 |
| `scripts/kalibre_esik.py` | `calculate_sigmoid` kullanımı kalkar | 1 |
| `app/config/config.py` | `embedding_model` ayarı | 2 |
| `app/services/chroma_service.py` | açık gömme fonksiyonu | 2 |
| `tests/birim/test_chroma_service.py` | **YENİ** — ayarın okunduğunu dondurur | 2 |
| `scripts/bilgi_tabani_kur.py` | **YENİ** — koleksiyonu sıfırlar ve yükler | 2 |
| `tests/entegrasyon/test_turkce_retrieval.py` | **YENİ** — `yavas`, gerçek model | 3 |

---

### Task 1: Çift sigmoidi kaldır

**Files:**
- Modify: `tests/yardimcilar/sahte_rag.py:20-34`
- Modify: `tests/birim/test_rag_esik_kapisi.py`
- Modify: `app/services/rag_service.py:18-30, 66-67`
- Modify: `scripts/kalibre_esik.py:21, 93`

**Interfaces:**
- Consumes: `sahte_reranker_uret(skorlar)`, `SahteKoleksiyon(dokumanlar, kaynaklar)`
  (`tests/yardimcilar/sahte_rag.py`)
- Produces: `retrieve_and_rerank` artık `predict()` çıktısını olduğu gibi skor
  sayar. `calculate_sigmoid` **silinir** — Görev 2 ve 3 onu çağırmaz.

- [ ] **Step 1: Sahte reranker'ın sözleşmesini düzelt**

`tests/yardimcilar/sahte_rag.py` içinde `_SahteReranker` ve `sahte_reranker_uret`
docstring'lerini değiştir. Kod gövdesi aynı kalıyor, değişen şey **ne ifade
ettiği**:

```python
class _SahteReranker:
    """predict() çağrısına önceden belirlenmiş OLASILIK skorları döndürür.

    Gerçek CrossEncoder.predict() modelin Sigmoid aktivasyonunu zaten uyguladığı
    için [0,1] aralığında olasılık döndürür. Sahte bunu birebir yansıtmalı —
    logit ölçeğinde değer döndürdüğü sürece çift sigmoid hatası testlerden
    kaçabiliyordu.
    """

    def __init__(self, skorlar: list[float]):
        self.skorlar = skorlar

    def predict(self, pairs):
        return self.skorlar[:len(pairs)]


def sahte_reranker_uret(skorlar: list[float]):
    """get_reranker yerine geçecek, sabit olasılık döndüren fabrika üretir."""
    def _sahte():
        return _SahteReranker(skorlar)
    return _sahte
```

- [ ] **Step 2: Mevcut dört testi olasılık ölçeğine taşı ve yeni testi ekle**

`tests/birim/test_rag_esik_kapisi.py` içindeki dört testin skor değerlerini ve
yorumlarını değiştir; dosyanın SONUNA yeni testi ekle.

`test_esik_altinda_bos_liste_doner` — skoru `[-10.0]` yerine `[0.10]` yap ve
yorumu şununla değiştir:
```python
    # 0.10 olasılığı 0.52 eşiğinin altında. Değer bilerek seçildi: eski çift
    # sigmoidli kodda sigmoid(0.10)=0.525 çıkıp eşiği GEÇİYORDU, yani bu test
    # düzeltmenin bağlayıcı kanıtı.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.10]))
```

`test_esik_ustunde_dokuman_doner` — skoru `[10.0]` yerine `[0.90]` yap, yorumu:
```python
    # 0.90 olasılığı 0.52 eşiğini rahatça geçer.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.90]))
```

`test_tam_esik_degeri_dahil_edilir` — skoru `[0.0]` yerine `[0.52]` yap, yorumu:
```python
    # Skor eşiğe tam eşit; karşılaştırma >= olduğu için dahil edilmeli.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.52]))
```

`test_dokumanlar_skora_gore_siralanir` — skorları `[1.0, 9.0]` yerine
`[0.60, 0.95]` yap, yorumu:
```python
    # İkinci doküman daha yüksek olasılık alıyor; çıktıda önce o gelmeli.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.60, 0.95]))
```

`test_dokuman_kaynagi_ciktiya_eklenir` — skoru `[10.0]` yerine `[0.90]` yap.

Dosyanın SONUNA yeni testi ekle:

```python
def test_reranker_skoru_ikinci_kez_ezilmez(monkeypatch):
    # CrossEncoder.predict() modelin Sigmoid aktivasyonunu zaten uyguluyor.
    # Kod bunu ikinci kez sigmoid'den geçirirse 0.90 skoru 0.711'e düşer ve
    # 0.80 eşiğini geçemez — dokuman sessizce elenir. Bu test o davranışı
    # dondurur: skor ne verildiyse o sayılmalı.
    monkeypatch.setattr(rag_service, "get_reranker", sahte_reranker_uret([0.90]))
    koleksiyon = SahteKoleksiyon(["Yanık protokolü"])

    sonuc = rag_service.retrieve_and_rerank(
        query="kaynar su döküldü", collection=koleksiyon, threshold=0.80
    )

    assert len(sonuc) == 1
```

- [ ] **Step 3: Testleri çalıştır, kırmızı olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/birim/test_rag_esik_kapisi.py -v --no-cov
```
Beklenen: `test_esik_altinda_bos_liste_doner` ve
`test_reranker_skoru_ikinci_kez_ezilmez` FAIL. Diğerleri geçebilir — sigmoid
monotonik olduğu için sıralama ve pozitif yol testleri her iki kodda da geçiyor.
Raporunda bu çıktıyı birebir göster.

- [ ] **Step 4: Aktivasyonu açıkça kur ve çift sigmoidi kaldır**

`app/services/rag_service.py` içinde `get_reranker`'ı şununla değiştir:

```python
def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        logger.info(f"Reranker yükleniyor: {settings.reranker_model} ({device})")
        # Aktivasyon açıkça veriliyor: predict()'in olasılık döndürmesi aksi hâlde
        # modelin config dosyasına bağlı kalır. Model ya da kütüphane varsayılanı
        # değişirse predict() sessizce ham logit döndürür ve her eşik anlamsızlaşır.
        _reranker = CrossEncoder(
            settings.reranker_model,
            device=device,
            activation_fn=torch.nn.Sigmoid(),
        )
    return _reranker
```

`calculate_sigmoid` fonksiyonunu (satır 26-30) **tamamen sil**.

`retrieve_and_rerank` içindeki satır 66-67'yi şununla değiştir:

```python
    # predict() olasılık döndürüyor (aktivasyon yukarıda açıkça kuruldu);
    # ikinci bir dönüşüm uygulanmıyor.
    skorlar = [float(skor) for skor in get_reranker().predict(pairs)]

    scored_docs = list(zip(skorlar, documents, metadatas))
```

- [ ] **Step 5: `kalibre_esik.py`'yi güncelle**

Satır 21'deki import'u `from app.services.rag_service import get_reranker` yap
(`calculate_sigmoid` çıkar). Satır 93'teki dönüşü şununla değiştir:

```python
    return max(float(s) for s in ham_skorlar)
```

Aynı fonksiyondaki `ham_skorlar` değişken adını `skorlar` yap ve üstüne şu yorumu
ekle: `# predict() olasılık döndürüyor; ek dönüşüm yok.`

- [ ] **Step 6: Testleri çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/birim/test_rag_esik_kapisi.py -v --no-cov
```
Beklenen: `7 passed`.

- [ ] **Step 7: `calculate_sigmoid` depoda kalmadığını doğrula**

```bash
git grep -n calculate_sigmoid || echo "HIC GECMIYOR"
```
Beklenen: `HIC GECMIYOR`. (`git grep` eşleşme bulamayınca 1 döndürür, bu yüzden
`||` ile mesaj basılıyor.)

- [ ] **Step 8: Tüm paketi çalıştır**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: `100 passed`.

- [ ] **Step 9: Commit**

```bash
git add app/services/rag_service.py scripts/kalibre_esik.py tests/birim/test_rag_esik_kapisi.py tests/yardimcilar/sahte_rag.py
git commit -m "fix: reranker skoru ikinci kez sigmoidden gecirilmiyor (99 -> 100)"
```

---

### Task 2: Çok dilli gömme modeli ve yeniden kurma scripti

**Files:**
- Modify: `app/config/config.py`
- Modify: `app/services/chroma_service.py`
- Create: `tests/birim/test_chroma_service.py`
- Create: `scripts/bilgi_tabani_kur.py`

**Interfaces:**
- Consumes: `settings` (`app/config/config.py`)
- Produces: `settings.embedding_model`, `chroma_service._gomme_fonksiyonu()`,
  `chroma_service._collection` (modül düzeyi tekil — testler sıfırlamak zorunda)

- [ ] **Step 1: Testi yaz**

`tests/birim/test_chroma_service.py` (yeni dosya):

```python
"""Koleksiyonun ayarlardaki çok dilli gömme modeliyle açıldığını dondurur.

ChromaDB'nin varsayılan gömme modeli İngilizcedir; Türkçe sorguda anlamsız vektör
üretir ve reranker doğru dokümanı hiç görmez. Bu test o varsayılana geri
dönülmesini engeller.
"""

import pytest

from app.config.config import settings
from app.services import chroma_service


class _SahteGomme:
    """SentenceTransformerEmbeddingFunction yerine geçer; model adını kaydeder."""

    def __init__(self, model_name):
        self.model_name = model_name


class _SahteIstemci:
    """chromadb.HttpClient yerine geçer; koleksiyon çağrısının kwargs'ını tutar."""

    def __init__(self, **kwargs):
        self.kurulum = kwargs
        self.koleksiyon_kwargs = None

    def get_or_create_collection(self, **kwargs):
        self.koleksiyon_kwargs = kwargs
        return object()


@pytest.fixture
def sahte_chromadb(monkeypatch):
    """Gerçek ChromaDB'ye ve gerçek modele hiç dokunmadan get_collection'ı izler."""
    olusan = {}

    def _istemci_uret(**kwargs):
        olusan["istemci"] = _SahteIstemci(**kwargs)
        return olusan["istemci"]

    monkeypatch.setattr(chroma_service.chromadb, "HttpClient", _istemci_uret)
    monkeypatch.setattr(
        chroma_service.embedding_functions,
        "SentenceTransformerEmbeddingFunction",
        _SahteGomme,
    )
    # Modül düzeyindeki tekil önceki testten dolu kalmış olabilir.
    monkeypatch.setattr(chroma_service, "_collection", None)
    return olusan


def test_gomme_modeli_ayarlardan_okunur(sahte_chromadb):
    chroma_service.get_collection()

    kwargs = sahte_chromadb["istemci"].koleksiyon_kwargs
    gomme = kwargs["embedding_function"]
    assert isinstance(gomme, _SahteGomme)
    assert gomme.model_name == settings.embedding_model
```

- [ ] **Step 2: Testleri çalıştır, kırmızı olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/birim/test_chroma_service.py -v --no-cov
```
Beklenen: FAIL — `chroma_service` içinde `embedding_functions` niteliği yok,
`AttributeError` alınır.

- [ ] **Step 3: Ayarı ekle**

`app/config/config.py` içinde `reranker_model` satırının ALTINA ekle:

```python
    # Gömme modeli çok dilli olmalı: ChromaDB'nin varsayılanı (all-MiniLM-L6-v2)
    # yalnızca İngilizce ve Türkçe sorguda anlamsız vektör üretiyor.
    embedding_model: str = "BAAI/bge-m3"
```

- [ ] **Step 4: `chroma_service`'i güncelle**

`app/services/chroma_service.py` dosyasının TAMAMINI şununla değiştir:

```python
import chromadb
from chromadb.utils import embedding_functions

from app.config.config import settings

# Ayarlar pydantic-settings üzerinden okunuyor: önce ortam değişkenleri
# (Docker Compose bunları veriyor), yoksa .env dosyası, o da yoksa varsayılan.

# Bağlantı tembel kuruluyor: import anında kurulursa ChromaDB kapalıyken
# uygulama hiç açılmıyordu (/health bile cevap vermiyordu). Desen
# rag_service.py içindeki get_reranker() ile aynı.
_collection = None


def _gomme_fonksiyonu():
    """Ayarlardaki çok dilli modelden gömme fonksiyonu kurar.

    Açıkça veriliyor çünkü ChromaDB'nin varsayılanı all-MiniLM-L6-v2 (İngilizce);
    Türkçe sorguda ayırt edici olmayan vektör üretip yanlış dokümanları getiriyor.
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model
    )


def get_collection():
    global _collection
    if _collection is None:
        chroma_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        _collection = chroma_client.get_or_create_collection(
            name="triage_documents",
            embedding_function=_gomme_fonksiyonu(),
        )
    return _collection
```

- [ ] **Step 5: Testleri çalıştır, yeşil olduğunu gör**

```
.venv\Scripts\python.exe -m pytest tests/birim/test_chroma_service.py -v --no-cov
```
Beklenen: `1 passed`.

- [ ] **Step 6: Yeniden kurma scriptini yaz**

`scripts/bilgi_tabani_kur.py` (yeni dosya):

```python
"""Bilgi tabanını sıfırdan kurar: koleksiyonu düşürüp derlemeyi yeniden yükler.

Gömme modeli değiştiğinde ZORUNLUDUR: eski vektörler farklı bir modelle üretildiği
için yeni sorgu vektörleriyle karşılaştırılamaz. Derleme değiştiğinde de temiz bir
başlangıç için kullanılır.

Backend'in ayakta olması gerekir; yükleme gerçek /document/upload ucundan geçer.

Kullanım (proje kökünden):
    .venv\\Scripts\\python.exe scripts/bilgi_tabani_kur.py
"""

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import chromadb
import requests

from app.config.config import settings
from app.services.auth_service import create_access_token

BACKEND = "http://localhost:8000"
DERLEME = Path(__file__).resolve().parent.parent / "ornek_dokumanlar" / "protokoller"
KATEGORI = "protokol"
KOLEKSIYON = "triage_documents"


def yonetici_basligi():
    """Admin jetonunu uygulamanın kendi imzalama fonksiyonuyla üretir."""
    return {"Authorization": f"Bearer {create_access_token({'sub': 'admin', 'role': 'admin'})}"}


def koleksiyonu_dusur():
    """Eski vektörleri tamamen siler; yeni model farklı bir anlam uzayı kullanıyor."""
    istemci = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    try:
        istemci.delete_collection(KOLEKSIYON)
        print(f"koleksiyon dusuruldu: {KOLEKSIYON}")
    except Exception as hata:
        print(f"koleksiyon dusurulemedi (muhtemelen yoktu): {type(hata).__name__}")


def main() -> None:
    dosyalar = [p for p in sorted(DERLEME.glob("*.txt")) if not p.name.startswith("_")]
    if not dosyalar:
        print(f"Derleme bos: {DERLEME}")
        sys.exit(1)

    print(f"Gomme modeli: {settings.embedding_model}")
    print(f"Derleme      : {len(dosyalar)} dosya\n")

    koleksiyonu_dusur()

    baslik = yonetici_basligi()
    toplam = 0
    hata = 0
    for yol in dosyalar:
        with yol.open("rb") as f:
            yanit = requests.post(
                f"{BACKEND}/document/upload",
                data={"category": KATEGORI},
                files={"file": (yol.name, f, "text/plain")},
                headers=baslik,
                timeout=300,
            )
        if yanit.status_code == 201:
            n = yanit.json()["total_chunks"]
            toplam += n
            print(f"  OK   {yol.name:<30} {n:>3} chunk")
        else:
            hata += 1
            print(f"  HATA {yol.name:<30} {yanit.status_code} {yanit.text[:120]}")

    print(f"\nToplam: {len(dosyalar) - hata} dosya, {toplam} chunk, {hata} hata")
    if hata:
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Tüm paketi çalıştır**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: `101 passed`.

**Script'i ÇALIŞTIRMA** — bilgi tabanını yeniden kurmak kontrolcünün işi, çünkü
backend'in yeni kodla yeniden başlatılmış olması gerekiyor.

- [ ] **Step 8: Commit**

```bash
git add app/config/config.py app/services/chroma_service.py tests/birim/test_chroma_service.py scripts/bilgi_tabani_kur.py
git commit -m "feat: cok dilli gomme modeli (bge-m3) ve bilgi tabani kurma scripti (100 -> 101)"
```

---

### Task 3: Türkçe retrieval entegrasyon testi

**Files:**
- Create: `tests/entegrasyon/test_turkce_retrieval.py`

**Interfaces:**
- Consumes: `settings.embedding_model`, `chroma_service._gomme_fonksiyonu` (Görev 2)
- Produces: üretim kodunda yeni ad yok.

- [ ] **Step 1: Testi yaz**

`tests/entegrasyon/test_turkce_retrieval.py` (yeni dosya):

```python
"""Türkçe sorgunun doğru protokolü getirdiğini gerçek gömme modeliyle sınar.

Bu testin var oluş sebebi somut: ChromaDB'nin varsayılan İngilizce gömme modeli
kullanılırken "kaynar su döküldü" sorgusu yanık protokolünü ilk beşe bile
sokamıyordu, ama hiçbir test bunu görmüyordu — çünkü gerçek modelle Türkçe
retrieval'ı sınayan test yoktu.

`yavas` işaretli: gerçek bge-m3 modelini yükler ve ChromaDB ister.
"""

import uuid
from pathlib import Path

import chromadb
import pytest

from app.config.config import settings
from app.services.chroma_service import _gomme_fonksiyonu

DERLEME = Path(__file__).resolve().parent.parent.parent / "ornek_dokumanlar" / "protokoller"


@pytest.fixture
def gecici_koleksiyon():
    """Testin kendi koleksiyonunu kurar; canlı triage_documents'a dokunulmaz."""
    istemci = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    ad = f"test_turkce_retrieval_{uuid.uuid4().hex[:8]}"
    koleksiyon = istemci.create_collection(name=ad, embedding_function=_gomme_fonksiyonu())
    try:
        yield koleksiyon
    finally:
        istemci.delete_collection(ad)


@pytest.mark.yavas
def test_turkce_sorgu_dogru_protokolu_getirir(gecici_koleksiyon):
    # Üç protokol yükleniyor; hasta ağzından yazılmış sorgu doğru olanı bulmalı.
    dosyalar = ["yanik.txt", "inme.txt", "psikiyatrik_aciller.txt"]
    gecici_koleksiyon.add(
        documents=[(DERLEME / ad).read_text(encoding="utf-8") for ad in dosyalar],
        metadatas=[{"source": ad} for ad in dosyalar],
        ids=list(dosyalar),
    )

    sonuc = gecici_koleksiyon.query(
        query_texts=["Kaynar su elimin üstüne döküldü, hemen su topladı."],
        n_results=1,
    )

    assert sonuc["metadatas"][0][0]["source"] == "yanik.txt"
```

- [ ] **Step 2: Testi çalıştır**

```
.venv\Scripts\python.exe -m pytest tests/entegrasyon/test_turkce_retrieval.py -v --no-cov -m yavas
```
Beklenen: `1 passed`. İlk koşuda bge-m3 indirilir (~2.2 GB), dakikalar sürebilir.

**Bu test kırmızıdan başlamıyor** — Görev 2 gömme modelini zaten düzeltti. Bu bir
sorun değil, ama "kırmızı görüldü" iddiası edilemez. Bunun yerine **bağlayıcı
olduğunu mutasyonla kanıtla:** `app/config/config.py` içindeki `embedding_model`
değerini geçici olarak `"all-MiniLM-L6-v2"` yap, testi koş, KIRMIZI olduğunu gör,
sonra GERİ AL ve tekrar yeşil olduğunu doğrula.

Raporunda üç çıktıyı da ve `git diff -- app/config/config.py` çıktısının boş
olduğunu göster.

- [ ] **Step 3: Normal paketin etkilenmediğini doğrula**

```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings
```
Beklenen: `101 passed` (yavaş test atlanır), kapsama %80'in altına düşmemeli.

- [ ] **Step 4: Commit**

```bash
git add tests/entegrasyon/test_turkce_retrieval.py
git commit -m "test: turkce sorgu dogru protokolu getiriyor (yavas, gercek bge-m3)"
```

---

## Görevler bittikten sonra: doğrulama

Kontrolcü tarafından yürütülür.

- [ ] **Otomatik**

```
.venv\Scripts\python.exe -m pytest -m "not yavas"
```
`101 passed`, kapsama %80'in altına düşmemeli.

- [ ] **Backend'i yeni kodla yeniden başlat**

Eski süreç bayat kodu çalıştırıyor; yeni gömme modeli devreye girmez.

- [ ] **Bilgi tabanını yeniden kur**

```
.venv\Scripts\python.exe scripts/bilgi_tabani_kur.py
```
Beklenen: 15 dosya, 48 chunk, 0 hata. İlk koşuda bge-m3 indirilir.

- [ ] **Retrieval'ın gerçekten düzeldiğini elle gör**

Gün 20'de kırık olduğu kanıtlanan iki sorguyu tekrarla:
`"Kaynar su elimin üstüne döküldü"` → `yanik.txt` ilk sırada olmalı;
`"Annemin yüzü düştü, kolunu kaldıramıyor, konuşması bozuk"` → `inme.txt` ilk
sırada olmalı. Düzeltme öncesi ikisi de ilk beşte bile yoktu.

- [ ] **Kalibrasyonu yeniden koş**

```
.venv\Scripts\python.exe scripts/kalibre_esik.py
```
Yeni skor dağılımını kaydet. Ölçüm temiz ayrım veriyorsa öneriyi
`app/config/config.py` → `rerank_threshold`'a yaz ve paketi tekrar koş. Ayrım temiz
değilse eşiği DEĞİŞTİRME, bulguyu kaydet (K7).

---

## Bitti sayılır

- [ ] Üç yeni test yeşil (ikisi hızlı, biri `yavas`); `test_rag_esik_kapisi.py` olasılık ölçeğinde
- [ ] Mevcut 99 test hâlâ yeşil; `-m "not yavas"` toplamı 99 → **101** (artı 1 `yavas` test)
- [ ] `calculate_sigmoid` depoda hiç geçmiyor
- [ ] `test_reranker_skoru_ikinci_kez_ezilmez` ve `test_esik_altinda_bos_liste_doner`
      eski kodda kırmızı olduğu ÇALIŞTIRILARAK görüldü
- [ ] `test_turkce_sorgu_dogru_protokolu_getirir` mutasyonla bağlayıcı kanıtlandı
- [ ] Bilgi tabanı bge-m3 ile yeniden kuruldu: 15 dosya, 48 chunk
- [ ] İki kırık sorgu artık doğru protokolü getiriyor
- [ ] Kalibrasyon koşuldu; eşik ya yazıldı ya da yazılmama gerekçesi kaydedildi
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
