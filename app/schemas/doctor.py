"""Doktor uçlarının istek ve yanıt şemaları."""

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Doktorun onaylayabileceği triyaj kodları. "Belirsiz" bilerek yok: o yapay zekânın
# "karar veremedim" çıktısı, doktorun işi ise tam olarak belirsizliği gidermek.
DoktorTriyajKodu = Literal["Kırmızı", "Sarı", "Yeşil"]


class AIOnerisi(BaseModel):
    """Bekleyen vaka listesinde gömülü gelen yapay zekâ önerisi."""

    model_config = ConfigDict(from_attributes=True)

    # Modelin verdiği aciliyet kodu; eşik altı vakalarda "Belirsiz" de olabildiği için düz str.
    triage_code: str
    # Modelin yönlendirdiği poliklinik/bölüm adı.
    department: str
    # Modelin önerdiği tetkikler; öneri boş dönebildiği için varsayılanı boş liste.
    onerilen_tetkikler: list[str] = []
    # Modelin doktora bıraktığı kısa gerekçe notu.
    ai_note: str
    # Önerinin dayandığı protokol dokümanları; doktor kararı kaynağıyla birlikte görsün.
    sources: list[str] = []


class BekleyenVaka(BaseModel):
    """Doktorun listede gördüğü tek bir bekleyen başvuru."""

    # Ziyaretin kimliği; doktor incelemeyi bu kimlikle gönderecek.
    visit_id: uuid.UUID
    # Hastanın yaşı.
    patient_age: int
    # Hastanın cinsiyeti.
    gender: str
    # Hastanın kendi ifadesiyle şikayet metni.
    symptom_text: str
    # Varsa kronik hastalık bilgisi; girilmemişse null.
    chronic_disease: Optional[str] = None
    # Varsa ölçülen vital değerler sözlüğü; girilmemişse null.
    vitals: Optional[dict] = None
    # Şikayetin geliş kanalı ("ses"/"metin"); doktor transkript hatası ihtimalini bilmeli.
    giris_tipi: str
    # Başvurunun alınma zamanı; liste bu alana göre en yeniden eskiye sıralanır.
    created_at: datetime
    # Öneri opsiyonel: yazma yolu ziyaret ve öneriyi birlikte yazıyor ama şema bunu
    # garanti etmiyor; önerisiz bir ziyarette uç çökmek yerine null döndürür.
    ai_onerisi: Optional[AIOnerisi] = None


class IncelemeIstegi(BaseModel):
    """Doktorun onay gövdesi; doctor_id bilinçli olarak yok, JWT'den okunur."""

    # İncelenen ziyaretin kimliği.
    visit_id: uuid.UUID
    # Doktorun onayladığı nihai triyaj kodu; "Belirsiz" kabul edilmez.
    onaylanan_triage_code: DoktorTriyajKodu
    # Doktorun onayladığı tetkik listesi; hiçbiri onaylanmayabilir, varsayılanı boş liste.
    onaylanan_tetkikler: list[str] = []
    # Doktorun serbest metin notu; opsiyonel ve en fazla 1000 karakter.
    doktor_notu: Optional[str] = Field(None, max_length=1000)


class IncelemeYaniti(BaseModel):
    """Kaydedilen incelemenin geri dönüşü."""

    model_config = ConfigDict(from_attributes=True)

    # Kaydedilen inceleme satırının kimliği.
    id: int
    # İncelemenin bağlı olduğu ziyaretin kimliği.
    visit_id: uuid.UUID
    # İncelemeyi yapan doktorun kullanıcı kimliği.
    doctor_id: int
    # Doktorun onayladığı triyaj kodu.
    onaylanan_triage_code: str
    # Doktorun onayladığı tetkik listesi.
    onaylanan_tetkikler: list[str]
    # Doktorun bıraktığı not; girilmemişse null.
    doktor_notu: Optional[str] = None
    # İncelemenin kaydedilme zamanı.
    created_at: datetime
