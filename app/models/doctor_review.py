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
