"""Test veritabanı adresinin yıkıcı işlemler için güvenli olup olmadığına karar verir.

Karar mantığı conftest'ten ayrı bir modülde: conftest içindeki bir dal test
edilemez, buradaki fonksiyon edilebilir. Kilit `Base.metadata.drop_all`'u
koruyor, yani yanlış karar bütün bir şemayı siler.

Fonksiyon adı bilerek `test_` ile BAŞLAMIYOR: bir test modülüne import edilen
`test_*` adlı her fonksiyonu pytest test sanıp toplamaya çalışır ve parametresi
olduğu için `fixture 'url_metni' not found` diye kırılır. Adı "daha açıklayıcı"
diye `test_hedefi_...` biçimine çevirmeyin.
"""

from sqlalchemy.engine import make_url

# Yalnızca bu host'larda test veritabanı düşürülebilir. "postgres" docker compose
# ve CI servis konteynerinin adıdır. Ortam değişkeniyle geçiş bilinçli olarak
# YOKTUR (tasarım K6): kolay kaçış kapısı olan kilit, kilit değildir.
IZINLI_HOSTLAR = frozenset({"localhost", "127.0.0.1", "::1", "postgres"})

# Testlerin dokunmasına izin verilen tek veritabanı adı.
TEST_VERITABANI = "ai_triage_test"

# libpq bağlantı hedefini query string'den de alabilir ve bu parametreler
# `url.host`'u EZER: `...@localhost/ai_triage_test?host=prod-host` adresinde
# `url.host` "localhost" görünür ama psycopg2 "prod-host"a bağlanır. Beyaz liste
# yalnızca `url.host`'a baktığı için bunlar sessiz bir kaçış kapısıdır.
HEDEFI_EZEN_PARAMETRELER = frozenset({"host", "hostaddr", "service"})


def hedef_guvenli_mi(url_metni: str) -> tuple[bool, str]:
    """Adres test veritabanına mı işaret ediyor; (guvenli, sebep) döndürür."""
    try:
        url = make_url(url_metni)
    except Exception:
        # Şüphede kapan: ayrıştıramadığımız bir adrese güvenmeyiz.
        return False, "adres ayrıştırılamadı"

    if url.database != TEST_VERITABANI:
        return False, f"veritabanı adı {TEST_VERITABANI!r} değil: {url.database!r}"

    # Host yoksa hedefi doğrulayamayız: libpq PGHOST'a düşer ve uzak sunucuya
    # bağlanabilir, yani "boş host = yerel" varsayımı kilidi delerdi.
    if not url.host:
        return False, "host belirtilmemiş"

    if url.host not in IZINLI_HOSTLAR:
        return False, f"host beyaz listede değil: {url.host!r}"

    # Beyaz listeyi geçen bir host, query string'deki bir parametreyle ezilmiş
    # olabilir; o durumda doğruladığımız hedef bağlanılan hedef değildir.
    kacak = HEDEFI_EZEN_PARAMETRELER & set(url.query)
    if kacak:
        return False, f"host'u ezen bağlantı parametresi: {sorted(kacak)}"

    return True, ""
