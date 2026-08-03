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
