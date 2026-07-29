from pydantic import BaseModel, ConfigDict
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserInfo(BaseModel):
    """/auth/me yanıtı. Parola hash'i bilinçli olarak dışarıda bırakıldı."""
    model_config = ConfigDict(from_attributes=True)

    username: str
    role: str