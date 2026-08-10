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


# --- Kontrol ile kaydetmenin ayrıldığı yol (giriş ucu, 10 Ağustos 2026) ---
# /auth/login "yalnızca başarısız denemeyi say" diyebilmek için tek çağrıda
# hem bakıp hem sayan izin_ver()'i kullanamıyor; aşağıdaki testler o ayrımı dondurur.


def test_izin_var_mi_kota_tuketmez():
    # Salt kontrol metodu: bakmak saymaya dönüşürse başarılı girişler de kota
    # tüketir ve kararın bütün dayanağı çöker.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=2, pencere_sn=60, saat=saat)

    for _ in range(10):
        assert sinirlayici.izin_var_mi("ayse") is True

    # Kota hiç harcanmadığı için gerçek bir istek hâlâ kabul edilmeli.
    assert sinirlayici.izin_ver("ayse") is True


def test_basarili_giris_kota_tuketmez():
    # Kararın dayandığı özellik: yalnızca BAŞARISIZ deneme kaydediliyor, doğru
    # parolayla giren kullanıcı istediği kadar giriş yapabilmeli.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=3, pencere_sn=60, saat=saat)
    sinirlayici.istegi_kaydet("ayse")  # bir kez parolayı yanlış girdi

    # Sonrasında hep doğru parola: kaydetme yok, yalnızca kontrol var.
    for _ in range(20):
        assert sinirlayici.izin_var_mi("ayse") is True


def test_istegi_kaydet_kotayi_tuketir():
    # Kaydetme gerçekten sayıyor mu; boş bir metot olsaydı yukarıdaki iki test
    # de yeşil kalır ve sınır hiç uygulanmazdı.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=2, pencere_sn=60, saat=saat)

    sinirlayici.istegi_kaydet("ayse")
    sinirlayici.istegi_kaydet("ayse")

    assert sinirlayici.izin_var_mi("ayse") is False


def test_izin_var_mi_pencere_kayinca_yeniden_izin_verir():
    # Kritik: kontrol yolu bayat kayıtları düşürmezse kotasını dolduran kullanıcı
    # BİR DAHA HİÇ giremez — kaydetme yolu artık yalnızca başarısızlıkta
    # çalıştığı için kuyruğu temizleyecek başka çağrı kalmıyor.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=1, pencere_sn=60, saat=saat)
    sinirlayici.istegi_kaydet("ayse")
    assert sinirlayici.izin_var_mi("ayse") is False

    saat.ilerlet(61)

    assert sinirlayici.izin_var_mi("ayse") is True


def test_istegi_kaydet_bayat_kayitlari_kuyruktan_dusurur():
    # Kaydetme yolu kuyruğu kaydırmazsa aynı anahtarın kayıtları pencereler
    # boyunca birikir: kota `izin_var_mi` okurken doğru hesaplansa bile kuyruk
    # sınırsız büyür. Uzun süre parolasını yanlış giren tek bir kullanıcı yeter.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=5, pencere_sn=60, saat=saat)

    sinirlayici.istegi_kaydet("ayse")
    saat.ilerlet(61)
    sinirlayici.istegi_kaydet("ayse")

    # Eski kayıt pencere dışında kaldığı için düşmeli; yalnızca yenisi kalmalı.
    assert len(sinirlayici._kayitlar["ayse"]) == 1


def test_izin_var_mi_supurmeyi_tetikler():
    # Kontrol yolu bir anahtarın kuyruğunu BOŞALTABİLİYOR. Süpürme yalnızca
    # kaydetme yolunda kalsaydı, boşalan kayıt başka bir çağrı eşiği aşana kadar
    # sözlükte asılı kalırdı. Anahtar uzayı saldırganın seçtiği kullanıcı
    # adlarından oluştuğu için bu birikim doğrudan bellek baskısına dönüşür.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=5, pencere_sn=60, saat=saat, temizlik_esigi=2)
    sinirlayici.istegi_kaydet("ayse")
    sinirlayici.istegi_kaydet("veli")
    # Eşik burada aşılıyor ama üç kayıt da taze: hiçbiri silinmemeli.
    sinirlayici.istegi_kaydet("zeynep")
    assert len(sinirlayici._kayitlar) == 3

    saat.ilerlet(61)

    # SALT KONTROL: hiçbir şey kaydedilmiyor, yalnızca bakılıyor.
    sinirlayici.izin_var_mi("ayse")

    # Hepsi pencere dışında kaldığı için süpürme sözlüğü boşaltmalı.
    assert sinirlayici._kayitlar == {}


def test_kaydetme_yolunda_da_bayat_anahtarlar_temizlenir():
    # Giriş ucu artık izin_ver() değil istegi_kaydet() çağırıyor; temizlik bu
    # yola taşınmazsa sözlük denenen her kullanıcı adıyla sınırsız büyür.
    saat = SahteSaat()
    sinirlayici = HizSinirlayici(limit=5, pencere_sn=60, saat=saat, temizlik_esigi=2)

    sinirlayici.istegi_kaydet("ayse")
    sinirlayici.istegi_kaydet("veli")
    assert len(sinirlayici._kayitlar) == 2

    saat.ilerlet(61)

    # Eşik (2) 3. farklı anahtarla aşılınca temizlik tetiklenmeli.
    sinirlayici.istegi_kaydet("zeynep")

    assert list(sinirlayici._kayitlar.keys()) == ["zeynep"]
