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


def test_ayristirilamayan_url_reddedilir():
    # Kilit şüphede kapanır: anlamadığı bir adrese güvenmez.
    guvenli, _ = hedef_guvenli_mi("bu bir url degil")

    assert guvenli is False
