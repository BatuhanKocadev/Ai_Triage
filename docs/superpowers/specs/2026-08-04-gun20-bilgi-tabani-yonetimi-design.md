# Gün 20 — Bilgi Tabanı Yönetimi Tasarım Dokümanı

**Tarih:** 4 Ağustos 2026
**Kapsam:** `GET /document/liste`, `DELETE /document`, ve `POST /document/upload`'ın
hayalet chunk düzeltmesi.

## Hedef

Bilgi tabanının içeriğini görülebilir ve düzeltilebilir kılmak. Bugün yalnızca
yazma ucu var (`POST /document/upload`); yüklenen dokümanları listeleyen ya da
kaldıran bir yol yok. Yanlış yüklenen bir dosya bilgi tabanında kalıcıdır.

## Bağlam — neden bugün

Gün 20 yol haritasında "bilgi tabanı yönetimi + gerçek protokol verisi + eşik
kalibrasyonu" günü ve kritik yolda (★). Staj yerinden protokol dokümanları
gelmediği için derleme kamuya açık kaynaklardan elle hazırlanıyor
(`ornek_dokumanlar/protokoller/00_NASIL_DOLDURULUR.md`). Bu, dosyaların **defalarca
düzeltilip yeniden yükleneceği** anlamına geliyor — ve mevcut `upload` bu döngüde
sessizce bozuluyor.

### Hayalet chunk hatası

`upload`, chunk id'lerini `{güvenli_dosya_adı}_chunk_{sıra}` diye üretip `upsert`
ediyor (`app/api/document.py:116-129`). `upsert` yalnızca kendisine verilen id'lere
dokunur.

1. `gogus_agrisi.txt` yüklenir, 10 chunk olur → `_chunk_0` … `_chunk_9`
2. Dosya kısaltılıp yeniden yüklenir, 6 chunk olur → `_chunk_0` … `_chunk_5` üzerine
   yazılır
3. `_chunk_6` … `_chunk_9` bilgi tabanında **eski sürümün metniyle kalır**

Sonuç: sistem silinmiş bir metinden alıntı yapabilir ve `sources` yine o dosyayı
gösterir — yani izlenebilirlik iddiası sessizce yalanlanır. Bu, derlemeyi düzelte
düzelte ilerleyen bir günde kaçınılmaz.

## Kapsam

**İçinde:** iki yeni uç, `upload`'ın sil-sonra-yaz düzeltmesi, doküman uçlarının ilk
test dosyası, bellek içi sahte ChromaDB koleksiyonu.

**Dışında:** protokol dosyalarının kendisi (kullanıcı hazırlıyor), toplu yükleme,
eşik kalibrasyonu (`kalibre_esik.py`), `rerank_threshold` güncellemesi. Bunlar
derleme hazır olunca ayrı bir oturumda yapılacak — bu tasarımın ön koşulu oldukları
için önce bu uçlar bitiyor.

## Tasarım kararları

**K1 — Her iki uç da `require_admin_role`.** `upload` ile aynı kapı. Bilgi tabanını
değiştirmek yönetici işi; doktor ve hasta rolleri buraya girmez. Listeleme de
admin'e kısıtlanıyor: okuma zararsız görünür ama koleksiyondaki bütün dosya adlarını
ve kategorileri dökmek sistemin iç yapısını açık eder, dolayısıyla yetki kapısı
okuma tarafında da duruyor.

**K2 — Doküman kimliği `source` metadata'sıdır, sorgu parametresiyle taşınır.**
Silme `DELETE /document?kaynak=<dosya adı>` biçiminde. Yol parametresi seçilmedi:
dosya adlarında nokta, boşluk ve Türkçe karakter var (`Göğüs Ağrısı.txt`), bunlar
yol parametresinde kodlama sorunu çıkarır.

**K3 — Boş koleksiyon `200` + `[]` döner, `404` değil.** "Hiç doküman yok" bir hata
değil, geçerli bir sistem durumu. Yol haritasının "yüklenen doküman sayısı" metriği
bu uçtan okunacak; sıfır da bir ölçümdür.

**K4 — Liste `kaynak` adına göre alfabetik sıralanır.** Gün 17+18'de sayfalamada
öğrenilen ders: belirlenimci olmayan sıralama, ölçüm alınan bir listede sessiz
karışıklık üretir. ChromaDB `get()` çağrısının dönüş sırası garanti değildir.

**K5 — `upload` yazmadan önce aynı `source`'a ait chunk'ları siler.** Sil-sonra-yaz.
Hayalet chunk sorunu kökten biter ve kullanıcı hiçbir şey hatırlamak zorunda kalmaz.
Alternatif — kullanıcının yeniden yüklemeden önce elle `DELETE` çağırması — disiplini
insana yükler; unutulduğu anda bilgi tabanı sessizce kirlenir ve kirlendiği fark
edilmez.

**K6 — Eşleşen chunk yoksa silme `404` döner.** Var olmayan bir dosyayı silmeye
çalışmak sessizce başarılı olmamalı; yanlış dosya adı yazan yönetici bunu bilmeli.

**K7 — Testler bellek içi sahte koleksiyonla koşar.** `tests/yardimcilar/sahte_chroma.py`
altında `upsert` / `get` / `delete` uygulayan bir sınıf. Monkeypatch **adın arandığı
ad alanına** uygulanır: `app.api.document.get_collection`. Gerçek `triage_documents`
koleksiyonuna hiçbir testte dokunulmaz — bu koleksiyon her hasta sorgusunun tarandığı
yer, kirlenmesi üretim davranışını bozar. Mevcut `dokuman_yazmayi_engelle` fixture'ı
bu tehlikeyi zaten belgeliyor (`tests/api/conftest.py:35-54`).

**K8 — Listede `kategori` ve `yukleme_tarihi`, `chunk_index` en küçük olan chunk'tan
okunur.** K5 sayesinde bir dosyanın tüm chunk'ları tek yüklemeden gelir, yani
metadata zaten tutarlıdır; yine de belirlenimci bir kural yazılıyor ki tutarsızlık
oluşursa çıktı rastgele değişmesin.

**K9 — Büyük/küçük harf çakışması bu günün kapsamı dışında.** `upload` id'leri
`dosya_adı.lower()` ile üretiyor ama `source`'a orijinal adı yazıyor. `Göğüs.txt` ve
`göğüs.txt` aynı id'lere, farklı `source`'a düşer; K5'in temizliği `source` ile
çalıştığı için bu ikiliyi ayrıştıramaz. Tetiklenmesi için aynı adın farklı harf
düzeniyle kasıtlı olarak iki kez yüklenmesi gerekir. Bilinen sınır olarak
kaydediliyor, Gün 22'ye devrediliyor.

## Uç sözleşmeleri

### `GET /document/liste`

Yanıt `200`:

```json
[
  {"kaynak": "gogus_agrisi.txt", "chunk_sayisi": 8, "kategori": "protokol", "yukleme_tarihi": "2026-08-04"},
  {"kaynak": "karin_agrisi.txt", "chunk_sayisi": 6, "kategori": "protokol", "yukleme_tarihi": "2026-08-04"}
]
```

Boş koleksiyon: `200` + `[]`. Yetkisiz: `401`. `admin` dışı rol: `403`.

### `DELETE /document?kaynak=<dosya adı>`

Yanıt `200`:

```json
{"silinen_chunk": 8}
```

Eşleşme yok: `404`. Yetkisiz: `401`. `admin` dışı rol: `403`.

### `POST /document/upload` (değişen davranış)

Sözleşmesi aynı kalır — istek gövdesi, yanıt gövdesi ve durum kodu değişmez.
Değişen tek şey yan etkisi: yazmadan önce aynı `source`'a ait chunk'lar silinir.
Bu, dışarıdan yalnızca "yeniden yükleme artık hayalet bırakmıyor" olarak görünür.

## Test mimarisi

`tests/api/test_document_api.py` **bugün doğuyor** — doküman uçlarının bugüne kadar
kendi test dosyası yoktu, yalnızca `tests/api/test_auth_api.py` içinde `upload`'ın
yetki kapısı sınanıyordu.

| Test | Neyi donduruyor |
|---|---|
| `test_liste_dokumanlari_kaynak_bazinda_gruplar` | gruplama ve chunk sayısı |
| `test_liste_bos_koleksiyonda_bos_liste_doner` | K3 |
| `test_liste_kaynak_adina_gore_siralanir` | K4 |
| `test_silme_dosyanin_tum_chunklarini_siler` | silme |
| `test_olmayan_dosya_silinince_404_doner` | K6 |
| `test_yeniden_yukleme_eski_chunklari_birakmaz` | K5 — hayalet chunk regresyonu |
| `test_user_rolu_listeye_403_alir` | K1 |
| `test_user_rolu_silmeye_403_alir` | K1 |

Yetki testleri iki ayrı uç için ayrı ayrı yazılıyor. Gün 17+18'de ölçülen desen:
bağımlılığı izole sınamak, **ucun onu kullandığını** kanıtlamaz — mutasyon deneyinde
`Depends(require_doctor_role)` düz `Depends(get_current_user)` ile değiştirildiğinde
paket yeşil kalmıştı.

`test_yeniden_yukleme_eski_chunklari_birakmaz` bu günün en önemli testi: önce çok
chunk'lı bir metin yükler, sonra aynı adla daha kısa bir metin yükler, koleksiyondaki
toplam chunk sayısının ikinci metnin chunk sayısına eşit olduğunu doğrular. K5
kaldırılırsa bu test kırmızıya döner.

## Bitti sayılır

- [ ] Sekiz test yeşil; toplam 90 → 98
- [ ] Mevcut 90 test hâlâ yeşil
- [ ] `test_yeniden_yukleme_eski_chunklari_birakmaz` mutasyonla bağlayıcı: K5
      kaldırıldığında kırmızıya düşüyor
- [ ] `GET /document/liste` gerçek ChromaDB'ye karşı elle doğrulandı ve mevcut
      2 dosyayı doğru sayıyor
- [ ] Hiçbir test gerçek `triage_documents` koleksiyonuna yazmıyor
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
