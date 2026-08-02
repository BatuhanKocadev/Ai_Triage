"""ChromaDB koleksiyonu ve cross-encoder yerine geçen sahteler."""


class SahteKoleksiyon:
    """collection.query(...) çağrısına sabit doküman listesi döndürür."""

    def __init__(self, dokumanlar: list[str], kaynaklar: list[str] | None = None):
        self.dokumanlar = dokumanlar
        self.kaynaklar = kaynaklar or ["protokol.pdf"] * len(dokumanlar)
        self.son_cagri = None  # testler filtrenin geçtiğini buradan doğrular

    def query(self, **kwargs):
        self.son_cagri = kwargs
        return {
            "documents": [self.dokumanlar],
            "metadatas": [[{"source": k} for k in self.kaynaklar]],
        }


class _SahteReranker:
    """predict() çağrısına önceden belirlenmiş ham skorları döndürür."""

    def __init__(self, skorlar: list[float]):
        self.skorlar = skorlar

    def predict(self, pairs):
        return self.skorlar[:len(pairs)]


def sahte_reranker_uret(skorlar: list[float]):
    """get_reranker yerine geçecek, sabit skor döndüren fabrika üretir."""
    def _sahte():
        return _SahteReranker(skorlar)
    return _sahte
