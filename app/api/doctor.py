"""Doktorun bekleyen vakaları görüp onayladığı uçlar."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.doctor_review import DoctorReview
from app.models.user import User
from app.models.visit import Visit
from app.schemas.doctor import AIOnerisi, BekleyenVaka, IncelemeIstegi, IncelemeYaniti
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
