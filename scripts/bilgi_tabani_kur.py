"""Bilgi tabanını sıfırdan kurar: koleksiyonu düşürüp derlemeyi yeniden yükler.

Gömme modeli değiştiğinde ZORUNLUDUR: eski vektörler farklı bir modelle üretildiği
için yeni sorgu vektörleriyle karşılaştırılamaz. Derleme değiştiğinde de temiz bir
başlangıç için kullanılır.

Backend'in ayakta olması gerekir; yükleme gerçek /document/upload ucundan geçer.

İki ayrı port var ve karıştırılması bu script'i sessizce yanlış işe sokuyor:
backend 8000'de, ChromaDB genelde 8001'de. `.env` yoksa `config.py` varsayılanı
`chroma_port=8000` olduğu için script backend'in portuna Chroma diye bağlanmaya
çalışır; bu yüzden aşağıda bağlantı açıkça heartbeat ile kanıtlanıyor.

Kullanım (proje kökünden):
    CHROMA_PORT=8001 .venv\\Scripts\\python.exe -m scripts.bilgi_tabani_kur
"""

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import chromadb
import requests
from chromadb.errors import NotFoundError

from app.config.config import settings
from app.services.auth_service import create_access_token

BACKEND = "http://localhost:8000"
DERLEME = Path(__file__).resolve().parent.parent / "ornek_dokumanlar" / "protokoller"
KATEGORI = "protokol"
KOLEKSIYON = "triage_documents"

# Yeni çok dilli gömmenin (BAAI/bge-m3) imzası; koleksiyon bu değerleri
# göstermiyorsa vektörler yanlış modelle üretilmiş demektir.
BEKLENEN_GOMME_ADI = "sentence_transformer"
BEKLENEN_BOYUT = 1024
# ChromaDB'nin eski varsayılanı all-MiniLM-L6-v2: adı "default", boyutu 384.
ESKI_GOMME_ADI = "default"
ESKI_BOYUT = 384


def yonetici_basligi():
    """Admin jetonunu uygulamanın kendi imzalama fonksiyonuyla üretir."""
    return {"Authorization": f"Bearer {create_access_token({'sub': 'admin', 'role': 'admin'})}"}


def backend_saglik_kontrolu():
    """Koleksiyonu düşürmeden önce backend'in ayakta olduğunu doğrular.

    Backend kapalıyken düşürme yapılırsa bilgi tabanı boş kalır ve geri dönüş
    olmaz; bu yüzden ulaşılamıyorsa ya da 200 dönmüyorsa koleksiyona hiç
    dokunmadan anlaşılır bir mesajla çıkılır.
    """
    try:
        yanit = requests.get(f"{BACKEND}/health/", timeout=5)
    except requests.exceptions.RequestException as baglanti_hatasi:
        print(f"Backend'e ulasilamiyor ({BACKEND}/health/): {type(baglanti_hatasi).__name__}")
        sys.exit(1)
    if yanit.status_code != 200:
        print(f"Backend saglik ucu {yanit.status_code} dondu, kurulum durduruldu.")
        sys.exit(1)


def kimlik_on_ucusu(baslik: dict) -> None:
    """Koleksiyonu düşürmeden önce jetonun backend tarafından kabul edildiğini doğrular.

    Tek çağrıda iki şeyi birden sınar: script'in imzaladığı JWT anahtarı
    backend'inkiyle aynı mı ve `admin` satırı veritabanında var mı. Bu kontrol
    olmadan koleksiyon düşürülüp ardından bütün yüklemeler 401 alıyor ve bilgi
    tabanı boş kalıyordu. `/document/liste` bilerek kullanılmıyor: o uç
    `get_collection()` çağırıp koleksiyonu boşuna açar.
    """
    try:
        yanit = requests.get(f"{BACKEND}/auth/me", headers=baslik, timeout=10)
    except requests.exceptions.RequestException as istek_hatasi:
        print(f"Kimlik on ucusu basarisiz ({BACKEND}/auth/me): {type(istek_hatasi).__name__}")
        print("Koleksiyona DOKUNULMADI.")
        sys.exit(1)
    if yanit.status_code != 200:
        print(f"Kimlik on ucusu {yanit.status_code} dondu: {yanit.text[:200]}")
        print(
            "Jetonu imzalayan JWT anahtari backend'inkiyle uyusmuyor ya da 'admin' "
            "kullanicisi veritabaninda yok."
        )
        print("Koleksiyona DOKUNULMADI.")
        sys.exit(1)


def koleksiyonu_dusur():
    """Eski vektörleri tamamen siler; yeni model farklı bir anlam uzayı kullanıyor.

    Kurduğu Chroma istemcisini geri döndürür: yükleme sonrası doğrulama aynı
    bağlantıyı kullanır.
    """
    adres = f"{settings.chroma_host}:{settings.chroma_port}"

    # Silmeden ÖNCE bağlantı kanıtlanıyor. HttpClient yanlış porta kurulduğunda
    # ham bir ValueError ile ölüyordu ve hangi adresin denendiği görünmüyordu.
    try:
        istemci = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        istemci.heartbeat()
    except Exception as baglanti_hatasi:
        print(
            f"ChromaDB'ye baglanilamadi (denenen adres: {adres}): "
            f"{type(baglanti_hatasi).__name__}: {baglanti_hatasi}"
        )
        print(
            "Canli ChromaDB genelde 8001'de calisir; 8000 backend'in portudur. "
            "CHROMA_HOST / CHROMA_PORT degerlerini kontrol edin."
        )
        print("Koleksiyona DOKUNULMADI.")
        sys.exit(1)

    print(f"ChromaDB baglantisi dogrulandi: {adres}")

    try:
        istemci.delete_collection(KOLEKSIYON)
        print(f"koleksiyon dusuruldu: {KOLEKSIYON}")
    except NotFoundError:
        # Yalnizca "koleksiyon zaten yoktu" durumu yutuluyor; baglanti veya yetki
        # hatasi yutulursa script kirik bir baglantiyla calismaya devam ederdi.
        print(f"koleksiyon zaten yoktu: {KOLEKSIYON}")

    return istemci


def gomme_yapilandirmasini_dogrula(istemci) -> None:
    """Yükleme bittikten sonra koleksiyonu geri okuyup gömmenin doğru modelle yapıldığını kanıtlar.

    `/health/` ucunun 200 dönmesi hangi KODUN koştuğunu kanıtlamaz: backend eski
    kodla ayaktaysa yükleme başarıyla tamamlanır, script "0 hata" basar ve bilgi
    tabanı sessizce eski İngilizce modelle dolar. Tek gerçek kanıt, koleksiyona
    yazılmış vektörlerin kendisidir.
    """
    try:
        # embedding_function=None: yalnizca yapilandirma okunacak, 2 GB'lik model
        # bu surecte bosuna yuklenmesin (ve kayitli EF ile catisma dogmasin).
        koleksiyon = istemci.get_collection(KOLEKSIYON, embedding_function=None)
    except Exception as okuma_hatasi:
        print(
            f"\nDOGRULAMA BASARISIZ: koleksiyon geri okunamadi: "
            f"{type(okuma_hatasi).__name__}: {okuma_hatasi}"
        )
        sys.exit(1)

    gomme_ayari = koleksiyon.configuration_json.get("embedding_function") or {}
    gomme_adi = gomme_ayari.get("name")

    # Boyut kayitli bir vektorden okunuyor; yapilandirma dogru gorunse bile asil
    # kanit yazilmis vektorun uzunlugudur.
    kayit = koleksiyon.get(limit=1, include=["embeddings"])
    vektorler = kayit.get("embeddings")
    boyut = len(vektorler[0]) if vektorler is not None and len(vektorler) > 0 else 0

    print(f"\nDogrulama: gomme fonksiyonu = {gomme_adi}, vektor boyutu = {boyut}")

    if gomme_adi == BEKLENEN_GOMME_ADI and boyut == BEKLENEN_BOYUT:
        return

    print("DOGRULAMA BASARISIZ: koleksiyon beklenen gomme yapilandirmasiyla dolmamis.")
    print(f"  bulunan : {gomme_adi} / {boyut} boyut")
    print(f"  beklenen: {BEKLENEN_GOMME_ADI} / {BEKLENEN_BOYUT} boyut ({settings.embedding_model})")
    if gomme_adi == ESKI_GOMME_ADI or boyut == ESKI_BOYUT:
        print(
            "  Bu imza ESKI INGILIZCE modelin (all-MiniLM-L6-v2) imzasidir: yukleme "
            "eski kodla kosan bir backend uzerinden yapilmis."
        )
        print(
            "  Backend'i guncel kodla YENIDEN BASLATIP bu scripti tekrar calistirin; "
            "/health/ 200 donmesi kodun guncel oldugunu kanitlamaz."
        )
    sys.exit(1)


def main() -> None:
    dosyalar = [p for p in sorted(DERLEME.glob("*.txt")) if not p.name.startswith("_")]
    if not dosyalar:
        print(f"Derleme bos: {DERLEME}")
        sys.exit(1)

    print(f"Gomme modeli: {settings.embedding_model}")
    print(f"Derleme      : {len(dosyalar)} dosya\n")

    backend_saglik_kontrolu()  # Once backend ayakta mi bak; degilse koleksiyona hic dokunma.
    baslik = yonetici_basligi()
    kimlik_on_ucusu(baslik)  # Jeton kabul edilmiyorsa yukleme zaten bosa gider; simdi ogren.
    istemci = koleksiyonu_dusur()

    toplam = 0
    hata = 0
    for yol in dosyalar:
        with yol.open("rb") as f:
            try:
                yanit = requests.post(
                    f"{BACKEND}/document/upload",
                    data={"category": KATEGORI},
                    files={"file": (yol.name, f, "text/plain")},
                    headers=baslik,
                    timeout=300,
                )
            except requests.exceptions.RequestException as istek_hatasi:
                # Tek dosyanin baglanti hatasi butun yuklemeyi cokertmesin; kaydedip devam et.
                hata += 1
                print(f"  HATA {yol.name:<30} istek basarisiz: {type(istek_hatasi).__name__}")
                continue
        if yanit.status_code == 201:
            n = yanit.json()["total_chunks"]
            toplam += n
            print(f"  OK   {yol.name:<30} {n:>3} chunk")
        else:
            hata += 1
            print(f"  HATA {yol.name:<30} {yanit.status_code} {yanit.text[:120]}")

    print(f"\nToplam: {len(dosyalar) - hata} dosya, {toplam} chunk, {hata} hata")
    if hata:
        sys.exit(1)

    gomme_yapilandirmasini_dogrula(istemci)

    # Chroma islemleri id-anahtarli: script koleksiyonu backend'in altindan cekti,
    # backend surecindeki tekil hala eski koleksiyonun id'sini tutuyor olabilir.
    print("\n" + "=" * 78)
    print("UYARI: BILGI TABANI YENIDEN KURULDU.")
    print("CALISAN BACKEND'IN KOLEKSIYON TEKILI ARTIK BAYAT.")
    print("BACKEND YENIDEN BASLATILMALIDIR; AKSI HALDE SORGULAR SILINMIS KOLEKSIYONUN")
    print("ID'SINE GIDER VE HATA VERIR YA DA ESKI VEKTORLERI OKUR.")
    print("=" * 78)


if __name__ == "__main__":
    main()
