"""Yüklenen dosyanın uzantısını, boyutunu ve gerçek içeriğini doğrular.

Uzantıya güvenmek yetmez: saldırgan yürütülebilir bir dosyayı .pdf diye
adlandırabilir. Bu yüzden dosyanın baş baytlarındaki imza da kontrol ediliyor.
Kütüphane kullanılmadı (tasarım K4): yalnızca üç biçim destekleniyor ve
python-magic Windows'ta ayrıca libmagic ikilisi istiyor.
"""

from fastapi import HTTPException, status

from app.config.config import settings

# Biçimlerin dosya başındaki imzaları. DOCX aslında bir ZIP arşividir.
IMZALAR = {
    "pdf": b"%PDF-",
    "docx": b"PK\x03\x04",
}

# Reddetme mesajı bilerek tek ve genel (tasarım K5): saldırgana hangi kontrolü
# aştığını söylemek, kontrolü aşmasını kolaylaştırır.
GENEL_RET = "Desteklenmeyen dosya"


def izinli_uzantilar() -> set[str]:
    """Ayardaki virgülle ayrılmış listeyi kümeye çevirir."""
    return {u.strip().lower() for u in settings.izinli_uzantilar.split(",") if u.strip()}


def dosyayi_dogrula(dosya_adi: str, icerik: bytes) -> str:
    """Uzantı, boyut ve içerik imzasını kontrol eder; geçerliyse uzantıyı döndürür."""
    uzanti = dosya_adi.lower().rsplit(".", 1)[-1] if "." in dosya_adi else ""
    if uzanti not in izinli_uzantilar():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET)

    # Boyut ayrı bir kodla dönüyor: istemcinin dosyayı küçültmesi gerektiğini
    # bilmesi gerek, bu bir saldırı ipucu değil.
    if len(icerik) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Dosya çok büyük",
        )

    beklenen_imza = IMZALAR.get(uzanti)
    if beklenen_imza and not icerik.startswith(beklenen_imza):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET)

    # TXT'nin imzası yok; geçerli UTF-8 olması tek kontrol edilebilir özelliği.
    if uzanti == "txt":
        try:
            icerik.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=GENEL_RET
            )

    return uzanti
