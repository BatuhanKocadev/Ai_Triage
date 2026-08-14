"""Gün 27: `scripts/seed_users.py` iki kez çalıştırılabilir olmalı.

Kurulum provasının ikinci turunda seed yeniden koşulur (README onu bir adım
olarak listeliyor). İdempotent değilse ikinci koşum ya unique kısıtına takılır
ya da sessizce yanlış rol/parola bırakır — ve ikisi de "bende çalışıyordu"
sınıfının tipik sebebidir.
"""
import pytest

import scripts.seed_users as seed
from app.models.user import User
from app.services.auth_service import verify_password


@pytest.fixture
def seed_test_oturumunda(db_oturum, monkeypatch):
    """`seed.main()`'i test oturumuna bağlar.

    Script üretim `SessionLocal`'ını kullanıyor; yamalanmazsa test gerçek
    `ai_triage` veritabanına yazardı. `close` da etkisizleştiriliyor, yoksa
    script ilk koşumda test oturumunu kapatır ve ikinci koşum patlar.
    """
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
    """İdempotentlik "hiçbir şey yapma" değil "hedef duruma getir" demek.

    Gün 17 öncesinde `doctor` hesabı `user` rolüyle yazılmıştı; seed'in bunu
    düzeltmesi bilinçli. Yalnızca "iki kez koşuyor" sınansaydı, seed var olan
    satıra hiç dokunmayacak şekilde bozulduğunda test yeşil kalırdı.
    """
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
