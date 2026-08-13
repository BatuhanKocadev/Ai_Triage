"""Test veritabanı adresinin yıkıcı işlemler için güvenli olup olmadığına karar verir.

Karar mantığı conftest'ten ayrı bir modülde: conftest içindeki bir dal test
edilemez, buradaki fonksiyon edilebilir. Kilit `Base.metadata.drop_all`'u
koruyor, yani yanlış karar bütün bir şemayı siler.

**URL'in görünen hâline değil, psycopg2'ye VERİLECEK hedefe bakıyoruz.** Sebebi
ölçüldü: libpq bağlantı hedefini query string'den de alır ve bu parametreler
URL'in kendi alanlarını EZER. `postgresql://...@localhost/ai_triage_test?dbname=ai_triage`
adresinde `url.database` "ai_triage_test" görünür ama psycopg2 `dbname=ai_triage`
ile bağlanır — yani kilit "güvenli" derken `drop_all` üretim veritabanında koşar.
Aynısı `host`, `hostaddr` ve `port` için de geçerli.

İlk denemede bu, yasaklı query anahtarlarından oluşan bir KARA LİSTEyle çözülmüştü.
O şekil fail-**open**'dır: kimsenin aklına gelmeyen her parametre kilitten geçer, ve
nitekim `dbname` gözden kaçtı. Bu depo dosya doğrulamasında bilinçli olarak
fail-**closed** davranıyor (`IMZALAR`'da kaydı olmayan uzantı reddedilir); kilit de
aynı disipline getirildi: hedefi çözüyoruz, çözemezsek reddediyoruz.

**Ortam değişkenleri:** libpq `PGHOSTADDR` / `PGSERVICE` / (portsuz URL'de)
`PGPORT` ile DSN'i ezer. Kilit bu kanalları da reddeder (Gün 23 borcu 8b).

Fonksiyon adı bilerek `test_` ile BAŞLAMIYOR: bir test modülüne import edilen
`test_*` adlı her fonksiyonu pytest test sanıp toplamaya çalışır ve parametresi
olduğu için `fixture 'url_metni' not found` diye kırılır. Adı "daha açıklayıcı"
diye `test_hedefi_...` biçimine çevirmeyin.
"""

import os

from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.engine import make_url

# Yalnızca bu host'larda test veritabanı düşürülebilir. "postgres" docker compose
# ve CI servis konteynerinin adıdır. Ortam değişkeniyle geçiş bilinçli olarak
# YOKTUR (tasarım K6): kolay kaçış kapısı olan kilit, kilit değildir.
IZINLI_HOSTLAR = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})

# Testlerin dokunmasına izin verilen tek veritabanı adı.
TEST_VERITABANI = "ai_triage_test"

# İzin verilen tek port. Beyaz listedeki bir host üzerinde başka bir port, çoğu
# zaman üretime açılmış bir tünel ya da ikinci bir küme demektir — yani host
# kontrolü tek başına yetmez.
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
