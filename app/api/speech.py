from fastapi import APIRouter, status
from pydantic import BaseModel, Field, EmailStr # YENİ: EmailStr eklendi
import uuid # YENİ: UUID kütüphanesi eklendi

router = APIRouter(
    prefix="/speech",
    tags=["Ses İşleme (Speech-to-Text)"]
)
class SpeechRequest(BaseModel):
    patientId: int = Field(..., gt=0)
    hasta_email: EmailStr = Field(..., description="Hastanın geçerli e-posta adresi")
    doctorId: str = Field(..., pattern=r"^DR-\d{4}$", description="Doktor sicil no (Örn: DR-1234)")
    visitId: uuid.UUID = Field(..., description="Evrensel benzersiz ziyaret numarası (UUID)")
    transcript: str = Field(..., min_length=5, max_length=1000, description="Ses kaydından dönüştürülen metin")
class SesYaniti(BaseModel):
    durum: str
    mesaj: str
@router.post("/kaydet", response_model=SesYaniti, status_code=status.HTTP_200_OK)
async def ses_metnini_kaydet(istek: SpeechRequest):
    return {
        "durum": "basarili",
        "mesaj": f"Tüm kurallar (UUID, Regex, Email, Min/Max) başarıyla doğrulandı. Doktor: {istek.doctorId}"
    }