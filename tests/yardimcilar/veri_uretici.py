"""Testlerin tekrar tekrar yazmaması için hazır istek gövdeleri."""


def ziyaret_verisi(**degisiklikler) -> dict:
    """/ai/analiz için geçerli bir istek gövdesi; alanlar kwargs ile ezilebilir."""
    govde = {
        "patient_age": 45,
        "gender": "Erkek",
        "symptom_text": "Göğsümde baskı hissi ve sol kola yayılan ağrı var",
        "chronic_disease": "Hipertansiyon",
        "vitals": {"fever": 36.8, "pulse": 96},
        "giris_tipi": "metin",
    }
    govde.update(degisiklikler)
    return govde
