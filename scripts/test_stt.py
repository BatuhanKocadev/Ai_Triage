"""faster-whisper ile bir ses dosyasını deneme amaçlı transkript eder.

Kullanım (proje kökünden):
    .venv\\Scripts\\python.exe -m scripts.test_stt [ses_dosyasi_yolu]

Yol verilmezse varsayılan olarak ornek_dokumanlar/ses_ornek.m4a kullanılır.
"""

import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.services.stt_service import transcribe, STTError

VARSAYILAN_DOSYA = "ornek_dokumanlar/ses_ornek.m4a"


def main() -> None:
    dosya_yolu = sys.argv[1] if len(sys.argv) > 1 else VARSAYILAN_DOSYA

    print(f"Dosya: {dosya_yolu}")
    baslangic = time.perf_counter()
    try:
        metin = transcribe(dosya_yolu)
    except STTError as exc:
        print(f"HATA: {exc}")
        sys.exit(1)
    sure = time.perf_counter() - baslangic

    print(f"Süre: {sure:.2f} saniye")
    print(f"Transkript: {metin}")


if __name__ == "__main__":
    main()
