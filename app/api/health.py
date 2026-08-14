"""Sistem durumu ucu.

Gün 27'ye kadar bu uç sabit bir dize döndürüyordu ve **hiçbir bağımlılık
hakkında hiçbir şey kanıtlamıyordu**. Gün 20'de bilgi tabanını boşaltmaya ramak
kalan tuzak tam buydu: `/health` 200 dönüyor diye kimlik doğrulamanın çalıştığı
varsayılmıştı. Artık üç bağımlılık ayrı ayrı yoklanıyor, çünkü bu ucun asıl
müşterisi kurulum yapan kişidir: tek istekle nerede takıldığını görmeli.

**HTTP durumu bilerek her zaman 200.** Uç "sistem sağlıklı mı"yı değil "API
süreci ayakta ve ne görüyor"u cevaplıyor; kurulum sırasında bağımlılıklar tanım
gereği bozuk olabilir ve teşhis için çağrılan ucun o yüzden 503 vermesi, aracı
tam ihtiyaç duyulduğu anda gürültüye çevirirdi. Karar veren alan `tumu_ok` —
çağıranlar durum koduna değil ona bakmalı.
"""
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.config.config import settings

router = APIRouter(
    prefix="/health",
    tags=["Sistem Durumu"]
)

# Yoklamalar kurulum sırasında çağrılıyor, yani karşı taraf çoğu zaman kapalı.
# Kısa timeout: teşhis aracı, teşhis ettiği arızada asılı kalmamalı.
YOKLAMA_TIMEOUT_SN = 3


class BagimlilikDurumu(BaseModel):
    """Tek bir bağımlılığın yoklama sonucu."""

    # Yoklama başarılı mı; `tumu_ok` bunların birleşimi.
    ok: bool
    # Başarısızlıkta sebep, başarıda "ok". Kurulumcunun okuyacağı tek metin bu.
    mesaj: str


class SistemDurumYaniti(BaseModel):
    """Ucun yanıt sözleşmesi; `durum`/`mesaj` geriye dönük uyumluluk için duruyor."""

    durum: str
    mesaj: str
    # Bağımlılık adı -> durumu. Kurulumda "nerede takıldım" sorusunun cevabı.
    bagimliliklar: dict[str, BagimlilikDurumu] = {}
    # Üç yoklamanın hepsi geçti mi. Çağıranlar HTTP durumuna değil buna baksın.
    tumu_ok: bool = False


def _postgres_yokla() -> tuple[bool, str]:
    """Postgres'e gerçekten bağlanıp bir sorgu koşar; motorun varlığı yetmez."""
    from sqlalchemy import text

    from app.db.database import engine

    with engine.connect() as baglanti:
        baglanti.execute(text("SELECT 1"))
    return True, "ok"


def _chromadb_yokla() -> tuple[bool, str]:
    """ChromaDB'ye heartbeat atar.

    `get_collection()` çağrılmıyor: o, gömme modelini (bge-m3) indirip belleğe
    alır ve bir sağlık yoklamasının yan etkisi olamayacak kadar pahalıdır.
    """
    # chromadb ağır bağımlılık zinciri çekiyor; modül düzeyine taşımayın
    # (`tests/birim/test_import_agirligi.py` bunu bağlıyor).
    import chromadb

    istemci = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    istemci.heartbeat()
    return True, "ok"


def _ollama_yokla() -> tuple[bool, str]:
    """Ollama ayakta mı ve yapılandırılmış model yüklü mü.

    Yalnızca "ayakta mı" sorulsaydı, model indirilmemişken uç yeşil görünür ve
    ilk analiz isteği 502 ile patlardı — kurulumcuyu yanlış yere bakmaya yollar.
    """
    import requests

    yanit = requests.get(
        f"{settings.ollama_base_url}/api/tags", timeout=YOKLAMA_TIMEOUT_SN
    )
    yanit.raise_for_status()
    modeller = {m.get("name") for m in yanit.json().get("models", [])}
    if settings.ollama_model not in modeller:
        return False, (
            f"{settings.ollama_model} yuklu degil "
            f"(bulunanlar: {sorted(m for m in modeller if m)}). "
            f"`ollama pull {settings.ollama_model}` calistirin."
        )
    return True, "ok"


def _guvenli_yokla(yoklama) -> BagimlilikDurumu:
    """Bir yoklamayı çalıştırır ve HER istisnayı durum bilgisine çevirir.

    İstisna sızarsa uç 500 verir; teşhis aracının teşhis ettiği arızada
    çökmesi, onu tam ihtiyaç duyulduğu anda kullanılamaz kılar.
    """
    try:
        ok, mesaj = yoklama()
    except Exception as exc:  # noqa: BLE001 - teşhis ucu, hiçbir arıza sızmamalı
        return BagimlilikDurumu(ok=False, mesaj=f"{type(exc).__name__}: {exc}")
    return BagimlilikDurumu(ok=ok, mesaj=mesaj)


@router.get("/", response_model=SistemDurumYaniti, status_code=status.HTTP_200_OK)
async def sistem_kontrol():
    """API'nin ayakta olduğunu ve üç bağımlılığı ayrı ayrı raporlar."""
    bagimliliklar = {
        "postgres": _guvenli_yokla(_postgres_yokla),
        "chromadb": _guvenli_yokla(_chromadb_yokla),
        "ollama": _guvenli_yokla(_ollama_yokla),
    }
    tumu_ok = all(d.ok for d in bagimliliklar.values())
    return SistemDurumYaniti(
        durum="basarili",
        mesaj="Tıbbi Triyaj API sorunsuz çalışıyor.",
        bagimliliklar=bagimliliklar,
        tumu_ok=tumu_ok,
    )
