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
    kullanici_uret(kullanici_adi=IZOLASYON_KULLANICI_ADI)
    db_oturum.commit()


# --- Gün 27: /health üç bağımlılığı ayrı ayrı raporlamalı ---


def _durumlar(yanit_govdesi: dict) -> dict:
    """Yanıttaki bağımlılık sözlüğünü döndürür; testlerin okuması tek yerde."""
    return yanit_govdesi["bagimliliklar"]


@pytest.mark.entegrasyon
def test_saglik_ucu_bagimliliklari_raporlar(istemci, monkeypatch):
    """Kurulum sorunu yaşayan biri tek istekle NEREDE takıldığını görebilmeli."""
    import app.api.health as saglik

    monkeypatch.setattr(saglik, "_postgres_yokla", lambda: (True, "ok"))
    monkeypatch.setattr(saglik, "_chromadb_yokla", lambda: (True, "ok"))
    monkeypatch.setattr(saglik, "_ollama_yokla", lambda: (True, "ok"))

    govde = istemci.get("/health/").json()

    assert set(_durumlar(govde)) == {"postgres", "chromadb", "ollama"}
    assert all(d["ok"] for d in _durumlar(govde).values())
    assert govde["tumu_ok"] is True
    # Eski sözleşme korunuyor: mevcut çağıranlar (ölçüm sürücüsünün ön uçuşu,
    # docker healthcheck) kırılmasın.
    assert govde["durum"] == "basarili"


@pytest.mark.entegrasyon
def test_saglik_ucu_bozuk_bagimliligi_isaretler(istemci, monkeypatch):
    """Tek bir bağımlılık düştüğünde HANGİSİ olduğu görünmeli, `tumu_ok` False olmalı."""
    import app.api.health as saglik

    monkeypatch.setattr(saglik, "_postgres_yokla", lambda: (True, "ok"))
    monkeypatch.setattr(saglik, "_chromadb_yokla", lambda: (False, "baglanti reddedildi"))
    monkeypatch.setattr(saglik, "_ollama_yokla", lambda: (True, "ok"))

    govde = istemci.get("/health/").json()

    assert govde["tumu_ok"] is False
    assert _durumlar(govde)["chromadb"]["ok"] is False
    assert "reddedildi" in _durumlar(govde)["chromadb"]["mesaj"]
    # Diğer ikisi etkilenmemeli: tek yoklamanın düşmesi diğerlerini karartmasın.
    assert _durumlar(govde)["postgres"]["ok"] is True
    assert _durumlar(govde)["ollama"]["ok"] is True


@pytest.mark.entegrasyon
def test_saglik_yoklamalari_istisnayi_yutar(istemci, monkeypatch):
    """Bir yoklama istisna fırlatırsa uç 500 vermemeli — teşhis aracı çökmemeli."""
    import app.api.health as saglik

    def _patla():
        raise RuntimeError("beklenmeyen surucu hatasi")

    monkeypatch.setattr(saglik, "_postgres_yokla", _patla)
    monkeypatch.setattr(saglik, "_chromadb_yokla", lambda: (True, "ok"))
    monkeypatch.setattr(saglik, "_ollama_yokla", lambda: (True, "ok"))

    yanit = istemci.get("/health/")

    assert yanit.status_code == 200
    assert yanit.json()["bagimliliklar"]["postgres"]["ok"] is False
    assert "beklenmeyen surucu hatasi" in yanit.json()["bagimliliklar"]["postgres"]["mesaj"]
