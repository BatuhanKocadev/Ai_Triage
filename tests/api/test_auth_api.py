"""Uçların jeton ve rol kapılarını dondurur."""

import pytest

from tests.yardimcilar.veri_uretici import ziyaret_verisi


@pytest.mark.entegrasyon
def test_jetonsuz_istek_401_doner(istemci):
    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi())
    assert yanit.status_code == 401


@pytest.mark.entegrasyon
def test_bozuk_jeton_401_doner(istemci):
    yanit = istemci.post(
        "/ai/analiz",
        json=ziyaret_verisi(),
        headers={"Authorization": "Bearer bu-gecerli-bir-jeton-degil"},
    )
    assert yanit.status_code == 401


@pytest.mark.entegrasyon
def test_tanimsiz_rol_403_doner(istemci, yetkili_baslik):
    # require_user_or_admin_role yalnızca "user" ve "admin" kabul eder.
    baslik = yetkili_baslik(kullanici_adi="doktor_ayse", rol="doktor")
    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=baslik)
    assert yanit.status_code == 403


@pytest.mark.entegrasyon
def test_veritabaninda_olmayan_kullanicinin_jetonu_401_doner(istemci, jeton_uret):
    # Jeton imzası geçerli ama kullanıcı silinmişse erişim reddedilmeli.
    jeton = jeton_uret(kullanici_adi="hic_var_olmayan", rol="user")
    yanit = istemci.post(
        "/ai/analiz",
        json=ziyaret_verisi(),
        headers={"Authorization": f"Bearer {jeton}"},
    )
    assert yanit.status_code == 401


@pytest.mark.entegrasyon
def test_admin_olmayan_dokuman_yukleyemez(istemci, yetkili_baslik):
    # Regresyon: require_admin_role'ün rol kontrolü gevşerse (auth_service.py:78)
    # sıradan "user" rolü protokol dokümanı yükleyebilir ve tüm hastaların
    # sorguladığı ortak ChromaDB koleksiyonunu değiştirebilir.
    # require_admin_role bağımlılık katmanında çalışır: 403 dönerken dosya
    # hiç işlenmez ve ChromaDB'ye dokunulmaz, bu yüzden test güvenli.
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("protokol.txt", b"deneme icerigi", "text/plain")},
        headers=yetkili_baslik(kullanici_adi="sade_kullanici", rol="user"),
    )
    assert yanit.status_code == 403


@pytest.mark.entegrasyon
def test_dokuman_yukleme_jetonsuz_401_doner(istemci):
    # Regresyon: /document/upload ucundan auth bağımlılığı düşerse
    # (app/api/document.py, Depends(require_admin_role)) uç tamamen halka
    # açılır — jetonsuz bir istek dokümanı ChromaDB'ye yazabilir.
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("protokol.txt", b"deneme icerigi", "text/plain")},
    )
    assert yanit.status_code == 401
