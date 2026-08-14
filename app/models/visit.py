"""Hasta ziyareti ve o ziyarete ait yapay zekâ önerisi tabloları."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class Visit(Base):
    """Bir hastanın tek bir başvurusu (şikayet + demografi + vitaller)."""

    __tablename__ = "visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)
    symptom_text = Column(String, nullable=False)
    chronic_disease = Column(String, nullable=True)
    vitals = Column(JSON, nullable=True)
    # Şikayetin geliş kanalı ("ses"/"metin"): doktor transkript hatası ihtimalini
    # bilmeli, rapor da "vakaların %X'i sesli girildi" diyebilmeli.
    giris_tipi = Column(String(10), default="metin", server_default="metin", nullable=False)
    # bekliyor -> incelendi -> tamamlandi
    status = Column(String(20), default="bekliyor", nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    recommendation = relationship(
        "AIRecommendation",
        back_populates="visit",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Doktor onayı (Gün 17-18); ziyaret silinince incelemesi de silinir.
    review = relationship(
        "DoctorReview",
        back_populates="visit",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Visit {self.id} ({self.status})>"


class AIRecommendation(Base):
    """Bir ziyaret için modelin ürettiği triyaj ve tetkik önerisi."""

    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True)
    visit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visits.id", ondelete="CASCADE"),
        nullable=False,
        # unique: bir ziyaretin en fazla bir önerisi olur. Visit.recommendation
        # ilişkisi zaten uselist=False diyordu; kısıt onu veritabanında da
        unique=True,
    )
    triage_code = Column(String(20), nullable=False)
    department = Column(String(100), nullable=False)
    onerilen_tetkikler = Column(JSON, default=list)
    ai_note = Column(String, nullable=True)
    sources = Column(JSON, default=list)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    visit = relationship("Visit", back_populates="recommendation")

    def __repr__(self) -> str:
        return f"<AIRecommendation {self.triage_code} / {self.department}>"
