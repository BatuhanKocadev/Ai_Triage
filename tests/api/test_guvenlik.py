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
