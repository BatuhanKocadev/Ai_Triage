"""Hasta şikayetinden doktor onayına kadar tam döngünün tek testi."""

import uuid

import pytest

from app.api import ai as ai_modulu
from app.models.visit import Visit
from tests.yardimcilar.sahte_llm import GECERLI_YANIT, sahte_llm_uret
from tests.yardimcilar.veri_uretici import ziyaret_verisi


@pytest.fixture
def esik_ustu(monkeypatch):
    """RAG'i eşiği geçmiş, LLM'i geçerli yanıt verir gibi ayarlar."""
    monkeypatch.setattr(ai_modulu, "get_collection", lambda: object())
    monkeypatch.setattr(
        ai_modulu,
        "retrieve_and_rerank",
        lambda **kwargs: ["[Kaynak: protokol.pdf] Göğüs ağrısı protokolü"],
    )
    monkeypatch.setattr(
        ai_modulu, "get_structured_completion", sahte_llm_uret(GECERLI_YANIT)
    )


@pytest.mark.entegrasyon
def test_sikayetten_doktor_onayina_tam_dongu(istemci, db_oturum, yetkili_baslik, esik_ustu):
    # Zincirin tamamı tek testte: hasta başvurusu girer, doktor kuyruğunda görür,
    # yapay zekânın kararını değiştirip onaylar, vaka kuyruktan düşer.
    hasta_baslik = yetkili_baslik(kullanici_adi="hasta_ayse", rol="user")
    doktor_baslik = yetkili_baslik(kullanici_adi="dr_veli", rol="doctor")

    # 1) Hasta şikayetini girer, yapay zekâ "Sarı" der.
    analiz = istemci.post("/ai/analiz", json=ziyaret_verisi(), headers=hasta_baslik)
    assert analiz.status_code == 200
    assert analiz.json()["triage_code"] == "Sarı"
    visit_id = analiz.json()["visit_id"]

    # 2) Vaka doktorun kuyruğunda görünür.
    liste = istemci.get("/doctor/bekleyen", headers=doktor_baslik).json()
    assert visit_id in [vaka["visit_id"] for vaka in liste]

    # 3) Doktor kararı "Kırmızı"ya çevirip onaylar.
    onay = istemci.post(
        "/doctor/inceleme",
        json={
            "visit_id": visit_id,
            "onaylanan_triage_code": "Kırmızı",
            "onaylanan_tetkikler": ["EKG"],
            "doktor_notu": "Acil servise alindi",
        },
        headers=doktor_baslik,
    )
    assert onay.status_code == 201

    # 4) Vaka kuyruktan düşer ve ziyaret tamamlandi olur.
    kalan = istemci.get("/doctor/bekleyen", headers=doktor_baslik).json()
    assert visit_id not in [vaka["visit_id"] for vaka in kalan]

    ziyaret = db_oturum.query(Visit).filter_by(id=uuid.UUID(visit_id)).one()
    assert ziyaret.status == "tamamlandi"
