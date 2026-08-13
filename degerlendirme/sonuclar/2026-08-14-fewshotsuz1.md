# Gün 24 değerlendirme sonuçları — 2026-08-14

Tek koşum. Ollama belirlenimsizdir; birden fazla koşum ortalaması gerekir.

## Ölçülen bilgi tabanı

15 dosya / 49 chunk.

| Protokol | chunk |
|---|---|
| anafilaksi.txt | 3 |
| ates_sepsis.txt | 4 |
| bas_agrisi.txt | 3 |
| bilinc_degisikligi.txt | 5 |
| gebelik_acilleri.txt | 3 |
| gis_kanamasi.txt | 3 |
| gogus_agrisi.txt | 3 |
| inme.txt | 3 |
| karin_agrisi.txt | 3 |
| nefes_darligi.txt | 3 |
| pediatrik_ates.txt | 3 |
| psikiyatrik_aciller.txt | 4 |
| travma.txt | 3 |
| yanik.txt | 3 |
| zehirlenme.txt | 3 |

## Kör set

Sette 9 senaryo var. Aşağıdaki paydalar bunun alt kümeleridir; hangi senaryonun hangi kovaya düştüğü kırılım tablosunda.

| Ölçü | Değer |
|---|---|
| Ölçülen senaryo (kapsam içi) | 8 |
| Doğru triyaj | 2 |
| **Genel doğruluk (tüm)** | **%25.0** |
| **Genel doğruluk (cevaplananlar)** | **%25.0** |
| **Kırmızı duyarlılık** | **n/d** (0/0) |
| Eşik altı oranı | %0.0 (0) |
| Tetkik Jaccard (ort.) | 0.28 (8 senaryodan) |
| Kök neden A/B/C | 0 / 6 / 2 |
| Şanslı doğru | 0 |
| Ölçülemedi (altyapı) | 0 |
| Sonucu yazılmamış | 0 |
| Kapsam dışı (doğru/toplam) | 1/1 |

> A/B/C dağılımı kapsam içi **ve** kapsam dışı senaryoları kapsar, oysa "Ölçülen senaryo" yalnızca kapsam içini sayar; ayrıca C kutusu triyaj kodu doğru olan senaryoları içerir. Bu üç sayı doğruluk sayılarıyla toplanarak denkleştirilemez.

### Senaryo kırılımı

| id | Beklenen | Çıkan | Kaynak geldi mi | Kutu | Beklenen tetkikler | Çıkan tetkikler | J |
|---|---|---|---|---|---|---|---|
| kor_01 | Yeşil | Sarı | evet | B | Nörolojik değerlendirme | Nörolojik değerlendirme ve anamnez, Bilgisayarlı Tomografi (BT), Tam kan sayımı | 0.00 |
| kor_02 | Yeşil | Kırmızı | evet | B | Tüm vücut veya bölgeye yönelik Bilgisayarlı Tomografi (BT) ve travma serisi grafiler | e-FAST (Odaklanmış Travma Ultrasonografisi), Tam Kan Sayımı, Laktat | 0.00 |
| kor_03 | Yeşil | Sarı | evet | B | Tam kan sayımı, Biyokimya, Tam İdrar Tetkiki, Beta-hCG | Tam kan sayımı, Biyokimya, Tam İdrar Tetkiki (TİT) | 0.75 |
| kor_04 | Yeşil | Sarı | evet | B | Göğüs Radyografisi | Batın muayenesi, X-ışığı çekimi (köpük, kemiği) | 0.00 |
| kor_05 | Sarı | Kırmızı | evet | B | — | Yanık değerlendirmesi, Tam kan sayımı | 0.00 |
| kor_06 | Sarı | Sarı | evet | C | Klinik değerlendirme ve fizik muayene, Tam kan sayımı | Tam kan sayımı | 0.50 |
| kor_07 | Sarı | Sarı | evet | C | Tam kan sayımı, Biyokimya, Tam İdrar Tetkiki | Tam kan sayımı, Biyokimya, Tam İdrar Tetkiki (TİT), Beta-hCG | 0.75 |
| kor_08 | Yeşil | Kırmızı | evet | B | Tam kan sayımı, Rutin biyokimya | Tam kan sayımı, Bilgisayar destekli görüntüleme (CT), Üst solunum yolu örneklemi | 0.25 |
| kor_09 | Belirsiz | Belirsiz | — | doğru | — | — | — |

## Türetilmiş set

Sette 20 senaryo var. Aşağıdaki paydalar bunun alt kümeleridir; hangi senaryonun hangi kovaya düştüğü kırılım tablosunda.

| Ölçü | Değer |
|---|---|
| Ölçülen senaryo (kapsam içi) | 19 |
| Doğru triyaj | 16 |
| **Genel doğruluk (tüm)** | **%84.2** |
| **Genel doğruluk (cevaplananlar)** | **%84.2** |
| **Kırmızı duyarlılık** | **%100.0** (10/10) |
| Eşik altı oranı | %0.0 (0) |
| Tetkik Jaccard (ort.) | 0.27 (19 senaryodan) |
| Kök neden A/B/C | 2 / 2 / 16 |
| Şanslı doğru | 0 |
| Ölçülemedi (altyapı) | 0 |
| Sonucu yazılmamış | 0 |
| Kapsam dışı (doğru/toplam) | 0/1 |

> A/B/C dağılımı kapsam içi **ve** kapsam dışı senaryoları kapsar, oysa "Ölçülen senaryo" yalnızca kapsam içini sayar; ayrıca C kutusu triyaj kodu doğru olan senaryoları içerir. Bu üç sayı doğruluk sayılarıyla toplanarak denkleştirilemez.

### Senaryo kırılımı

| id | Beklenen | Çıkan | Kaynak geldi mi | Kutu | Beklenen tetkikler | Çıkan tetkikler | J |
|---|---|---|---|---|---|---|---|
| tur_01 | Kırmızı | Kırmızı | evet | C | EKG, Tam kan sayımı, Rutin biyokimya, Direkt grafi | Elektrokardiyografi (EKG), Tam kan sayımı | 0.50 |
| tur_02 | Sarı | Sarı | evet | C | EKG, Tam kan sayımı, Rutin biyokimya, Direkt grafi | Elektrokardiyografi (EKG), Kontrol oksijen saturasyonu (SpO2) | 0.20 |
| tur_03 | Sarı | Kırmızı | evet | B | Göğüs Radyografisi, Kan Gazı Analizi | Elektrokardiyografi (EKG), SpO2 ölçümü, Tam kan sayımı | 0.00 |
| tur_04 | Sarı | Sarı | evet | C | Tam kan sayımı, Biyokimya, Tam İdrar Tetkiki, EKG | Hemogram (Tam kan sayımı), Biyokimya, Tam İdrar Tetkiki (TİT), Beta-hCG | 0.60 |
| tur_05 | Kırmızı | Kırmızı | evet | C | Nörolojik değerlendirme, Bilgisayarlı Tomografi, Tam kan sayımı, Rutin biyokimya | Parmak ucu kan şekeri, Nabız ve ateş ölçümü, Kapsamlı fizik ve nörolojik muayene | 0.00 |
| tur_06 | Kırmızı | Kırmızı | evet | C | Tam kan sayımı | FAST-ED skorunu belirleme, Glasgow Koma Skalasını (GKS) ölçme, Pupilla muayenesi | 0.00 |
| tur_07 | Sarı | Kırmızı | HAYIR | A | Parmak ucu kan şekeri, Rutin laboratuvar testleri, Serum elektrolitleri | Basılansal kan testi, Nörolojik değerlendirme | 0.00 |
| tur_08 | Kırmızı | Kırmızı | evet | C | e-FAST, Tam kan sayımı, Laktat, Bilgisayarlı Tomografi | e-FAST, Tam Kan Sayımı, Laktat | 0.75 |
| tur_09 | Kırmızı | Kırmızı | evet | C | Karboksihemoglobin, Kan gazı | Tam kan sayımı, Ses ve solunum bulge kontrolü, Laktat seviyesi | 0.00 |
| tur_10 | Yeşil | Yeşil | evet | C | — | — | 1.00 |
| tur_11 | Kırmızı | Kırmızı | evet | C | Kapiller kan şekeri, EKG, Kan gazı | Tam kan sayımı, Bilirritaryon testi | 0.00 |
| tur_12 | Sarı | Sarı | evet | C | Kapiller kan şekeri, EKG, Parasetamol düzeyi | Tam kan sayımı, Parasetamol dozunu kontrol etmek için farmakolojik takip | 0.00 |
| tur_13 | Kırmızı | Kırmızı | evet | C | Klinik değerlendirme ve fizik muayene | Tam kan sayımı, Bilirritaryon testi, Plasma kloroteli ve sodyum seviyeleri | 0.00 |
| tur_14 | Kırmızı | Kırmızı | evet | C | Kan laktat düzeyi, Kan kültürü, Tam kan sayımı, Rutin biyokimya | Kan laktat düzeyi, Antibiyotik öncesi en az iki set Kan Kültürü ve odak kültürleri, Tam kan sayımı ve rutin biyokimya | 0.17 |
| tur_15 | Kırmızı | Kırmızı | evet | C | Tam kan sayımı, Kan grubu, Cross-match, Koagülasyon paneli | Tam kan sayımı, Nabız ölçümü | 0.20 |
| tur_16 | Yeşil | Yeşil | evet | C | Tam kan sayımı | Tam kan sayımı | 1.00 |
| tur_17 | Sarı | Yeşil | evet | B | Beta-hCG, Yatak başı obstetrik USG, Tam kan sayımı | Beta-hCG, Yatak başı obstetrik USG | 0.67 |
| tur_18 | Kırmızı | Kırmızı | evet | C | Kapiller kan şekeri, Tam kan sayımı, Kan kültürü | Kapiller kan şekeri ölçümü, Tam kan sayımı ve enfeksiyon belirteçleri (Rutin biyokimya) | 0.00 |
| tur_19 | Sarı | Sarı | evet | C | Parmak ucu kan şekeri, Tam kan sayımı, Rutin biyokimya | Psikiyatrik değerlendirme, Kontrol edilme | 0.00 |
| tur_20 | Belirsiz | Yeşil | — | A | — | — | — |

## Ses tanıma (WER) — Kör set

| id | WER | Transkript |
|---|---|---|
| kor_01 | 0.056 | Sabah kalktığımdan beri başımın sağ tarafı helaketi zonkluyor ağrısı resmen gözü… |
| kor_02 | 0.071 | Merdivenden inerken ayağım vurkuldu, bileğim inanılmaz şişti, üstüne kesinlikle … |
| kor_03 | 0.053 | Dünden beri karnıma krantlar giriyor, midem sürekli bulanıyor, ağzıma bir lokma … |
| kor_04 | 0.227 | 3 gündür geçmeyen bir öksürüğüm var, yut kururken boğazım jilet gibi kesiliyor, … |
| kor_05 | 0.176 | Kaynar su elime döküldü, bileğime kadar kırmızı oldu, şimdiden su toplamaya başl… |
| kor_06 | 0.217 | Dün akşam içeride bir şeyler yiyemiştim sabahtan beri her yerim deriler gibi kaş… |
| kor_07 | 0.190 | İki gündür idrala çıkarken çok fena yanmam oluyor. Belimin sağ tarafına, boşluğu… |
| kor_08 | 0.000 | Kaç gündür üstümde bir kırgınlık var. Bütün eklemlerim sızlıyor, sürekli üşüyoru… |
| kor_09 | 0.300 | Bu akşam yanlış ilaç içmişim kendimi iyi hissetmiyorum.… |

**Ortalama WER: 0.143** (9 kayıt)

> NORMALİZASYON ARTEFAKTI: kor_04 transkriptlerinde rakam var. Referans metinlerde sayılar kelimeyle yazılmışsa bu fark tanıma hatası değildir ve WER'i haksız yere şişirir. Sayıyı düzeltmeyin, sınırı raporlayın.

Dürüst sınır: kullanıcı kendi yazdığı metni okudu. Okunan konuşma, telaşlı bir hastanın konuşmasından kolaydır; bu WER iyimser taraflıdır.
