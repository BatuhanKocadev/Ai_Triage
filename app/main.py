from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import health, speech, ai 
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
        "name": "Batuhan Kocaa",
        "url": "https://github.com/BatuhanKocadev/Ai_Triage.git",
        "email": "batuhankocadev@gmail.com",
    },
    license_info={
        "name": "MIT License",
    },
    lifespan=lifespan 
)

app.include_router(health.router)
app.include_router(speech.router)
app.include_router(ai.router)