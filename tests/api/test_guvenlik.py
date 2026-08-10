"""Güvenlik kurallarının testleri; her test bir saldırıyı taklit eder.

Bu dosyadaki testler "kural var mı" değil "kural UCU koruyor mu" sorusunu
yanıtlar. Kuralın kendi davranışı tests/birim/ altında ayrıca sınanıyor.
"""

import io
import logging

import pytest

from app.api import speech as speech_modulu
from app.config.config import settings
from tests.yardimcilar.sahte_stt import sahte_transkript_uret
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
def test_transkript_ucu_hiz_sinirina_takilir(istemci, yetkili_baslik, monkeypatch):
    # /speech/transkript, /ai/analiz ile aynı pahalı sınıfta: faster-whisper
    # "medium" modelini yüklüyor, 25 MB'a kadar dosyayı belleğe alıyor, geçici
    # dosya yazıp CPU'yu doyuruyor. Kimlik doğrulaması hız sınırı DEĞİLDİR —
    # `user` rolündeki herhangi bir hesap ucu sınırsız çağırabiliyordu.
    # Gövde bilerek GEÇERLİ gönderiliyor (yukarıdaki /ai/analiz testiyle aynı
    # gerekçe): geçersiz gövdeyle 400'ün 429'dan önce dönmesi testi yanlış
    # sebeple kırardı. transcribe yamalı, gerçek model hiç yüklenmiyor.
    monkeypatch.setattr(speech_modulu, "transcribe", sahte_transkript_uret("metin"))
    baslik = yetkili_baslik(kullanici_adi="hasta_ayse", rol="user")

    son_durum = None
    for _ in range(settings.rate_limit_genel + 1):
        son_durum = istemci.post(
            "/speech/transkript",
            files={"file": ("kayit.wav", io.BytesIO(b"sahte-ses-baytlari"), "audio/wav")},
            headers=baslik,
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
def test_giris_hiz_siniri_kullanici_adina_bagli(istemci, kullanici_uret):
    # Anahtar IP olsaydı bir kullanıcının hatalı denemeleri HERKESİ kilitlerdi:
    # Streamlit backend'i sunucu tarafından (`requests` ile) çağırıyor, yani
    # Docker dağıtımında tüm girişler tek IP'den — frontend konteynerinin
    # IP'sinden — geliyor. Triyaj sisteminde bu klinik bir erişilebilirlik sorunu.
    kullanici_uret(kullanici_adi="ayse", parola="dogru-parola")
    for _ in range(settings.rate_limit_giris + 1):
        istemci.post("/auth/login", data={"username": "mehmet", "password": "yanlis"})

    yanit = istemci.post(
        "/auth/login", data={"username": "ayse", "password": "dogru-parola"}
    )

    assert yanit.status_code == 200


@pytest.mark.entegrasyon
def test_giris_hiz_siniri_harf_durumuyla_asilamaz(istemci):
    # Anahtar HAM kullanıcı adı olsaydı "yok", "YOK" ve " yok " üç ayrı kova
    # olurdu; saldırgan yalnızca yazımı değiştirerek sınırı katlardı.
    # Denemeler bilerek iki farklı yazımla gönderiliyor: anahtar normalize
    # edilmezse hiçbir kova limite ulaşmaz ve son yanıt 429 yerine 401 olur.
    varyantlar = [
        "YOK" if sira % 2 else "  yok  "
        for sira in range(settings.rate_limit_giris + 1)
    ]

    son_durum = None
    for ad in varyantlar:
        son_durum = istemci.post(
            "/auth/login", data={"username": ad, "password": "yanlis"}
        ).status_code

    assert son_durum == 429


@pytest.mark.entegrasyon
def test_basarili_giris_hiz_kotasi_tuketmez(istemci, kullanici_uret):
    # Kararın dayandığı özellik: yalnızca BAŞARISIZ deneme sayılıyor. Uç gövdesine
    # başarı yolunda kalmış tek bir kayıt çağrısı bu testi kırar.
    kullanici_uret(kullanici_adi="ayse", parola="dogru-parola")

    son_durum = None
    for _ in range(settings.rate_limit_giris + 1):
        son_durum = istemci.post(
            "/auth/login", data={"username": "ayse", "password": "dogru-parola"}
        ).status_code

    assert son_durum == 200


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


@pytest.mark.entegrasyon
def test_hata_mesajinda_yigin_izi_yok(istemci, yetkili_baslik, monkeypatch):
    # Yığın izi ve dosya yolları istemciye sızarsa saldırgan iç yapıyı öğrenir.
    # Beklenmeyen bir istisna, /document/liste üzerinden tetikleniyor.
    from app.api import document as document_modulu

    def _patlat():
        raise RuntimeError("gizli-ic-detay-sizmamali")

    monkeypatch.setattr(document_modulu, "get_collection", _patlat)

    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    assert yanit.status_code == 500
    govde = yanit.text
    assert "gizli-ic-detay-sizmamali" not in govde
    assert "Traceback" not in govde
    assert "RuntimeError" not in govde
    # İzleme kodu, sızıntı yaratmadan log'daki satırla eşleşmeyi sağlıyor.
    assert yanit.json()["izleme_kodu"]


@pytest.mark.entegrasyon
def test_izleme_kodu_ve_hata_detayi_loga_yaziliyor(
    istemci, yetkili_baslik, monkeypatch, caplog
):
    # İzleme kodunun TEK amacı, kullanıcının ekranda okuduğu kodu operatörün
    # log'da bulabilmesi. Yukarıdaki test yalnızca istemci yarısını donduruyor;
    # log yarısı bağlanmazsa `logger.exception` -> `logger.error` değişimi
    # (yığın izinin kaybı) ya da kodun format dizesinden düşmesi bütün testler
    # yeşilken izleme kodunu işe yaramaz hale getirir.
    from app.api import document as document_modulu

    def _patlat():
        raise RuntimeError("gizli-ic-detay-sizmamali")

    monkeypatch.setattr(document_modulu, "get_collection", _patlat)
    # Handler ERROR seviyesinde yazıyor; caplog'un o seviyeyi kapsadığı açıkça
    # sabitleniyor ki testin yakalaması kök logger ayarına bağlı kalmasın.
    caplog.set_level(logging.ERROR, logger="ai_triage")

    yanit = istemci.get(
        "/document/liste",
        headers=yetkili_baslik(kullanici_adi="yonetici", rol="admin"),
    )

    izleme_kodu = yanit.json()["izleme_kodu"]
    # İstemciye dönen kod log satırında AYNEN geçmeli; yoksa eşleştirme imkânsız.
    assert izleme_kodu in caplog.text
    # İstemciden gizlenen ayrıntı log'da DURMALI: yığın izi olmadan operatörün
    # elinde yalnızca "Sunucu hatası" kalır ve kod hiçbir şeye götürmez.
    assert "gizli-ic-detay-sizmamali" in caplog.text


@pytest.mark.entegrasyon
def test_gecersiz_jwt_ile_401_ve_detay_sizmaz(istemci, jeton_uret):
    # İki FARKLI başarısızlık sebebi aynı yanıtı vermeli: "kullanıcı yok" ile
    # "jeton bozuk" ayrımı dışarı verilirse saldırgan geçerli kullanıcı adı
    # numaralandırabilir.
    olmayan_kullanici_jetonu = jeton_uret(kullanici_adi="hic_olmayan", rol="user")
    bozuk_jeton = "bu.gecerli.bir.jwt.degil"

    yanit_a = istemci.get(
        "/auth/me", headers={"Authorization": f"Bearer {olmayan_kullanici_jetonu}"}
    )
    yanit_b = istemci.get("/auth/me", headers={"Authorization": f"Bearer {bozuk_jeton}"})

    assert yanit_a.status_code == 401
    assert yanit_b.status_code == 401
    assert yanit_a.json()["detail"] == yanit_b.json()["detail"]


@pytest.mark.entegrasyon
def test_cors_sadece_izinli_kaynaga_acik(istemci):
    # İKİ yönlü doğrulama şart. Yalnızca "izinsiz origin başlık almamalı" demek
    # bağlayıcı DEĞİL: CORS middleware'i hiç yokken de o başlık dönmez, yani test
    # düzeltmeden önce de geçerdi. İzinli origin'in başlığı ALDIĞINI da
    # doğrulamak, middleware'in gerçekten kurulu olmasını zorunlu kılıyor.
    izinli = [k.strip() for k in settings.cors_origins.split(",") if k.strip()][0]

    izinli_yanit = istemci.get("/health/", headers={"Origin": izinli})
    izinsiz_yanit = istemci.get("/health/", headers={"Origin": "http://kotu-site.example"})

    assert izinli_yanit.headers.get("access-control-allow-origin") == izinli
    assert (
        izinsiz_yanit.headers.get("access-control-allow-origin")
        != "http://kotu-site.example"
    )
