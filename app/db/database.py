"""SQLAlchemy motoru, oturum fabrikası ve FastAPI bağımlılığı."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config.config import settings

# pool_pre_ping: Postgres bağlantısı koptuğunda (konteyner yeniden başlarsa)
# ilk sorguda sessizce yeniden bağlanır, "server closed the connection" hatasını önler.
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """Her istek için bir oturum açar ve istek bitince kapatır."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
