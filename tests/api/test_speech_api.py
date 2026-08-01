"""POST /speech/transkript sözleşmesini dondurur.
faster-whisper modeli hiçbir testte yüklenmez."""

import io

import pytest

from app.api import speech as speech_modulu
from tests.yardimcilar.sahte_stt import hata_firlatan_stt, sahte_transkript_uret


def _ses_dosyasi(ad="kayit.wav", icerik=b"sahte-ses-baytlari"):
    """multipart yüklemesi için dosya demeti üretir."""
    return {"file": (ad, io.BytesIO(icerik), "audio/wav")}


@pytest.mark.entegrasyon
def test_jetonsuz_istek_401_doner(istemci):
    # Regresyon: uçtaki auth bağımlılığı düşerse ses yükleme herkese açılır.
    yanit = istemci.post("/speech/transkript", files=_ses_dosyasi())
    assert yanit.status_code == 401


@pytest.mark.entegrasyon
def test_desteklenmeyen_format_400_doner(istemci, yetkili_baslik):
    # Regresyon: beyaz liste gevşerse ses olmayan dosya STT'ye gider (model boşuna yüklenir).
    # .txt beyaz listede yok; STT hiç çağrılmadan reddedilmeli.
    yanit = istemci.post(
        "/speech/transkript",
        files=_ses_dosyasi(ad="notlar.txt"),
        headers=yetkili_baslik(),
    )
    assert yanit.status_code == 400
    assert "Desteklenmeyen dosya formatı" in yanit.json()["detail"]


@pytest.mark.entegrasyon
def test_cok_buyuk_dosya_400_doner(istemci, yetkili_baslik):
    # Regresyon: boyut kapısı kalkarsa devasa yükleme belleği ve CPU'yu sınırsız tüketir.
    # 25 MB sınırının üstü reddedilmeli.
    buyuk = b"x" * (26 * 1024 * 1024)
    yanit = istemci.post(
        "/speech/transkript",
        files=_ses_dosyasi(icerik=buyuk),
        headers=yetkili_baslik(),
    )
    assert yanit.status_code == 400
    assert "25 MB" in yanit.json()["detail"]


@pytest.mark.entegrasyon
def test_basarili_transkript_metin_sure_ve_model_doner(
    istemci, yetkili_baslik, monkeypatch
):
    # Regresyon: yanıt alan adları ya da model bilgisi değişirse frontend sessizce boş metin gösterir.
    monkeypatch.setattr(
        speech_modulu, "transcribe", sahte_transkript_uret("Başım çok ağrıyor")
    )
    yanit = istemci.post(
        "/speech/transkript", files=_ses_dosyasi(), headers=yetkili_baslik()
    )
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["transcript"] == "Başım çok ağrıyor"
    assert govde["sure_saniye"] >= 0
    assert govde["model"] == "medium"  # settings.whisper_model_size


@pytest.mark.entegrasyon
def test_stt_hatasi_422_doner(istemci, yetkili_baslik, monkeypatch):
    # Regresyon: STTError yakalanmazsa kullanıcı anlaşılır uyarı yerine 500 görür.
    monkeypatch.setattr(speech_modulu, "transcribe", hata_firlatan_stt())
    yanit = istemci.post(
        "/speech/transkript", files=_ses_dosyasi(), headers=yetkili_baslik()
    )
    assert yanit.status_code == 422
    assert "Ses anlaşılamadı" in yanit.json()["detail"]


@pytest.mark.entegrasyon
def test_bos_transkript_422_doner(istemci, yetkili_baslik, monkeypatch):
    # Regresyon: boşluk kontrolü kalkarsa sessiz kayıt boş şikayetle analize kadar ilerler.
    # Sessiz kayıt: model boş metin döndürürse kullanıcıya hata gösterilmeli.
    monkeypatch.setattr(speech_modulu, "transcribe", sahte_transkript_uret("   "))
    yanit = istemci.post(
        "/speech/transkript", files=_ses_dosyasi(), headers=yetkili_baslik()
    )
    assert yanit.status_code == 422


@pytest.mark.entegrasyon
@pytest.mark.parametrize("uzanti", [".wav", ".mp3", ".m4a", ".ogg", ".webm"])
def test_desteklenen_formatlarin_hepsi_kabul_edilir(
    istemci, yetkili_baslik, monkeypatch, uzanti
):
    # Regresyon: beyaz listeden bir uzantı düşerse o tarayıcının kaydı (örn. webm) reddedilir.
    monkeypatch.setattr(speech_modulu, "transcribe", sahte_transkript_uret("metin"))
    yanit = istemci.post(
        "/speech/transkript",
        files=_ses_dosyasi(ad=f"kayit{uzanti}"),
        headers=yetkili_baslik(),
    )
    assert yanit.status_code == 200
