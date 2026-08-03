# Gün 17+18 — Doktor Uçları Uygulama Planı

> **Ajan çalışanlar için:** ZORUNLU ALT BECERİ: Bu planı görev görev uygulamak için
> superpowers:subagent-driven-development kullanın. Adımlar takip için checkbox
> (`- [ ]`) sözdizimi kullanır.

**Hedef:** Doktorun bekleyen vakaları listeleyip bir yapay zekâ önerisini onaylayabildiği
API katmanını, yapay zekânın orijinal önerisini hiç bozmadan çalışır hâle getirmek.

**Mimari:** İki yeni uç (`GET /doctor/bekleyen`, `POST /doctor/inceleme`) tek bir router
dosyasında (`app/api/doctor.py`) toplanıyor; şemaları `app/schemas/doctor.py`'de.
Onay, `AIRecommendation` satırını güncellemek yerine yeni bir `doctor_reviews` satırı
yazıyor — "yapay zekâ ne dedi, doktor ne dedi" farkı böylece kalıcı ve denetlenebilir
kalıyor. Yetki, mevcut iki bağımlılığın yanına eklenen üçüncü bir `require_doctor_role`
ile veriliyor.

**Teknoloji:** FastAPI, SQLAlchemy 2.x ORM, Alembic, PostgreSQL, Pydantic v2, pytest.

**Tasarım dokümanı:** `docs/superpowers/specs/2026-08-03-doktor-uclari-design.md` —
çelişkide o belge kazanır, kararlar K1–K10 numaralarıyla oradadır.

## Global Constraints

Aşağıdakiler her görevin gereksinimlerine dahildir; ayrıca tekrarlanmaz.

- **Türkçe açıklama zorunlu.** Eklenen her fonksiyon, sütun, şema alanı ve yeni yapının
  yanına tek cümlelik Türkçe yorum yazılır. Kod tabanı, log mesajları ve API alan adları
  Türkçedir (bkz. `CLAUDE.md`).
- **Test adları birebir uygulanır.** Bu plandaki 17 test adının hiçbiri değiştirilemez,
  birleştirilemez, atlanamaz — yol haritası belgesinden alınmışlardır.
- **Saf TDD.** Her görevde önce test yazılır, kırmızı olduğu ÇALIŞTIRILARAK görülür,
  sonra minimum üretim kodu yazılır. "Testi sonra yazarım" yasak.
- **Mevcut 67 test yeşil kalmalı.** Taban çizgisi bu dalda ölçüldü: `67 passed`.
- **Python komutu her zaman:**
  `C:\Users\batuh\Desktop\Ai_Triage-myself\.venv\Scripts\python.exe`
  (worktree'nin kendi `.venv`'i yok, ana deponunki kullanılır).
- **Testler repo kökünden çalıştırılır:** `C:\Users\batuh\Desktop\Ai_Triage-worktrees\gun17-doktor-uclari`
- **PostgreSQL ayakta olmalı:** `docker compose up -d postgres`. Test veritabanı
  `ai_triage_test`; `tests/conftest.py` başka bir hedefte testleri durdurur.
- **`require_doctor_role` = doctor + admin.** `user` rolü 403 alır, jetonsuz istek 401.
- **Zaman damgası alanının adı `created_at`.** `olusturma_zamani` KULLANILMAZ (K3).
- **`AIRecommendation` satırına asla yazılmaz.** Ne güncelleme, ne silme (K4).
- **Triyaj kodu kümesi:** `"Kırmızı"`, `"Sarı"`, `"Yeşil"`. `"Belirsiz"` doktor onayında
  geçersizdir (K8).
- **`Visit` durum sütununun adı `status`** (`durum` DEĞİL), değerleri `"bekliyor"` ve
  `"tamamlandi"`.
- **Commit mesajları ASCII.** Depoda mevcut kalıp bu; Türkçe karakter kullanılmaz.

---

## Dosya Yapısı

| Dosya | Sorumluluk | Görev |
|---|---|---|
| `app/services/auth_service.py` | `require_doctor_role` bağımlılığı eklenir | 1 |
| `app/models/user.py` | `role` yorumu üç rolü anlatacak şekilde güncellenir | 1 |
| `scripts/seed_users.py` | Üç başlangıç hesabı; var olan hesabın rolünü de düzeltir | 1 |
| `app/models/doctor_review.py` | **YENİ** — `DoctorReview` ORM modeli | 2 |
| `app/models/visit.py` | `Visit.review` ilişkisi eklenir | 2 |
| `app/models/__init__.py` | `DoctorReview` import edilir (autogenerate görsün) | 2 |
| `app/db/alembic/versions/*` | **YENİ** — `doctor_reviews` tablosu migration'ı | 2 |
| `app/schemas/doctor.py` | **YENİ** — dört Pydantic şeması | 3, 4 |
| `app/api/doctor.py` | **YENİ** — `/doctor` router'ı, iki uç | 3, 4 |
| `app/main.py` | Router kaydı | 3 |
| `tests/birim/test_auth_service.py` | Rol bağımlılığının 3 birim testi | 1 |
| `tests/entegrasyon/test_doktor_inceleme_kaliciligi.py` | **YENİ** — 3 kalıcılık testi | 2 |
| `tests/api/test_doctor_api.py` | **YENİ** — 11 uç testi | 3, 4 |

---

### Task 1: doctor rolü ve yetki bağımlılığı

**Files:**
- Modify: `app/services/auth_service.py` (dosya sonuna ekle, `require_user_or_admin_role`'ün altına)
- Modify: `app/models/user.py:16` (yalnızca yorum satırı)
- Modify: `scripts/seed_users.py:18-31`
- Test: `tests/birim/test_auth_service.py` (mevcut dosyanın sonuna ekle)

**Interfaces:**
- Consumes: `app.models.user.User` (mevcut), `app.services.auth_service.get_current_user` (mevcut)
- Produces: `async def require_doctor_role(current_user: User = Depends(get_current_user)) -> User`
  — Görev 3 ve 4 bu bağımlılığı `Depends(require_doctor_role)` olarak kullanacak.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/birim/test_auth_service.py` dosyasının SONUNA ekle. Mevcut testlere dokunma.
Dosyanın başındaki import bloğuna `asyncio` ve `HTTPException` eklemen gerekecek.

```python
import asyncio

from fastapi import HTTPException

from app.models.user import User
from app.services.auth_service import require_doctor_role


def _rolde_kullanici(rol: str) -> User:
    """Veritabanına yazmadan, yalnızca rolü doldurulmuş bir User nesnesi üretir."""
    return User(username=f"{rol}_kullanici", hashed_password="onemsiz", role=rol)


def test_doktor_rolu_bekleyen_vakalari_gorebilir():
    # require_doctor_role, doctor rolündeki kullanıcıyı olduğu gibi geri vermeli.
    kullanici = _rolde_kullanici("doctor")
    assert asyncio.run(require_doctor_role(current_user=kullanici)) is kullanici


def test_user_rolu_doktor_ucuna_403_alir():
    # Hasta başvurusu giren "user" rolü doktor uçlarına giremez.
    with pytest.raises(HTTPException) as hata:
        asyncio.run(require_doctor_role(current_user=_rolde_kullanici("user")))
    assert hata.value.status_code == 403


def test_admin_doktor_uclarina_erisebilir():
    # Karar: admin her şeyi görür (tasarım dokümanı K1).
    kullanici = _rolde_kullanici("admin")
    assert asyncio.run(require_doctor_role(current_user=kullanici)) is kullanici
```

- [ ] **Step 2: Testleri çalıştır, kırmızı olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/birim/test_auth_service.py -v --no-cov
```
Beklenen: üç yeni test de toplama (collection) sırasında `ImportError: cannot import name
'require_doctor_role'` ile patlar. Bu doğru kırmızıdır.

- [ ] **Step 3: `require_doctor_role`'ü yaz**

`app/services/auth_service.py` dosyasının sonuna, `require_user_or_admin_role`'ün altına:

```python
async def require_doctor_role(current_user: User = Depends(get_current_user)) -> User:
    """Doktor veya admin rolü gerektiren uçları korur."""
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required."
        )
    return current_user
```

- [ ] **Step 4: Testleri çalıştır, yeşil olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/birim/test_auth_service.py -v --no-cov
```
Beklenen: 8 passed (mevcut 5 + yeni 3).

- [ ] **Step 5: `user.py` yorumunu güncelle**

`app/models/user.py:16` satırındaki yorum artık eksik. Değiştir:

```python
    role = Column(String(20), nullable=False)  # "admin", "doctor" veya "user"
```

- [ ] **Step 6: `seed_users.py`'yi üç hesaba çıkar**

`scripts/seed_users.py` içindeki listeyi ve döngüyü değiştir. `doctor` hesabının rolü
bugüne kadar `"user"` idi; veritabanında öyle yazılmış olabileceği için script var olan
kaydın rolünü de düzeltmeli — yoksa "atlandı" deyip yanlış rolü bırakır ve doktor kendi
ucundan 403 alır.

```python
BASLANGIC_KULLANICILARI = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "doctor", "password": "doctor123", "role": "doctor"},
    # "doctor" artık ayrı bir rol olduğu için /ai/analiz'e girebilen bir hesap
    # kalmıyordu; hasta başvurusu akışı bu hesapla denenir.
    {"username": "hasta", "password": "hasta123", "role": "user"},
]


def main() -> None:
    db = SessionLocal()
    try:
        for veri in BASLANGIC_KULLANICILARI:
            mevcut = db.query(User).filter(User.username == veri["username"]).first()
            if mevcut:
                # Rol listedekinden farklıysa düzeltilir: "doctor" hesabı Gün 17
                # öncesinde "user" rolüyle yazılmıştı.
                if mevcut.role != veri["role"]:
                    eski_rol = mevcut.role
                    mevcut.role = veri["role"]
                    print(f"  guncellendi: {veri['username']} (rol {eski_rol} -> {veri['role']})")
                else:
                    print(f"  atlandı  : {veri['username']} (zaten var, rol={mevcut.role})")
                continue

            db.add(User(
                username=veri["username"],
                hashed_password=hash_password(veri["password"]),
                role=veri["role"],
            ))
            print(f"  eklendi  : {veri['username']} (rol={veri['role']})")

        db.commit()

        print("\nVeritabanındaki kullanıcılar:")
        for kullanici in db.query(User).order_by(User.id).all():
            print(f"  #{kullanici.id}  {kullanici.username:10} {kullanici.role}")
    finally:
        db.close()
```

- [ ] **Step 7: Tüm paketi çalıştır, hiçbir şeyin bozulmadığını gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest -m "not yavas" -q --no-cov
```
Beklenen: `70 passed`. Daha az ise mevcut bir testi bozdun; devam etme, düzelt.

> `seed_users.py`'yi bu görevde ÇALIŞTIRMA. Gerçek `ai_triage` veritabanına yazar ve
> `doctor_reviews` tablosu henüz yok. Çalıştırma adımı Görev 2'den sonra, doğrulama
> bölümündedir.

- [ ] **Step 8: Commit**

```bash
git add app/services/auth_service.py app/models/user.py scripts/seed_users.py tests/birim/test_auth_service.py
git commit -m "feat: doctor rolu ve require_doctor_role bagimliligi"
```

---

### Task 2: DoctorReview modeli ve migration

**Files:**
- Create: `app/models/doctor_review.py`
- Modify: `app/models/visit.py` (`Visit` sınıfına `review` ilişkisi)
- Modify: `app/models/__init__.py`
- Create: `app/db/alembic/versions/<otomatik>_doctor_reviews_tablosu.py`
- Create: `tests/entegrasyon/__init__.py` (boş dosya)
- Test: `tests/entegrasyon/test_doktor_inceleme_kaliciligi.py`

**Interfaces:**
- Consumes: `app.db.database.Base`, `app.models.visit.Visit`, `app.models.user.User`
- Produces: `DoctorReview` modeli — alanları: `id`, `visit_id`, `doctor_id`,
  `onaylanan_triage_code`, `onaylanan_tetkikler`, `doktor_notu`, `created_at`.
  Görev 3 ve 4 bu adlara birebir dayanır. Ayrıca `Visit.review` ilişkisi.

- [ ] **Step 1: Test paketini oluştur**

`tests/entegrasyon/__init__.py` adında boş bir dosya oluştur. (`tests/api/` ve
`tests/birim/` de aynı şekilde paket; pytest bu düzeni bekliyor.)

- [ ] **Step 2: Başarısız testleri yaz**

`tests/entegrasyon/test_doktor_inceleme_kaliciligi.py`:

```python
"""doctor_reviews tablosunun kalıcılık kurallarını dondurur: ziyarete bağlanma,
cascade silme ve bir ziyarete tek inceleme kısıtı."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.doctor_review import DoctorReview
from app.models.visit import Visit


def _ziyaret_uret(db_oturum) -> Visit:
    """Testlerin inceleme bağlayabileceği, bekleyen durumda bir ziyaret üretir."""
    ziyaret = Visit(
        patient_age=45,
        gender="Erkek",
        symptom_text="Göğsümde baskı hissi var",
    )
    db_oturum.add(ziyaret)
    db_oturum.flush()
    return ziyaret


@pytest.mark.entegrasyon
def test_inceleme_ziyarete_bagli_kaydedilir(db_oturum, kullanici_uret):
    doktor = kullanici_uret(kullanici_adi="dr_ayse", rol="doctor")
    ziyaret = _ziyaret_uret(db_oturum)

    db_oturum.add(DoctorReview(
        visit_id=ziyaret.id,
        doctor_id=doktor.id,
        onaylanan_triage_code="Kırmızı",
        onaylanan_tetkikler=["EKG"],
        doktor_notu="Acil servise alındı",
    ))
    db_oturum.flush()

    kayit = db_oturum.query(DoctorReview).filter_by(visit_id=ziyaret.id).one()
    assert kayit.doctor_id == doktor.id
    assert kayit.onaylanan_triage_code == "Kırmızı"
    assert kayit.onaylanan_tetkikler == ["EKG"]
    assert kayit.doktor_notu == "Acil servise alındı"
    # created_at varsayılanı modelde tanımlı; migration'a bel bağlamıyoruz.
    assert kayit.created_at is not None


@pytest.mark.entegrasyon
def test_ziyaret_silinince_inceleme_de_silinir(db_oturum, kullanici_uret):
    # Ziyaret silinince incelemesi ortada kalmamalı (cascade).
    doktor = kullanici_uret(kullanici_adi="dr_mehmet", rol="doctor")
    ziyaret = _ziyaret_uret(db_oturum)
    ziyaret_id = ziyaret.id
    db_oturum.add(DoctorReview(
        visit_id=ziyaret_id,
        doctor_id=doktor.id,
        onaylanan_triage_code="Sarı",
        onaylanan_tetkikler=[],
    ))
    db_oturum.flush()

    db_oturum.delete(ziyaret)
    db_oturum.flush()

    assert db_oturum.query(DoctorReview).filter_by(visit_id=ziyaret_id).count() == 0


@pytest.mark.entegrasyon
def test_ayni_ziyarete_ikinci_inceleme_reddedilir(db_oturum, kullanici_uret):
    # visit_id üzerindeki tekillik kısıtı "bir ziyaret bir kez incelenir"in
    # veritabanı seviyesindeki karşılığı; uçtaki 409 kontrolünün yedeği.
    doktor = kullanici_uret(kullanici_adi="dr_zeynep", rol="doctor")
    ziyaret = _ziyaret_uret(db_oturum)

    for kod in ("Yeşil", "Sarı"):
        db_oturum.add(DoctorReview(
            visit_id=ziyaret.id,
            doctor_id=doktor.id,
            onaylanan_triage_code=kod,
            onaylanan_tetkikler=[],
        ))

    with pytest.raises(IntegrityError):
        db_oturum.flush()
```

- [ ] **Step 3: Testleri çalıştır, kırmızı olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/entegrasyon -v --no-cov
```
Beklenen: `ModuleNotFoundError: No module named 'app.models.doctor_review'`.

- [ ] **Step 4: Modeli yaz**

`app/models/doctor_review.py`:

```python
"""Doktorun bir yapay zekâ önerisini inceleyip onayladığı kaydı tutar."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class DoctorReview(Base):
    """Bir ziyaretin doktor onayı; AI önerisinin yerine geçmez, yanına yazılır."""

    __tablename__ = "doctor_reviews"

    id = Column(Integer, primary_key=True)
    # unique: bir ziyaret yalnızca bir kez incelenir — uçtaki 409'un veritabanı karşılığı.
    visit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Onayı veren doktor; istek gövdesinden değil JWT'deki kullanıcıdan okunur.
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Doktorun nihai triyaj kodu; yapay zekânınkinden farklı olabilir, fark korunur.
    onaylanan_triage_code = Column(String(20), nullable=False)
    # Doktorun onayladığı tetkik listesi; yapay zekânın listesini değiştirmiş olabilir.
    onaylanan_tetkikler = Column(JSON, nullable=False, default=list)
    # Serbest metin doktor notu; zorunlu değil (tasarım kararı K7).
    doktor_notu = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    visit = relationship("Visit", back_populates="review")

    def __repr__(self) -> str:
        return f"<DoctorReview visit={self.visit_id} kod={self.onaylanan_triage_code}>"
```

- [ ] **Step 5: `Visit` ilişkisini ekle**

`app/models/visit.py` içinde `Visit` sınıfına, mevcut `recommendation` ilişkisinin hemen
altına ekle:

```python
    # Doktor onayı (Gün 17-18); ziyaret silinince incelemesi de silinir.
    review = relationship(
        "DoctorReview",
        back_populates="visit",
        uselist=False,
        cascade="all, delete-orphan",
    )
```

- [ ] **Step 6: `__init__.py`'ye import et**

`app/models/__init__.py` — bu satır olmadan Alembic autogenerate tabloyu göremez:

```python
"""ORM modelleri.

Alembic'in autogenerate'i ve SQLAlchemy'nin ilişki çözümlemesi tüm modellerin
import edilmiş olmasını gerektirir; tek yerden toplanıyor.
"""

from app.models.doctor_review import DoctorReview
from app.models.user import User
from app.models.visit import AIRecommendation, Visit

__all__ = ["User", "Visit", "AIRecommendation", "DoctorReview"]
```

- [ ] **Step 7: Testleri çalıştır, yeşil olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/entegrasyon -v --no-cov
```
Beklenen: 3 passed. Testler `Base.metadata.create_all` sayesinde migration olmadan da
geçer — migration ayrı bir adımda, ayrıca doğrulanır (tasarım kararı K9).

- [ ] **Step 8: Migration üret**

Çalıştır:
```
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "doctor_reviews tablosu"
```

Üretilen dosyayı `app/db/alembic/versions/` altında AÇ ve kontrol et:
- `op.create_table('doctor_reviews', ...)` var mı?
- `visit_id` üzerinde unique kısıt/index var mı?
- `down_revision` bir önceki revizyonu (`7219b20bb9b5`) gösteriyor mu?

Migration BOŞSA: `app/models/__init__.py` importu eksiktir (Step 6). Ekleyip komutu
tekrarla.

Migration'da bu tablolarla ilgisiz `drop`/`alter` satırları varsa SİL — autogenerate
bazen modelle veritabanı arasındaki eski farkları da yakalar; bu görevin kapsamı yalnızca
`doctor_reviews`.

- [ ] **Step 9: Migration'ı uygula ve doğrula**

Çalıştır:
```
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic current
```
Beklenen: `alembic current` çıktısı yeni revizyonu ve `(head)` etiketini gösterir.

- [ ] **Step 10: Tüm paketi çalıştır**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest -m "not yavas" -q --no-cov
```
Beklenen: `73 passed`.

- [ ] **Step 11: Commit**

```bash
git add app/models/ app/db/alembic/versions/ tests/entegrasyon/
git commit -m "feat: DoctorReview modeli ve doctor_reviews migration"
```

---

### Task 3: GET /doctor/bekleyen

**Files:**
- Create: `app/schemas/doctor.py`
- Create: `app/api/doctor.py`
- Modify: `app/main.py:3` (import) ve dosya sonu (router kaydı)
- Test: `tests/api/test_doctor_api.py`

**Interfaces:**
- Consumes: `require_doctor_role` (Görev 1), `DoctorReview` (Görev 2), `Visit`,
  `AIRecommendation`, `Visit.recommendation` ilişkisi (mevcut)
- Produces: `app/schemas/doctor.py` içinde `DoktorTriyajKodu`, `AIOnerisi`,
  `BekleyenVaka`, `IncelemeIstegi`, `IncelemeYaniti`; `app/api/doctor.py` içinde `router`
  ve `_bekleyen_vakaya_cevir`. Görev 4 aynı iki dosyaya EKLEME yapar, yeniden yazmaz.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/api/test_doctor_api.py`:

```python
"""GET /doctor/bekleyen ve POST /doctor/inceleme sözleşmelerini dondurur."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.visit import AIRecommendation, Visit


def _ziyaret_ekle(db_oturum, durum="bekliyor", sikayet="Göğüs ağrısı var", oneri=True):
    """Verilen durumda bir ziyaret ve istenirse yapay zekâ önerisini yazar."""
    ziyaret = Visit(
        patient_age=50,
        gender="Erkek",
        symptom_text=sikayet,
        status=durum,
    )
    db_oturum.add(ziyaret)
    db_oturum.flush()
    if oneri:
        db_oturum.add(AIRecommendation(
            visit_id=ziyaret.id,
            triage_code="Sarı",
            department="Dahiliye",
            onerilen_tetkikler=["EKG"],
            ai_note="Gözlem önerilir.",
            sources=["protokol.pdf"],
        ))
        db_oturum.flush()
    return ziyaret


@pytest.fixture
def doktor_baslik(yetkili_baslik):
    """doctor rolünde hazır Authorization başlığı."""
    return yetkili_baslik(kullanici_adi="dr_ayse", rol="doctor")


@pytest.mark.entegrasyon
def test_bekleyen_liste_sadece_bekliyor_durumundakileri_dondurur(istemci, db_oturum, doktor_baslik):
    _ziyaret_ekle(db_oturum, durum="bekliyor", sikayet="Bekleyen vaka")
    _ziyaret_ekle(db_oturum, durum="tamamlandi", sikayet="Kapanmis vaka")

    yanit = istemci.get("/doctor/bekleyen", headers=doktor_baslik)

    assert yanit.status_code == 200
    sikayetler = [vaka["symptom_text"] for vaka in yanit.json()]
    assert "Bekleyen vaka" in sikayetler
    assert "Kapanmis vaka" not in sikayetler


@pytest.mark.entegrasyon
def test_liste_en_yeni_once_siralanir(istemci, db_oturum, doktor_baslik):
    # created_at varsayılanı iki kaydı aynı anda damgalayabildiği için
    # zaman değerleri testte açıkça ayrılıyor.
    simdi = datetime.now(timezone.utc)
    eski = _ziyaret_ekle(db_oturum, sikayet="Eski vaka", oneri=False)
    eski.created_at = simdi - timedelta(hours=2)
    yeni = _ziyaret_ekle(db_oturum, sikayet="Yeni vaka", oneri=False)
    yeni.created_at = simdi
    db_oturum.flush()

    yanit = istemci.get("/doctor/bekleyen", headers=doktor_baslik)

    sikayetler = [vaka["symptom_text"] for vaka in yanit.json()]
    assert sikayetler.index("Yeni vaka") < sikayetler.index("Eski vaka")


@pytest.mark.entegrasyon
def test_liste_sayfalanir(istemci, db_oturum, doktor_baslik):
    for sira in range(3):
        _ziyaret_ekle(db_oturum, sikayet=f"Vaka {sira}", oneri=False)

    ilk = istemci.get("/doctor/bekleyen?limit=2&offset=0", headers=doktor_baslik).json()
    ikinci = istemci.get("/doctor/bekleyen?limit=2&offset=2", headers=doktor_baslik).json()

    assert len(ilk) == 2
    assert len(ikinci) == 1
    # Sayfalar çakışmamalı: aynı vaka iki sayfada birden görünmemeli.
    assert {vaka["visit_id"] for vaka in ilk}.isdisjoint({vaka["visit_id"] for vaka in ikinci})


@pytest.mark.entegrasyon
def test_liste_ai_onerisini_de_icerir(istemci, db_oturum, doktor_baslik):
    # Doktor öneriyi görmek için ikinci bir isteğe zorlanmamalı.
    _ziyaret_ekle(db_oturum, sikayet="Onerili vaka")

    yanit = istemci.get("/doctor/bekleyen", headers=doktor_baslik)

    vaka = yanit.json()[0]
    assert vaka["ai_onerisi"]["triage_code"] == "Sarı"
    assert vaka["ai_onerisi"]["department"] == "Dahiliye"
    assert vaka["ai_onerisi"]["onerilen_tetkikler"] == ["EKG"]
    assert vaka["ai_onerisi"]["sources"] == ["protokol.pdf"]


@pytest.mark.entegrasyon
def test_jetonsuz_liste_401(istemci, db_oturum):
    _ziyaret_ekle(db_oturum)
    assert istemci.get("/doctor/bekleyen").status_code == 401
```

- [ ] **Step 2: Testleri çalıştır, kırmızı olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_doctor_api.py -v --no-cov
```
Beklenen: beş test de 404 alır (router henüz kayıtlı değil) — `assert 404 == 200` ve
`assert 404 == 401` şeklinde. Bu doğru kırmızıdır.

- [ ] **Step 3: Şemaları yaz**

`app/schemas/doctor.py` — Görev 4'ün kullanacağı `IncelemeIstegi` ve `IncelemeYaniti` da
şimdi yazılıyor, çünkü ikisi de aynı dosyada ve tek seferde yazmak daha temiz:

```python
"""Doktor uçlarının istek ve yanıt şemaları."""

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Doktorun onaylayabileceği triyaj kodları. "Belirsiz" bilerek yok: o yapay zekânın
# "karar veremedim" çıktısı, doktorun işi ise tam olarak belirsizliği gidermek.
DoktorTriyajKodu = Literal["Kırmızı", "Sarı", "Yeşil"]


class AIOnerisi(BaseModel):
    """Bekleyen vaka listesinde gömülü gelen yapay zekâ önerisi."""

    model_config = ConfigDict(from_attributes=True)

    triage_code: str
    department: str
    onerilen_tetkikler: list[str] = []
    ai_note: str
    sources: list[str] = []


class BekleyenVaka(BaseModel):
    """Doktorun listede gördüğü tek bir bekleyen başvuru."""

    visit_id: uuid.UUID
    patient_age: int
    gender: str
    symptom_text: str
    chronic_disease: Optional[str] = None
    vitals: Optional[dict] = None
    giris_tipi: str
    created_at: datetime
    # Öneri opsiyonel: yazma yolu ziyaret ve öneriyi birlikte yazıyor ama şema bunu
    # garanti etmiyor; önerisiz bir ziyarette uç çökmek yerine null döndürür.
    ai_onerisi: Optional[AIOnerisi] = None


class IncelemeIstegi(BaseModel):
    """Doktorun onay gövdesi; doctor_id bilinçli olarak yok, JWT'den okunur."""

    visit_id: uuid.UUID
    onaylanan_triage_code: DoktorTriyajKodu
    onaylanan_tetkikler: list[str] = []
    doktor_notu: Optional[str] = Field(None, max_length=1000)


class IncelemeYaniti(BaseModel):
    """Kaydedilen incelemenin geri dönüşü."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: uuid.UUID
    doctor_id: int
    onaylanan_triage_code: str
    onaylanan_tetkikler: list[str]
    doktor_notu: Optional[str] = None
    created_at: datetime
```

- [ ] **Step 4: Router'ı ve liste ucunu yaz**

`app/api/doctor.py`:

```python
"""Doktorun bekleyen vakaları görüp onayladığı uçlar."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.user import User
from app.models.visit import Visit
from app.schemas.doctor import AIOnerisi, BekleyenVaka
from app.services.auth_service import require_doctor_role

router = APIRouter(prefix="/doctor", tags=["Doctor"])


def _bekleyen_vakaya_cevir(ziyaret: Visit) -> BekleyenVaka:
    """Visit + AIRecommendation çiftini doktorun gördüğü tek şemaya indirger."""
    return BekleyenVaka(
        visit_id=ziyaret.id,
        patient_age=ziyaret.patient_age,
        gender=ziyaret.gender,
        symptom_text=ziyaret.symptom_text,
        chronic_disease=ziyaret.chronic_disease,
        vitals=ziyaret.vitals,
        giris_tipi=ziyaret.giris_tipi,
        created_at=ziyaret.created_at,
        ai_onerisi=(
            AIOnerisi.model_validate(ziyaret.recommendation)
            if ziyaret.recommendation
            else None
        ),
    )


@router.get("/bekleyen", response_model=list[BekleyenVaka])
def bekleyen_vakalar(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_doctor_role),
    db: Session = Depends(get_db),
):
    """Henüz incelenmemiş başvuruları, yapay zekâ önerisiyle birlikte döndürür."""
    # joinedload: öneri aynı sorguda gelsin, liste her vaka için ek sorgu açmasın.
    ziyaretler = (
        db.query(Visit)
        .options(joinedload(Visit.recommendation))
        .filter(Visit.status == "bekliyor")
        .order_by(Visit.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [_bekleyen_vakaya_cevir(ziyaret) for ziyaret in ziyaretler]
```

- [ ] **Step 5: Router'ı uygulamaya kaydet**

`app/main.py` — import satırına `doctor` ekle ve dosyanın sonuna kaydı ekle:

```python
from app.api import health, speech, ai, document, auth, doctor
```

```python
app.include_router(doctor.router)
```

- [ ] **Step 6: Testleri çalıştır, yeşil olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_doctor_api.py -v --no-cov
```
Beklenen: 5 passed.

- [ ] **Step 7: Tüm paketi çalıştır**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest -m "not yavas" -q --no-cov
```
Beklenen: `78 passed`.

- [ ] **Step 8: Commit**

```bash
git add app/api/doctor.py app/schemas/doctor.py app/main.py tests/api/test_doctor_api.py
git commit -m "feat: GET /doctor/bekleyen ucu ve doktor semalari"
```

---

### Task 4: POST /doctor/inceleme

**Files:**
- Modify: `app/api/doctor.py` (dosya sonuna ikinci uç; mevcut kodu yeniden yazma)
- Modify: `app/schemas/doctor.py` — Görev 3'te zaten yazıldı, **değişiklik gerekmiyor**;
  ihtiyaç çıkarsa yalnızca ekleme yap
- Test: `tests/api/test_doctor_api.py` (dosya sonuna 6 test ekle)

**Interfaces:**
- Consumes: `IncelemeIstegi`, `IncelemeYaniti` (Görev 3), `DoctorReview` (Görev 2),
  `require_doctor_role` (Görev 1), `_ziyaret_ekle` ve `doktor_baslik` (Görev 3'ün test
  dosyasında zaten tanımlı — yeniden tanımlama)
- Produces: `POST /doctor/inceleme`, başarıda `201 Created`

- [ ] **Step 1: Başarısız testleri yaz**

`tests/api/test_doctor_api.py` dosyasının SONUNA ekle. Dosyanın başına `import uuid` ve
`from app.models.doctor_review import DoctorReview` satırlarını eklemen gerekecek.

```python
def _onay_govdesi(visit_id, **degisiklikler) -> dict:
    """POST /doctor/inceleme için geçerli bir gövde; alanlar kwargs ile ezilebilir."""
    govde = {
        "visit_id": str(visit_id),
        "onaylanan_triage_code": "Kırmızı",
        "onaylanan_tetkikler": ["EKG", "Troponin"],
        "doktor_notu": "Acil servise alındı",
    }
    govde.update(degisiklikler)
    return govde


@pytest.mark.entegrasyon
def test_onay_ziyaret_durumunu_tamamlandi_yapar(istemci, db_oturum, doktor_baslik):
    ziyaret = _ziyaret_ekle(db_oturum)

    yanit = istemci.post(
        "/doctor/inceleme", json=_onay_govdesi(ziyaret.id), headers=doktor_baslik
    )

    assert yanit.status_code == 201
    db_oturum.refresh(ziyaret)
    assert ziyaret.status == "tamamlandi"


@pytest.mark.entegrasyon
def test_onayda_doktorun_degistirdigi_triyaj_kodu_kaydedilir(istemci, db_oturum, doktor_baslik):
    # Yapay zekâ "Sarı" demişti; doktor "Kırmızı" diyor ve doktorunki kaydedilir.
    ziyaret = _ziyaret_ekle(db_oturum)

    yanit = istemci.post(
        "/doctor/inceleme",
        json=_onay_govdesi(ziyaret.id, onaylanan_triage_code="Kırmızı"),
        headers=doktor_baslik,
    )

    assert yanit.json()["onaylanan_triage_code"] == "Kırmızı"
    kayit = db_oturum.query(DoctorReview).filter_by(visit_id=ziyaret.id).one()
    assert kayit.onaylanan_triage_code == "Kırmızı"


@pytest.mark.entegrasyon
def test_onayda_tetkik_listesi_degistirilebilir(istemci, db_oturum, doktor_baslik):
    # Yapay zekâ ["EKG"] önermişti; doktor listeyi tamamen değiştirebilmeli.
    ziyaret = _ziyaret_ekle(db_oturum)

    istemci.post(
        "/doctor/inceleme",
        json=_onay_govdesi(ziyaret.id, onaylanan_tetkikler=["Akciğer grafisi"]),
        headers=doktor_baslik,
    )

    kayit = db_oturum.query(DoctorReview).filter_by(visit_id=ziyaret.id).one()
    assert kayit.onaylanan_tetkikler == ["Akciğer grafisi"]


@pytest.mark.entegrasyon
def test_ai_onerisi_degismeden_saklanir(istemci, db_oturum, doktor_baslik):
    # Günün en önemli kuralı: onay, yapay zekânın orijinal önerisini ezmez.
    # İzlenebilirlik buna bağlı; Gün 23'ün ölçümü de bu farkı okuyacak.
    ziyaret = _ziyaret_ekle(db_oturum)

    istemci.post(
        "/doctor/inceleme",
        json=_onay_govdesi(
            ziyaret.id, onaylanan_triage_code="Kırmızı", onaylanan_tetkikler=["Troponin"]
        ),
        headers=doktor_baslik,
    )

    oneri = db_oturum.query(AIRecommendation).filter_by(visit_id=ziyaret.id).one()
    assert oneri.triage_code == "Sarı"
    assert oneri.onerilen_tetkikler == ["EKG"]


@pytest.mark.entegrasyon
def test_olmayan_ziyaret_icin_404(istemci, doktor_baslik):
    yanit = istemci.post(
        "/doctor/inceleme", json=_onay_govdesi(uuid.uuid4()), headers=doktor_baslik
    )
    assert yanit.status_code == 404


@pytest.mark.entegrasyon
def test_zaten_incelenmis_ziyaret_icin_409(istemci, db_oturum, doktor_baslik):
    ziyaret = _ziyaret_ekle(db_oturum)

    ilk = istemci.post(
        "/doctor/inceleme", json=_onay_govdesi(ziyaret.id), headers=doktor_baslik
    )
    assert ilk.status_code == 201

    ikinci = istemci.post(
        "/doctor/inceleme", json=_onay_govdesi(ziyaret.id), headers=doktor_baslik
    )
    assert ikinci.status_code == 409
```

- [ ] **Step 2: Testleri çalıştır, kırmızı olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_doctor_api.py -v --no-cov
```
Beklenen: yeni 6 test 404/405 alır (uç yok), Görev 3'ün 5 testi yeşil kalır.

- [ ] **Step 3: Onay ucunu yaz**

`app/api/doctor.py` dosyasının SONUNA ekle. Import bloğunu da genişlet:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.doctor_review import DoctorReview
from app.schemas.doctor import AIOnerisi, BekleyenVaka, IncelemeIstegi, IncelemeYaniti
```

```python
@router.post(
    "/inceleme", response_model=IncelemeYaniti, status_code=status.HTTP_201_CREATED
)
def inceleme_kaydet(
    istek: IncelemeIstegi,
    current_user: User = Depends(require_doctor_role),
    db: Session = Depends(get_db),
):
    """Doktorun onayını ayrı bir satır olarak yazar; AI önerisine dokunmaz."""
    ziyaret = db.query(Visit).filter(Visit.id == istek.visit_id).first()
    if ziyaret is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ziyaret bulunamadı"
        )

    mevcut = (
        db.query(DoctorReview).filter(DoctorReview.visit_id == istek.visit_id).first()
    )
    if mevcut is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Bu ziyaret zaten incelendi"
        )

    inceleme = DoctorReview(
        visit_id=istek.visit_id,
        # Doktor kimliği gövdeden değil jetondan: kimse başkasının adına onay yazamasın.
        doctor_id=current_user.id,
        onaylanan_triage_code=istek.onaylanan_triage_code,
        onaylanan_tetkikler=istek.onaylanan_tetkikler,
        doktor_notu=istek.doktor_notu,
    )
    db.add(inceleme)
    # Vaka kuyruktan düşer; AIRecommendation satırına BİLEREK dokunulmuyor.
    ziyaret.status = "tamamlandi"

    try:
        db.commit()
    except IntegrityError:
        # Yedek savunma: iki eşzamanlı onay yukarıdaki kontrolü birlikte geçerse
        # tekillik kısıtı devreye girer ve istek yine 409 ile döner.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Bu ziyaret zaten incelendi"
        )

    db.refresh(inceleme)
    return inceleme
```

- [ ] **Step 4: Testleri çalıştır, yeşil olduğunu gör**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest tests/api/test_doctor_api.py -v --no-cov
```
Beklenen: 11 passed.

- [ ] **Step 5: Tüm paketi çalıştır**

Çalıştır:
```
.venv\Scripts\python.exe -m pytest -m "not yavas" -q --no-cov
```
Beklenen: `84 passed` (taban 67 + bu günün 17'si).

- [ ] **Step 6: Commit**

```bash
git add app/api/doctor.py tests/api/test_doctor_api.py
git commit -m "feat: POST /doctor/inceleme ucu, 404 ve 409 davranisi"
```

---

## Görevler bittikten sonra: doğrulama

Bu adımlar kontrolcü tarafından, subagent'lar bittikten sonra yürütülür.

- [ ] **Migration gerçekten uygulandı mı**

```
.venv\Scripts\python.exe -m alembic current
```
Çıktı head revizyonunu göstermeli.

- [ ] **Kapsama ile birlikte tüm paket**

```
.venv\Scripts\python.exe -m pytest -m "not yavas"
```
`84 passed` ve `app/` kapsaması taban %72'nin altına düşmemeli.

- [ ] **Seed hesaplarını üret**

```
.venv\Scripts\python.exe scripts/seed_users.py
```
Çıktıda `doctor` hesabının rolü `doctor`, `hasta` hesabının rolü `user` görünmeli.

- [ ] **Uçlar canlıda çalışıyor mu**

Backend'i başlat (8000 portunu başka proje tutuyorsa önce onu kapat):
```
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Jeton al ve listeyi çek:
```
curl -X POST http://localhost:8000/auth/login -d "username=doctor&password=doctor123"
curl -H "Authorization: Bearer <doktor_jetonu>" http://localhost:8000/doctor/bekleyen
```

- [ ] **İzlenebilirlik kanıtı (mentöre gösterilecek)**

Bir vakayı onayla, sonra yapay zekâ önerisinin değişmediğini SQL ile göster:
```sql
SELECT v.status,
       a.triage_code            AS ai_kodu,
       d.onaylanan_triage_code  AS doktor_kodu
FROM visits v
JOIN ai_recommendations a ON a.visit_id = v.id
JOIN doctor_reviews d     ON d.visit_id = v.id
ORDER BY v.created_at DESC
LIMIT 5;
```
`ai_kodu` ile `doktor_kodu` farklı olabilir; olması gereken de bu.

---

## Bitti sayılır

- [ ] `doctor` rolü var, `require_doctor_role` yazıldı, `seed_users.py` üç hesabı üretiyor
- [ ] `doctor_reviews` tablosu migration ile oluştu, `alembic current` = head
- [ ] `GET /doctor/bekleyen` ve `POST /doctor/inceleme` çalışıyor
- [ ] 17 testin tamamı önce kırmızı görüldü, şimdi yeşil
- [ ] Mevcut 67 test hâlâ yeşil (toplam 84)
- [ ] Onaydan sonra `AIRecommendation` değişmiyor (test + SQL kanıtı)
- [ ] Her yeni fonksiyon/sütun yanında tek cümlelik Türkçe açıklama var
- [ ] Dal `main`'e birleşti
