"""RAG servisi: Chroma'dan aday getirme + cross-encoder ile yeniden sıralama."""

import math

import torch
from sentence_transformers import CrossEncoder

from app.config.config import settings
from app.utils.logger import logger

device = "cuda" if torch.cuda.is_available() else "cpu"

# Model tembel yükleniyor: import anında ~2 GB'lık ağırlık yüklemek hem uygulama
# açılışını hem de testleri gereksiz yere bloke ediyordu.
_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        logger.info(f"Reranker yükleniyor: {settings.reranker_model} ({device})")
        _reranker = CrossEncoder(settings.reranker_model, device=device)
    return _reranker


def calculate_sigmoid(value: float) -> float:
    try:
        return 1 / (1 + math.exp(-value))
    except OverflowError:
        return 0.0 if value < 0 else 1.0


def retrieve_and_rerank(
    query: str,
    collection,
    top_k_initial: int = 10,
    top_k_final: int = 3,
    threshold: float | None = None,
    metadata_filter: dict = None,
) -> list[str]:
    if not collection:
        return []

    # Eşik ayarlardan geliyor; reranker modeli değişince eşik de değişmeli.
    if threshold is None:
        threshold = settings.rerank_threshold

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

    raw_scores = get_reranker().predict(pairs)
    normalized_scores = [calculate_sigmoid(float(score)) for score in raw_scores]

    scored_docs = list(zip(normalized_scores, documents, metadatas))
    scored_docs.sort(key=lambda x: x[0], reverse=True)

    if scored_docs and scored_docs[0][0] < threshold:
        logger.info(
            f"Eşik altında kalındı (en yüksek skor {scored_docs[0][0]:.4f} < {threshold}); "
            "LLM analizi yapılmayacak."
        )
        return []

    top_docs = [
        f"[Kaynak: {meta.get('source', 'Bilinmeyen Kaynak')}] {doc}"
        for score, doc, meta in scored_docs[:top_k_final]
        if score >= threshold
    ]

    return top_docs
