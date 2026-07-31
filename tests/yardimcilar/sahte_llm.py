"""Ollama yerine geçen sahte servis. Gerçek model asla çağrılmaz."""

from app.services.llm_service import LLMError


def sahte_llm_uret(yanit: dict):
    """Verilen sözlüğü aynen döndüren sahte get_structured_completion üretir."""
    def _sahte(system_prompt: str, user_prompt: str, **kwargs) -> dict:
        return yanit
    return _sahte


def hata_firlatan_llm():
    """Ollama'ya ulaşılamadığında olduğu gibi LLMError fırlatan sahte üretir."""
    def _sahte(system_prompt: str, user_prompt: str, **kwargs):
        raise LLMError("Yerel LLM servisine ulaşılamadı")
    return _sahte


# Testlerin çoğunun beklediği, tüm alanları dolu geçerli bir LLM yanıtı.
GECERLI_YANIT = {
    "status": "success",
    "triage_code": "Sarı",
    "department": "Dahiliye",
    "onerilen_tetkikler": ["Tam kan sayımı"],
    "ai_note": "Hastanın yakından izlenmesi önerilir.",
}
