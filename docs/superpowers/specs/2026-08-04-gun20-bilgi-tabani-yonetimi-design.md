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

**İçinde:** iki yeni uç, `upload`'ın yaz-sonra-artakalanı-sil düzeltmesi, doküman
uçlarının ilk test dosyası, bellek içi sahte ChromaDB koleksiyonu.

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

**K5 — `upload` önce yeni sürümü yazar, sonra artakalan eski chunk'ları siler.**
Yaz-sonra-artakalanı-sil. Sıra şu: aynı `source`'a ait eski chunk id'leri okunur →
yeni sürüm `upsert` edilir → yeni id kümesinde karşılığı olmayan eski id'ler
silinir. Hayalet chunk sorunu kökten biter ve kullanıcı hiçbir şey hatırlamak
zorunda kalmaz.

Gerekçe iki maddedir:

1. Alternatif — kullanıcının yeniden yüklemeden önce elle `DELETE` çağırması —
   disiplini insana yükler; unutulduğu anda bilgi tabanı sessizce kirlenir ve
   kirlendiği fark edilmez.
2. **Yarıda kalan yükleme önceki sürümü kaybettirmemeli.** Sil-sonra-yaz sırasında
   `delete` başarılı olup `upsert` patlarsa (ChromaDB kopar, embedding hatası,
   süreç ölür) elde ne eski ne yeni sürüm kalır — düzeltme amaçlı bir yükleme
   girişimi veri kaybına dönüşür. Yaz-sonra-sil sırasında en kötü ihtimalle birkaç
   artakalan chunk kalır; bunlar bir sonraki başarılı yüklemede temizlenir ve
   arada bilgi tabanı hiçbir zaman boş kalmaz.

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

**K9 — Dosya adı normalizasyonundan doğan id çakışması bu günün kapsamı dışında.**
`upload` id'leri `dosya_adı.replace(" ", "_").lower()` ile üretiyor ama `source`'a
orijinal adı yazıyor. Yani id üretimi **iki** normalizasyon yapıyor: harf düzeyini
küçültüyor **ve** boşlukları alt çizgiye çeviriyor. Normalize edilmiş hâlleri
eşleşen iki farklı dosya adı aynı id'lere, farklı `source`'a düşer; K5'in temizliği
`source` sorgusundan gelen id'lerle çalıştığı için bu ikiliyi ayrıştıramaz —
ikinci dosya birincinin chunk'larının üzerine yazar, birincinin `source` kaydı da
görünürde kalmaya devam eder.

Çakışan çiftlere iki örnek:

- `Göğüs.txt` / `göğüs.txt` — yalnızca harf düzeni farkı.
- `Rapor A.txt` / `Rapor_A.txt` — yalnızca boşluk/alt çizgi farkı.

İkinci örnek önemli: bunun için kasıt gerekmez. Aynı dokümanın bir kopyası boşluklu,
bir kopyası alt çizgili adlandırıldığında (indirme aracı, işletim sistemi ya da elle
yeniden adlandırma bunu kendiliğinden üretir) çakışma kazara tetiklenir. Yani bu, tek
başına "kullanıcı bilerek uğraşırsa olur" türü bir sınır değil. Yine de bilinen sınır
olarak kaydediliyor ve Gün 22'ye devrediliyor.

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
Değişen tek şey yan etkisi: yeni sürüm önce yazılır, ardından aynı `source`'a ait
eski chunk'lardan yeni sürümde karşılığı olmayanlar silinir (K5). Silme
`where={"source": ...}` ile toptan değil, hesaplanan artakalan id listesiyle
yapılır — böylece hem başka dosyalara hem de yeni yazılan chunk'lara dokunulmaz.
Bu, dışarıdan yalnızca "yeniden yükleme artık hayalet bırakmıyor" olarak görünür;
ek olarak yarıda kalan bir yükleme artık önceki sürümü silmiş olmaz.

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
| `test_yeniden_yukleme_baska_dosyanin_chunklarina_dokunmaz` | K5 — temizliğin kapsamı |
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

- [ ] Dokuz test yeşil; toplam 90 → 99
- [ ] Mevcut 90 test hâlâ yeşil
- [ ] `test_yeniden_yukleme_eski_chunklari_birakmaz` mutasyonla bağlayıcı: K5
      kaldırıldığında kırmızıya düşüyor
- [ ] `test_yeniden_yukleme_baska_dosyanin_chunklarina_dokunmaz` mutasyonla
      bağlayıcı: temizlik `source` yerine `category` ile yapıldığında kırmızıya düşüyor
- [ ] `GET /document/liste` gerçek ChromaDB'ye karşı elle doğrulandı ve mevcut
      2 dosyayı doğru sayıyor
- [ ] Hiçbir test gerçek `triage_documents` koleksiyonuna yazmıyor
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama
- [ ] Dal `main`'e birleşti
