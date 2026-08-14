"""Uçların jeton ve rol kapılarını dondurur."""

import pytest

from tests.yardimcilar.veri_uretici import ziyaret_verisi


@pytest.mark.entegrasyon
def test_jetonsuz_istek_401_doner(istemci, esik_alti):
    # Uçtan yetkilendirme bağımlılığının düşmesini yakalar; hasta verisi
    # jetonsuz işlenmemeli. esik_alti güvenlik ağı: yetki kapısı düşerse istek
    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi())
    assert yanit.status_code == 401


@pytest.mark.entegrasyon
def test_bozuk_jeton_401_doner(istemci, esik_alti):
    # Bozuk imzalı jetonun kabul edilmesini yakalar: jwt.decode'un
    # doğrulamasız çağrılması ya da except JWTError dalının düşmesi.
    yanit = istemci.post(
        "/ai/analiz",
        json=ziyaret_verisi(),
        headers={"Authorization": "Bearer bu-gecerli-bir-jeton-degil"},
    )
    assert yanit.status_code == 401


@pytest.mark.entegrasyon
def test_tanimsiz_rol_403_doner(istemci, yetkili_baslik, esik_alti):
    # require_user_or_admin_role yalnızca "user" ve "admin" kabul eder.
    # esik_alti: rol kontrolü gevşerse istek gövdeye ilerler, gerçek servise gitmesin.
    baslik = yetkili_baslik(kullanici_adi="doktor_ayse", rol="doktor")
    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=baslik)
    assert yanit.status_code == 403


@pytest.mark.entegrasyon
def test_veritabaninda_olmayan_kullanicinin_jetonu_401_doner(
    istemci, jeton_uret, esik_alti
):
    # Jeton imzası geçerli ama kullanıcı silinmişse erişim reddedilmeli.
    # esik_alti: kullanıcı arama dalı düşerse istek gövdeye ilerler,
    jeton = jeton_uret(kullanici_adi="hic_var_olmayan", rol="user")
    yanit = istemci.post(
        "/ai/analiz",
        json=ziyaret_verisi(),
        headers={"Authorization": f"Bearer {jeton}"},
    )
    assert yanit.status_code == 401


@pytest.mark.entegrasyon
def test_admin_olmayan_dokuman_yukleyemez(istemci, yetkili_baslik, dokuman_yazmayi_engelle):
    # Regresyon: require_admin_role'ün rol kontrolü gevşerse (auth_service.py:78)
    # sıradan "user" rolü protokol dokümanı yükleyebilir ve tüm hastaların
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("protokol.txt", b"deneme icerigi", "text/plain")},
        headers=yetkili_baslik(kullanici_adi="sade_kullanici", rol="user"),
    )
    assert yanit.status_code == 403


@pytest.mark.entegrasyon
def test_dokuman_yukleme_jetonsuz_401_doner(istemci, dokuman_yazmayi_engelle):
    # Regresyon: /document/upload ucundan auth bağımlılığı düşerse
    # (app/api/document.py, Depends(require_admin_role)) uç tamamen halka
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("protokol.txt", b"deneme icerigi", "text/plain")},
    )
    assert yanit.status_code == 401


@pytest.mark.entegrasyon
def test_rol_bilgisi_auth_me_ile_donuyor(istemci, yetkili_baslik):
    # Panel rolü buradan okuyor (kullanıcı adından tahmin etmiyor); bu uç
    # bozulursa arayüz yanlış sekmeleri açar. Parola hash'inin sızmadığı da
    yanit = istemci.get(
        "/auth/me", headers=yetkili_baslik(kullanici_adi="dr_veli", rol="doctor")
    )

    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["username"] == "dr_veli"
    assert govde["role"] == "doctor"
    assert "hashed_password" not in govde
