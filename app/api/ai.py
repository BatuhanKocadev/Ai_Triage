from fastapi import APIRouter

# ai prefix'i ile bir router oluşturuyoruz
router = APIRouter(
    prefix="/ai",
    tags=["Yapay Zekâ Analizi"]
)

@router.get("/")
async def ai_test():
    return {"mesaj": "Yapay zekâ modülü hazır."}