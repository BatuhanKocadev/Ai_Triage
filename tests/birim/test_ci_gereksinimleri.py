"""`requirements-ci.txt` ile `requirements.txt` arasındaki sürüm paritesini dondurur.

CI, üretimin kurduğundan farklı bir sürümle koşarsa kanıtladığı şey üretim için
geçerli olmaz — yeşil bir CI, çalışmayan bir üretim sürümünü örtebilir.
`requirements-ci.txt` bu sözü başlığında veriyor; bu test onu dayatıyor.

Kapsamı bilinçli olarak dar: yalnızca CI listesindeki paketler denetleniyor.
Geçişli bağımlılıklar CI listesinde pinli değil (sebebi o dosyanın başlığında
yazılı), dolayısıyla burada da denetlenemez.
"""

import re
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent.parent

# "paket==surum" satirlari; yorumlar ve bos satirlar atlanir.
PIN_DESENI = re.compile(r"^([A-Za-z0-9._-]+)==([^\s#]+)")


def _ad_normalize(ad: str) -> str:
    """PyPI paket adlarını karşılaştırılabilir biçime indirger.

    `SQLAlchemy` ile `sqlalchemy`, `python_docx` ile `python-docx` aynı pakettir;
    normalize edilmezse test gerçek bir ayrışma olmadan kırılır ve yanlış alarm,
    hiç test olmamasından beterdir.
    """
    return ad.lower().replace("_", "-")


def _pinleri_oku(dosya_adi: str) -> dict[str, str]:
    """Bir gereksinim dosyasındaki sabitlenmiş sürümleri sözlüğe çevirir."""
    pinler = {}
    for satir in (KOK / dosya_adi).read_text(encoding="utf-8").splitlines():
        eslesme = PIN_DESENI.match(satir.strip())
        if eslesme:
            pinler[_ad_normalize(eslesme.group(1))] = eslesme.group(2)
    return pinler


def test_ci_listesi_bos_degil():
    # Ayrıştırıcı sessizce hiçbir şey bulmazsa aşağıdaki test boş küme üzerinde
    # koşup yanlışlıkla yeşil kalırdı; bu satır o durumu engelliyor.
    assert len(_pinleri_oku("requirements-ci.txt")) > 15


def test_ci_pinleri_uretim_listesinde_var():
    # Yalnizca CI listesine eklenen bir paket, uretimde hic kurulmayan bir
    # bagimliligin uzerinde test kosmak demektir.
    uretim = _pinleri_oku("requirements.txt")
    ci = _pinleri_oku("requirements-ci.txt")

    eksikler = sorted(paket for paket in ci if paket not in uretim)

    assert eksikler == [], (
        f"CI listesinde olup requirements.txt'te olmayan paketler: {eksikler}"
    )


def test_ci_pinleri_uretimle_ayni_surumde():
    uretim = _pinleri_oku("requirements.txt")
    ci = _pinleri_oku("requirements-ci.txt")

    ayrisanlar = {
        paket: (surum, uretim[paket])
        for paket, surum in ci.items()
        if paket in uretim and uretim[paket] != surum
    }

    assert ayrisanlar == {}, (
        "CI ile üretim sürümleri ayrıştı (paket: CI, üretim): "
        f"{ayrisanlar}. İkisini de aynı turda güncelleyin."
    )
