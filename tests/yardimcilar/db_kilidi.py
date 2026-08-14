"""Test veritabanı adresinin yıkıcı işlemler için güvenli olup olmadığına karar verir."""

import os

from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.engine import make_url

# Yalnızca bu host'larda test veritabanı düşürülebilir. "postgres" docker compose
# ve CI servis konteynerinin adıdır. Ortam değişkeniyle geçiş bilinçli olarak
IZINLI_HOSTLAR = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})

# Testlerin dokunmasına izin verilen tek veritabanı adı.
TEST_VERITABANI = "ai_triage_test"

# İzin verilen tek port. Beyaz listedeki bir host üzerinde başka bir port, çoğu
# zaman üretime açılmış bir tünel ya da ikinci bir küme demektir — yani host
IZINLI_PORT = 5432

# libpq'nun onaylı DSN'i ezmesine yol açan ortam değişkenleri.
_TEHLIKELI_ORTAM = ("PGHOSTADDR", "PGSERVICE")


def _ortam_guvenli_mi() -> tuple[bool, str]:
    """Süreç ortamı libpq hedefini DSN dışından değiştirmesin."""
    for ad in _TEHLIKELI_ORTAM:
        if os.environ.get(ad):
            return False, f"{ad} ayarlı; libpq DSN hedefini ezer"
    pgport = os.environ.get("PGPORT")
    if pgport is not None and str(pgport) != str(IZINLI_PORT):
        return False, f"PGPORT {pgport!r} hedef portunu ezer"
    return True, ""


def hedef_guvenli_mi(url_metni: str) -> tuple[bool, str]:
    """Adres test veritabanına mı işaret ediyor; (guvenli, sebep) döndürür."""
    ortam_ok, ortam_sebep = _ortam_guvenli_mi()
    if not ortam_ok:
        return False, ortam_sebep

    try:
        url = make_url(url_metni)
    except Exception:
        # Şüphede kapan: ayrıştıramadığımız bir adrese güvenmeyiz.
        return False, "adres ayrıştırılamadı"

    # `service`, hedefi bir pg_service dosyasından okur; host, port ve dbname'i
    # aynı anda ve bizim göremeyeceğimiz bir yerden belirleyebilir.
    if "service" in url.query:
        return False, "service parametresi hedefi dosyadan okuyor, doğrulanamaz"

    try:
        _, secenekler = PGDialect_psycopg2().create_connect_args(url)
    except Exception:
        return False, "bağlantı argümanları çözülemedi"

    # Bundan sonrası psycopg2'nin gerçekten kullanacağı değerler üzerinde.
    veritabani = secenekler.get("dbname")
    if veritabani != TEST_VERITABANI:
        return False, f"veritabanı adı {TEST_VERITABANI!r} değil: {veritabani!r}"

    # hostaddr verilirse libpq bağlantıyı ona kurar, `host` yalnızca sertifika
    # doğrulaması için kullanılır — yani beyaz listeyi hostaddr'a uygulamalıyız.
    host = secenekler.get("hostaddr") or secenekler.get("host")
    if not host:
        # Host yoksa hedefi doğrulayamayız: libpq PGHOST'a düşer ve uzak
        # sunucuya bağlanabilir.
        return False, "host belirtilmemiş"
    if host not in IZINLI_HOSTLAR:
        return False, f"host beyaz listede değil: {host!r}"

    port = secenekler.get("port")
    if port is not None and int(port) != IZINLI_PORT:
        return False, f"port {IZINLI_PORT} değil: {port!r}"

    return True, ""
