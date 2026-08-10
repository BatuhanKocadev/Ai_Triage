import os
import tempfile
import time

from fastapi import APIRouter, status, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr # YENİ: EmailStr eklendi
import uuid # YENİ: UUID kütüphanesi eklendi

from app.config.config import settings
from app.models.user import User
from app.schemas.speech import TranskriptYaniti
from app.services.auth_service import require_user_or_admin_role
from app.services.stt_service import transcribe, STTError
from app.utils.hiz_sinirlayici import genel_sinirlayici, hiz_siniri
from app.utils.logger import logger

router = APIRouter(
    prefix="/speech",
    tags=["Ses İşleme (Speech-to-Text)"]
)

DESTEKLENEN_UZANTILAR = {".wav", ".mp3", ".m4a", ".ogg", ".webm"}
MAKS_DOSYA_BOYUTU = 25 * 1024 * 1024  # 25 MB
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


# /ai/analiz ile aynı pahalı sınıf: whisper "medium" modelini yükleyip 25 MB'a
# kadar dosyayı işliyor, yani kötüye kullanım CPU'yu ve belleği tüketir —
# kimlik doğrulaması tek başına hız sınırı değildir (10 Ağustos 2026).
@router.post(
    "/transkript",
    response_model=TranskriptYaniti,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(hiz_siniri(genel_sinirlayici))],
)
async def ses_dosyasini_transkript_et(
    file: UploadFile = File(...),
    current_user: User = Depends(require_user_or_admin_role),
):
    dosya_uzantisi = os.path.splitext(file.filename or "")[1].lower()
    if dosya_uzantisi not in DESTEKLENEN_UZANTILAR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Desteklenmeyen dosya formatı: {dosya_uzantisi or 'bilinmiyor'}"
        )

    dosya_icerigi = await file.read()
    if len(dosya_icerigi) > MAKS_DOSYA_BOYUTU:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya boyutu 25 MB sınırını aşıyor"
        )

    gecici_dosya = tempfile.NamedTemporaryFile(suffix=dosya_uzantisi, delete=False)
    gecici_dosya_yolu = gecici_dosya.name
    try:
        # Windows'ta delete=True ile açık kalan dosyayı başka bir kütüphane
        # okuyamaz; bu yüzden önce kapatıp öyle okutuyoruz.
        gecici_dosya.write(dosya_icerigi)
        gecici_dosya.close()

        baslangic = time.perf_counter()
        try:
            metin = transcribe(gecici_dosya_yolu)
        except STTError as exc:
            logger.error(f"STT hatası (kullanıcı={current_user.username}): {exc}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ses anlaşılamadı, lütfen tekrar deneyin"
            )
        sure_saniye = time.perf_counter() - baslangic

        if not metin.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ses anlaşılamadı, lütfen tekrar deneyin"
            )

        # Şikayet metni (sağlık verisi) loglanmıyor; sadece uzunluk ve süre.
        logger.info(
            f"Transkript tamamlandı: kullanıcı={current_user.username}, "
            f"uzunluk={len(metin)} karakter, süre={sure_saniye:.2f}sn"
        )

        return TranskriptYaniti(
            transcript=metin,
            sure_saniye=round(sure_saniye, 2),
            model=settings.whisper_model_size,
        )
    finally:
        os.remove(gecici_dosya_yolu)