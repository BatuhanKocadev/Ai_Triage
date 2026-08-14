"""Ses tanıma (STT) servisi: faster-whisper ile Türkçe transkripsiyon."""

# Tip açıklamalarının çalışma zamanında değerlendirilmesini kapatır. ZORUNLU:
# aşağıdaki `_model: WhisperModel | None` satırı, WhisperModel modül düzeyinde
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from app.config.config import settings
from app.utils.logger import logger

if TYPE_CHECKING:  # yalnızca tip denetleyici için; çalışma zamanında import edilmez
    from faster_whisper import WhisperModel


class STTError(Exception):
    """Ses dosyası transkript edilemediğinde fırlatılır."""


# Model tembel yükleniyor: import anında ~500 MB ağırlık yüklemek hem uygulama
# açılışını hem de testleri gereksiz yere bloke eder.
_model: WhisperModel | None = None


def _resolve_device() -> tuple[str, str]:
    """Cihazı ve hesaplama tipini seçer; torch yalnızca burada gerekiyor."""
    if settings.whisper_device != "auto":
        device = settings.whisper_device
    else:
        # torch BURADA import ediliyor: modül düzeyinde import CI'a ve her test
        # koşusuna ağırlık ekliyordu (tasarım K2).
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        # faster_whisper BURADA import ediliyor, modül düzeyinde değil: kendisi
        # `ctranslate2` ve `onnxruntime` çekiyor ve modül düzeyine alınırsa
        from faster_whisper import WhisperModel

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
