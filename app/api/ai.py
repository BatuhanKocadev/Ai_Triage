import uuid
from fastapi import APIRouter, status, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.visit import AIRecommendation, Visit
from app.services.llm_service import get_structured_completion, LLMError
from app.services.rag_service import retrieve_and_rerank
from app.utils.logger import logger
from app.services.chroma_service import get_collection
from app.services.auth_service import require_user_or_admin_role
from app.utils.hiz_sinirlayici import genel_sinirlayici, hiz_siniri

router = APIRouter(
    prefix="/ai",
    tags=["AI Analysis"]
)

# Modelin döndürebileceği geçerli triyaj kodları. Yerel 7B model zaman zaman
# bunların dışına çıkabildiği için yanıt normalize ediliyor.
GECERLI_TRIYAJ_KODLARI = {"Kırmızı", "Sarı", "Yeşil"}

KLINIK_UYARI = (
    "Bu öneri klinik karar destek amaçlıdır; kesin tanı ve tedavi hekim onayına tabidir."
)

class GenderEnum(str, Enum):
    male = "Erkek"
    female = "Kadın"
    other = "Diğer"

class Vitals(BaseModel):
    fever: Optional[float] = Field(None)
    pulse: Optional[int] = Field(None)

class AnalysisRequest(BaseModel):
    patient_age: int = Field(..., ge=0, le=120)
    gender: GenderEnum
    symptom_text: str = Field(..., min_length=10, max_length=500)
    chronic_disease: Optional[str] = Field(None)
    vitals: Optional[Vitals] = None
    source_document: Optional[str] = Field(None)
    # Şikayetin nereden geldiği: ses akışı "ses" gönderir, yazılı akış "metin".
    # Literal sayesinde bu ikisi dışında bir değer daha istekte reddedilir.
    giris_tipi: Literal["metin", "ses"] = "metin"

class AnalysisResponse(BaseModel):
    status: str
    triage_code: str
    department: str
    onerilen_tetkikler: list[str] = []
    ai_note: str
    sources: list[str] = []
    # Doktor inceleme akışı (Gün 17-18) bu ziyareti bu kimlikle bulacak.
    visit_id: Optional[uuid.UUID] = None


def _sadelestir(metin: str) -> str:
    """Türkçe karakterleri ASCII'ye indirger ve küçük harfe çevirir.

    Yerel model triyaj kodunu bazen 'Kirmizi' gibi ASCII'leştirilmiş yazıyor;
    bu sadeleştirme sayesinde 'Kırmızı' ile eşleşiyor.
    """
    esleme = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iisSgGuUoOcC")
    return metin.translate(esleme).lower().strip()


def _normalize_triage_code(raw_code) -> str:
    """Modelin döndürdüğü triyaj kodunu geçerli kümeye indirger."""
    if not isinstance(raw_code, str):
        return "Belirsiz"

    sade = _sadelestir(raw_code)
    for gecerli in GECERLI_TRIYAJ_KODLARI:
        if sade == _sadelestir(gecerli):
            return gecerli

    logger.warning(f"Beklenmeyen triyaj kodu: {raw_code!r} -> 'Belirsiz'")
    return "Belirsiz"


def _normalize_tetkikler(raw_tetkikler) -> list[str]:
    """Tetkik listesini temizler; model string döndürürse listeye çevirir."""
    if isinstance(raw_tetkikler, str):
        raw_tetkikler = [raw_tetkikler]
    if not isinstance(raw_tetkikler, list):
        return []

    return [str(t).strip() for t in raw_tetkikler if str(t).strip()]


def _kaydet(db: Session, request_data: "AnalysisRequest", sonuc: AnalysisResponse) -> uuid.UUID:
    """Ziyareti ve yapay zekâ önerisini veritabanına yazar, ziyaret kimliğini döndürür.

    Eşik altında kalan (LLM'e hiç gitmeyen) başvurular da kaydediliyor: bunlar
    doktorun bizzat bakması gereken vakalar, dolayısıyla bekleyen vaka
    listesinde görünmeleri gerekiyor.
    """
    ziyaret = Visit(
        patient_age=request_data.patient_age,
        gender=request_data.gender.value,
        symptom_text=request_data.symptom_text,
        chronic_disease=request_data.chronic_disease,
        vitals=request_data.vitals.model_dump() if request_data.vitals else None,
        # Giriş kanalı ziyaretle birlikte kalıcı hale getiriliyor (Gün 15).
        giris_tipi=request_data.giris_tipi,
    )
    db.add(ziyaret)
    db.flush()  # ziyaret.id üretilsin ki öneriye bağlayabilelim

    db.add(AIRecommendation(
        visit_id=ziyaret.id,
        triage_code=sonuc.triage_code,
        department=sonuc.department,
        onerilen_tetkikler=sonuc.onerilen_tetkikler,
        ai_note=sonuc.ai_note,
        sources=sonuc.sources,
    ))
    db.commit()
    return ziyaret.id


# En pahalı uç: yerel LLM'i çalıştırıyor, kötüye kullanım servisi tüketir (Gün 21).
@router.post(
    "/analiz",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(hiz_siniri(genel_sinirlayici))],
)
def analyze_symptoms(
    request_data: AnalysisRequest,
    current_user: User = Depends(require_user_or_admin_role),
    db: Session = Depends(get_db),
):
    filter_kwargs = {"source": request_data.source_document} if request_data.source_document else None

    try:
        # Eşik ayarlardan okunuyor (settings.rerank_threshold), böylece
        # değerlendirme sırasında kod değiştirmeden ayarlanabiliyor.
        relevant_documents = retrieve_and_rerank(
            query=request_data.symptom_text,
            collection=get_collection(),
            metadata_filter=filter_kwargs
        )
    except Exception as e:
        logger.error(f"Rerank Error: {str(e)}")
        relevant_documents = []

    if not relevant_documents:
        esik_alti_sonuc = AnalysisResponse(
            status="success",
            triage_code="Belirsiz",
            department="Triyaj Bankosu",
            onerilen_tetkikler=[],
            ai_note="Semptomlar veritabanındaki kritik eşiği geçemediği için LLM analizi yapılmadı. Hasta doğrudan bankoya yönlendirildi.",
            sources=[]
        )
        esik_alti_sonuc.visit_id = _kaydet(db, request_data, esik_alti_sonuc)
        return esik_alti_sonuc

    source_text = "\n".join(relevant_documents)

    fever_info = request_data.vitals.fever if request_data.vitals and request_data.vitals.fever else 'Bilinmiyor'
    pulse_info = request_data.vitals.pulse if request_data.vitals and request_data.vitals.pulse else 'Bilinmiyor'
    chronic_info = request_data.chronic_disease if request_data.chronic_disease else 'Yok'

    system_prompt = f"""
    Sen uzman bir tıbbi triyaj yapay zekasısın.
    Yaş: {request_data.patient_age}, Cinsiyet: {request_data.gender.value}, Kronik Hastalık: {chronic_info}
    Vitaller: Ateş: {fever_info}, Nabız: {pulse_info}

    Referans dokümanlar:
    {source_text}

    Sadece JSON formatında döndür:
    {{"status": "success", "triage_code": "Kırmızı/Sarı/Yeşil", "department": "Bölüm Adı",
      "onerilen_tetkikler": ["Tam kan sayımı", "..."], "ai_note": "Açıklama"}}

    Kurallar:
    - triage_code yalnızca "Kırmızı", "Sarı" veya "Yeşil" olabilir.
    - onerilen_tetkikler sadece yukarıdaki referans dokümanlarda geçen veya
      onlarla desteklenen tetkikleri içersin; uydurma tetkik yazma.
    - Referans dokümanlar tetkik önermek için yeterli değilse onerilen_tetkikler
      alanını boş liste olarak döndür.
    - Bu bir klinik karar destek önerisidir; kesin tanı ve tedavi hekim onayına tabidir.
    """

    try:
        result_dict = get_structured_completion(
            system_prompt=system_prompt,
            user_prompt=f"Şikayet: {request_data.symptom_text}",
        )
    except LLMError as e:
        logger.error(f"LLM Error: {str(e)}")
        raise HTTPException(status_code=502, detail="Yerel LLM servisi yanıt vermiyor")

    ai_note = str(result_dict.get("ai_note") or "").strip()
    if KLINIK_UYARI not in ai_note:
        ai_note = f"{ai_note} {KLINIK_UYARI}".strip()

    sonuc = AnalysisResponse(
        status="success",
        triage_code=_normalize_triage_code(result_dict.get("triage_code")),
        department=str(result_dict.get("department") or "Triyaj Bankosu").strip(),
        onerilen_tetkikler=_normalize_tetkikler(result_dict.get("onerilen_tetkikler")),
        ai_note=ai_note,
        sources=relevant_documents,
    )
    sonuc.visit_id = _kaydet(db, request_data, sonuc)
    return sonuc
