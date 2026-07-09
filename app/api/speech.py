from fastapi import APIRouter, status
from pydantic import BaseModel, Field, EmailStr # YENİ: EmailStr eklendi
import uuid # YENİ: UUID kütüphanesi eklendi

router = APIRouter(
    prefix="/speech",
    tags=["Ses İşleme (Speech-to-Text)"]
)

# --- REHBERDEKİ TÜM KURALLARI İÇEREN REQUEST MODELİ ---
class SpeechRequest(BaseModel):
    patientId: int = Field(..., gt=0)
    
    # 1. YENİ EKLENDİ (Email Doğrulama): Sadece geçerli e-posta formatını kabul eder.
    hasta_email: EmailStr = Field(..., description="Hastanın geçerli e-posta adresi")
    
    # 2. YENİ EKLENDİ (Regex Doğrulama): 'DR-' ile başlamak ve ardından 4 rakam gelmek ZORUNDA (Örn: DR-1024)
    doctorId: str = Field(..., pattern=r"^DR-\d{4}$", description="Doktor sicil no (Örn: DR-1234)")
    
    # 3. YENİ EKLENDİ (UUID Doğrulama): Rastgele sayılar yerine evrensel benzersiz ID (UUID formatı) zorunlu kılındı.
    visitId: uuid.UUID = Field(..., description="Evrensel benzersiz ziyaret numarası (UUID)")
    
    # 4 & 5. ZATEN UYDUĞUMUZ (Min / Max Karakter Doğrulama)
    transcript: str = Field(..., min_length=5, max_length=1000, description="Ses kaydından dönüştürülen metin")

# --- RESPONSE MODELİ ---
class SesYaniti(BaseModel):
    durum: str
    mesaj: str

# --- ENDPOINT ---
@router.post("/kaydet", response_model=SesYaniti, status_code=status.HTTP_200_OK)
async def ses_metnini_kaydet(istek: SpeechRequest):
    return {
        "durum": "basarili",
        "mesaj": f"Tüm kurallar (UUID, Regex, Email, Min/Max) başarıyla doğrulandı. Doktor: {istek.doctorId}"
    }