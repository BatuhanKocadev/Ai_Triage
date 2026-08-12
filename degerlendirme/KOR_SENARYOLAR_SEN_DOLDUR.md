# Kör senaryolar — Batuhan dolduracak

Bu dosya Gün 23 değerlendirme setinin **kör yarısıdır.** Buradaki metinleri
protokolleri okumadan yazman, ölçümün geçerliliğini taşıyan tek şeydir.

## Neden kör

Gün 22'de protokol metnini de kalibrasyon sorgularını da aynı kişi yazdı ve sorgu
belgenin özetine dönüştü — çıkan skor sistemin iyi olduğunu değil, sorgunun
belgeden kopyalandığını gösteriyordu. Üç ayrı inceleme bunu yakalayamadı. Yakalayan
şey, metni **görmeden** yazılmış tek bir sorgu oldu:

> "mangalda kolumu ateşe tuttum, kolum bembeyaz oldu hissetmiyorum"

O tek cümle, yapılan düzeltmenin genelleşmediğini gösterdi. Bu dosya o mekanizmayı
sistematik hâle getiriyor.

## Kural

**`ornek_dokumanlar/protokoller/` klasörünü açma.** Tek kural bu.

Aşağıdaki konu başlıklarını bilmen sorun değil — hangi protokollerin yüklü
olduğunu bilmek, o protokollerin klinik eşiklerini bilmek demek değil. Senaryolarının
bu konularla örtüşmesi gerekiyor, yoksa sistemin hiç bilmediği bir hastalığı sormuş
oluruz ve bu adil bir test olmaz.

**Konu başlıkları:** göğüs ağrısı · nefes darlığı · karın ağrısı · baş ağrısı ·
inme · bilinç değişikliği · travma · yanık · zehirlenme · anafilaksi · ateş/sepsis ·
GİS kanaması · gebelik acilleri · pediatrik ateş · psikiyatrik aciller

Bunlardan **6-8 tanesini** seç. En az biri yanık, en az biri zehirlenme olsun —
bilinen iki defektin bedelini tam olarak orada ölçeceğiz.

## Nasıl yazılacak

- **Hastanın ağzından yaz.** "Substernal baskı tarzı ağrı" değil, "göğsümde bir
  ağırlık var, sanki biri üstüme oturmuş gibi".
- **Tıbbi terim kullanma.** Bildiğin terimler varsa bile bırak; gerçek hasta onları
  kullanmaz ve sistemin işi tam olarak bu boşluğu kapatmak.
- **10-500 karakter arası.** Bir-üç cümle yeter.
- **Türkçe karakterleri kullan** (ş, ç, ğ, ı, ö, ü). Karaktersiz yazımın skorları
  düşürdüğü ayrı bir bilinen sorun; buraya karıştırırsak hangi etkinin kimden
  geldiğini ayıramayız.
- **Etiket yazmayacaksın.** Kırmızı/Sarı/Yeşil, bölüm ve tetkik alanlarını ben
  protokol kriterlerine bakarak dolduracağım. Senin işin yalnızca şikayet metni;
  yaş ve cinsiyeti istersen yaz, istemezsen ben uydururum.

## Sonra: sesli kayıt

Metinleri bitirince **aynı metinleri mikrofona oku** ve kaydet. Windows'un yerleşik
**Ses Kaydedici** uygulaması yeterli (`.m4a` kaydediyor, backend kabul ediyor;
`.wav .mp3 .m4a .ogg .webm` destekleniyor, 25 MB sınır). Telefonun ses notu da olur.

Dosyaları **`degerlendirme/ses/`** klasörüne at ve `kor_01.m4a`, `kor_02.m4a` …
diye numaralandır — aşağıdaki numaralarla eşleşsin.

Yazdığın metin referans transkript olduğu için elle transkripsiyon işi yok; WER
kendiliğinden çıkacak.

---

## Senaryolar

Aşağıdaki boşlukları doldur. 6 tanesi yeterli, 8 daha iyi.

### kor_01
**Konu:**
**Şikayet:**
Sabah kalktığımdan beri başımın sağ tarafı felaket zonkluyor. Ağrısı resmen gözüme vuruyor. Işığa falan hiç bakamıyorum, midem kalkıyor.
**Yaş / cinsiyet:**

### kor_02
**Konu:**
**Şikayet:**
"Merdivenden inerken ayağım burkuldu. Bileğim inanılmaz şişti, üstüne kesinlikle basamıyorum. Durduğu yerde zonkluyor resmen."
**Yaş / cinsiyet:**

### kor_03
**Konu:**
**Şikayet:**
"Dünden beri karnıma kramplar giriyor. Midem sürekli bulanıyor, ağzıma bir lokma bir şey koyamadım. Biraz da ateşim çıktı galiba."
**Yaş / cinsiyet:**

### kor_04
**Konu:**
**Şikayet:**
"Üç gündür geçmeyen bir öksürüğüm var. Yutkunurken boğazım jilet gibi kesiliyor. Bir de derin nefes almaya çalışırken sırtıma garip bir ağrı saplanıyor."
**Yaş / cinsiyet:**

### kor_05
**Konu:**
**Şikayet:**
"Çay demlerken kaynar su elime döküldü. Bileğime kadar kıpkırmızı oldu, şimdiden su toplamaya başladı. Acısından yerimde duramıyorum."
**Yaş / cinsiyet:**

### kor_06
**Konu:**
**Şikayet:**
"Dün akşam dışarıda bir şeyler yemiştim, sabahtan beri her yerim deliler gibi kaşınıyor. Kollarımda kırmızı kırmızı lekeler çıktı, yüzüm de hafiften şişmeye başladı."
**Yaş / cinsiyet:**

### kor_07 (isteğe bağlı)
**Konu:**
**Şikayet:**
"İki gündür idrara çıkarken çok fena yanmam oluyor. Belimin sağ tarafına, boşluğuma doğru da öyle bir ağrı vuruyor ki nefesimi kesiyor."
**Yaş / cinsiyet:**

### kor_08 (isteğe bağlı)
**Konu:**
**Şikayet:**
"Kaç gündür üstümde bir kırgınlık var, bütün eklemlerim sızlıyor. Sürekli üşüyorum, ara ara titreme geliyor ama alnım da yanıyor sanki."
**Yaş / cinsiyet:**

### kor_09 (isteğe bağlı)
**Konu:**
**Şikayet:**
"Dün akşam yanlış ilaç içmişim bu yüzden kendimi iyi hissetmiyorum
**Yaş / cinsiyet:**
