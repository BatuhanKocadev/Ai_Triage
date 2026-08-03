"""ORM modelleri.

Alembic'in autogenerate'i ve SQLAlchemy'nin ilişki çözümlemesi tüm modellerin
import edilmiş olmasını gerektirir; tek yerden toplanıyor.
"""

from app.models.doctor_review import DoctorReview
from app.models.user import User
from app.models.visit import AIRecommendation, Visit

__all__ = ["User", "Visit", "AIRecommendation", "DoctorReview"]
