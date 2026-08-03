"""GET /doctor/bekleyen ve POST /doctor/inceleme sözleşmelerini dondurur."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.doctor_review import DoctorReview
from app.models.user import User
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


@pytest.fixture
def hasta_baslik(yetkili_baslik):
    """user rolünde hazır Authorization başlığı; doktor uçları bunu reddetmeli."""
    return yetkili_baslik(kullanici_adi="hasta_ali", rol="user")


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
    # gender ile giris_tipi aynı tipte olduğu için response_model ikisinin yer
    # değiştirmesini yakalayamaz; eşleme burada tek tek sabitleniyor.
    assert vaka["gender"] == "Erkek"
    assert vaka["giris_tipi"] == "metin"
    assert vaka["ai_onerisi"]["triage_code"] == "Sarı"
    assert vaka["ai_onerisi"]["department"] == "Dahiliye"
    assert vaka["ai_onerisi"]["onerilen_tetkikler"] == ["EKG"]
    assert vaka["ai_onerisi"]["sources"] == ["protokol.pdf"]


@pytest.mark.entegrasyon
def test_jetonsuz_liste_401(istemci, db_oturum):
    _ziyaret_ekle(db_oturum)
    assert istemci.get("/doctor/bekleyen").status_code == 401


@pytest.mark.entegrasyon
def test_user_rolu_bekleyen_listesine_403_alir(istemci, db_oturum, hasta_baslik):
    # Uçun require_doctor_role yerine sıradan bir kimlik bağımlılığına kayması
    # hasta şikayet metnini user rolüne açardı; bu test o gerilemeyi yakalar.
    _ziyaret_ekle(db_oturum)

    yanit = istemci.get("/doctor/bekleyen", headers=hasta_baslik)

    assert yanit.status_code == 403


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
    # Onaylayan doktor JWT'den okunmalı: doctor_id'nin istek gövdesinden ya da
    # sabit bir değerden gelmeye kayması bu satırla yakalanır.
    doktor = db_oturum.query(User).filter_by(username="dr_ayse").one()
    assert kayit.doctor_id == doktor.id


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
    # Mesaj da sabitleniyor: yoksa test "rota yok" ile "ziyaret yok" durumlarını
    # birbirinden ayıramaz ve rota silinse bile yeşil kalırdı.
    assert yanit.json()["detail"] == "Ziyaret bulunamadı"


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
    # Reddedilen istek hiçbir şey yazmamış olmalı: ziyarete ait tek satır kalır.
    assert db_oturum.query(DoctorReview).filter_by(visit_id=ziyaret.id).count() == 1


@pytest.mark.entegrasyon
def test_user_rolu_inceleme_ucuna_403_alir(istemci, db_oturum, hasta_baslik):
    # Onay ucu require_doctor_role'dan koparsa hasta kendi triyajını onaylayabilirdi;
    # bu test o gerilemeyi uç seviyesinde yakalar.
    ziyaret = _ziyaret_ekle(db_oturum)

    yanit = istemci.post(
        "/doctor/inceleme", json=_onay_govdesi(ziyaret.id), headers=hasta_baslik
    )

    assert yanit.status_code == 403
