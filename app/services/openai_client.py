from openai import OpenAI
from app.config.config import settings
client = OpenAI(api_key=settings.openai_api_key)