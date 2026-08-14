"""gun22 kisitlar"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '6922a872c59d'
down_revision: Union[str, Sequence[str], None] = '72dffb9e5194'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Bir ziyarete iki öneri yazılmasını engeller (Gün 22).
    op.drop_index("ix_ai_recommendations_visit_id", table_name="ai_recommendations")
    op.create_unique_constraint(
        "uq_ai_recommendations_visit_id", "ai_recommendations", ["visit_id"]
    )
    # Gün 23'ün doktor bazlı raporlaması bu index'i isteyecek.
    op.create_index(
        "ix_doctor_reviews_doctor_id", "doctor_reviews", ["doctor_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # İki değişikliği de geri alır: doctor_id index'i düşer, unique kısıt kalkar
    # ve yerine eski düz index geri gelir. Unique kısıt düşerken arkasındaki
    op.drop_index("ix_doctor_reviews_doctor_id", table_name="doctor_reviews")
    op.drop_constraint(
        "uq_ai_recommendations_visit_id", "ai_recommendations", type_="unique"
    )
    op.create_index(
        "ix_ai_recommendations_visit_id", "ai_recommendations", ["visit_id"], unique=False
    )
