from fastapi import APIRouter, UploadFile, File, Form, status, HTTPException, Depends
from datetime import datetime
import io
import pdfplumber
import docx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.utils.logger import logger
from app.models.user import User
from app.services.chroma_service import triage_collection
from app.services.auth_service import require_admin_role

router = APIRouter(
    prefix="/document",
    tags=["Document Management"]
)

def format_table_to_markdown(table_data: list[list[str]]) -> str:
    if not table_data or not table_data[0]:
        return ""
    
    markdown_table = "\n"
    headers = [str(item).replace("\n", " ").strip() if item else "" for item in table_data[0]]
    markdown_table += "| " + " | ".join(headers) + " |\n"
    markdown_table += "|-" + "-|-".join(["-" * len(h) for h in headers]) + "-|\n"
    
    for row in table_data[1:]:
        row_values = [str(item).replace("\n", " ").strip() if item else "" for item in row]
        while len(row_values) < len(headers):
            row_values.append("")
        markdown_table += "| " + " | ".join(row_values[:len(headers)]) + " |\n"
    
    return markdown_table + "\n"

def process_pdf_content(file_bytes: bytes) -> str:
    extracted_text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n\n"
            
            tables = page.extract_tables()
            for table in tables:
                extracted_text += format_table_to_markdown(table)
    return extracted_text

def process_docx_content(file_bytes: bytes) -> str:
    extracted_text = ""
    doc = docx.Document(io.BytesIO(file_bytes))
    
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            extracted_text += paragraph.text + "\n\n"
    
    for table in doc.tables:
        table_data = []
        for row in table.rows:
            row_data = [cell.text for cell in row.cells]
            table_data.append(row_data)
        extracted_text += format_table_to_markdown(table_data)
        
    return extracted_text

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    category: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin_role)
):
    try:
        file_content = await file.read()
        extracted_text = ""
        file_extension = file.filename.lower().split('.')[-1]
        
        if file_extension == "pdf":
            try:
                extracted_text = process_pdf_content(file_content)
            except Exception as e:
                logger.error(f"PDF processing error: {str(e)}")
                raise HTTPException(status_code=400, detail="PDF processing error")
        elif file_extension == "docx":
            try:
                extracted_text = process_docx_content(file_content)
            except Exception as e:
                logger.error(f"DOCX processing error: {str(e)}")
                raise HTTPException(status_code=400, detail="DOCX processing error")
        elif file_extension == "txt":
            try:
                extracted_text = file_content.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Encoding error")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Empty content")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        text_chunks = text_splitter.split_text(extracted_text)
        
        if not text_chunks:
            raise HTTPException(status_code=400, detail="Chunking failed")
            
        metadata_list = []
        id_list = []
        
        safe_filename = file.filename.replace(" ", "_").lower()
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        for index, chunk in enumerate(text_chunks):
            metadata_list.append({
                "source": file.filename,
                "upload_date": current_date,
                "category": category,
                "chunk_index": index
            })
            id_list.append(f"{safe_filename}_chunk_{index}")
        
        triage_collection.upsert(
            documents=text_chunks,
            metadatas=metadata_list,
            ids=id_list
        )
        
        logger.info(f"Uploaded and chunked: {file.filename} by {current_user.username}")
        
        return {
            "status": "success",
            "message": "Success",
            "total_chunks": len(text_chunks),
            "sample_metadata": metadata_list[0] if metadata_list else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload error")