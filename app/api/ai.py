from fastapi import APIRouter, status, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import json
from app.services.openai_client import client
from app.services.rag_service import retrieve_and_rerank
from app.utils.logger import logger
from app.services.chroma_service import triage_collection
from app.services.auth_service import require_user_or_admin_role

router = APIRouter(
    prefix="/ai",
    tags=["AI Analysis"]
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

class AnalysisResponse(BaseModel):
    status: str
    triage_code: str           
    department: str 
    ai_note: str
    sources: list[str] = []

@router.post("/analiz", response_model=AnalysisResponse, status_code=status.HTTP_200_OK)
def analyze_symptoms(request_data: AnalysisRequest, current_user: dict = Depends(require_user_or_admin_role)):
    filter_kwargs = {"source": request_data.source_document} if request_data.source_document else None
    
    try:
        relevant_documents = retrieve_and_rerank(
            query=request_data.symptom_text, 
            collection=triage_collection,
            threshold=0.70,
            metadata_filter=filter_kwargs
        )
    except Exception as e:
        logger.error(f"Rerank Error: {str(e)}")
        relevant_documents = []
    
    if not relevant_documents:
        return AnalysisResponse(
            status="success",
            triage_code="Belirsiz",
            department="Triyaj Bankosu",
            ai_note="Semptomlar veritabanındaki kritik eşiği geçemediği için LLM analizi yapılmadı. Hasta doğrudan bankoya yönlendirildi.",
            sources=[]
        )
        
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
    {{"status": "success", "triage_code": "Kırmızı/Sarı/Yeşil", "department": "Bölüm Adı", "ai_note": "Açıklama"}}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Şikayet: {request_data.symptom_text}"}
            ]
        )
        
        result_dict = json.loads(response.choices[0].message.content)
        result_dict["sources"] = relevant_documents
        return AnalysisResponse(**result_dict)
        
    except json.JSONDecodeError:
        logger.error("JSON Error")
        raise HTTPException(status_code=500, detail="JSON parse error")
    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        raise HTTPException(status_code=502, detail="API unavailable")