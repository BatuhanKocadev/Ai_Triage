"""Bellek içi kayan pencere hız sınırlayıcı ve onu uçlara bağlayan bağımlılık.

Kütüphane yerine elle yazıldı (tasarım K1): yeni bağımlılık requirements ve Docker
imajına yayılırdı, buna karşılık sayaç kırk satır. Asıl belirleyici test izolasyonu
oldu — burada `sifirla()` bir metot, kütüphanede iç depolamaya elle müdahale.

Sayaçlar süreç belleğinde yaşıyor. Tek uvicorn süreci çalıştığı için bu doğru
çözüm; çok süreçli bir dağıtımda paylaşılan bir depo (Redis vb.) gerekir.
"""

import time
from collections import deque

from fastapi import HTTPException, Request, status

from app.config.config import settings


class HizSinirlayici:
    """Anahtar başına, kayan pencere içinde istek sayar."""

    def __init__(
        self,
        limit: int,
        pencere_sn: int,
        saat=time.monotonic,
        temizlik_esigi: int = 10_000,
    ):
        self.limit = limit
        self.pencere_sn = pencere_sn
        # Saat enjekte edilebilir: testler gerçek zamana bağlı kalmasın.
        self._saat = saat
        # Sözlük bu boyutu aşınca bayat anahtarlar taranıp silinir; teste küçük
        # bir değer verilebilsin diye parametreleştirildi.
        self.temizlik_esigi = temizlik_esigi
        # defaultdict yerine düz dict: defaultdict salt okuma erişiminde bile
        # boş bir kayıt yaratır, bu da temizlenmesi gereken sızıntıyı gizler.
        self._kayitlar: dict[str, deque] = {}

    def izin_ver(self, anahtar: str) -> bool:
        """İstek kabul edilebilir mi; kabul edilirse zaman damgasını kaydeder."""
        simdi = self._saat()
        # setdefault ile açıkça oluşturuluyor; defaultdict'in örtük davranışına
        # benzer ama yalnızca gerçek bir istek geldiğinde kayıt açılıyor.
        kuyruk = self._kayitlar.setdefault(anahtar, deque())
        # Kuyruk zaman sırasında olduğu için pencereden çıkanları baştan atmak yeter.
        while kuyruk and simdi - kuyruk[0] >= self.pencere_sn:
            kuyruk.popleft()
        if len(kuyruk) >= self.limit:
            return False
        kuyruk.append(simdi)
        # Sözlük eşiği aştığında bayat anahtarları temizle; her çağrıda taramak
        # O(n) maliyetli olurdu, eşik aşıldığında amortize maliyet kabul edilebilir.
        if len(self._kayitlar) > self.temizlik_esigi:
            self._bayat_anahtarlari_temizle(simdi)
        return True

    def izin_var_mi(self, anahtar: str) -> bool:
        """Kota dolmuş mu diye SALT BAKAR; hiçbir şey kaydetmez.

        `izin_ver()` bakmakla saymayı tek çağrıda birleştirdiği için "yalnızca
        başarısız denemeyi say" kuralı onunla ifade edilemiyor; giriş ucu bu
        yüzden önce buraya bakıp sonra ayrıca `istegi_kaydet()` çağırıyor.
        """
        simdi = self._saat()
        # get(): olmayan anahtar için kayıt AÇMIYOR — salt kontrol sözlüğü
        # şişirmemeli, yoksa her denenen kullanıcı adı kalıcı iz bırakırdı.
        kuyruk = self._kayitlar.get(anahtar)
        if not kuyruk:
            return True
        # Bayat kayıtlar burada da düşürülmeli: kaydetme yolu artık yalnızca
        # başarısızlıkta çalıştığı için kuyruğu kaydıracak başka çağrı yok ve
        # temizlenmezse kotasını dolduran kullanıcı bir daha hiç giremezdi.
        while kuyruk and simdi - kuyruk[0] >= self.pencere_sn:
            kuyruk.popleft()
        return len(kuyruk) < self.limit

    def istegi_kaydet(self, anahtar: str) -> None:
        """Bir denemeyi kotaya SALT YAZAR; kabul edilir mi diye bakmaz.

        Limit kontrolü çağırana ait (bkz. `izin_var_mi`); burada koşulsuz
        yazılıyor ki giriş ucu yalnızca başarısız denemeleri sayabilsin.
        """
        simdi = self._saat()
        kuyruk = self._kayitlar.setdefault(anahtar, deque())
        # Kuyruk zaman sırasında olduğu için pencereden çıkanları baştan atmak yeter.
        while kuyruk and simdi - kuyruk[0] >= self.pencere_sn:
            kuyruk.popleft()
        kuyruk.append(simdi)
        # Bayat anahtar temizliği bu yolda da yapılmalı: giriş ucu artık
        # `izin_ver()` çağırmıyor, temizlik yalnızca orada kalsaydı sözlük
        # denenen her kullanıcı adıyla sınırsız büyürdü.
        if len(self._kayitlar) > self.temizlik_esigi:
            self._bayat_anahtarlari_temizle(simdi)

    def _bayat_anahtarlari_temizle(self, simdi: float) -> None:
        """Kuyruğu boş ya da son kaydı pencere dışında kalan anahtarları siler."""
        # Kuyruk zaman sırasıyla dolduğu için en yeni kayıt (kuyruk[-1]) bile
        # pencere dışındaysa tüm kuyruk bayattır; aktif anahtar asla silinmez
        # çünkü kendi son kaydı biraz önce eklendi.
        bayat_anahtarlar = [
            anahtar
            for anahtar, kuyruk in self._kayitlar.items()
            if not kuyruk or simdi - kuyruk[-1] >= self.pencere_sn
        ]
        for anahtar in bayat_anahtarlar:
            del self._kayitlar[anahtar]

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
