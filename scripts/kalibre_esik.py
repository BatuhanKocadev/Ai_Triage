"""Rerank eşiğini ölçerek kalibre eder."""

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.config.config import settings
from app.services.chroma_service import get_collection
from app.services.rag_service import get_reranker

# Bilgi tabanındaki 15 protokolün her biri için en az bir sorgu; geçmesi beklenir.
# Sorgular bilerek HASTA AĞZINDAN yazılmıştır, protokol cümlesi kopyalanmamıştır:
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
    # inme — eski sorgu ("yüzünün bir tarafı düştü, kolunu kaldıramıyor,
    # konuşması bozuldu") inme.txt'ye eklenen FAST cümlesinin üç öbeğini de
    "Dedem yarım saat önce birden yere yığıldı, sağ tarafını hiç oynatamıyor ve ağzından çıkanlar anlaşılmıyor.",
    "Dedem yarim saat once birden yere yigildi, sag tarafini hic oynatamiyor ve agzindan cikanlar anlasilmiyor.",
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
    # yanık — birinci sorgu: protokolün kelimelerini kullanmadan, hasta ağzından.
    # ESKİ sorgu ("Kaynar su elimin üstüne döküldü, hemen su toplamaya başladı.")
    "Çaydanlığı devirdim, kolum fena halde haşlandı ve derim kabardı.",
    # yanık — İKİNCİ, TUTULAN sorgu (tasarım K5). Bu satır yanik.txt'ye
    # dokunulmadan ÖNCE yazıldı ve belge düzenlenirken buna BAKILMADI. Amacı,
    "Ütü elimin üstüne düştü, deri soyuldu ve çok acıyor.",
    # yanık — ÜÇÜNCÜ sorgu: projeyi yürüten kişi tarafından, yanik.txt'nin yeni
    # metnini GÖRMEDEN yazıldı (11 Ağustos 2026). İlk iki sorgu aynı kişi tarafından
    "mangalda kolumu ateşe tuttum, kolum bembeyaz oldu hissetmiyorum",
]

# Elenmesi beklenen sorgular. İKİ SINIF var ve ikincisi asıl zorlayıcı olan:
# "hava güzel" gibi tamamen alakasız metinler kolayca elenir, ama TIBBİ olup
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


def en_iyi_eslesme(sorgu: str, n_results: int | None = None) -> tuple[float, str | None]:
    """Sorgu için en yüksek rerank skorunu ve kazanan kaynak dosya adını döndürür."""
    if n_results is None:
        n_results = settings.top_k_initial
    sonuc = get_collection().query(query_texts=[sorgu], n_results=n_results)
    dokumanlar = sonuc["documents"][0]
    if not dokumanlar:
        return 0.0, None
    metadatas = (sonuc.get("metadatas") or [[]])[0]
    skorlar = get_reranker().predict([[sorgu, d] for d in dokumanlar])
    en_iyi_i = max(range(len(skorlar)), key=lambda i: float(skorlar[i]))
    kaynak = None
    if en_iyi_i < len(metadatas) and isinstance(metadatas[en_iyi_i], dict):
        kaynak = metadatas[en_iyi_i].get("source")
    return float(skorlar[en_iyi_i]), kaynak


def en_yuksek_skor(sorgu: str) -> float:
    """Geriye uyum: yalnızca skoru döndürür (eski çağrı noktaları için)."""
    skor, _ = en_iyi_eslesme(sorgu)
    return skor


def main() -> None:
    if get_collection().count() == 0:
        print("Bilgi tabanı boş. Önce /document/upload ile doküman yükleyin.")
        sys.exit(1)

    print(f"Model: {settings.reranker_model}")
    print(f"Mevcut eşik: {settings.rerank_threshold}")
    print(f"top_k_initial: {settings.top_k_initial}")
    print(f"Bilgi tabanındaki parça sayısı: {get_collection().count()}\n")

    print("=== İLGİLİ sorgular (geçmeli) ===")
    ilgili_skorlar = []
    for sorgu in ILGILI:
        skor, kaynak = en_iyi_eslesme(sorgu)
        ilgili_skorlar.append(skor)
        durum = "GEÇER" if skor >= settings.rerank_threshold else "elenir"
        kaynak_yazi = kaynak or "?"
        print(f"  [{durum}] {skor:.4f}  kaynak={kaynak_yazi}  {sorgu[:50]}")

    print("\n=== ALAKASIZ sorgular (elenmeli) ===")
    alakasiz_skorlar = []
    for sorgu in ALAKASIZ:
        skor, kaynak = en_iyi_eslesme(sorgu)
        alakasiz_skorlar.append(skor)
        durum = "GEÇER" if skor >= settings.rerank_threshold else "elenir"
        kaynak_yazi = kaynak or "?"
        print(f"  [{durum}] {skor:.4f}  kaynak={kaynak_yazi}  {sorgu[:50]}")

    print("\n=== ÖZET ===")
    print(f"  ilgili   -> min={min(ilgili_skorlar):.4f}  max={max(ilgili_skorlar):.4f}")
    print(f"  alakasız -> min={min(alakasiz_skorlar):.4f}  max={max(alakasiz_skorlar):.4f}")

    print("\n=== EŞİK TARAMASI ===")
    # Adaylar ölçülen skorlardan türetiliyor, sabit bir aralıktan değil. Sabit
    # aralık bir kez çok pahalıya mal oldu: reranker'daki çift sigmoid
    tum_skorlar = sorted(set(ilgili_skorlar + alakasiz_skorlar))
    adaylar = []
    for onceki, sonraki in zip(tum_skorlar, tum_skorlar[1:]):
        adaylar.append((onceki + sonraki) / 2)  # iki gözlem arasındaki orta nokta
    adaylar.append(max(tum_skorlar) + 1e-6)

    en_yuksek_alakasiz = max(alakasiz_skorlar)

    print("  eşik       geçen ilgili   geçen alakasız   güvenlik payı")
    en_iyi = None
    for esik in adaylar:
        dogru = sum(1 for s in ilgili_skorlar if s >= esik)
        yanlis = sum(1 for s in alakasiz_skorlar if s >= esik)
        if yanlis == 0 and (en_iyi is None or dogru > en_iyi[1]):
            # Yanlış kabul yokken en çok ilgiliyi geçiren aday.
            en_iyi = (esik, dogru, esik - en_yuksek_alakasiz)

    # Eğri, karar verenin dengeyi görebilmesi için birkaç noktada basılıyor.
    for esik in adaylar[:: max(1, len(adaylar) // 12)]:
        dogru = sum(1 for s in ilgili_skorlar if s >= esik)
        yanlis = sum(1 for s in alakasiz_skorlar if s >= esik)
        pay = f"{esik - en_yuksek_alakasiz:+.4f}" if yanlis == 0 else "YANLIS KABUL"
        print(f"  {esik:.4f}     {dogru:>2}/{len(ILGILI)}           {yanlis:>2}/{len(ALAKASIZ)}      {pay}")

    if en_iyi:
        esik, dogru, pay = en_iyi
        print(f"\n  ÖNERİ: rerank_threshold = {esik:.4f}")
        print(f"         ({dogru}/{len(ILGILI)} ilgili geçer, 0 alakasız geçer)")
        print(f"         güvenlik payı: en yüksek alakasız skorun {pay:+.4f} üstünde")
        if pay < 0.001:
            print("         UYARI: pay çok ince — alakasız bir sorgu kolayca geçebilir.")
        elenen = [s for s in ilgili_skorlar if s < esik]
        if elenen:
            print(f"         elenen {len(elenen)} ilgili sorgunun skorları: "
                  + ", ".join(f"{s:.4f}" for s in sorted(elenen)))
    else:
        print("\n  Yanlış kabul olmadan ayıran eşik bulunamadı; reranker modelini gözden geçirin.")


if __name__ == "__main__":
    main()
