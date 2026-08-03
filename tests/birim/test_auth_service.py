"""Parola hash'leme ve JWT üretimi/doğrulaması davranışını dondurur."""

import asyncio
from datetime import timedelta

import pytest
from fastapi import HTTPException
from jose import JWTError, jwt

from app.config.config import settings
from app.models.user import User
from app.services.auth_service import (
    create_access_token,
    hash_password,
    require_doctor_role,
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


def _rolde_kullanici(rol: str) -> User:
    """Veritabanına yazmadan, yalnızca rolü doldurulmuş bir User nesnesi üretir."""
    return User(username=f"{rol}_kullanici", hashed_password="onemsiz", role=rol)


def test_doktor_rolu_bekleyen_vakalari_gorebilir():
    # require_doctor_role, doctor rolündeki kullanıcıyı olduğu gibi geri vermeli.
    kullanici = _rolde_kullanici("doctor")
    assert asyncio.run(require_doctor_role(current_user=kullanici)) is kullanici


def test_user_rolu_doktor_ucuna_403_alir():
    # Hasta başvurusu giren "user" rolü doktor uçlarına giremez.
    with pytest.raises(HTTPException) as hata:
        asyncio.run(require_doctor_role(current_user=_rolde_kullanici("user")))
    assert hata.value.status_code == 403


def test_admin_doktor_uclarina_erisebilir():
    # Karar: admin her şeyi görür (tasarım dokümanı K1).
    kullanici = _rolde_kullanici("admin")
    assert asyncio.run(require_doctor_role(current_user=kullanici)) is kullanici
