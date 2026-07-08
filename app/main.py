from fastapi import FastAPI
from app.api import health, speech, ai 

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
    }
)
app.include_router(health.router)
app.include_router(speech.router)
app.include_router(ai.router)