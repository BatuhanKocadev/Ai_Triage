"""ChromaDB koleksiyonu yerine geçen bellek içi sahte servis.

Gerçek `triage_documents` koleksiyonu her hasta sorgusunun tarandığı yerdir;
testlerin oraya yazması üretim davranışını bozar. Bu sınıf yalnızca doküman
uçlarının kullandığı yöntemleri taklit eder.
"""


class SahteKoleksiyon:
    """Kayıtları bellekte tutan, ChromaDB koleksiyon arayüzünün küçük bir taklidi."""

    def __init__(self):
        # id -> {"document": metin, "metadata": üstveri}
        self._kayitlar = {}

    def upsert(self, documents, metadatas, ids):
        """Verilen id'leri yazar; var olanın üzerine yazar, diğerlerine dokunmaz."""
        for belge, ustveri, kimlik in zip(documents, metadatas, ids):
            self._kayitlar[kimlik] = {"document": belge, "metadata": dict(ustveri)}

    def get(self, where=None, include=None):
        """Kayıtları döndürür; `where` verilirse eşitlik filtresi uygular."""
        kimlikler, ustveriler, belgeler = [], [], []
        for kimlik, kayit in self._kayitlar.items():
            if where and not self._eslesiyor(kayit["metadata"], where):
                continue
            kimlikler.append(kimlik)
            ustveriler.append(kayit["metadata"])
            belgeler.append(kayit["document"])
        return {"ids": kimlikler, "metadatas": ustveriler, "documents": belgeler}

    def delete(self, ids=None, where=None):
        """Verilen id'leri ya da `where` ile eşleşen kayıtları siler."""
        if ids is not None:
            for kimlik in ids:
                self._kayitlar.pop(kimlik, None)
            return
        if where is not None:
            silinecek = [
                kimlik
                for kimlik, kayit in self._kayitlar.items()
                if self._eslesiyor(kayit["metadata"], where)
            ]
            for kimlik in silinecek:
                self._kayitlar.pop(kimlik, None)

    def sayac(self):
        """Testlerin toplam kayıt sayısını okuması için."""
        return len(self._kayitlar)

    @staticmethod
    def _eslesiyor(ustveri, where):
        """Basit eşitlik filtresi — üretimde yalnızca {"source": ad} kullanılıyor."""
        return all(ustveri.get(anahtar) == deger for anahtar, deger in where.items())
