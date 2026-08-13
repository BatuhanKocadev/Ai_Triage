"""Kimlik doğrulama ve rol kontrolü.

Kullanıcılar artık bellekteki mock_database yerine PostgreSQL'deki `users`
tablosunda tutuluyor. Bağımlılıklar `User` ORM nesnesi döndürür.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import TokenData

# Gizli anahtar artık kodda gömülü değil; .env / ortam değişkeninden geliyor.
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Var olmayan kullanıcıda da bcrypt maliyeti ödemek için sabit hash
# ("timing-oracle-pad"). Import'ta hash üretilmez — app.main açılışı yavaşlamasın.
SAHTE_PAROLA_HASH = (
    "$2b$12$N/foJk/tMRglJHd7PRt9OOeutbWqq4UnL.kXgZJrgqoefehHaBRmK"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    return password_context.hash(plain_password)


def get_user(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    data_to_encode = data.copy()
    if expires_delta:
        expire_time = datetime.now(timezone.utc) + expires_delta
    else:
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=15)
    data_to_encode.update({"exp": expire_time})
    return jwt.encode(data_to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise auth_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise auth_exception

    user = get_user(db, username=token_data.username)
    if user is None:
        raise auth_exception
    return user


async def require_admin_role(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )
    return current_user


async def require_user_or_admin_role(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    return current_user


async def require_doctor_role(current_user: User = Depends(get_current_user)) -> User:
    """Doktor veya admin rolü gerektiren uçları korur."""
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required."
        )
    return current_user
