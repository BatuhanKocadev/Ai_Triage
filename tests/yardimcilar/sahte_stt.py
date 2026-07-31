"""faster-whisper yerine geçen sahte servis. Model indirilmez, yüklenmez."""

from app.services.stt_service import STTError


def sahte_transkript_uret(metin: str = "Karnımın sağ alt tarafında şiddetli ağrı var"):
    """Ses dosyasına bakmadan sabit metin döndüren sahte transcribe üretir."""
    def _sahte(dosya_yolu: str) -> str:
        return metin
    return _sahte


def hata_firlatan_stt():
    """Ses çözümlenemediğinde olduğu gibi STTError fırlatan sahte üretir."""
    def _sahte(dosya_yolu: str) -> str:
        raise STTError("Ses dosyası transkript edilemedi")
    return _sahte
