"""Parola hash'leme ve JWT üretimi/doğrulaması davranışını dondurur."""

from datetime import timedelta

import pytest
from jose import JWTError, jwt

from app.config.config import settings
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)


def test_parola_hashlenir_ve_dogrulanir():
    hash_degeri = hash_password("parola123")
    # bcrypt hash'i asla düz metne eşit olmamalı.
    assert hash_degeri != "parola123"
    assert verify_password("parola123", hash_degeri) is True


def test_gecersiz_parola_reddedilir():
    hash_degeri = hash_password("parola123")
    assert verify_password("yanlis_parola", hash_degeri) is False


def test_ayni_parola_farkli_hash_uretir():
    # bcrypt her seferinde farklı tuz kullanır; iki hash aynı olmamalı.
    assert hash_password("parola123") != hash_password("parola123")


def test_jeton_kullanici_adi_ve_rol_tasir():
    jeton = create_access_token({"sub": "ahmet", "role": "admin"})
    icerik = jwt.decode(jeton, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert icerik["sub"] == "ahmet"
    assert icerik["role"] == "admin"


def test_suresi_dolmus_jeton_reddedilir():
    # Negatif süre ile üretilen jeton geçmişte sona ermiş olur.
    jeton = create_access_token({"sub": "ahmet", "role": "user"}, expires_delta=timedelta(minutes=-1))
    # ExpiredSignatureError, JWTError'ın alt sınıfıdır; auth_service de JWTError yakalıyor.
    with pytest.raises(JWTError):
        jwt.decode(jeton, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
