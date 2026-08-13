"""Yüklenen dosyanın uzantısını, boyutunu ve gerçek içeriğini doğrular.

Uzantıya güvenmek yetmez: saldırgan yürütülebilir bir dosyayı .pdf diye
adlandırabilir. Bu yüzden dosyanın baş baytlarındaki imza da kontrol ediliyor.
Kütüphane kullanılmadı (tasarım K4): yalnızca üç biçim destekleniyor ve
python-magic Windows'ta ayrıca libmagic ikilisi istiyor.
"""

import io
import zipfile

from fastapi import HTTPException, status

from app.config.config import settings
from app.utils.logger import logger

# Biçimlerin dosya başındaki imzaları. DOCX aslında bir ZIP arşividir;
# yalnızca PK imzası yetmez — aşağıda Content_Types ile sıkılaştırılır.
# "txt" bilerek None ile kayıtlı (tasarım K4 devamı, Görev 3 düzeltmesi):
# `IMZALAR.get(uzanti)` yerine `uzanti not in IMZALAR` kontrolü yapılıyor,
# böylece yeni bir uzantı `izinli_uzantilar` ayarına eklenip IMZALAR'a
# eklenmesi unutulursa imza kontrolü sessizce atlanmak yerine dosya
# fail-closed biçimde reddedilir.
IMZALAR = {
    "pdf": b"%PDF-",
    "docx": b"PK\x03\x04",
    "txt": None,
}

# Reddetme mesajı bilerek tek ve genel (tasarım K5): saldırgana hangi kontrolü
# aştığını söylemek, kontrolü aşmasını kolaylaştırır. Ayrım yalnızca sunucu
# log'unda tutulur (K5'in log ayağı) — her ret dalı hangi kontrolün
# tetiklendiğini, dosya adını ve boyutu logger.warning ile kaydeder.
GENEL_RET = "Desteklenmeyen dosya"


def izinli_uzanti_kumesi() -> set[str]:
    """Ayardaki virgülle ayrılmış listeyi kümeye çevirir."""
    return {u.strip().lower() for u in settings.izinli_uzantilar.split(",") if u.strip()}


def max_upload_bayt() -> int:
    """Ayarlanan azami yükleme boyutu (bayt)."""
    return settings.max_upload_mb * 1024 * 1024


def _docx_zip_mi(icerik: bytes) -> bool:
    """DOCX: ZIP olmalı ve Office Open XML Content_Types taşımalı.

    Yalnızca PK imzası herhangi bir ZIP'i (ör. .jar, rastgele arşiv) kabul
    ederdi; Content_Types yoksa reddedilir.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(icerik)) as zf:
            return "[Content_Types].xml" in zf.namelist()
    except zipfile.BadZipFile:
        return False


def dosyayi_dogrula(dosya_adi: str, icerik: bytes) -> str:
    """Uzantı, boyut ve içerik imzasını kontrol eder; geçerliyse uzantıyı döndürür."""
    # file.filename None gelebilir; .lower() patlarsa istemci 400 yerine 500 alır.
    if not isinstance(dosya_adi, str) or not dosya_adi:
        logger.warning(
            f"Dosya reddedildi (dosya adi yok): dosya_adi={dosya_adi!r} "
            f"boyut={len(icerik)}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET)

    uzanti = dosya_adi.lower().rsplit(".", 1)[-1] if "." in dosya_adi else ""
    if uzanti not in izinli_uzanti_kumesi():
        logger.warning(
            f"Dosya reddedildi (izinsiz uzanti): dosya_adi={dosya_adi!r} "
            f"boyut={len(icerik)}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET)

    # Boyut ayrı bir kodla dönüyor: istemcinin dosyayı küçültmesi gerektiğini
    # bilmesi gerek, bu bir saldırı ipucu değil.
    if len(icerik) > max_upload_bayt():
        logger.warning(
            f"Dosya reddedildi (boyut asimi): dosya_adi={dosya_adi!r} "
            f"boyut={len(icerik)}"
        )
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Dosya çok büyük",
        )

    # Fail-closed: uzantı IMZALAR'da hiç kayıtlı değilse (ör. ayarda izinli
    # ama burada unutulmuş bir uzantı) içerik doğrulanamadığı için reddedilir.
    if uzanti not in IMZALAR:
        logger.warning(
            f"Dosya reddedildi (imzasi tanimsiz uzanti): dosya_adi={dosya_adi!r} "
            f"boyut={len(icerik)}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET)

    beklenen_imza = IMZALAR[uzanti]
    if beklenen_imza and not icerik.startswith(beklenen_imza):
        logger.warning(
            f"Dosya reddedildi (imza uyusmuyor): dosya_adi={dosya_adi!r} "
            f"boyut={len(icerik)}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET)

    if uzanti == "docx" and not _docx_zip_mi(icerik):
        logger.warning(
            f"Dosya reddedildi (docx degil zip): dosya_adi={dosya_adi!r} "
            f"boyut={len(icerik)}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET)

    # TXT'nin imzası yok; geçerli UTF-8 olması tek kontrol edilebilir özelliği.
    if uzanti == "txt":
        try:
            icerik.decode("utf-8")
        except UnicodeDecodeError as hata:
            logger.warning(
                f"Dosya reddedildi (gecersiz utf-8): dosya_adi={dosya_adi!r} "
                f"boyut={len(icerik)}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET
            ) from hata

    return uzanti
