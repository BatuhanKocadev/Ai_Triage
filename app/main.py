import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, speech, ai, document, auth, doctor
from app.config.config import settings
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Tıbbi Triyaj Pipeline API başlatılıyor...")
    yield
    logger.info("Tıbbi Triyaj Pipeline API kapatılıyor...")

app = FastAPI(
    title="Tıbbi Triyaj Pipeline API",
    description=(
        "Hastalardan alınan ses kayıtlarını metne çeviren (Speech-to-Text) "
        "ve OpenAI modelleri kullanarak semptom analizi gerçekleştiren "
        "yapay zekâ destekli modern REST servis."
    ),
    version="1.0.0",
    contact={
        "name": "Batuhan Koca",
        "url": "https://github.com/BatuhanKocadev/Ai_Triage.git",
        "email": "batuhankocadev@gmail.com",
    },
    license_info={
        "name": "MIT License",
    },
    lifespan=lifespan
)

# İzinli origin'ler ayardan okunuyor; "*" bırakmak herhangi bir siteden tarayıcı
# üzerinden çağrı yapılmasına izin verirdi (Gün 21).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[k.strip() for k in settings.cors_origins.split(",") if k.strip()],
    # False: kimlik doğrulama Bearer başlığıyla yapılıyor, projede hiç çerez yok —
    # yani açık olmasının hiçbir faydası yok, buna karşılık ayar "*" yapıldığında
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_basliklari(request: Request) -> dict[str, str]:
    """Global 500 handler CORS middleware'inin dışında doğduğu için başlıkları elle ekler."""
    origin = request.headers.get("origin")
    if not origin:
        return {}
    izinliler = [k.strip() for k in settings.cors_origins.split(",") if k.strip()]
    if origin not in izinliler and "*" not in izinliler:
        return {}
    # "*" + credentials yasak deseni; credentials kapalı, yine de açık origin yaz.
    return {
        "Access-Control-Allow-Origin": origin if "*" not in izinliler else "*",
        "Vary": "Origin",
    }


@app.exception_handler(Exception)
async def beklenmeyen_hata_yakalayici(request: Request, hata: Exception):
    """Beklenmeyen istisnada tam izi log'a yazar, istemciye yalnızca kod döner."""
    izleme_kodu = uuid.uuid4().hex[:8]
    logger.exception(
        f"[{izleme_kodu}] Beklenmeyen hata: {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Sunucu hatası", "izleme_kodu": izleme_kodu},
        headers=_cors_basliklari(request),
    )


app.include_router(health.router)
app.include_router(speech.router)
app.include_router(ai.router)
app.include_router(document.router)
app.include_router(auth.router)
app.include_router(doctor.router)
