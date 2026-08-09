"""Bilgi tabanını sıfırdan kurar: koleksiyonu düşürüp derlemeyi yeniden yükler.

Gömme modeli değiştiğinde ZORUNLUDUR: eski vektörler farklı bir modelle üretildiği
için yeni sorgu vektörleriyle karşılaştırılamaz. Derleme değiştiğinde de temiz bir
başlangıç için kullanılır.

Backend'in ayakta olması gerekir; yükleme gerçek /document/upload ucundan geçer.

Kullanım (proje kökünden):
    .venv\\Scripts\\python.exe scripts/bilgi_tabani_kur.py
"""

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import chromadb
import requests

from app.config.config import settings
from app.services.auth_service import create_access_token

BACKEND = "http://localhost:8000"
DERLEME = Path(__file__).resolve().parent.parent / "ornek_dokumanlar" / "protokoller"
KATEGORI = "protokol"
KOLEKSIYON = "triage_documents"


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


def koleksiyonu_dusur():
    """Eski vektörleri tamamen siler; yeni model farklı bir anlam uzayı kullanıyor."""
    istemci = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    try:
        istemci.delete_collection(KOLEKSIYON)
        print(f"koleksiyon dusuruldu: {KOLEKSIYON}")
    except Exception as hata:
        print(f"koleksiyon dusurulemedi (muhtemelen yoktu): {type(hata).__name__}")


def main() -> None:
    dosyalar = [p for p in sorted(DERLEME.glob("*.txt")) if not p.name.startswith("_")]
    if not dosyalar:
        print(f"Derleme bos: {DERLEME}")
        sys.exit(1)

    print(f"Gomme modeli: {settings.embedding_model}")
    print(f"Derleme      : {len(dosyalar)} dosya\n")

    backend_saglik_kontrolu()  # Once backend ayakta mi bak; degilse koleksiyona hic dokunma.
    koleksiyonu_dusur()

    baslik = yonetici_basligi()
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


if __name__ == "__main__":
    main()
