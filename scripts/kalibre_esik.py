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
from app.services.chroma_service import get_collection
from app.services.rag_service import get_reranker, calculate_sigmoid

# Bilgi tabanındaki 15 protokolün her biri için en az bir sorgu; geçmesi beklenir.
# Sorgular bilerek HASTA AĞZINDAN yazılmıştır, protokol cümlesi kopyalanmamıştır:
# protokolden cümle kopyalamak retrieval'ı birebir kelime eşleşmesine indirger ve
# ölçümü yapay olarak yükseltir (veri sızıntısı).
# Türkçe karakterli ve karaktersiz yazımlar birlikte tutuluyor: kullanıcılar sık
# sık karaktersiz yazıyor ve bu skorları belirgin düşürüyor.
ILGILI = [
    # göğüs ağrısı
    "Yarım saattir göğsümde baskı tarzında şiddetli ağrı var, sol koluma vuruyor.",
    "Yarim saattir gogsumde baski tarzinda siddetli agri var, sol koluma vuruyor.",
    # karın ağrısı
    "İki gündür sağ alt karnımda ağrı var, bugün ateşim çıktı ve bulantım oldu.",
    "Iki gundur sag alt karnimda agri var, bugun atesim cikti ve bulantim oldu.",
    # nefes darlığı
    "Nefes almakta zorlanıyorum, dudaklarım morardı ve hırıltılı soluyorum.",
    # bilinç değişikliği
    "Babam aniden bayıldı, şimdi kendine geldi ama nerede olduğunu bilmiyor.",
    # baş ağrısı
    "Aniden çok şiddetli bir baş ağrısı başladı, hayatımın en kötü ağrısı.",
    # inme
    "Annemin yüzünün bir tarafı düştü, kolunu kaldıramıyor ve konuşması bozuldu.",
    "Annemin yuzunun bir tarafi dustu, kolunu kaldiramiyor ve konusmasi bozuldu.",
    # ateş ve sepsis
    "Üç gündür ateşim düşmüyor, titriyorum ve halsizlikten yataktan kalkamıyorum.",
    # anafilaksi
    "İlaç içtikten sonra vücudumu kaşıntılı kızarıklık kapladı, dudaklarım şişti.",
    # zehirlenme
    "Yanlışlıkla çamaşır suyu içtim, boğazım ve göğsüm yanıyor.",
    # GİS kanaması
    "Kahve telvesi gibi kustum ve dışkım simsiyah geliyor.",
    # travma
    "Motosikletten düştüm, bacağım şekilsiz duruyor ve üzerine basamıyorum.",
    # gebelik acilleri
    "Altı haftalık gebeyim, kasık ağrım ve kanamam başladı, başım dönüyor.",
    # pediatrik ateş
    "İki aylık bebeğimin ateşi 38.5 çıktı ve sürekli uyukluyor.",
    # psikiyatrik aciller
    "Kendime zarar vermeyi düşünüyorum, artık dayanamıyorum.",
    # yanık
    "Kaynar su elimin üstüne döküldü, hemen su toplamaya başladı.",
]

# Elenmesi beklenen sorgular. İKİ SINIF var ve ikincisi asıl zorlayıcı olan:
# "hava güzel" gibi tamamen alakasız metinler kolayca elenir, ama TIBBİ olup
# derlemede KARŞILIĞI OLMAYAN sorgular reranker'ı gerçekten sınar. Eşik yalnızca
# kolay sınıfa göre seçilirse, sistem bilmediği bir konuda da kendinden emin
# cevap üretir — eşik kapısının varlık sebebi tam olarak bunu önlemek.
ALAKASIZ = [
    # tıbbi olmayan
    "Bugün hava çok güzel, parkta yürüyüş yapmayı düşünüyorum.",
    "Yarın akşam sinemaya gitmek için bilet almak istiyorum.",
    "Arabamın motorundan garip bir ses geliyor, tamirciye götürmeliyim.",
    "Bilgisayarımın klavyesi bozuldu, yeni bir tane almam lazım.",
    "Bugun hava cok guzel, parkta yuruyus yapmayi dusunuyorum.",
    # tıbbi ama derlemede yok (acil triyaj kapsamı dışı)
    "Sırtımdaki egzama yıllardır geçmiyor, hangi nemlendirici kremi önerirsiniz?",
    "Diş etim şişti ve diş fırçalarken kanıyor, diş hekimine gitmeli miyim?",
    "Kulağımda sürekli çınlama var, aylardır artarak devam ediyor.",
    "Şeker hastasıyım, sabah insülin dozumu nasıl ayarlamam gerekir?",
    "Gözlük numaram değişti mi diye göz muayenesi olmak istiyorum.",
]


def en_yuksek_skor(sorgu: str) -> float:
    """Sorgu için bilgi tabanındaki en iyi eşleşmenin normalize skorunu döndürür."""
    sonuc = get_collection().query(query_texts=[sorgu], n_results=10)
    dokumanlar = sonuc["documents"][0]
    if not dokumanlar:
        return 0.0
    ham_skorlar = get_reranker().predict([[sorgu, d] for d in dokumanlar])
    return max(calculate_sigmoid(float(s)) for s in ham_skorlar)


def main() -> None:
    if get_collection().count() == 0:
        print("Bilgi tabanı boş. Önce /document/upload ile doküman yükleyin.")
        sys.exit(1)

    print(f"Model: {settings.reranker_model}")
    print(f"Mevcut eşik: {settings.rerank_threshold}")
    print(f"Bilgi tabanındaki parça sayısı: {get_collection().count()}\n")

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
    # Aralık bilerek geniş: doküman seti büyüdükçe skor dağılımı kayıyor ve dar
    # bir pencere en iyi eşiği aralığın dışında bırakabiliyor.
    for adim in range(0, 131):
        esik = 0.300 + adim * 0.005
        dogru = sum(1 for s in ilgili_skorlar if s >= esik)
        yanlis = sum(1 for s in alakasiz_skorlar if s >= esik)
        if adim % 10 == 0:
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
