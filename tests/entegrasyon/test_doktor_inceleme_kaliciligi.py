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
