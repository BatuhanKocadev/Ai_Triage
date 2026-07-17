import chromadb
import os

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))

chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
triage_collection = chroma_client.get_or_create_collection(name="triage_documents")