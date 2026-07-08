from fastapi import APIRouter

# speech prefix'i ile bir router oluşturuyoruz
router = APIRouter(
    prefix="/speech",
    tags=["Ses İşleme (Speech-to-Text)"]
)

@router.get("/")
async def speech_test():
    return {"mesaj": "Ses işleme modülü hazır."}