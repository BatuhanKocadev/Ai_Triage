"""Test veritabanı kilidinin kendi davranışını dondurur.

Kilit, şemayı tamamen silen `Base.metadata.drop_all`'u koruyor. Bugünkü kontrol
`endswith("/ai_triage_test")` idi ve iki yönden kusurluydu: üretim sunucusundaki
aynı adlı veritabanı geçiyordu, buna karşılık `?sslmode=require` gibi meşru bir
URL takılıyordu. Bu testler ikisini birden bağlar.
"""

from tests.yardimcilar.db_kilidi import hedef_guvenli_mi


def test_yerel_test_veritabani_kabul_edilir():
    guvenli, _ = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test"
    )

    assert guvenli is True


def test_uzak_host_ayni_ad_olsa_bile_reddedilir():
    # Asıl tehlike bu: üretim sunucusunda ai_triage_test adlı bir veritabanı
    # varsa eski kilit onu korumuyordu ve drop_all oraya iniyordu.
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@prod-host:5432/ai_triage_test"
    )

    assert guvenli is False
    assert "host" in sebep


def test_hostsuz_url_reddedilir():
    # Host yoksa libpq PGHOST'a düşer; "boş host = yerel" varsaymak, uzak bir
    # sunucuda drop_all çalıştırmanın önündeki tek engeli kaldırırdı.
    guvenli, sebep = hedef_guvenli_mi("postgresql:///ai_triage_test")

    assert guvenli is False
    assert "host" in sebep


def test_yanlis_veritabani_adi_reddedilir():
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage"
    )

    assert guvenli is False
    assert "veritabanı" in sebep


def test_query_stringli_yerel_url_kabul_edilir():
    # Eski sonek testi burada YANLIŞ yönde başarısız oluyordu: meşru bir CI
    # koşusunu durduruyordu.
    guvenli, _ = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test?sslmode=require"
    )

    assert guvenli is True


def test_docker_servis_adi_kabul_edilir():
    # docker compose ve CI servis konteynerinin host adı "postgres".
    guvenli, _ = hedef_guvenli_mi(
        "postgresql://triage:triage@postgres:5432/ai_triage_test"
    )

    assert guvenli is True


def test_ipv4_loopback_kabul_edilir():
    # "127.0.0.1" beyaz listeden düşerse yerelde adı yerine IP'siyle bağlanan koşu durur.
    guvenli, _ = hedef_guvenli_mi(
        "postgresql://triage:triage@127.0.0.1:5432/ai_triage_test"
    )

    assert guvenli is True


def test_ipv6_loopback_kabul_edilir():
    # "::1" beyaz listeden düşerse IPv6 loopback ile bağlanan koşu durur; make_url köşeli parantezi ayıklar.
    guvenli, _ = hedef_guvenli_mi(
        "postgresql://triage:triage@[::1]:5432/ai_triage_test"
    )

    assert guvenli is True


def test_ayristirilamayan_url_reddedilir():
    # Kilit şüphede kapanır: anlamadığı bir adrese güvenmez.
    guvenli, _ = hedef_guvenli_mi("bu bir url degil")

    assert guvenli is False


def test_query_stringle_ezilen_host_reddedilir():
    # libpq bağlantı hedefini query string'den de alır ve bu url.host'u EZER:
    # aşağıdaki adreste url.host "localhost" görünür ama psycopg2 "prod-host"a
    # bağlanır, yani doğruladığımız hedef bağlanılan hedef olmaz. Bos-host
    # deliğiyle aynı sınıf.
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test?host=prod-host"
    )

    assert guvenli is False
    assert "host" in sebep


def test_hostaddr_ile_ezilen_host_reddedilir():
    # hostaddr da aynı işi yapar; tek parametreyi kapatmak yetmez.
    guvenli, _ = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test?hostaddr=10.0.0.5"
    )

    assert guvenli is False


def test_query_stringle_ezilen_veritabani_adi_reddedilir():
    # En tehlikelisi bu: uzak sunucu bile gerekmiyor. url.database
    # "ai_triage_test" görünür ama psycopg2 dbname=ai_triage ile bağlanır,
    # yani drop_all geliştiricinin kendi makinesindeki ÜRETİM veritabanında koşar.
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test?dbname=ai_triage"
    )

    assert guvenli is False
    assert "veritabanı" in sebep


def test_query_stringle_ezilen_port_reddedilir():
    # Beyaz listedeki bir host üzerinde başka port, çoğu zaman üretime açılmış
    # bir tünel ya da ikinci bir küme demektir; host kontrolü tek başına yetmez.
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test?port=5433"
    )

    assert guvenli is False
    assert "port" in sebep


def test_service_parametresi_reddedilir():
    # service, hedefi bir pg_service dosyasından okur ve host/port/dbname'i
    # aynı anda belirleyebilir; göremediğimiz bir kaynağı doğrulayamayız.
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test?service=prod"
    )

    assert guvenli is False
    assert "service" in sebep


def test_pghostaddr_ortami_reddedilir(monkeypatch):
    # URL onaylı olsa bile PGHOSTADDR libpq'yu başka adrese götürür (ölçülmüş).
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.7")
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test"
    )

    assert guvenli is False
    assert "PGHOSTADDR" in sebep


def test_pgservice_ortami_reddedilir(monkeypatch):
    monkeypatch.setenv("PGSERVICE", "prod")
    guvenli, sebep = hedef_guvenli_mi(
        "postgresql://triage:triage@localhost:5432/ai_triage_test"
    )

    assert guvenli is False
    assert "PGSERVICE" in sebep


def test_portsuz_yerel_adres_kabul_edilir():
    # Port belirtilmemesi meşrudur (varsayılan 5432); kilit fazla sıkı olmamalı.
    guvenli, _ = hedef_guvenli_mi("postgresql://triage:triage@localhost/ai_triage_test")

    assert guvenli is True
