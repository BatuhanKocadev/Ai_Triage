"""Bellek içi kayan pencere hız sınırlayıcı ve onu uçlara bağlayan bağımlılık.

Kütüphane yerine elle yazıldı (tasarım K1): yeni bağımlılık requirements ve Docker
imajına yayılırdı, buna karşılık sayaç kırk satır. Asıl belirleyici test izolasyonu
oldu — burada `sifirla()` bir metot, kütüphanede iç depolamaya elle müdahale.

Sayaçlar süreç belleğinde yaşıyor. Tek uvicorn süreci çalıştığı için bu doğru
çözüm; çok süreçli bir dağıtımda paylaşılan bir depo (Redis vb.) gerekir.
"""

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, status

from app.config.config import settings


class HizSinirlayici:
    """Anahtar başına, kayan pencere içinde istek sayar."""

    def __init__(self, limit: int, pencere_sn: int, saat=time.monotonic):
        self.limit = limit
        self.pencere_sn = pencere_sn
        # Saat enjekte edilebilir: testler gerçek zamana bağlı kalmasın.
        self._saat = saat
        self._kayitlar: dict[str, deque] = defaultdict(deque)

    def izin_ver(self, anahtar: str) -> bool:
        """İstek kabul edilebilir mi; kabul edilirse zaman damgasını kaydeder."""
        simdi = self._saat()
        kuyruk = self._kayitlar[anahtar]
        # Kuyruk zaman sırasında olduğu için pencereden çıkanları baştan atmak yeter.
        while kuyruk and simdi - kuyruk[0] >= self.pencere_sn:
            kuyruk.popleft()
        if len(kuyruk) >= self.limit:
            return False
        kuyruk.append(simdi)
        return True

    def sifirla(self) -> None:
        """Tüm sayaçları siler; testler arası izolasyon buna dayanıyor."""
        self._kayitlar.clear()


# Uygulama genelinde tek örnek: sayaçlar süreç belleğinde tutuluyor.
giris_sinirlayici = HizSinirlayici(
    limit=settings.rate_limit_giris, pencere_sn=settings.rate_limit_pencere_sn
)
genel_sinirlayici = HizSinirlayici(
    limit=settings.rate_limit_genel, pencere_sn=settings.rate_limit_pencere_sn
)


def hiz_siniri(sinirlayici: HizSinirlayici):
    """Verilen sınırlayıcıyı uygulayan bir FastAPI bağımlılığı üretir.

    Bağımlılık olarak yazıldı, middleware olarak değil (tasarım K2): yol haritası
    uç bazında farklı sınır istiyor ve hangi ucun korunduğu böylece kodda görünür.
    """

    async def _kontrol(request: Request):
        # İstemci IP'si yoksa (test/proxy) tek bir kovada toplanıyor.
        anahtar = request.client.host if request.client else "bilinmeyen"
        if not sinirlayici.izin_ver(anahtar):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Çok fazla istek. Lütfen biraz bekleyin.",
            )

    return _kontrol
