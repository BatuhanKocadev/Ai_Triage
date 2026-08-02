"""istemci fixture'ının gerçekten ayakta olduğunu ve get_db'nin
test oturumuyla değiştirildiğini kanıtlar; ayrıca db_oturum'un commit
edilmiş satırları bile bir sonraki teste sızdırmadığını kanıtlar."""

import pytest

# İki testte de aynı kullanıcı adı: User.username unique olduğu için, önceki
# testin commit'i gerçekten kalıcı olsaydı ikinci test IntegrityError alırdı.
IZOLASYON_KULLANICI_ADI = "izolasyon_denek"


@pytest.mark.entegrasyon
def test_saglik_ucu_200_doner(istemci):
    # Yol sondaki eğik çizgiyle: router prefix="/health", route path="/".
    yanit = istemci.get("/health/")
    assert yanit.status_code == 200
    assert yanit.json()["durum"] == "basarili"


@pytest.mark.entegrasyon
def test_izolasyon_denegi_ilk_testte_commit_edilir(db_oturum, kullanici_uret):
    # /ai/analiz'daki _kaydet() gibi gerçek bir db.commit() çağırıyoruz; salt
    # flush join_transaction_mode'a duyarlı değildir, gerçek commit gerekir.
    kullanici_uret(kullanici_adi=IZOLASYON_KULLANICI_ADI)
    db_oturum.commit()


@pytest.mark.entegrasyon
def test_izolasyon_denegi_ikinci_testte_hala_yaratilabilir(db_oturum, kullanici_uret):
    # Bu test, yukarıdaki testten SONRA çalışmalı (dosya içi çalıştırma sırası).
    # Önceki testin commit'i gerçekten kalıcıysa burada unique kısıt ihlali
    # (IntegrityError) alırız; almamak izolasyonun gerçekten çalıştığını kanıtlar.
    kullanici_uret(kullanici_adi=IZOLASYON_KULLANICI_ADI)
    db_oturum.commit()
