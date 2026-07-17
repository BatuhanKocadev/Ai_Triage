import math
import torch
from sentence_transformers import CrossEncoder

device = "cuda" if torch.cuda.is_available() else "cpu"
reranker = CrossEncoder("BAAI/bge-reranker-base", device=device)

def calculate_sigmoid(value: float) -> float:
    try:
        return 1 / (1 + math.exp(-value))
    except OverflowError:
        return 0.0 if value < 0 else 1.0

def retrieve_and_rerank(query: str, collection, top_k_initial: int = 10, top_k_final: int = 3, threshold: float = 0.70, metadata_filter: dict = None) -> list[str]:
    if not collection:
        return []

    query_kwargs = {
        "query_texts": [query],
        "n_results": top_k_initial
    }
    
    if metadata_filter:
        query_kwargs["where"] = metadata_filter

    results = collection.query(**query_kwargs)
    
    if not results.get('documents') or not results['documents'][0]:
        return []
        
    documents = results['documents'][0]
    metadatas = results.get('metadatas', [[{}] * len(documents)])[0]
    
    pairs = [[query, doc] for doc in documents]
    
    raw_scores = reranker.predict(pairs)
    normalized_scores = [calculate_sigmoid(float(score)) for score in raw_scores]
    
    scored_docs = list(zip(normalized_scores, documents, metadatas))
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    if scored_docs and scored_docs[0][0] < threshold:
        return []
        
    top_docs = [f"[Kaynak: {meta.get('source', 'Bilinmeyen Kaynak')}] {doc}" for score, doc, meta in scored_docs[:top_k_final] if score >= threshold]
    
    return top_docs