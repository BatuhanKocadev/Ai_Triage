# Gün 20 — Bilgi Tabanı Yönetimi Uygulama Planı

> **Ajan çalışanlar için:** ZORUNLU ALT BECERİ: Bu planı görev görev uygulamak için
> superpowers:subagent-driven-development kullanın. Adımlar takip için checkbox
> (`- [ ]`) sözdizimi kullanır.

**Hedef:** Bilgi tabanının içeriğini görülebilir ve düzeltilebilir kılmak; yeniden
yüklemenin geride hayalet chunk bırakmasını durdurmak.

**Mimari:** `app/api/document.py`'ye iki uç ekleniyor (`GET /document/liste`,
`DELETE /document`) ve mevcut `upload` sil-sonra-yaz yapacak şekilde düzeltiliyor.
Testler gerçek ChromaDB'ye hiç dokunmuyor: `tests/yardimcilar/sahte_chroma.py`
altında bellek içi bir sahte koleksiyon yazılıyor ve `app.api.document.get_collection`
yamalanıyor.

**Teknoloji:** FastAPI, ChromaDB (yalnızca arayüzü taklit ediliyor), pytest.

**Tasarım dokümanı:** `docs/superpowers/specs/2026-08-04-gun20-bilgi-tabani-yonetimi-design.md`
— çelişkide o belge kazanır, kararlar K1–K9 numaralarıyla oradadır.

## Global Constraints

Aşağıdakiler her görevin gereksinimlerine dahildir; ayrıca tekrarlanmaz.

- **Türkçe açıklama zorunlu.** Eklenen her fonksiyon, blok ve yeni yapının yanına tek
  cümlelik Türkçe yorum. Kod tabanı ve API alan adları Türkçedir.
- **Test adları birebir uygulanır.** Sekiz testin adı tasarım dokümanından gelir,
  değiştirilemez.
- **Saf TDD.** Her görevde önce test yazılır, kırmızı olduğu ÇALIŞTIRILARAK görülür,
  sonra üretim kodu yazılır.
- **Mevcut 90 test yeşil kalmalı.** Taban çizgisi `main` üzerinde ölçüldü: `90 passed`,
  `app/` kapsaması %75.
- **Hiçbir test gerçek `triage_documents` koleksiyonuna dokunamaz.** Bu koleksiyon her
  hasta sorgusunun tarandığı yer. Monkeypatch **adın arandığı ad alanına** uygulanır:
  `app.api.document.get_collection` — `app.services.chroma_service` değil.
- **Python komutu her zaman:**
  `C:\Users\batuh\Desktop\Ai_Triage-myself\.venv\Scripts\python.exe`
- **PostgreSQL ayakta olmalı.** `entegrasyon` işaretli testler `ai_triage_test`
  veritabanını ister; konteyner `ai_triage_postgres` çalışıyor.
- **Commit mesajları ASCII.** Kod ve arayüz metinlerinde Türkçe karakter beklenir.
- **`app/api/document.py` tek dosyadır — paralel subagent YOK.** Görev 1, 2 ve 3
  sırayla koşar.

---

## Dosya Yapısı

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `tests/yardimcilar/sahte_chroma.py` | **YENİ** — bellek içi sahte koleksiyon | 1 |
| `tests/api/test_document_api.py` | **YENİ** — doküman uçlarının testleri | 1, 2, 3 |
| `app/api/document.py` | `GET /liste` ucu | 1 |
| `app/api/document.py` | `DELETE` ucu | 2 |
| `app/api/document.py` | `upload` sil-sonra-yaz düzeltmesi | 3 |

---

### Task 1: Sahte koleksiyon ve listeleme ucu

**Files:**
- Create: `tests/yardimcilar/sahte_chroma.py`
- Create: `tests/api/test_document_api.py`
- Modify: `app/api/document.py` (dosya sonuna yeni uç)

**Interfaces:**
- Consumes: `istemci`, `yetkili_baslik` (`tests/conftest.py`), `require_admin_role`
  ve `get_collection` (`app/api/document.py` içinde zaten import edilmiş)
- Produces: `SahteKoleksiyon` sınıfı (`upsert` / `get` / `delete` / `sayac`),
  `sahte_koleksiyon` fixture'ı ve `_chunk_ekle` yardımcısı — Görev 2 ve 3 bunları
  aynen kullanacak, yeniden tanımlamayacak.

- [ ] **Step 1: Sahte koleksiyonu yaz**

`tests/yardimcilar/sahte_chroma.py` (yeni dosya):

```python
"""ChromaDB koleksiyonu yerine geçen bellek içi sahte servis.

Gerçek `triage_documents` koleksiyonu her hasta sorgusunun tarandığı yerdir;
testlerin oraya yazması üretim davranışını bozar. Bu sınıf yalnızca doküman
uçlarının kullandığı yöntemleri taklit eder.
"""


class SahteKoleksiyon:
    """Kayıtları bellekte tutan, ChromaDB koleksiyon arayüzünün küçük bir taklidi."""

    def __init__(self):
        # id -> {"document": metin, "metadata": üstveri}
        self._kayitlar = {}

    def upsert(self, documents, metadatas, ids):
        """Verilen id'leri yazar; var olanın üzerine yazar, diğerlerine dokunmaz."""
        for belge, ustveri, kimlik in zip(documents, metadatas, ids):
            self._kayitlar[kimlik] = {"document": belge, "metadata": dict(ustveri)}

    def get(self, where=None, include=None):
        """Kayıtları döndürür; `where` verilirse eşitlik filtresi uygular."""
        kimlikler, ustveriler, belgeler = [], [], []
        for kimlik, kayit in self._kayitlar.items():
            if where and not self._eslesiyor(kayit["metadata"], where):
                continue
            kimlikler.append(kimlik)
            ustveriler.append(kayit["metadata"])
            belgeler.append(kayit["document"])
        return {"ids": kimlikler, "metadatas": ustveriler, "documents": belgeler}

    def delete(self, ids=None, where=None):
        """Verilen id'leri ya da `where` ile eşleşen kayıtları siler."""
        if ids is not None:
            for kimlik in ids:
                self._kayitlar.pop(kimlik, None)
            return
        if where is not None:
            silinecek = [
                kimlik
                for kimlik, kayit in self._kayitlar.items()
                if self._eslesiyor(kayit["metadata"], where)
            ]
            for kimlik in silinecek:
                self._kayitlar.pop(kimlik, None)

    def sayac(self):
        """Testlerin toplam kayıt sayısını okuması için."""
        return len(self._kayitlar)

    @staticmethod
    def _eslesiyor(ustveri, where):
        """Basit eşitlik filtresi — üretimde yalnızca {"source": ad} kullanılıyor."""
        return all(ustveri.get(anahtar) == deger for anahtar, deger in where.items())
```

- [ ] **Step 2: Test dosyasını ve dört testi yaz**

`tests/api/test_document_api.py` (yeni dosya):

```python
"""Doküman uçlarının testleri: listeleme, silme ve yeniden yükleme davranışı."""

import pytest

from app.api import document as document_modulu
from tests.yardimcilar.sahte_chroma import SahteKoleksiyon


@pytest.fixture
def sahte_koleksiyon(monkeypatch):
    """Doküman uçlarını bellek içi sahte koleksiyona bağlar.

    Yamalama adın arandığı ad alanına uygulanıyor (`app.api.document`), adı
    tanımlayan `chroma_service`'e değil — uç modülü adı kendi ad alanına almış.
    """
    koleksiyon = SahteKoleksiyon()
    monkeypatch.setattr(document_modulu, "get_collection", lambda: koleksiyon)
    return koleksiyon


def _chunk_ekle(koleksiyon, kaynak, adet, kategori="protokol", tarih="2026-08-04"):
    """Sahte koleksiyona bir dosyaya ait `adet` kadar chunk yazar."""
    koleksiyon.upsert(
        documents=[f"{kaynak} parça {i}" for i in range(adet)],
        metadatas=[
            {
                "source": kaynak,
                "upload_date": tarih,
                "category": kategori,
                "chunk_index": i,
            }
            for i in range(adet)
        ],
        ids=[f"{kaynak}_chunk_{i}" for i in range(adet)],
    )


@pytest.mark.entegrasyon
def test_liste_dokumanlari_kaynak_bazinda_gruplar(istemci, sahte_koleksiyon, yetkili_baslik):
    # Panelin ve yol haritasının "yüklenen doküman sayısı" metriği bu uçtan
    # okunuyor; gruplama bozulursa sayı sessizce yanlış çıkar.
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 8)
    _chunk_ekle(sahte_koleksiyon, "karin_agrisi.txt", 6)

    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 200
    kayitlar = {k["kaynak"]: k for k in yanit.json()}
    assert kayitlar["gogus_agrisi.txt"]["chunk_sayisi"] == 8
    assert kayitlar["karin_agrisi.txt"]["chunk_sayisi"] == 6
    assert kayitlar["gogus_agrisi.txt"]["kategori"] == "protokol"
    assert kayitlar["gogus_agrisi.txt"]["yukleme_tarihi"] == "2026-08-04"


@pytest.mark.entegrasyon
def test_liste_bos_koleksiyonda_bos_liste_doner(istemci, sahte_koleksiyon, yetkili_baslik):
    # "Hiç doküman yok" bir hata değil, geçerli bir durum (K3). Sıfır da bir ölçümdür.
    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 200
    assert yanit.json() == []


@pytest.mark.entegrasyon
def test_liste_kaynak_adina_gore_siralanir(istemci, sahte_koleksiyon, yetkili_baslik):
    # ChromaDB get() dönüş sırası garanti değil; ekleme sırası kasıtlı olarak
    # alfabetik değil ve uç yine de belirlenimci sıra vermeli (K4).
    _chunk_ekle(sahte_koleksiyon, "zehirlenme.txt", 2)
    _chunk_ekle(sahte_koleksiyon, "anafilaksi.txt", 2)
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 2)

    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    adlar = [k["kaynak"] for k in yanit.json()]
    assert adlar == ["anafilaksi.txt", "gogus_agrisi.txt", "zehirlenme.txt"]


@pytest.mark.entegrasyon
def test_user_rolu_listeye_403_alir(istemci, sahte_koleksiyon, yetkili_baslik):
    # Bağımlılığı izole sınamak, UCUN onu kullandığını kanıtlamaz — Gün 17+18'de
    # ölçülen desen. Bu test doğrudan uca gidiyor.
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 3)

    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="hasta_ayse", rol="user"),
    )

    assert yanit.status_code == 403
```

- [ ] **Step 3: Testleri çalıştır, kırmızı olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_document_api.py -v --no-cov
```
Beklenen: dördü de FAIL. Üçü `404 != 200` (uç yok), yetki testi de `404 != 403`.
Raporunda bu çıktıyı göster.

- [ ] **Step 4: Listeleme ucunu yaz**

`app/api/document.py` dosyasının SONUNA ekle:

```python
@router.get("/liste")
async def dokumanlari_listele(
    current_user: User = Depends(require_admin_role)
):
    """Yüklenen dokümanları kaynak dosya adına göre gruplayıp döndürür.

    Bilgi tabanında ne olduğunu görmenin tek yolu bu uç; yol haritasının
    "yüklenen doküman sayısı" metriği buradan okunuyor.
    """
    kayitlar = get_collection().get(include=["metadatas"])
    ustveriler = kayitlar.get("metadatas") or []

    # Dosya adı -> o dosyaya ait chunk'ların üstverileri
    gruplar: dict[str, list[dict]] = {}
    for ustveri in ustveriler:
        kaynak = (ustveri or {}).get("source")
        if kaynak is None:
            continue  # kaynağı olmayan kayıt listelenemez
        gruplar.setdefault(kaynak, []).append(ustveri)

    liste = []
    for kaynak, parcalar in gruplar.items():
        # Kategori ve tarih, chunk_index'i en küçük olan parçadan okunuyor:
        # üstveri tutarsız olsa bile çıktı rastgele değişmesin (K8).
        ilk = min(parcalar, key=lambda u: u.get("chunk_index", 0))
        liste.append({
            "kaynak": kaynak,
            "chunk_sayisi": len(parcalar),
            "kategori": ilk.get("category"),
            "yukleme_tarihi": ilk.get("upload_date"),
        })

    # Belirlenimci sıra (K4): ChromaDB get() dönüş sırasını garanti etmiyor.
    liste.sort(key=lambda kayit: kayit["kaynak"])
    return liste
```

- [ ] **Step 5: Testleri çalıştır, yeşil olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_document_api.py -v --no-cov
```
Beklenen: `4 passed`.

- [ ] **Step 6: Tüm paketi çalıştır**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: `94 passed`.

- [ ] **Step 7: Commit**

```bash
git add tests/yardimcilar/sahte_chroma.py tests/api/test_document_api.py app/api/document.py
git commit -m "feat: GET /document/liste ucu ve bellek ici sahte koleksiyon (90 -> 94)"
```

---

### Task 2: Silme ucu

**Files:**
- Modify: `tests/api/test_document_api.py` (dosya sonuna 3 test)
- Modify: `app/api/document.py` (dosya sonuna yeni uç, `Query` import'u eklenir)

**Interfaces:**
- Consumes: `sahte_koleksiyon` fixture'ı ve `_chunk_ekle` yardımcısı (Görev 1'de
  tanımlandı, yeniden tanımlanmaz)
- Produces: `DELETE /document?kaynak=<ad>` ucu — Görev 3 bunu kullanmaz ama aynı
  `delete(where=...)` çağrısını paylaşır.

- [ ] **Step 1: Üç testi yaz**

`tests/api/test_document_api.py` dosyasının SONUNA ekle:

```python
@pytest.mark.entegrasyon
def test_silme_dosyanin_tum_chunklarini_siler(istemci, sahte_koleksiyon, yetkili_baslik):
    # Yanlış yüklenen bir dosyayı kaldırmanın tek yolu bu uç.
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 8)
    _chunk_ekle(sahte_koleksiyon, "karin_agrisi.txt", 6)

    yanit = istemci.delete(
        "/document",
        params={"kaynak": "gogus_agrisi.txt"},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 200
    assert yanit.json()["silinen_chunk"] == 8
    # Diğer dosyaya dokunulmadığı da kanıtlanıyor.
    assert sahte_koleksiyon.sayac() == 6


@pytest.mark.entegrasyon
def test_olmayan_dosya_silinince_404_doner(istemci, sahte_koleksiyon, yetkili_baslik):
    # Yanlış dosya adı yazan yönetici bunu bilmeli; sessiz başarı yanıltır (K6).
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 3)

    yanit = istemci.delete(
        "/document",
        params={"kaynak": "olmayan.txt"},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 404
    assert sahte_koleksiyon.sayac() == 3


@pytest.mark.entegrasyon
def test_user_rolu_silmeye_403_alir(istemci, sahte_koleksiyon, yetkili_baslik):
    _chunk_ekle(sahte_koleksiyon, "gogus_agrisi.txt", 3)

    yanit = istemci.delete(
        "/document",
        params={"kaynak": "gogus_agrisi.txt"},
        headers=yetkili_baslik(kullanici_adi="hasta_ayse", rol="user"),
    )

    assert yanit.status_code == 403
    # Yetki reddedilirken hiçbir şey silinmemiş olmalı: kapı gövdeden önce durmalı.
    assert sahte_koleksiyon.sayac() == 3
```

- [ ] **Step 2: Testleri çalıştır, kırmızı olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_document_api.py -v --no-cov
```
Beklenen: `4 passed, 3 failed` — Görev 1'in dört testi yeşil kalır, yeni üç test
FAIL eder (`/document` yolunda hiç route yok, `404` dönecek).

- [ ] **Step 3: `Query` import'unu ekle**

`app/api/document.py:1` satırını şununla değiştir:

```python
from fastapi import APIRouter, UploadFile, File, Form, status, HTTPException, Depends, Query
```

- [ ] **Step 4: Silme ucunu yaz**

`app/api/document.py` dosyasının SONUNA ekle:

```python
@router.delete("")
async def dokumani_sil(
    kaynak: str = Query(..., min_length=1, description="Silinecek dosyanın adı"),
    current_user: User = Depends(require_admin_role)
):
    """Bir dosyaya ait bütün chunk'ları bilgi tabanından siler.

    Dosya adı yol parametresi değil sorgu parametresi olarak alınıyor (K2):
    dosya adlarında nokta, boşluk ve Türkçe karakter var.
    """
    koleksiyon = get_collection()
    mevcut = koleksiyon.get(where={"source": kaynak})
    silinecek = mevcut.get("ids") or []

    if not silinecek:
        raise HTTPException(status_code=404, detail="Doküman bulunamadı")

    koleksiyon.delete(where={"source": kaynak})
    logger.info(
        f"Dokuman silindi: {kaynak} ({len(silinecek)} chunk) by {current_user.username}"
    )
    return {"silinen_chunk": len(silinecek)}
```

- [ ] **Step 5: Testleri çalıştır, yeşil olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_document_api.py -v --no-cov
```
Beklenen: `7 passed`.

- [ ] **Step 6: Tüm paketi çalıştır**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: `97 passed`.

- [ ] **Step 7: Commit**

```bash
git add tests/api/test_document_api.py app/api/document.py
git commit -m "feat: DELETE /document ucu, dosyanin tum chunklarini siler (94 -> 97)"
```

---

### Task 3: Yeniden yüklemenin hayalet chunk bırakmasını durdur

**Files:**
- Modify: `tests/api/test_document_api.py` (dosya sonuna 1 test)
- Modify: `app/api/document.py:125-129` (upsert bloğu)

**Interfaces:**
- Consumes: `sahte_koleksiyon` fixture'ı (Görev 1)
- Produces: üretim kodunda yeni ad yok — yalnızca `upload`'ın yan etkisi değişiyor.
  Uç sözleşmesi (istek gövdesi, yanıt gövdesi, durum kodu) aynı kalır.

- [ ] **Step 1: Regresyon testini yaz**

`tests/api/test_document_api.py` dosyasının SONUNA ekle:

```python
@pytest.mark.entegrasyon
def test_yeniden_yukleme_eski_chunklari_birakmaz(istemci, sahte_koleksiyon, yetkili_baslik):
    # upsert yalnızca kendisine verilen id'lere dokunur. Daha kısa bir sürüm
    # yüklendiğinde eski sürümün fazla chunk'ları koleksiyonda kalırsa sistem
    # silinmiş bir metinden alıntı yapar ve sources onu hâlâ bu dosyaya bağlar —
    # yani izlenebilirlik iddiası sessizce yalanlanır.
    baslik = yetkili_baslik(kullanici_adi="yonetici", rol="admin")
    uzun_metin = ("Gogus agrisi protokolu. " * 400).encode("utf-8")
    kisa_metin = "Gogus agrisi protokolu kisa surum.".encode("utf-8")

    ilk = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("gogus_agrisi.txt", uzun_metin, "text/plain")},
        headers=baslik,
    )
    assert ilk.status_code == 201
    # Test anlamlı olsun diye: ilk yükleme gerçekten çok parçaya bölünmeli.
    assert ilk.json()["total_chunks"] > 1

    ikinci = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("gogus_agrisi.txt", kisa_metin, "text/plain")},
        headers=baslik,
    )
    assert ikinci.status_code == 201
    ikinci_chunk_sayisi = ikinci.json()["total_chunks"]

    # Koleksiyonda yalnızca ikinci sürümün chunk'ları kalmalı.
    assert sahte_koleksiyon.sayac() == ikinci_chunk_sayisi
```

- [ ] **Step 2: Testi çalıştır, kırmızı olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_document_api.py::test_yeniden_yukleme_eski_chunklari_birakmaz -v --no-cov
```
Beklenen: FAIL. Son satırdaki karşılaştırma `assert N == M` biçiminde patlayacak;
burada `N` ilk (uzun) yüklemenin chunk sayısı, `M` ikinci (kısa) yüklemeninki ve
`N > M`. Aradaki fark, koleksiyonda kalan hayalet chunk sayısıdır — hatanın
doğrudan ölçüsü. Raporunda bu çıktıyı **birebir** göster.

- [ ] **Step 3: Sil-sonra-yaz düzeltmesini uygula**

`app/api/document.py` içindeki şu bloğu:

```python
        get_collection().upsert(
            documents=text_chunks,
            metadatas=metadata_list,
            ids=id_list
        )
```

şununla değiştir:

```python
        koleksiyon = get_collection()

        # Aynı dosyanın eski chunk'ları önce siliniyor (K5). upsert yalnızca
        # kendisine verilen id'lere dokunduğu için, daha kısa bir sürüm
        # yüklendiğinde eski sürümün fazla chunk'ları koleksiyonda kalıyordu.
        koleksiyon.delete(where={"source": file.filename})

        koleksiyon.upsert(
            documents=text_chunks,
            metadatas=metadata_list,
            ids=id_list
        )
```

- [ ] **Step 4: Testi çalıştır, yeşil olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_document_api.py -v --no-cov
```
Beklenen: `8 passed`.

- [ ] **Step 5: Mutasyonla bağlayıcılığı kanıtla**

Step 3'te eklediğin `koleksiyon.delete(where={"source": file.filename})` satırını
geçici olarak sil, testi koş, kırmızı olduğunu gör, sonra satırı GERİ KOY.

```
.venv\Scripts\python.exe -m pytest tests/api/test_document_api.py::test_yeniden_yukleme_eski_chunklari_birakmaz -v --no-cov
```

Raporunda mutasyonlu çıktıyı, geri koyduktan sonraki yeşil çıktıyı ve
`git diff -- app/api/document.py` ile satırın geri geldiğinin kanıtını göster.

- [ ] **Step 6: Tüm paketi çalıştır**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings
```
Beklenen: `98 passed`, kapsama %75'in altına düşmemeli.

- [ ] **Step 7: Commit**

```bash
git add tests/api/test_document_api.py app/api/document.py
git commit -m "fix: yeniden yukleme eski chunklari birakmiyor, sil-sonra-yaz (97 -> 98)"
```

---

## Görevler bittikten sonra: doğrulama

Kontrolcü tarafından yürütülür.

- [ ] **Otomatik**

```
.venv\Scripts\python.exe -m pytest -m "not yavas"
```
`98 passed`, kapsama %75'in altına düşmemeli.

- [ ] **Gerçek ChromaDB'ye karşı elle doğrulama**

Backend ayakta ve ChromaDB konteyneri çalışıyorken, `admin` jetonuyla:

```
GET  http://localhost:8000/document/liste
```

Beklenen: iki kayıt — `gogus_agrisi_protokolu.txt` ve `karin_agrisi_protokolu.txt`,
her biri 2 chunk. Bu, sahte koleksiyonun gerçek ChromaDB arayüzünü doğru taklit
ettiğinin kanıtıdır; sahte yeşil verip gerçek patlarsa burada görülür.

- [ ] **Silmenin gerçek koleksiyonda çalıştığı**

`DELETE /document?kaynak=<olmayan bir ad>` çağır, `404` geldiğini gör. **Gerçek bir
dosyayı silme** — bilgi tabanındaki iki dosya derlemeye kadar duruyor.

---

## Bitti sayılır

- [ ] Sekiz yeni test yeşil; toplam 90 → 98
- [ ] Mevcut 90 test hâlâ yeşil
- [ ] `test_yeniden_yukleme_eski_chunklari_birakmaz` mutasyonla bağlayıcı olduğu
      kanıtlandı
- [ ] `GET /document/liste` gerçek ChromaDB'ye karşı doğru sayıyor
- [ ] Hiçbir test gerçek `triage_documents` koleksiyonuna yazmadı
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama var
- [ ] Dal `main`'e birleşti
