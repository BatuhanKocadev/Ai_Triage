# Gün 19 — Streamlit Doktor Paneli Uygulama Planı

> **Ajan çalışanlar için:** ZORUNLU ALT BECERİ: Bu planı görev görev uygulamak için
> superpowers:subagent-driven-development kullanın. Adımlar takip için checkbox
> (`- [ ]`) sözdizimi kullanır.

**Hedef:** Doktorun tarayıcıdan bekleyen vakaları görüp bir yapay zekâ önerisini
inceleyerek onaylayabildiği paneli çalışır hâle getirmek; hasta girişinden doktor onayına
kadar tam döngüyü kapatmak.

**Mimari:** Backend değişmiyor — Gün 17+18'in iki ucu zaten sözleşmeyi kuruyor. Bugün
`frontend/app.py`'ye rol tabanlı sekme haritası ve doktor paneli ekleniyor, ve o
sözleşmeyi kilitleyen dört backend testi yazılıyor. Streamlit'in kendisi otomatik test
edilmiyor (K12); testler panelin okuduğu HTTP katmanını donduruyor.

**Teknoloji:** Streamlit 1.59.2, `requests`, FastAPI, pytest.

**Tasarım dokümanı:** `docs/superpowers/specs/2026-08-03-gun19-doktor-paneli-design.md` —
çelişkide o belge kazanır, kararlar K1–K12 numaralarıyla oradadır.

## Global Constraints

Aşağıdakiler her görevin gereksinimlerine dahildir; ayrıca tekrarlanmaz.

- **Türkçe açıklama zorunlu.** Eklenen her fonksiyon, blok ve yeni yapının yanına tek
  cümlelik Türkçe yorum. Kod tabanı ve arayüz metinleri Türkçedir.
- **Test adları birebir uygulanır.** Dört testin adı yol haritasından alınmıştır,
  değiştirilemez.
- **Saf TDD.** Backend testleri (Görev 1) önce yazılır, kırmızı olduğu ÇALIŞTIRILARAK
  görülür. Görev 2 ve 3 Streamlit kodudur ve otomatik testi yoktur (K12) — orada kural,
  mevcut 90 testin bozulmamasıdır.
- **Mevcut 86 test yeşil kalmalı.** Taban çizgisi bu dalda ölçüldü: `86 passed`.
- **Python komutu her zaman:**
  `C:\Users\batuh\Desktop\Ai_Triage-myself\.venv\Scripts\python.exe`
- **Her şey worktree kökünden çalıştırılır:**
  `C:\Users\batuh\Desktop\Ai_Triage-worktrees\gun19-doktor-paneli`
- **PostgreSQL ayakta olmalı.** Konteyner `ai_triage_postgres` çalışıyor.
- **Testlerde Ollama/ChromaDB/Whisper çağrılmaz.** Sahteler `tests/yardimcilar/` altında
  ve **adın arandığı ad alanında** yamalanır — uç testlerinde `app.api.ai.*`.
- **`Visit` durum sütunu `status`**, değerleri `"bekliyor"` / `"tamamlandi"`; zaman damgası
  `created_at`. (`durum` / `olusturma_zamani` DEĞİL — K9.)
- **`ai_onerisi` iç içedir.** `triage_code`, `department`, `onerilen_tetkikler`,
  `ai_note`, `sources` üst düzeyde değil, `vaka["ai_onerisi"]` altındadır.
- **Commit mesajları ASCII.** Kod ve arayüz metinlerinde Türkçe karakter beklenir.
- **`frontend/app.py` tek dosyadır — paralel subagent YOK.** Görev 2 ve 3 sırayla koşar.

---

## Dosya Yapısı

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `tests/api/test_doctor_api.py` | Panelin okuduğu sözleşme + listeden düşme | 1 |
| `tests/api/test_auth_api.py` | `/auth/me` rol bilgisi | 1 |
| `tests/api/test_uctan_uca_dongu.py` | **YENİ** — hasta→doktor tam döngü | 1 |
| `frontend/app.py` | `istek_at()`, `hasta_sekmesi()`, rol→sekme haritası | 2 |
| `frontend/app.py` | `doktor_sekmesi()` — liste + onay formu | 3 |

---

### Task 1: Backend sözleşme testleri

**Files:**
- Modify: `tests/api/test_doctor_api.py` (dosya sonuna 2 test)
- Modify: `tests/api/test_auth_api.py` (dosya sonuna 1 test)
- Create: `tests/api/test_uctan_uca_dongu.py`

**Interfaces:**
- Consumes: `_ziyaret_ekle`, `doktor_baslik`, `_onay_govdesi` (hepsi
  `tests/api/test_doctor_api.py` içinde tanımlı), `yetkili_baslik` ve `db_oturum`
  (`tests/conftest.py`), `sahte_llm_uret` / `GECERLI_YANIT`
  (`tests/yardimcilar/sahte_llm.py`), `ziyaret_verisi`
  (`tests/yardimcilar/veri_uretici.py`)
- Produces: hiçbir üretim kodu — bu görev yalnızca sözleşmeyi dondurur. Görev 2 ve 3 bu
  testleri kırmadan çalışmak zorunda.

- [ ] **Step 1: `test_doctor_api.py`'ye iki testi yaz**

Dosyanın SONUNA ekle. `_ziyaret_ekle`, `doktor_baslik` ve `_onay_govdesi` zaten dosyada
tanımlı — yeniden tanımlama.

```python
@pytest.mark.entegrasyon
def test_bekleyen_liste_yaniti_panelin_bekledigi_alanlari_icerir(istemci, db_oturum, doktor_baslik):
    # Panel bu alan adlarını doğrudan okuyor; biri sessizce yeniden adlandırılırsa
    # ekran hata vermeden boşalır. Sözleşme burada kilitleniyor.
    _ziyaret_ekle(db_oturum, sikayet="Panelin okudugu vaka")

    vaka = istemci.get("/doctor/bekleyen", headers=doktor_baslik).json()[0]

    for alan in (
        "visit_id", "patient_age", "gender", "symptom_text",
        "chronic_disease", "vitals", "giris_tipi", "created_at",
    ):
        assert alan in vaka, f"panelin beklediği üst düzey alan eksik: {alan}"

    # Öneri alanları üst düzeyde DEĞİL, ai_onerisi altında iç içe (tasarım kararı K9).
    assert "triage_code" not in vaka
    for alan in ("triage_code", "department", "onerilen_tetkikler", "ai_note", "sources"):
        assert alan in vaka["ai_onerisi"], f"panelin beklediği öneri alanı eksik: {alan}"


@pytest.mark.entegrasyon
def test_onay_sonrasi_vaka_bekleyen_listesinde_gorunmez(istemci, db_oturum, doktor_baslik):
    # Panelin "onaylayınca vaka listeden düşer" davranışının kanıtı; kuyruğun
    # kapanması bu davranışa bağlı.
    ziyaret = _ziyaret_ekle(db_oturum, sikayet="Onaylanacak vaka")
    ziyaret_id = str(ziyaret.id)

    onceki = istemci.get("/doctor/bekleyen", headers=doktor_baslik).json()
    assert ziyaret_id in [vaka["visit_id"] for vaka in onceki]

    onay = istemci.post(
        "/doctor/inceleme", json=_onay_govdesi(ziyaret.id), headers=doktor_baslik
    )
    assert onay.status_code == 201

    sonraki = istemci.get("/doctor/bekleyen", headers=doktor_baslik).json()
    assert ziyaret_id not in [vaka["visit_id"] for vaka in sonraki]
```

- [ ] **Step 2: `test_auth_api.py`'ye `/auth/me` testini yaz**

Dosyanın SONUNA ekle. Bu uç bugüne kadar hiçbir testten geçmiyordu.

```python
@pytest.mark.entegrasyon
def test_rol_bilgisi_auth_me_ile_donuyor(istemci, yetkili_baslik):
    # Panel rolü buradan okuyor (kullanıcı adından tahmin etmiyor); bu uç
    # bozulursa arayüz yanlış sekmeleri açar. Parola hash'inin sızmadığı da
    # burada sabitleniyor.
    yanit = istemci.get(
        "/auth/me", headers=yetkili_baslik(kullanici_adi="dr_veli", rol="doctor")
    )

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["username"] == "dr_veli"
    assert govde["role"] == "doctor"
    assert "hashed_password" not in govde
```

- [ ] **Step 3: Uçtan uca döngü testini yaz**

`tests/api/test_uctan_uca_dongu.py` (yeni dosya):

```python
"""Hasta şikayetinden doktor onayına kadar tam döngünün tek testi.

Ollama, ChromaDB ve reranker çağrılmaz; sahte servislerle koşar.
"""

import uuid

import pytest

from app.api import ai as ai_modulu
from app.models.visit import Visit
from tests.yardimcilar.sahte_llm import GECERLI_YANIT, sahte_llm_uret
from tests.yardimcilar.veri_uretici import ziyaret_verisi


@pytest.fixture
def esik_ustu(monkeypatch):
    """RAG'i eşiği geçmiş, LLM'i geçerli yanıt verir gibi ayarlar."""
    monkeypatch.setattr(ai_modulu, "get_collection", lambda: object())
    monkeypatch.setattr(
        ai_modulu,
        "retrieve_and_rerank",
        lambda **kwargs: ["[Kaynak: protokol.pdf] Göğüs ağrısı protokolü"],
    )
    monkeypatch.setattr(
        ai_modulu, "get_structured_completion", sahte_llm_uret(GECERLI_YANIT)
    )


@pytest.mark.entegrasyon
def test_sikayetten_doktor_onayina_tam_dongu(istemci, db_oturum, yetkili_baslik, esik_ustu):
    # Zincirin tamamı tek testte: hasta başvurusu girer, doktor kuyruğunda görür,
    # yapay zekânın kararını değiştirip onaylar, vaka kuyruktan düşer.
    # İki ayrı kimlik kullanılıyor (tasarım kararı K11): rol ayrımının uçtan uca
    # çalıştığı da böylece kanıtlanmış oluyor.
    hasta_baslik = yetkili_baslik(kullanici_adi="hasta_ayse", rol="user")
    doktor_baslik = yetkili_baslik(kullanici_adi="dr_veli", rol="doctor")

    # 1) Hasta şikayetini girer, yapay zekâ "Sarı" der.
    analiz = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=hasta_baslik)
    assert analiz.status_code == 200
    assert analiz.json()["triage_code"] == "Sarı"
    visit_id = analiz.json()["visit_id"]

    # 2) Vaka doktorun kuyruğunda görünür.
    liste = istemci.get("/doctor/bekleyen", headers=doktor_baslik).json()
    assert visit_id in [vaka["visit_id"] for vaka in liste]

    # 3) Doktor kararı "Kırmızı"ya çevirip onaylar.
    onay = istemci.post(
        "/doctor/inceleme",
        json={
            "visit_id": visit_id,
            "onaylanan_triage_code": "Kırmızı",
            "onaylanan_tetkikler": ["EKG"],
            "doktor_notu": "Acil servise alindi",
        },
        headers=doktor_baslik,
    )
    assert onay.status_code == 201

    # 4) Vaka kuyruktan düşer ve ziyaret tamamlandi olur.
    kalan = istemci.get("/doctor/bekleyen", headers=doktor_baslik).json()
    assert visit_id not in [vaka["visit_id"] for vaka in kalan]

    ziyaret = db_oturum.query(Visit).filter_by(id=uuid.UUID(visit_id)).one()
    assert ziyaret.status == "tamamlandi"
```

- [ ] **Step 4: Testleri çalıştır, kırmızı olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_uctan_uca_dongu.py tests/api/test_auth_api.py -v --no-cov
```

DİKKAT — bu görevin dört testinden üçü **zaten yeşil olabilir**, çünkü backend'i Gün
17+18 yazdı ve bu testler onun sözleşmesini dondurmak için var. Bu bir sorun değil, ama
"kırmızı görüldü" iddiası edilemez. Yapılacak: her testin gerçekten bağlayıcı olduğunu
**mutasyonla** kanıtla. Her mutasyondan sonra ilgili testi koş, kırmızı olduğunu gör,
mutasyonu GERİ AL:

| Mutasyon | Kırmızıya düşmesi gereken test |
|---|---|
| `app/schemas/doctor.py` içinde `BekleyenVaka.symptom_text` alanını `sikayet` diye yeniden adlandır | `test_bekleyen_liste_yaniti_panelin_bekledigi_alanlari_icerir` |
| `app/api/doctor.py` içindeki `ziyaret.status = "tamamlandi"` satırını sil | `test_onay_sonrasi_vaka_bekleyen_listesinde_gorunmez` ve `test_sikayetten_doktor_onayina_tam_dongu` |
| `app/schemas/auth.py` içindeki `UserInfo.role` alanını sil | `test_rol_bilgisi_auth_me_ile_donuyor` |

Raporunda her mutasyonun komutunu, çıktısını ve geri alındığının kanıtını göster
(`git diff` boş olmalı, yalnızca test dosyaları değişmiş olmalı).

- [ ] **Step 5: Tüm paketi çalıştır**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: `90 passed`.

- [ ] **Step 6: Commit**

```bash
git add tests/api/test_doctor_api.py tests/api/test_auth_api.py tests/api/test_uctan_uca_dongu.py
git commit -m "test: panel sozlesmesi, /auth/me rolu ve uctan uca dongu (86 -> 90)"
```

---

### Task 2: Rol → sekme haritası ve `hasta_sekmesi()` çıkarımı

**Files:**
- Modify: `frontend/app.py` — `istek_at()` yardımcısı eklenir, hasta bloğu
  (`frontend/app.py:118-277`) `hasta_sekmesi()` fonksiyonuna taşınır, sekme kurulum
  bloğu (`frontend/app.py:109-116`) yeniden yazılır

**Interfaces:**
- Consumes: `BACKEND_URL`, `st.session_state.user_role`, `auth_headers`
- Produces: `istek_at(metot, yol, jeton, **kwargs)` ve `hasta_sekmesi(auth_headers)`;
  ayrıca `doktor_container` değişkeni — Görev 3 panelini oraya yerleştirecek.

- [ ] **Step 1: `istek_at()` yardımcısını ekle**

`triyaj_sonucunu_goster` fonksiyonunun ÜSTÜNE ekle:

```python
def istek_at(metot: str, yol: str, jeton: str, **kwargs):
    """Backend'e yetkili istek atar; adres kurma ve başlık ekleme tek yerde toplanır.

    Bağlantı kurulamazsa None döndürür — çağıran taraf kullanıcıya anlaşılır bir
    mesaj gösterir, ham istisna arayüze sızmaz.
    """
    try:
        return requests.request(
            metot,
            f"{BACKEND_URL}{yol}",
            headers={"Authorization": f"Bearer {jeton}"},
            timeout=kwargs.pop("timeout", 30),
            **kwargs,
        )
    except requests.exceptions.RequestException:
        return None
```

- [ ] **Step 2: Hasta bloğunu fonksiyona taşı**

`frontend/app.py:118` `with chat_container:` satırından `:277`'ye kadar olan blok
(sidebar hasta bilgileri, yazılı/sesli sekmeler, "uzmana sor" formu) modül düzeyinde bir
fonksiyona alınır. **Bu saf bir yer değiştirmedir** — tek satır mantık değişmeyecek,
yalnızca girinti 4 boşluk azalacak ve `auth_headers` parametreye dönecek.

Fonksiyonu `triyaj_sonucunu_goster`'in altına, giriş formundan ÖNCE koy:

```python
def hasta_sekmesi(auth_headers):
    """Hastanın yazılı/sesli şikayet girip analiz sonucunu gördüğü sekme.

    Gün 19'da doktor sekmesi eklenirken buraya taşındı: doctor rolünde bu sekme
    hiç oluşturulmadığı için blok koşullu hâle gelmek zorundaydı (tasarım kararı K8).
    Taşıma dışında içeriği değişmedi.
    """
    with st.sidebar:
        st.header("Patient Information")
        ...
```

Doğrulama: taşıma bittikten sonra `git diff -w -- frontend/app.py` çıktısında bu 160
satırdan yalnızca fonksiyon tanımı ve docstring görünmeli; gövde satırları
görünmemeli. Görünüyorsa mantığı da değiştirmişsin demektir — geri al.

- [ ] **Step 3: Sekme haritasını yaz**

`frontend/app.py:109-116` arasındaki mevcut ikili blok bununla değiştirilir:

```python
    # Rol -> sekme haritası (tasarım kararı K2): kullanıcıya yalnızca gerçekten
    # yetkisi olan sekmeler gösterilir. Basınca 403 alınacak bir düğme göstermek,
    # arayüzün yetki modeli hakkında yalan söylemesidir.
    rol = st.session_state.user_role
    chat_container = doktor_container = admin_container = None

    if rol == "admin":
        # Admin her üç yetki grubundan da geçer ("admin her şeyi görür").
        chat_container, doktor_container, admin_container = st.tabs(
            ["Kullanıcı Sohbet Ekranı", "Doktor Paneli", "Yönetici Paneli"]
        )
    elif rol == "doctor":
        # Doktor /ai/analiz, /document/upload ve /speech/transkript uçlarının
        # üçünden de 403 alır; ona yalnızca kendi paneli gösterilir.
        doktor_container, = st.tabs(["Doktor Paneli"])
    else:
        chat_container, = st.tabs(["Kullanıcı Sohbet Ekranı"])

    if chat_container is not None:
        with chat_container:
            hasta_sekmesi(auth_headers)
```

`if admin_container:` bloğu (`frontend/app.py:279`) olduğu gibi kalır — zaten korumalı.

- [ ] **Step 4: Yanıltıcı "Bekleyen Sorular" başlığını düzelt**

`frontend/app.py:307` bugün şunu diyor:
`st.header("Bekleyen Sorular (geçici — Gün 19'da gerçek veriye bağlanacak)")`

Gerçek veriye bağlanmıyor (tasarım kararı K10). Söz veren metni dürüst olanla değiştir:

```python
            st.header("Bekleyen Sorular")
            # Bu liste demo amaçlı, bellekte tutulan örnek sorulardır; henüz bir
            # veritabanı tablosuna bağlı değildir. Altındaki "Bilgi Tabanına Ekle"
            # akışı ise gerçektir ve dokümanı ChromaDB'ye yükler.
            st.caption("Örnek veri — sorular henüz kalıcı olarak saklanmıyor.")
```

- [ ] **Step 5: Sözdizimi ve paket kontrolü**

Streamlit kodu testsiz; en azından dosyanın derlendiğini ve backend testlerinin
bozulmadığını doğrula:
```
.venv\Scripts\python.exe -m py_compile frontend/app.py
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: derleme sessiz, `90 passed`.

- [ ] **Step 6: Commit**

```bash
git add frontend/app.py
git commit -m "feat: rol bazli sekme haritasi, hasta_sekmesi cikarimi ve istek_at yardimcisi"
```

---

### Task 3: Doktor sekmesi — liste ve onay formu

**Files:**
- Modify: `frontend/app.py` — `doktor_sekmesi()` fonksiyonu ve onu `doktor_container`
  içine yerleştiren blok

**Interfaces:**
- Consumes: `istek_at()` ve `doktor_container` (Görev 2), `GET /doctor/bekleyen`,
  `POST /doctor/inceleme`
- Produces: `doktor_sekmesi(jeton)`; `st.session_state` anahtarları
  `doktor_liste_limiti` ve `doktor_son_onay`

- [ ] **Step 1: Oturum durumu anahtarlarını ekle**

Dosyanın başındaki `session_state` kurulum bloğuna ekle:

```python
# Doktor panelinin durumu: Streamlit her etkileşimde scripti baştan çalıştırdığı
# için liste penceresi ve onay sonucu session_state'te saklanıyor.
if "doktor_liste_limiti" not in st.session_state:
    st.session_state.doktor_liste_limiti = 20  # "Daha fazla göster" bunu 20'şer artırır
if "doktor_son_onay" not in st.session_state:
    st.session_state.doktor_son_onay = None  # onay sonrası bir kez gösterilip temizlenir
```

- [ ] **Step 2: `doktor_sekmesi()` fonksiyonunu yaz**

`hasta_sekmesi`'nin altına ekle:

```python
# Triyaj kodunun ekrandaki rengi; expander başlığı HTML kabul etmediği için
# renk emoji ile veriliyor (tasarım kararı K7).
TRIYAJ_ISARETI = {"Kırmızı": "🔴", "Sarı": "🟡", "Yeşil": "🟢", "Belirsiz": "⚪"}

# Doktorun onaylayabileceği kodlar; "Belirsiz" bilerek yok — doktorun işi
# belirsizliği gidermek (backend de 422 ile reddeder).
ONAYLANABILIR_KODLAR = ["Kırmızı", "Sarı", "Yeşil"]


def doktor_sekmesi(jeton: str):
    """Doktorun bekleyen vakaları görüp yapay zekâ önerisini onayladığı panel."""
    st.header("Bekleyen Vakalar")

    # Bir önceki çalıştırmada onay verilmişse mesajı burada gösterip bayrağı
    # HEMEN temizliyoruz; temizlenmezse mesaj her yeniden çizimde tekrar çıkar.
    if st.session_state.doktor_son_onay:
        st.success(st.session_state.doktor_son_onay)
        st.session_state.doktor_son_onay = None

    limit = st.session_state.doktor_liste_limiti
    yanit = istek_at("GET", f"/doctor/bekleyen?limit={limit}&offset=0", jeton)

    if yanit is None:
        st.error("Sunucuya ulaşılamadı. Backend'in çalıştığından emin olup tekrar deneyin.")
        return
    if yanit.status_code == 401:
        st.error("Oturum süreniz dolmuş. Lütfen çıkıp yeniden giriş yapın.")
        return
    if yanit.status_code != 200:
        st.error("Bekleyen vakalar alınamadı. Lütfen kısa bir süre sonra tekrar deneyin.")
        return

    vakalar = yanit.json()
    if not vakalar:
        st.success("Bekleyen vaka yok. Kuyruk temiz.")
        return

    st.caption(f"{len(vakalar)} bekleyen vaka gösteriliyor.")

    for vaka in vakalar:
        _vaka_karti(vaka, jeton)

    # Dönen kayıt sayısı limite eşitse muhtemelen daha fazlası var (tasarım kararı K6).
    if len(vakalar) == limit:
        if st.button("Daha fazla göster"):
            st.session_state.doktor_liste_limiti += 20
            st.rerun()


def _vaka_karti(vaka: dict, jeton: str):
    """Tek bir bekleyen vakayı ve onun inceleme formunu çizer."""
    oneri = vaka.get("ai_onerisi") or {}
    ai_kodu = oneri.get("triage_code", "Belirsiz")
    baslik = (
        f"{TRIYAJ_ISARETI.get(ai_kodu, '⚪')} {vaka['patient_age']} yaş, "
        f"{vaka['gender']} — yapay zekâ: {ai_kodu}"
    )

    with st.expander(baslik):
        st.markdown(f"**Şikayet:** {vaka['symptom_text']}")
        if vaka.get("chronic_disease"):
            st.markdown(f"**Kronik hastalık:** {vaka['chronic_disease']}")
        if vaka.get("vitals"):
            st.markdown(f"**Vitaller:** {vaka['vitals']}")
        # Şikayetin sesle mi yazıyla mı geldiği, transkript hatası ihtimalini
        # doktorun bilmesi için gösteriliyor.
        st.caption(f"Giriş kanalı: {vaka['giris_tipi']} · Kayıt: {vaka['created_at']}")

        if oneri.get("ai_note"):
            st.info(oneri["ai_note"])
        if oneri.get("sources"):
            with st.expander("Kaynak dokümanlar"):
                for kaynak in oneri["sources"]:
                    st.write(kaynak)

        st.markdown("---")

        # Form anahtarları visit_id ile benzersizleştiriliyor; aksi hâlde Streamlit
        # aynı anahtarı iki kez görüp hata verir.
        vid = vaka["visit_id"]
        with st.form(f"inceleme_{vid}"):
            ai_tetkikler = oneri.get("onerilen_tetkikler") or []
            varsayilan_kod = ai_kodu if ai_kodu in ONAYLANABILIR_KODLAR else "Sarı"

            kod = st.radio(
                "Triyaj kodu",
                ONAYLANABILIR_KODLAR,
                index=ONAYLANABILIR_KODLAR.index(varsayilan_kod),
                horizontal=True,
                key=f"kod_{vid}",
            )
            # accept_new_options: doktor yapay zekânın önermediği tetkiki de
            # ekleyebilmeli, yoksa onay ucunun varlık sebebi boşa çıkar (K5).
            tetkikler = st.multiselect(
                "Tetkikler",
                options=ai_tetkikler,
                default=ai_tetkikler,
                accept_new_options=True,
                key=f"tetkik_{vid}",
            )
            not_metni = st.text_area("Doktor notu (opsiyonel)", key=f"not_{vid}")

            if st.form_submit_button("Onayla", type="primary"):
                _onayi_gonder(vid, kod, tetkikler, not_metni, jeton)


def _onayi_gonder(vid: str, kod: str, tetkikler: list, not_metni: str, jeton: str):
    """Onayı backend'e yollar ve sonucuna göre paneli tazeler."""
    yanit = istek_at(
        "POST",
        "/doctor/inceleme",
        jeton,
        json={
            "visit_id": vid,
            "onaylanan_triage_code": kod,
            "onaylanan_tetkikler": tetkikler,
            "doktor_notu": not_metni or None,
        },
    )

    if yanit is None:
        st.error("Sunucuya ulaşılamadı. Onay kaydedilmedi.")
        return

    if yanit.status_code == 201:
        # Mesajı doğrudan basmıyoruz: rerun sonrası kaybolurdu. Bayrağa yazıp
        # listeyi tazeliyoruz, mesaj bir sonraki çizimde gösterilip siliniyor (K3).
        st.session_state.doktor_son_onay = f"Vaka onaylandı: {kod}"
        st.rerun()
    elif yanit.status_code == 409:
        # Hata değil, yarış durumu: başka bir doktor önce davranmış.
        st.session_state.doktor_son_onay = "Bu vaka başka bir doktor tarafından incelenmiş."
        st.rerun()
    elif yanit.status_code == 404:
        st.session_state.doktor_son_onay = "Vaka bulunamadı; liste tazelendi."
        st.rerun()
    elif yanit.status_code == 401:
        st.error("Oturum süreniz dolmuş. Lütfen çıkıp yeniden giriş yapın.")
    else:
        st.error("Onay kaydedilemedi. Lütfen tekrar deneyin.")
```

- [ ] **Step 3: Paneli sekmeye bağla**

Görev 2'nin `if chat_container is not None:` bloğunun ALTINA ekle:

```python
    if doktor_container is not None:
        with doktor_container:
            doktor_sekmesi(st.session_state.access_token)
```

- [ ] **Step 4: Sözdizimi ve paket kontrolü**

```
.venv\Scripts\python.exe -m py_compile frontend/app.py
.venv\Scripts\python.exe -m pytest -m "not yavas" -p no:warnings --no-cov
```
Beklenen: derleme sessiz, `90 passed` (Streamlit değişikliği backend testlerini
etkilememeli — etkiliyorsa yanlış dosyaya dokunmuşsundur).

- [ ] **Step 5: Commit**

```bash
git add frontend/app.py
git commit -m "feat: doktor paneli - bekleyen vaka listesi ve onay formu"
```

---

## Görevler bittikten sonra: doğrulama

Kontrolcü tarafından yürütülür.

- [ ] **Otomatik**

```
.venv\Scripts\python.exe -m pytest -m "not yavas"
```
`90 passed`, kapsama %75'in altına düşmemeli.

- [ ] **Tarayıcıda uçtan uca**

Backend ve frontend'i başlat (`localhost` kullan, `127.0.0.1` değil — `st.audio_input`
güvenli bağlam ister):
```
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

Sırayla ve her adımın ekran görüntüsünü alarak:
1. `hasta` / `hasta123` ile gir → yalnızca sohbet sekmesi görünmeli
2. Şikayeti yazarak gönder, analiz sonucunu gör
3. Çık, `doctor` / `doctor123` ile gir → yalnızca **Doktor Paneli** görünmeli
4. Vakayı listede bul, expander'ı aç, yapay zekâ notunu ve kaynakları gör
5. Triyaj kodunu değiştir, bir tetkik ekle, not yaz, onayla
6. Vakanın listeden düştüğünü ve başarı mesajını gör
7. `admin` / `admin123` ile gir → üç sekmenin de göründüğünü doğrula

- [ ] **Veritabanı kanıtı**

```sql
SELECT v.status,
       a.triage_code            AS ai_kodu,
       d.onaylanan_triage_code  AS doktor_kodu,
       a.onerilen_tetkikler     AS ai_tetkikler,
       d.onaylanan_tetkikler    AS doktor_tetkikler
FROM visits v
JOIN ai_recommendations a ON a.visit_id = v.id
JOIN doctor_reviews d     ON d.visit_id = v.id
ORDER BY v.created_at DESC
LIMIT 5;
```

- [ ] **Kullanıcıya kalan adım:** mikrofonla ses girişinin gerçek tarayıcıda denenmesi
      (Gün 16'dan kalan borç). Gerçek mikrofon ve insan sesi gerektirir.

---

## Bitti sayılır

- [ ] Dört yeni test yeşil ve mutasyonla bağlayıcı oldukları kanıtlandı; toplam 90
- [ ] Mevcut 86 test hâlâ yeşil
- [ ] `doctor` rolü yalnızca kendi panelini görüyor
- [ ] `admin` üç sekmeyi de görüyor, `user` yalnızca sohbeti
- [ ] Tam döngü tarayıcıda çalıştı ve ekran görüntüleri alındı
- [ ] Doktorun kodu ile yapay zekânın kodu veritabanında ayrı ayrı duruyor
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama var
- [ ] Dal `main`'e birleşti
