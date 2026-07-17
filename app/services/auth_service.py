from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.schemas.auth import TokenData

SECRET_KEY = "ai_triage_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

mock_database = {
    "admin": {
        "username": "admin",
        "hashed_password": password_context.hash("admin123"),
        "role": "admin"
    },
    "doctor": {
        "username": "doctor",
        "hashed_password": password_context.hash("doctor123"),
        "role": "user"
    }
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)

def get_user(username: str) -> dict:
    if username in mock_database:
        return mock_database[username]
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    data_to_encode = data.copy()
    if expires_delta:
        expire_time = datetime.now(timezone.utc) + expires_delta
    else:
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=15)
    data_to_encode.update({"exp": expire_time})
    return jwt.encode(data_to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
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
        
    user = get_user(username=token_data.username)
    if user is None:
        raise auth_exception
    return user

async def require_admin_role(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )
    return current_user

async def require_user_or_admin_role(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied."
        )
    return current_user