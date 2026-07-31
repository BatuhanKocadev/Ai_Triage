from pydantic import BaseModel


class TranskriptYaniti(BaseModel):
    transcript: str
    sure_saniye: float
    model: str
