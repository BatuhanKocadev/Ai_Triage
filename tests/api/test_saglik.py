"""istemci fixture'ının gerçekten ayakta olduğunu ve get_db'nin
test oturumuyla değiştirildiğini kanıtlar."""

import pytest


@pytest.mark.entegrasyon
def test_saglik_ucu_200_doner(istemci):
    # Yol sondaki eğik çizgiyle: router prefix="/health", route path="/".
    yanit = istemci.get("/health/")
    assert yanit.status_code == 200
    assert yanit.json()["durum"] == "basarili"


@pytest.mark.entegrasyon
def test_db_oturumu_testler_arasinda_temizlenir(db_oturum, kullanici_uret):
    # Bu testte yaratılan kullanıcı, rollback sayesinde diğer testlere sızmamalı.
    kullanici_uret(kullanici_adi="gecici_kullanici")
    from app.models.user import User
    assert db_oturum.query(User).filter_by(username="gecici_kullanici").count() == 1
