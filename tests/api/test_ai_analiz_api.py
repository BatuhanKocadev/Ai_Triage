"""POST /ai/analiz sözleşmesini dondurur: durum kodları, yanıt şeması,
eşik altı yolu ve veritabanına yazma davranışı."""

import uuid

import pytest

from app.api import ai as ai_modulu
from app.models.visit import AIRecommendation, Visit
from tests.yardimcilar.sahte_llm import GECERLI_YANIT, hata_firlatan_llm, sahte_llm_uret
from tests.yardimcilar.veri_uretici import ziyaret_verisi


@pytest.fixture
def esik_ustu(monkeypatch):
    """RAG'i eşiği geçmiş gibi, LLM'i geçerli yanıt verir gibi ayarlar."""
    monkeypatch.setattr(ai_modulu, "get_collection", lambda: object())
    monkeypatch.setattr(
        ai_modulu, "retrieve_and_rerank",
        lambda **kwargs: ["[Kaynak: protokol.pdf] Göğüs ağrısı protokolü"],
    )
    monkeypatch.setattr(
        ai_modulu, "get_structured_completion", sahte_llm_uret(GECERLI_YANIT)
    )


@pytest.mark.entegrasyon
def test_kisa_sikayet_422_doner(istemci, yetkili_baslik, esik_alti):
    # symptom_text min_length=10; 9 karakter reddedilmeli.
    # esik_alti: kural gevşerse test temiz kırmızı versin, gerçek servise gitmesin.
    yanit = istemci.post(
        "/ai/analiz",
        json=ziyaret_verisi(symptom_text="karin agr"),
        headers=yetkili_baslik(),
    )
    assert yanit.status_code == 422


@pytest.mark.entegrasyon
def test_gecersiz_yas_422_doner(istemci, yetkili_baslik, esik_alti):
    # patient_age le=120 sınırının üstü reddedilmeli.
    # esik_alti: kural gevşerse test temiz kırmızı versin, gerçek servise gitmesin.
    yanit = istemci.post(
        "/ai/analiz",
        json=ziyaret_verisi(patient_age=200),
        headers=yetkili_baslik(),
    )
    assert yanit.status_code == 422


@pytest.mark.entegrasyon
def test_gecersiz_giris_tipi_422_doner(istemci, yetkili_baslik, esik_alti):
    # giris_tipi Literal["metin","ses"]; başka değer reddedilmeli.
    # esik_alti: kural gevşerse test temiz kırmızı versin, gerçek servise gitmesin.
    yanit = istemci.post(
        "/ai/analiz",
        json=ziyaret_verisi(giris_tipi="faks"),
        headers=yetkili_baslik(),
    )
    assert yanit.status_code == 422


@pytest.mark.entegrasyon
def test_basarili_analiz_200_ve_sema_alanlari(istemci, yetkili_baslik, esik_ustu):
    # Frontend'in okuduğu alan adlarının/normalizasyonun sessizce değişmesini yakalar.
    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=yetkili_baslik())
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["triage_code"] == "Sarı"
    assert govde["department"] == "Sarı Alan"
    assert govde["onerilen_tetkikler"] == ["Tam kan sayımı"]
    assert govde["visit_id"] is not None
    assert govde["sources"] == ["[Kaynak: protokol.pdf] Göğüs ağrısı protokolü"]


@pytest.mark.entegrasyon
def test_few_shot_ornekleri_prompta_enjekte_edilir(
    istemci, yetkili_baslik, monkeypatch
):
    """Few-shot enjeksiyonu `settings.few_shot_aktif`e bağlı ve VARSAYILAN KAPALI."""
    yakalanan = {}

    def _yakala(system_prompt: str, user_prompt: str, **kwargs):
        yakalanan["system_prompt"] = system_prompt
        return dict(GECERLI_YANIT)

    monkeypatch.setattr(ai_modulu, "get_collection", lambda: object())
    monkeypatch.setattr(
        ai_modulu,
        "retrieve_and_rerank",
        lambda **kwargs: ["[Kaynak: protokol.pdf] Göğüs ağrısı protokolü"],
    )
    monkeypatch.setattr(ai_modulu, "get_structured_completion", _yakala)

    ORNEK = "arı soktu, kolum şişti ama nefesim rahat"
    # Başlık bir kez alınıyor: `yetkili_baslik()` her çağrıda kullanıcı yaratıyor
    # ve ikinci çağrı unique kısıtına takılırdı.
    baslik = yetkili_baslik()

    # VARSAYILAN: kapalı — örnek prompt'a girmiyor.
    assert ai_modulu.settings.few_shot_aktif is False
    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=baslik)
    assert yanit.status_code == 200
    assert ORNEK not in yakalanan["system_prompt"]

    # AÇIKKEN: havuz gerçekten enjekte ediliyor (mekanizma sağlam, yalnızca kapalı).
    monkeypatch.setattr(ai_modulu.settings, "few_shot_aktif", True)
    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=baslik)
    assert yanit.status_code == 200
    assert ORNEK in yakalanan["system_prompt"]


@pytest.mark.entegrasyon
def test_esik_altinda_llm_cagrilmaz_ve_belirsiz_doner(
    istemci, yetkili_baslik, esik_alti, monkeypatch
):
    # LLM çağrılırsa test patlasın diye bilerek hata fırlatan sahte koyuyoruz.
    # Eşik kapısının kalkması (her isteğin LLM'e gitmesi) burada yakalanır.
    monkeypatch.setattr(ai_modulu, "get_structured_completion", hata_firlatan_llm())

    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=yetkili_baslik())
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["triage_code"] == "Belirsiz"
    assert govde["department"] == "Triyaj Bankosu"
    assert govde["onerilen_tetkikler"] == []
    assert govde["visit_id"] is not None  # eşik altı vaka da kaydedilmeli


@pytest.mark.entegrasyon
def test_llm_hatasi_502_doner(istemci, yetkili_baslik, monkeypatch):
    # Ollama çökmesinin 500 ya da yakalanmamış istisna olarak sızmasını yakalar.
    monkeypatch.setattr(ai_modulu, "get_collection", lambda: object())
    monkeypatch.setattr(ai_modulu, "retrieve_and_rerank", lambda **kwargs: ["dokuman"])
    monkeypatch.setattr(ai_modulu, "get_structured_completion", hata_firlatan_llm())

    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=yetkili_baslik())
    assert yanit.status_code == 502


@pytest.mark.entegrasyon
def test_ziyaret_ve_oneri_veritabanina_yazilir(
    istemci, yetkili_baslik, esik_ustu, db_oturum
):
    # Kayıt adımının düşmesini yakalar: vaka doktor kuyruğuna hiç girmezdi.
    yanit = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=yetkili_baslik())
    # JSON'dan string gelir; UUID sütununda sorgulamak için tipe çeviriyoruz.
    ziyaret_id = uuid.UUID(yanit.json()["visit_id"])

    ziyaret = db_oturum.query(Visit).filter_by(id=ziyaret_id).one()
    assert ziyaret.status == "bekliyor"  # yeni vaka doktor kuyruğunda başlar
    oneri = db_oturum.query(AIRecommendation).filter_by(visit_id=ziyaret_id).one()
    assert oneri.triage_code == "Sarı"


@pytest.mark.entegrasyon
def test_ses_kaynakli_basvuru_giris_tipi_ses_kaydedilir(
    istemci, yetkili_baslik, esik_ustu, db_oturum
):
    # giris_tipi'ni /speech/transkript değil, /ai/analiz kaydeder.
    yanit = istemci.post(
        "/ai/analiz",
        json=ziyaret_verisi(giris_tipi="ses"),
        headers=yetkili_baslik(),
    )
    ziyaret = db_oturum.query(Visit).filter_by(id=uuid.UUID(yanit.json()["visit_id"])).one()
    assert ziyaret.giris_tipi == "ses"


@pytest.mark.entegrasyon
def test_varsayilan_giris_tipi_metindir(
    istemci, yetkili_baslik, esik_ustu, db_oturum
):
    # Alan gönderilmeyen eski istemcilerin kaydının bozulmasını yakalar.
    govde = ziyaret_verisi()
    del govde["giris_tipi"]  # alan hiç gönderilmezse
    yanit = istemci.post("/ai/analiz", json=govde, headers=yetkili_baslik())
    ziyaret = db_oturum.query(Visit).filter_by(id=uuid.UUID(yanit.json()["visit_id"])).one()
    assert ziyaret.giris_tipi == "metin"
