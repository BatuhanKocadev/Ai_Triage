from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum # YENİ EKLENDİ: Enum sınıfını dahil ettik

router = APIRouter(
    prefix="/ai",
    tags=["Yapay Zekâ Analizi"]
)

# --- 1. YENİ EKLENDİ: ENUM SINIFI ---
class Cinsiyet(str, Enum):
    erkek = "Erkek"
    kadin = "Kadın"
    diger = "Diğer"

# --- 2. YENİ EKLENDİ: NESTED (İÇ İÇE) MODEL ---
# Bu model tek başına çalışmayacak, ana modelin içinde bir "grup" olarak yer alacak.
class VitalBulgular(BaseModel):
    ates: Optional[float] = Field(None, description="Hastanın vücut ısısı (örn: 36.5)")
    nabiz: Optional[int] = Field(None, description="Dakikadaki kalp atım hızı (örn: 85)")

# --- 3. ANA REQUEST MODELİ ---
class SemptomAnalizIstegi(BaseModel):
    hasta_yasi: int = Field(..., ge=0, le=120, description="Hastanın yaşı")
    
    # Enum kullanımı: Cinsiyet değişkeni artık sadece Cinsiyet sınıfındaki değerleri alabilir.
    cinsiyet: Cinsiyet 
    
    semptom_metni: str = Field(..., min_length=10, max_length=500)
    kronik_hastalik: Optional[str] = Field(None)
    
    # Nested Model kullanımı: vitaller değişkeninin tipi, yukarıda yazdığımız VitalBulgular modeli oldu.
    vitaller: Optional[VitalBulgular] = None

# --- 4. RESPONSE MODELİ ---
class TriageSonucYaniti(BaseModel):
    durum: str
    triyaj_kodu: str           
    yonlendirilecek_birim: str 
    yapay_zeka_notu: str

# --- 5. ENDPOINT ---
@router.post("/analiz", response_model=TriageSonucYaniti, status_code=status.HTTP_200_OK)
async def semptom_analizi(istek: SemptomAnalizIstegi):
    
    # Eğer vitaller girildiyse mesajımızı ona göre zenginleştiriyoruz
    vital_mesaji = f" (Ateş: {istek.vitaller.ates}, Nabız: {istek.vitaller.nabiz})" if istek.vitaller else ""
    
    return {
        "durum": "basarili",
        "triyaj_kodu": "Sarı",
        "yonlendirilecek_birim": "Dahiliye",
        "yapay_zeka_notu": f"{istek.cinsiyet.value}, {istek.hasta_yasi} yaşındaki hastanın '{istek.semptom_metni}' şikayeti sisteme işlendi.{vital_mesaji}"
    }