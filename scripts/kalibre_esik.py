"""Rerank eşiğini ölçerek kalibre eder.

Kullanım (proje kökünden):
    .venv\\Scripts\\python.exe scripts/kalibre_esik.py

Reranker modeli veya doküman seti değiştiğinde yeniden çalıştırılmalıdır;
skor dağılımı modele göre değiştiği için eşik de değişir.

İlgili sorguların geçmesi, alakasız sorguların elenmesi beklenir. Çıktıdaki
"ONERI" satırındaki değer app/config/config.py içindeki rerank_threshold
(veya .env içindeki RERANK_THRESHOLD) alanına yazılır.
"""

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.config.config import settings
from app.services.chroma_service import triage_collection
from app.services.rag_service import get_reranker, calculate_sigmoid

# Bilgi tabanındaki protokollerle ilgili olan, geçmesi beklenen sorgular.
# Türkçe karakterli ve karaktersiz yazımlar bilerek birlikte tutuluyor:
# kullanıcılar sık sık karaktersiz yazıyor ve bu skorları belirgin düşürüyor.
ILGILI = [
    "Yarım saattir göğsümde baskı tarzında şiddetli ağrı var, sol koluma vuruyor.",
    "Yarim saattir gogsumde baski tarzinda siddetli agri var, sol koluma vuruyor.",
    "Göğsüm sıkışıyor, nefes almakta zorlanıyorum ve terliyorum.",
    "Gogsum sikisiyor, nefes almakta zorlaniyorum ve terliyorum.",
    "İki gündür sağ alt karnımda ağrı var, bugün ateşim çıktı ve bulantım oldu.",
    "Iki gundur sag alt karnimda agri var, bugun atesim cikti ve bulantim oldu.",
    "Karnımın sağ üst tarafında yemeklerden sonra artan ağrı hissediyorum.",
    "Göğüs ağrım var ve çenem uyuşuyor.",
]

# Tıbbi olmayan, elenmesi beklenen sorgular.
ALAKASIZ = [
    "Bugün hava çok güzel, parkta yürüyüş yapmayı düşünüyorum.",
    "Yarın akşam sinemaya gitmek için bilet almak istiyorum.",
    "Arabamın motorundan garip bir ses geliyor, tamirciye götürmeliyim.",
    "Bilgisayarımın klavyesi bozuldu, yeni bir tane almam lazım.",
    "Bugun hava cok guzel, parkta yuruyus yapmayi dusunuyorum.",
]


def en_yuksek_skor(sorgu: str) -> float:
    """Sorgu için bilgi tabanındaki en iyi eşleşmenin normalize skorunu döndürür."""
    sonuc = triage_collection.query(query_texts=[sorgu], n_results=10)
    dokumanlar = sonuc["documents"][0]
    if not dokumanlar:
        return 0.0
    ham_skorlar = get_reranker().predict([[sorgu, d] for d in dokumanlar])
    return max(calculate_sigmoid(float(s)) for s in ham_skorlar)


def main() -> None:
    if triage_collection.count() == 0:
        print("Bilgi tabanı boş. Önce /document/upload ile doküman yükleyin.")
        sys.exit(1)

    print(f"Model: {settings.reranker_model}")
    print(f"Mevcut eşik: {settings.rerank_threshold}")
    print(f"Bilgi tabanındaki parça sayısı: {triage_collection.count()}\n")

    print("=== İLGİLİ sorgular (geçmeli) ===")
    ilgili_skorlar = []
    for sorgu in ILGILI:
        skor = en_yuksek_skor(sorgu)
        ilgili_skorlar.append(skor)
        durum = "GEÇER" if skor >= settings.rerank_threshold else "elenir"
        print(f"  [{durum}] {skor:.4f}  {sorgu[:60]}")

    print("\n=== ALAKASIZ sorgular (elenmeli) ===")
    alakasiz_skorlar = []
    for sorgu in ALAKASIZ:
        skor = en_yuksek_skor(sorgu)
        alakasiz_skorlar.append(skor)
        durum = "GEÇER" if skor >= settings.rerank_threshold else "elenir"
        print(f"  [{durum}] {skor:.4f}  {sorgu[:60]}")

    print("\n=== ÖZET ===")
    print(f"  ilgili   -> min={min(ilgili_skorlar):.4f}  max={max(ilgili_skorlar):.4f}")
    print(f"  alakasız -> min={min(alakasiz_skorlar):.4f}  max={max(alakasiz_skorlar):.4f}")

    print("\n=== EŞİK TARAMASI ===")
    print("  eşik     geçen ilgili   geçen alakasız")
    en_iyi = None
    for adim in range(0, 41):
        esik = 0.500 + adim * 0.005
        dogru = sum(1 for s in ilgili_skorlar if s >= esik)
        yanlis = sum(1 for s in alakasiz_skorlar if s >= esik)
        if adim % 5 == 0:
            print(f"  {esik:.3f}    {dogru}/{len(ILGILI)}            {yanlis}/{len(ALAKASIZ)}")
        # Yanlış kabul yokken en çok ilgiliyi geçiren eşiği seç; eşitlikte
        # güvenlik payı için daha yüksek olanı tercih et.
        if yanlis == 0 and (en_iyi is None or dogru >= en_iyi[1]):
            en_iyi = (esik, dogru)

    if en_iyi:
        print(f"\n  ÖNERİ: rerank_threshold = {en_iyi[0]:.3f}")
        print(f"         ({en_iyi[1]}/{len(ILGILI)} ilgili geçer, 0 alakasız geçer)")
    else:
        print("\n  Yanlış kabul olmadan ayıran eşik bulunamadı; reranker modelini gözden geçirin.")


if __name__ == "__main__":
    main()
