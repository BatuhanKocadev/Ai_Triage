# Bilgi tabanı derlemesi — nasıl doldurulur

Bu klasördeki dosyalar sistemin **bildiği her şey**. ChromaDB'ye yüklendikten sonra
`/ai/analiz` yalnızca buradaki metinlere dayanarak triyaj kodu ve tetkik öneriyor;
burada olmayan bir konuda sistem "Belirsiz" der ve triyaj bankosuna yönlendirir.

Şu an bilgi tabanında **4 chunk / 2 dosya** var. Bu, Gün 23'ün ölçümü için çok az —
`rerank_threshold` değeri (0.52) o iki dosya üzerinde ölçüldüğü için bugün
istatistiksel olarak anlamsız.

## Ne yapman gerekiyor

Aşağıdaki başlıkların her biri için bir `.txt` dosyası yaz. `_SABLON.txt`'yi kopyala,
adını değiştir, köşeli parantezleri kaynaktan okuduğunla doldur.

Her dosya **2–5 sayfa** olsun. Toplamda 80–150 chunk hedefliyoruz.

## Doldurma listesi

- [ ] `gogus_agrisi.txt` — göğüs ağrısı / akut koroner sendrom
- [ ] `karin_agrisi.txt` — karın ağrısı / akut batın
- [ ] `nefes_darligi.txt` — dispne / solunum sıkıntısı
- [ ] `bilinc_degisikligi.txt` — bilinç bulanıklığı / senkop
- [ ] `bas_agrisi.txt` — baş ağrısı
- [ ] `inme.txt` — inme / FAST değerlendirmesi
- [ ] `ates_sepsis.txt` — ateş / enfeksiyon / sepsis
- [ ] `anafilaksi.txt` — alerjik reaksiyon / anafilaksi
- [ ] `zehirlenme.txt` — zehirlenme / intoksikasyon
- [ ] `gis_kanamasi.txt` — gastrointestinal kanama
- [ ] `travma.txt` — travmaya genel yaklaşım
- [ ] `gebelik_acilleri.txt` — gebelikle ilgili aciller
- [ ] `pediatrik_ates.txt` — pediatrik ateş / febril konvülziyon
- [ ] `psikiyatrik_aciller.txt` — ajitasyon / intihar riski
- [ ] `yanik.txt` — yanık

Bu 15 başlık aynı zamanda **Gün 23'ün senaryo setinin sınırını** çiziyor: sistemin
bilmediği bir hastalığı sormak adil test değil. Listeden çıkardığın başlık, ölçüm
setinden de çıkar.

## Kaynaklar

Üçü de ücretsiz ve indirilebilir:

| Kaynak | Ne için |
|---|---|
| [Sağlık Bakanlığı Tebliği](https://hhdd.org.tr/wp-content/uploads/2022/01/Yatakli-Saglik-Tesislerinde-Acil-Servis-Hizmetlerinin-Uygulama-Usul-ve-Esaslari-Hakkinda-Teblig.pdf) | Kırmızı/sarı/yeşil tanımları, resmî dayanak (Ek-7) |
| [ATUDER — Acil Serviste Triaj](http://file.atuder.org.tr/_atuder.org/fileUpload/pkzssuhbfz1h.pdf) | Türkçe klinik yaklaşım |
| [ESI Handbook](https://media.emscimprovement.center/documents/Emergency_Severity_Index_Handbook.pdf) | Hangi vital bulgular "tehlike bölgesi" sayılır |

ESI beş seviyeli, bizim şema üç seviyeli. Seviyeleri birebir eşleme — ESI'yi
*muhakeme yapısı* için kullan (kaç kaynak gerekiyor, hangi vital eşikleri riskli),
seviye adı için değil.

Tebliğ'in güncel sürümünü doğrula; 2009'da yayımlandı ama değişiklik gördü.

## Dört kural

**1. İçeriği bir dil modeline yazdırma.** Kaynağı okuyup özetle. Bilgi tabanını
Claude'a veya qwen'e ürettirirsen, Gün 23'te modelin kendi ürettiği metni ne kadar
iyi geri getirdiğini ölçersin — bu doğruluk değil, yankıdır. Ayrıca projenin bütün
savunması `sources` alanının izlenebilir olması; kaynağı "model uydurdu" olan bir
öneri o iddiayı çürütür.

**2. Bölüm başlığında tablo adını tekrarla.** Chunk, belge bağlamını kaybeder.
`## Kırmızı Alan Kriterleri` değil, `Göğüs ağrısı — Kırmızı Alan Kriterleri` yaz.
Aksi hâlde getirilen parça "neyin kriteri" belirsiz kalır.

**3. Bölümleri 600–900 karakter aralığında tut.** Bölme `chunk_size=1000,
overlap=200` ile yapılıyor; bu aralıkta kalan bölüm tek chunk'a sığar ve retrieval
temiz olur. Uzun tabloyu madde listesine çevir.

**4. Dosya adı doktorun gördüğü atıftır.** `sources` alanına dosya adı gidiyor ve
doktor panelinde "Kaynak dokümanlar" altında görünüyor. Anlaşılır ad ver.

## Sızıntı uyarısı

Gün 23'ün senaryolarını bu dosyalardan **cümle kopyalayarak** yazma. Senaryo hastanın
ağzından olmalı ("iki gündür göğsümde baskı var, sol koluma vuruyor"), protokolün
kendi cümlesi değil ("ST elevasyonu kırmızı kod gerektirir"). Kopyalarsan retrieval'ı
kelime eşleşmesiyle kolaylaştırır ve doğruluk yapay yükselir.

Aynı kural Gün 24'ün few-shot örnekleri için de geçerli: few-shot havuzuna giren
örnek ölçüm setine giremez.

## Mevcut iki dosya

`ornek_dokumanlar/gogus_agrisi_protokolu.txt` ve `karin_agrisi_protokolu.txt` bu
yapıyı zaten izliyor ama **kaynak satırı yok**. Yeni derlemeye alırken kaynaktan
doğrulayıp kaynak satırını ekle, ya da bu klasördeki yeni sürümleriyle değiştir.
Aynı içerik iki dosyada durmasın — chunk id'leri dosya adına bağlı olduğu için
ChromaDB ikisini ayrı kayıt sayar ve aynı bilgi iki kez getirilir.

## Bittiğinde

Haber ver. Sırayla şunlar yapılacak:

1. `/document/liste` ve silme uçları (bunlar veriye bağlı değil, önce yazılıyor ki
   yanlış yüklenen dosyayı temizleyebilelim)
2. Dosyaların toplu yüklenmesi
3. `scripts/kalibre_esik.py`'nin `ILGILI` / `ALAKASIZ` listelerinin yeni tabana göre
   genişletilmesi ve çalıştırılması
4. Çıkan değerin `app/config/config.py` → `rerank_threshold`'a yazılması

## Mentöre anlatısı

Gizlenecek bir şey yok, tersine öne çıkar:

> Kurumdan protokol alınamadığı için bilgi tabanını Sağlık Bakanlığı tebliği, TATD
> materyali ve ESI el kitabı gibi kamuya açık kaynaklardan derledim. Sistem gerçek
> hasta verisi görmedi. Ölçtüğüm şey, boru hattının doğru protokolü getirip tutarlı
> uygulayıp uygulamadığı — bir hastanenin klinik pratiğine uygunluk değil.

Bu savunulabilir bir mühendislik iddiası. Kurum verisi sonradan gelirse aynı boru
hattı değişmeden çalışır.
