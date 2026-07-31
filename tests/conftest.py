"""Tüm testlerin gördüğü ortak yapılandırma ve fixture'lar."""

# DİKKAT: Bu blok her `app` import'undan ÖNCE gelmek zorunda.
# app/db/database.py import edilir edilmez create_engine(settings.database_url)
# çalışıyor; ortam burada ayarlanmazsa testler gerçek `ai_triage` veritabanına bağlanır.
import os

os.environ.setdefault("DATABASE_URL", "postgresql://triage:triage@localhost:5432/ai_triage_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-anahtari-sadece-testler-icin")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")

import pytest  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config.config import settings  # noqa: E402
from app.db.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
# Modeller Base.metadata'ya kaydolsun diye açıkça import ediliyor;
# yoksa create_all boş şema üretir.
from app.models.user import User  # noqa: E402,F401
from app.models.visit import AIRecommendation, Visit  # noqa: E402,F401


@pytest.fixture(scope="session")
def test_motoru():
    """Test veritabanına tek bir motor açar ve şemayı bir kez kurar."""
    motor = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=motor)
    yield motor
    Base.metadata.drop_all(bind=motor)
    motor.dispose()


@pytest.fixture
def db_oturum(test_motoru):
    """Her teste kendi işlemini verir; test bitince geri alır (izolasyon)."""
    baglanti = test_motoru.connect()
    islem = baglanti.begin()
    Oturum = sessionmaker(
        bind=baglanti,
        autoflush=False,
        autocommit=False,
        # KRİTİK: /ai/analiz içindeki _kaydet() db.commit() çağırıyor. Bu ayar
        # olmadan o commit dış işlemi kapatır, aşağıdaki rollback etkisiz kalır
        # ve testler birbirine veri sızdırır.
        join_transaction_mode="create_savepoint",
    )
    oturum = Oturum()
    try:
        yield oturum
    finally:
        oturum.close()
        islem.rollback()  # test ne yazdıysa silinir
        baglanti.close()


@pytest.fixture
def istemci(db_oturum):
    """get_db'yi test oturumuyla değiştirilmiş TestClient döndürür."""
    def _test_oturumu():
        yield db_oturum

    app.dependency_overrides[get_db] = _test_oturumu
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def kullanici_uret(db_oturum):
    """İstenen rolde kullanıcı üreten fabrika; parolayı gerçek hash'le yazar."""
    from app.services.auth_service import hash_password

    def _uret(kullanici_adi="test_kullanici", parola="parola123", rol="user"):
        kullanici = User(
            username=kullanici_adi,
            hashed_password=hash_password(parola),
            role=rol,
        )
        db_oturum.add(kullanici)
        db_oturum.flush()
        return kullanici

    return _uret


@pytest.fixture
def jeton_uret():
    """Verilen kullanıcı adı ve rol için geçerli bir JWT üretir."""
    from app.services.auth_service import create_access_token

    def _uret(kullanici_adi="test_kullanici", rol="user"):
        return create_access_token({"sub": kullanici_adi, "role": rol})

    return _uret


@pytest.fixture
def yetkili_baslik(kullanici_uret, jeton_uret):
    """Hazır Authorization başlığı: kullanıcıyı yaratır ve jetonunu döndürür."""
    def _uret(kullanici_adi="test_kullanici", rol="user"):
        kullanici_uret(kullanici_adi=kullanici_adi, rol=rol)
        jeton = jeton_uret(kullanici_adi=kullanici_adi, rol=rol)
        return {"Authorization": f"Bearer {jeton}"}

    return _uret
