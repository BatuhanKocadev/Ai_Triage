"""Gün 27: `scripts/seed_users.py` iki kez çalıştırılabilir olmalı."""
import pytest

import scripts.seed_users as seed
from app.models.user import User
from app.services.auth_service import verify_password


@pytest.fixture
def seed_test_oturumunda(db_oturum, monkeypatch):
    """`seed.main()`'i test oturumuna bağlar."""
    monkeypatch.setattr(db_oturum, "close", lambda: None)
    monkeypatch.setattr(seed, "SessionLocal", lambda: db_oturum)
    return db_oturum


@pytest.mark.entegrasyon
def test_seed_users_iki_kez_calistirilabilir(seed_test_oturumunda, capsys):
    db = seed_test_oturumunda
    beklenen = {v["username"]: v for v in seed.BASLANGIC_KULLANICILARI}

    seed.main()
    ilk = {k.username: k for k in db.query(User).all()}
    assert set(ilk) == set(beklenen), "ilk koşum üç hesabı da yaratmalı"

    seed.main()
    ikinci = {k.username: k for k in db.query(User).all()}

    # Tekrar yok: unique kısıt ihlali de, çift satır da olmamalı.
    assert set(ikinci) == set(beklenen)
    assert len(db.query(User).all()) == len(beklenen)
    # Kimlikler korunmalı — ikinci koşum satırı silip yeniden yaratmıyor.
    assert {k: v.id for k, v in ikinci.items()} == {k: v.id for k, v in ilk.items()}

    for ad, veri in beklenen.items():
        assert ikinci[ad].role == veri["role"]
        assert verify_password(veri["password"], ikinci[ad].hashed_password)


@pytest.mark.entegrasyon
def test_seed_users_bozulmus_rol_ve_parolayi_duzeltir(seed_test_oturumunda, capsys):
    """İdempotentlik "hiçbir şey yapma" değil "hedef duruma getir" demek."""
    db = seed_test_oturumunda
    seed.main()

    bozuk = db.query(User).filter(User.username == "doctor").first()
    bozuk.role = "user"
    bozuk.hashed_password = seed.hash_password("yanlis_parola")
    db.commit()

    seed.main()

    duzelmis = db.query(User).filter(User.username == "doctor").first()
    assert duzelmis.role == "doctor"
    assert verify_password("doctor123", duzelmis.hashed_password)
