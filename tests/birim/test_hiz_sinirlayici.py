"""Hız sınırlayıcının kendi davranışını dondurur.

Uç testleri sınırlayıcının KULLANILDIĞINI gösterir; bu testler DOĞRU ÇALIŞTIĞINI.
İkisi birbirinin yerine geçmez — Gün 17+18'de mutasyonla ölçülen kusur tam olarak
bu ayrımın atlanmasıydı.

Saat enjekte ediliyor: gerçek zamana bağlı test, pencere kaymasını ya hiç
sınayamaz ya da rastgele kırılır.
"""

from app.utils.hiz_sinirlayici import HizSinirlayici


class SahteSaat:
    """Testin elle ilerlettiği saat; time.monotonic yerine geçer."""

    def __init__(self):
        self.an = 0.0

    def __call__(self) -> float:
        return self.an

    def ilerlet(self, saniye: float) -> None:
        self.an += saniye


def test_limit_altinda_izin_verir():
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=3, pencere_sn=60, saat=saat)

    assert sinirlayici.izin_ver("1.2.3.4") is True
    assert sinirlayici.izin_ver("1.2.3.4") is True
    assert sinirlayici.izin_ver("1.2.3.4") is True


def test_limit_asilinca_reddeder():
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=2, pencere_sn=60, saat=saat)
    sinirlayici.izin_ver("1.2.3.4")
    sinirlayici.izin_ver("1.2.3.4")

    assert sinirlayici.izin_ver("1.2.3.4") is False


def test_pencere_kayinca_yeniden_izin_verir():
    # Sabit pencere değil KAYAN pencere: eski kayıtlar düşünce kota geri gelir.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=1, pencere_sn=60, saat=saat)
    assert sinirlayici.izin_ver("1.2.3.4") is True
    assert sinirlayici.izin_ver("1.2.3.4") is False

    saat.ilerlet(61)

    assert sinirlayici.izin_ver("1.2.3.4") is True


def test_anahtarlar_birbirini_etkilemez():
    # Bir IP'nin kotayı tüketmesi başka IP'yi engellememeli.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=1, pencere_sn=60, saat=saat)
    sinirlayici.izin_ver("1.2.3.4")

    assert sinirlayici.izin_ver("5.6.7.8") is True


def test_sifirla_sayaclari_temizler():
    # Testler arası izolasyonun dayanağı; bu metot olmadan bir testin tükettiği
    # kota diğerini 429'a düşürür.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=1, pencere_sn=60, saat=saat)
    sinirlayici.izin_ver("1.2.3.4")

    sinirlayici.sifirla()

    assert sinirlayici.izin_ver("1.2.3.4") is True


def test_bayat_anahtarlar_temizlenir():
    # Pencere dışına düşmüş anahtarların sözlükten silindiğini doğrular; aksi
    # halde her görülen IP kalıcı bir kayıt bırakır ve sözlük sınırsız büyür.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=5, pencere_sn=60, saat=saat, temizlik_esigi=2)

    sinirlayici.izin_ver("1.1.1.1")
    sinirlayici.izin_ver("2.2.2.2")
    assert len(sinirlayici._kayitlar) == 2

    saat.ilerlet(61)

    # Eşik (2) 3. farklı anahtarla aşılınca temizlik tetiklenmeli.
    sinirlayici.izin_ver("3.3.3.3")

    # Pencere dışına düşen eski anahtarlar silinmiş, yalnızca aktif anahtar kalmış olmalı.
    assert list(sinirlayici._kayitlar.keys()) == ["3.3.3.3"]
