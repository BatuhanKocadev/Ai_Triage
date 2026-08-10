"""Bir ziyaretin en fazla bir yapay zekâ önerisi olabileceğini veritabanı
seviyesinde dondurur.

Bu kural bugün yalnızca ORM'de vardı: Visit.recommendation ilişkisi
`uselist=False` diyor ama sütunda unique kısıtı yoktu. İkinci bir öneri satırı
yazılabilseydi ilişki yalanlanır, ayrıca doktor kuyruğundaki joinedload + LIMIT
sorgusu 20 satır yerine 19 farklı ziyaret döndürüp bekleyen bir vakayı SESSİZCE
düşürürdü — kuyruktan kaybolan hasta demek.
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.visit import AIRecommendation, Visit


@pytest.mark.entegrasyon
def test_ayni_ziyarete_ikinci_oneri_yazilamaz(db_oturum):
    ziyaret = Visit(
        id=uuid.uuid4(),
        patient_age=44,
        gender="Kadın",
        symptom_text="Göğsümde sıkışma var",
        status="bekliyor",
    )
    db_oturum.add(ziyaret)
    db_oturum.flush()

    db_oturum.add(
        AIRecommendation(
            visit_id=ziyaret.id,
            triage_code="Kırmızı",
            department="Kardiyoloji",
            onerilen_tetkikler=["EKG"],
        )
    )
    db_oturum.flush()

    # İkinci öneri: veritabanı reddetmeli.
    db_oturum.add(
        AIRecommendation(
            visit_id=ziyaret.id,
            triage_code="Yeşil",
            department="Dahiliye",
            onerilen_tetkikler=[],
        )
    )

    with pytest.raises(IntegrityError):
        db_oturum.flush()
