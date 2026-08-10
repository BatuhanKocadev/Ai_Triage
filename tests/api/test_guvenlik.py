"""Güvenlik kurallarının testleri; her test bir saldırıyı taklit eder.

Bu dosyadaki testler "kural var mı" değil "kural UCU koruyor mu" sorusunu
yanıtlar. Kuralın kendi davranışı tests/birim/ altında ayrıca sınanıyor.
"""

import pytest

from app.config.config import settings
from tests.yardimcilar.veri_uretici import ziyaret_verisi


@pytest.mark.entegrasyon
def test_ardarda_istek_hiz_sinirina_takilir(istemci, yetkili_baslik, esik_alti):
    # /ai/analiz yerel LLM'i çalıştıran en pahalı uç; sınırsız çağrı servisi tüketir.
    # Gövde bilerek GEÇERLİ gönderiliyor: FastAPI'de gövde doğrulaması ile bağımlılık
    # çözümü aynı aşamada yürüyor ve geçersiz gövdeyle 422'nin 429'dan önce dönme
    # ihtimali var — o durumda test yanlış sebeple kırılır ve hız sınırı hakkında
    # hiçbir şey kanıtlamaz. `esik_alti` fixture'ı gerçek LLM'e gidilmesini önlüyor.
    baslik = yetkili_baslik(kullanici_adi="hasta_ayse", rol="user")
    son_durum = None
    for _ in range(settings.rate_limit_genel + 1):
        son_durum = istemci.post(
            "/ai/analiz", json=ziyaret_verisi(), headers=baslik
        ).status_code

    assert son_durum == 429


@pytest.mark.entegrasyon
def test_giris_denemesi_hiz_sinirli(istemci):
    # Parola deneme saldırısı: /auth/login kimlik doğrulaması olmadan çağrılabilen
    # tek yazma ucu, bu yüzden sınırı diğerlerinden sıkı.
    son_durum = None
    for _ in range(settings.rate_limit_giris + 1):
        son_durum = istemci.post(
            "/auth/login", data={"username": "yok", "password": "yanlis"}
        ).status_code

    assert son_durum == 429


@pytest.mark.entegrasyon
def test_desteklenmeyen_uzantili_dosya_reddedilir(
    istemci, yetkili_baslik, dokuman_yazmayi_engelle
):
    # Yürütülebilir dosya bilgi tabanına hiç girmemeli.
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("zararli.exe", b"MZ\x90\x00", "application/octet-stream")},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 400
    # Mesaj iddiası doğrulayıcıyı bağlar: eski uzantı zincirinin ürettiği
    # "Unsupported file format" ile karışmasın diye (aksi halde bu test
    # doğrulayıcı silinse de yeşil kalırdı).
    assert yanit.json()["detail"] == "Desteklenmeyen dosya"


@pytest.mark.entegrasyon
def test_cok_buyuk_dosya_reddedilir(istemci, yetkili_baslik, dokuman_yazmayi_engelle):
    # Boyut sınırı bellek tüketimini ve chunk patlamasını engelliyor.
    buyuk = b"a" * (settings.max_upload_mb * 1024 * 1024 + 1)
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("buyuk.txt", buyuk, "text/plain")},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 413


@pytest.mark.entegrasyon
def test_pdf_gibi_gorunen_bozuk_dosya_reddedilir(
    istemci, yetkili_baslik, dokuman_yazmayi_engelle
):
    # Uzantıya güvenmek yetmez: saldırgan .exe dosyasını .pdf diye adlandırabilir.
    # Gerçek PDF "%PDF-" ile başlar.
    yanit = istemci.post(
        "/document/upload",
        data={"category": "protokol"},
        files={"file": ("sahte.pdf", b"MZ\x90\x00 bu bir PDF degil", "application/pdf")},
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 400
    # Mesaj iddiası doğrulayıcıyı bağlar: doğrulayıcı olmasa da pdfplumber
    # geçersiz baytlarda istisna fırlatıp "PDF processing error" ile 400
    # döner — durum kodu tek başına imza kontrolünü kanıtlamıyor.
    assert yanit.json()["detail"] == "Desteklenmeyen dosya"
