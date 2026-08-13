"""RAG servisi: Chroma'dan aday getirme + cross-encoder ile yeniden sıralama."""

# Tip açıklamalarının çalışma zamanında değerlendirilmesini kapatır. ZORUNLU:
# aşağıdaki `_reranker: CrossEncoder | None` satırı, CrossEncoder modül düzeyinde
# import EDİLMEDİĞİ için aksi hâlde NameError verir (tasarım K3).
from __future__ import annotations

from typing import TYPE_CHECKING

from app.config.config import settings
from app.utils.logger import logger

if TYPE_CHECKING:  # yalnızca tip denetleyici için; çalışma zamanında import edilmez
    from sentence_transformers import CrossEncoder

# Model tembel yükleniyor: import anında ~2 GB'lık ağırlık yüklemek hem uygulama
# açılışını hem de testleri gereksiz yere bloke ediyordu.
_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        # torch ve sentence_transformers BURADA import ediliyor, modül düzeyinde
        # değil: modül düzeyinde import `app.main` açılışına ~25 saniye ekliyordu
        # (28,5 sn → 1,85 sn ölçüldü) ve CI ortamını ~1,2 GB büyütüyordu (torch
        # tek başına 497 MB). Tasarım K2.
        import torch
        from sentence_transformers import CrossEncoder

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Reranker yükleniyor: {settings.reranker_model} ({device})")
        # Aktivasyon açıkça veriliyor: predict()'in olasılık döndürmesi aksi hâlde
        # modelin config dosyasına bağlı kalır. Model ya da kütüphane varsayılanı
        # değişirse predict() sessizce ham logit döndürür ve her eşik anlamsızlaşır.
        _reranker = CrossEncoder(
            settings.reranker_model,
            device=device,
            activation_fn=torch.nn.Sigmoid(),
        )
    return _reranker


def retrieve_and_rerank(
    query: str,
    collection,
    top_k_initial: int | None = None,
    top_k_final: int = 3,
    threshold: float | None = None,
    metadata_filter: dict = None,
) -> list[str]:
    if not collection:
        return []

    # Eşik ayarlardan geliyor; reranker modeli değişince eşik de değişmeli.
    if threshold is None:
        threshold = settings.rerank_threshold
    # Aday sayısı da ayardan; None = settings.top_k_initial (Gün 24: 20).
    if top_k_initial is None:
        top_k_initial = settings.top_k_initial

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

    # predict() olasılık döndürüyor (aktivasyon yukarıda açıkça kuruldu);
    # ikinci bir dönüşüm uygulanmıyor.
    skorlar = [float(skor) for skor in get_reranker().predict(pairs)]

    scored_docs = list(zip(skorlar, documents, metadatas))
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
