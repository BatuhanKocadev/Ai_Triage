"""Bellek içi kayan pencere hız sınırlayıcı ve onu uçlara bağlayan bağımlılık."""

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
        """Kota dolmuş mu diye SALT BAKAR; hiçbir şey kaydetmez."""
        simdi = self._saat()
        # get(): olmayan anahtar için kayıt AÇMIYOR — salt kontrol sözlüğü
        # şişirmemeli, yoksa her denenen kullanıcı adı kalıcı iz bırakırdı.
        kuyruk = self._kayitlar.get(anahtar)
        if not kuyruk:
            return True
        # Bayat kayıtlar burada da düşürülmeli: kaydetme yolu artık yalnızca
        # başarısızlıkta çalıştığı için kuyruğu kaydıracak başka çağrı yok ve
        while kuyruk and simdi - kuyruk[0] >= self.pencere_sn:
            kuyruk.popleft()
        # Süpürme bu yolda da tetikleniyor: kontrol yolu bir anahtarın kuyruğunu
        # boşaltabiliyor ve temizlik yalnızca kaydetme yolunda kalsaydı o boş
        if len(self._kayitlar) > self.temizlik_esigi:
            self._bayat_anahtarlari_temizle(simdi)
        return len(kuyruk) < self.limit

    def istegi_kaydet(self, anahtar: str) -> None:
        """Bir denemeyi kotaya SALT YAZAR; kabul edilir mi diye bakmaz."""
        simdi = self._saat()
        kuyruk = self._kayitlar.setdefault(anahtar, deque())
        # Kuyruk zaman sırasında olduğu için pencereden çıkanları baştan atmak yeter.
        while kuyruk and simdi - kuyruk[0] >= self.pencere_sn:
            kuyruk.popleft()
        kuyruk.append(simdi)
        # Bayat anahtar temizliği bu yolda da yapılmalı: giriş ucu artık
        # `izin_ver()` çağırmıyor, temizlik yalnızca orada kalsaydı sözlük
        if len(self._kayitlar) > self.temizlik_esigi:
            self._bayat_anahtarlari_temizle(simdi)

    def _bayat_anahtarlari_temizle(self, simdi: float) -> None:
        """Kuyruğu boş ya da son kaydı pencere dışında kalan anahtarları siler."""
        # Kuyruk zaman sırasıyla dolduğu için en yeni kayıt (kuyruk[-1]) bile
        # pencere dışındaysa tüm kuyruk bayattır; aktif anahtar asla silinmez
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
# Giriş ucunun ikinci katmanı: kullanıcı adı kovaları dolmasa bile (her istekte
# farklı ad denenirse dolmaz) IP başına toplam hacmi bağlar.
giris_ip_sinirlayici = HizSinirlayici(
    limit=settings.rate_limit_giris_ip, pencere_sn=settings.rate_limit_pencere_sn
)


def hiz_siniri(sinirlayici: HizSinirlayici):
    """Verilen sınırlayıcıyı uygulayan bir FastAPI bağımlılığı üretir."""

    async def _kontrol(request: Request):
        # İstemci IP'si yoksa (test/proxy) tek bir kovada toplanıyor.
        anahtar = request.client.host if request.client else "bilinmeyen"
        if not sinirlayici.izin_ver(anahtar):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Çok fazla istek. Lütfen biraz bekleyin.",
                # Pencere sabit; istemci ne kadar bekleyeceğini bilsin.
                headers={"Retry-After": str(sinirlayici.pencere_sn)},
            )

    return _kontrol
