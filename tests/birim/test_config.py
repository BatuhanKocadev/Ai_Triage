"""Ayarların ortam değişkenlerinden okunduğunu doğrular."""

from app.config.config import settings


def test_ayarlar_env_dosyasindan_okunur():
    # conftest'in ayarladığı test anahtarı okunmalı; üretim varsayılanı değil.
    assert settings.jwt_secret_key == "test-anahtari-sadece-testler-icin"


def test_veritabani_url_test_veritabanini_gosterir():
    # Testler asla üretim veritabanına (ai_triage) bağlanmamalı.
    assert settings.database_url.endswith("/ai_triage_test")
