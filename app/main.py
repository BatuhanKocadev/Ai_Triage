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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def beklenmeyen_hata_yakalayici(request: Request, hata: Exception):
    """Beklenmeyen istisnada tam izi log'a yazar, istemciye yalnızca kod döner.

    Yığın izi ve dosya yolları istemciye sızarsa saldırgan iç yapıyı öğrenir.
    İzleme kodu, sızıntı yaratmadan log'daki satırla eşleşmeyi mümkün kılıyor:
    kullanıcı "şu kodu aldım" der, operatör log'da o kodu arar.
    """
    izleme_kodu = uuid.uuid4().hex[:8]
    logger.exception(
        f"[{izleme_kodu}] Beklenmeyen hata: {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Sunucu hatası", "izleme_kodu": izleme_kodu},
    )


app.include_router(health.router)
app.include_router(speech.router)
app.include_router(ai.router)
app.include_router(document.router)
app.include_router(auth.router)
app.include_router(doctor.router)
