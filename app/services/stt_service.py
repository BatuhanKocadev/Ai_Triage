"""Ses tanıma (STT) servisi: faster-whisper ile Türkçe transkripsiyon."""

import os

import torch
from faster_whisper import WhisperModel

from app.config.config import settings
from app.utils.logger import logger


class STTError(Exception):
    """Ses dosyası transkript edilemediğinde fırlatılır."""


# Model tembel yükleniyor: import anında ~500 MB ağırlık yüklemek hem uygulama
# açılışını hem de testleri gereksiz yere bloke eder (aynı ders rag_service.py
# içindeki get_reranker()'da öğrenildi, aynı desen burada da kullanılıyor).
_model: WhisperModel | None = None


def _resolve_device() -> tuple[str, str]:
    if settings.whisper_device != "auto":
        device = settings.whisper_device
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        device, compute_type = _resolve_device()
        logger.info(
            f"Whisper modeli yükleniyor: {settings.whisper_model_size} "
            f"({device}, {compute_type})"
        )
        _model = WhisperModel(
            settings.whisper_model_size, device=device, compute_type=compute_type
        )
    return _model


def transcribe(dosya_yolu: str) -> str:
    """Ses dosyasını Türkçe metne çevirir. Dil otomatik algılama yerine sabit
    "tr" kullanılır; kısa kayıtlarda otomatik algılama yanılabiliyor."""
    if not os.path.isfile(dosya_yolu):
        raise STTError(f"Ses dosyası bulunamadı: {dosya_yolu}")

    try:
        # vad_filter: konuşma içermeyen bölümleri ayıklıyor; bu olmayınca Whisper
        # tam sessizliğe "İzlediğiniz için teşekkürler" gibi kalıp cümleler uyduruyor.
        segments, _ = get_model().transcribe(dosya_yolu, language="tr", vad_filter=True)
        return " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as exc:
        raise STTError(f"Ses dosyası transkript edilemedi: {dosya_yolu}") from exc
