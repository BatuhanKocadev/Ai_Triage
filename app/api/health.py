from fastapi import APIRouter, status
from pydantic import BaseModel
router = APIRouter(
    prefix="/health",
    tags=["Sistem Durumu"]
)
class SistemDurumYaniti(BaseModel):
    durum: str
    mesaj: str

@router.get("/", response_model=SistemDurumYaniti, status_code=status.HTTP_200_OK)
async def sistem_kontrol():
    return {
        "durum": "basarili",
        "mesaj": "Tıbbi Triyaj API sorunsuz çalışıyor."
    }