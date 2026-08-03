# Gün 19 — Streamlit doktor paneli: döngü kapanıyor

**Tarih:** 3 Ağustos 2026 (yol haritasında 4 Ağustos'a yazılmıştı; Gün 17+18 aynı gün
bittiği için bir gün erken başlandı — takvim açığı bu kadar kapanıyor)
**Dal:** `gun19-doktor-paneli`
**Kaynak:** `AI_Triage_Son_Yol_Haritasi.docx`, "GÜN 19 · Streamlit doktor paneli" bölümü
**Durum:** Onaylandı (kullanıcı "önceki günlerdeki metodolojinin tamamen aynısı" dedi;
Gün 17+18'deki gibi açık kararlar bu yetkiyle alınmıştır ve her biri gerekçelidir)

## Amaç

Doktor tarayıcıdan giriş yapıp bekleyen vakaları görecek, bir vakayı açıp yapay zekâ
önerisini inceleyecek, triyaj kodunu ve tetkikleri değiştirebilecek, onaylayacak ve vaka
listeden düşecek. Günün sonunda hasta girişinden doktor onayına kadar tam döngü tarayıcıda
çalışıyor olacak.

Bu, projenin "demo edilebilir" olduğu gün. Dünkü uçlar sözleşmeyi kurdu; bugün o
sözleşmeyi bir insanın kullanabileceği hâle getiriyoruz.

## Mevcut durumun özeti

Backend tarafı hazır: `GET /doctor/bekleyen` yapay zekâ önerisini gömülü döndürüyor,
`POST /doctor/inceleme` onayı ayrı satıra yazıp ziyareti `tamamlandi` yapıyor, `doctor`
rolü ve `require_doctor_role` yerinde (Gün 17+18, `main` üzerinde `0ff856b`).

Frontend tarafı (`frontend/app.py`, 340 satır, tek dosya) giriş yapıyor, rolü
`/auth/me`'den okuyor, hastanın yazılı ve sesli şikayet akışlarını ve admin doküman
yükleme panelini barındırıyor. Eksik olan tek şey doktorun ekranı.

## Kararlar

Yol haritasının Gün 19 bölümü kodla dört yerde çelişiyor, ve panel tasarımı sekiz karar
daha gerektiriyor. Hepsi burada; plan ve subagent brief'leri bu bölümü tek doğru kaynak
sayacak.

### K1 — "Rol tahminini sil" maddesinin karşılığı yok; iş sekme haritasında

Yol haritası Görev 2'yi "Kullanıcı adından tahmin eden mevcut mantığı SİL" diye
tanımlıyor. **Silinecek bir şey yok** — `frontend/app.py:78-85` rolü giriş sonrası
`/auth/me`'den okuyor ve `app/api/auth.py:41-47` onu döndürüyor. Bu madde, Gün 17+18'de
düzelttiğimiz eskimiş `CLAUDE.md` iddiasından miras kalmış.

Gerçekten eksik olan iki şey:

1. **`/auth/me` hiçbir testten geçmiyor.** Panelin rolü doğru okuduğu iddiası bugün
   yalnızca elle denemeye dayanıyor. Yol haritasının `test_rol_bilgisi_auth_me_ile_donuyor`
   testi bu boşluğu kapatıyor — gerçek ve gerekli iş.
2. **Sekme seçimi hâlâ ikili:** `user_role == "admin"` ise sohbet + yönetici, aksi hâlde
   yalnızca sohbet (`frontend/app.py:109-116`). Yani `doctor` rolündeki hesap, gönderdiğinde
   403 alacağı hasta sohbet sekmesine düşüyor. Görev 2'nin asıl işi bu.

### K2 — Rol → sekme haritası

| Rol | Gördüğü sekmeler | Neden |
|---|---|---|
| `user` | Sohbet | Hasta başvurusu girer; `/doctor/*`'tan 403 alır |
| `doctor` | **Doktor Paneli** | `/ai/analiz`, `/document/upload`, `/speech/transkript` üçünden de 403 alır — hasta sekmesini göstermek yalancı bir arayüzdür |
| `admin` | Sohbet · Doktor Paneli · Yönetici | `admin` her üç yetki grubundan da geçer ("admin her şeyi görür", Gün 17 kararı) |

Doktora hasta sohbet sekmesi **gösterilmiyor**. Kullanıcının basınca 403 aldığı bir düğme,
arayüzün yetki modeli hakkında yalan söylemesidir. Bu, K1'de tarif edilen bugünkü kusurun
ta kendisi.

### K3 — Onay sonrası akış: bayrak + tek `st.rerun()`

Streamlit her etkileşimde scripti baştan çalıştırdığı için, onay sonrası "başarılı" mesajı
göstermek ile listeyi tazelemek çakışır. Yol haritasının "TAKILIRSAN" bölümü de sonsuz
döngü riskini işaretliyor.

Desen şu:

1. `POST /doctor/inceleme` 201 dönerse, sonucun özeti
   `st.session_state.doktor_son_onay` içine yazılır ve `st.rerun()` çağrılır.
2. Yeni çalıştırmada bayrak doluysa `st.success(...)` basılır ve **bayrak hemen
   temizlenir**.

Bayrağı temizlemek zorunlu: temizlenmezse her yeniden çizim mesajı tekrar gösterir, ve
`st.rerun()` bayrağa bağlı kalırsa döngü kapanmaz.

### K4 — Liste önbelleğe alınmıyor

Yol haritası "Panel yavaş açılıyor" belirtisi için `@st.cache_data` öneriyor.
**Uygulanmıyor.**

Gerekçe: bekleyen vaka kuyruğu bayatlaması en pahalı olan veridir. Önbellek, bir doktora
başka bir doktorun az önce kapattığı vakayı gösterir; üstüne basınca 409 alır ve arayüz
sebepsiz kırık görünür. Kazanç ise sıfıra yakın — liste tek bir indeksli sorgu ve
prototipte kuyruk küçük. Performans gerçekten sorun olursa doğru çözüm önbellek değil,
sayfa boyunu küçültmektir.

### K5 — Tetkik seçimi: `st.multiselect(accept_new_options=True)`

Yol haritası `st.multiselect` diyor ama seçeneklerin nereden geleceğini söylemiyor. Eğer
seçenekler yapay zekânın önerdiği tetkiklerle sınırlanırsa doktor **listeye yeni tetkik
ekleyemez** — oysa onay ucunun varlık sebebi tam olarak doktorun yapay zekâyı
düzeltebilmesi.

Kurulu Streamlit 1.59.2 `accept_new_options` parametresini destekliyor (kontrol edildi).
Seçenekler yapay zekânın önerisiyle başlar, varsayılan olarak hepsi seçilidir, doktor
çıkarabilir **ve serbest metinle yenisini ekleyebilir**.

### K6 — Sayfalama: "Daha fazla göster"

`GET /doctor/bekleyen` `limit`/`offset` alıyor ve K6 (Gün 17+18) bu seçimi tam olarak bu
düğmeye dayandırmıştı. `st.session_state.doktor_liste_limiti` 20'den başlar; dönen kayıt
sayısı limite eşitse "Daha fazla göster" düğmesi görünür ve limiti 20 artırır.

Sayfa sayfa gezinme değil, artan pencere: doktorun kuyruğunda ileri-geri gitmesi gereken
bir iş yok, aşağı inmesi gereken bir liste var.

### K7 — Renk kodu expander başlığında

Yol haritası "video sunumunda en çok işe yarayacak detay" diyor. Streamlit expander
başlığı HTML kabul etmediği için renk emoji ile veriliyor:

| Triyaj kodu | İşaret |
|---|---|
| Kırmızı | 🔴 |
| Sarı | 🟡 |
| Yeşil | 🟢 |
| Belirsiz (eşik altı) | ⚪ |

`Belirsiz` ayrı bir işaret alıyor çünkü ayrı bir durum: yapay zekâ karar veremedi, LLM'e
hiç gidilmedi. Doktorun ilk bakması gereken vakalar bunlar ve diğer üçüyle
karıştırılmamalı.

### K8 — Kısmi refactor: yalnızca yeni kod fonksiyona alınır

Yol haritasının REFACTOR adımı `hasta_sekmesi()`, `doktor_sekmesi()`, `admin_sekmesi()`
üçünün de çıkarılmasını öneriyor. **Yalnızca `doktor_sekmesi()` yazılıyor**, mevcut hasta
ve admin blokları yerinde bırakılıyor.

Gerekçe: Streamlit kodu konuma duyarlıdır (sidebar bağlamı, `session_state` sırası,
`st.tabs` iç içe geçişi) ve bu dosyanın **hiç otomatik testi yok**. Çalışan 340 satırı
test ağı olmadan taşımak, bugünün asıl işini riske atar. Yeni kod baştan fonksiyon olarak
doğar; mevcut blokların çıkarılması Gün 22'ye bırakılır.

Aynı gerekçeyle `istek_at(metot, yol, jeton, ...)` yardımcısı yazılır ama **yalnızca yeni
doktor kodunda kullanılır**; mevcut sekiz `requests.*` çağrısı dönüştürülmez.

### K9 — Yol haritasının test alan adları yanlış

`test_bekleyen_liste_yaniti_panelin_bekledigi_alanlari_icerir` maddesi alanları
"visit_id, sikayet, yas, cinsiyet, triage_code, onerilen_tetkikler, sources,
olusturma_zamani" diye sayıyor. Gerçek sözleşme (Gün 17+18, `app/schemas/doctor.py`):

- Üst düzey: `visit_id`, `patient_age`, `gender`, `symptom_text`, `chronic_disease`,
  `vitals`, `giris_tipi`, `created_at`
- `ai_onerisi` altında: `triage_code`, `department`, `onerilen_tetkikler`, `ai_note`,
  `sources`

Yani `triage_code` ve `sources` üst düzeyde **değil**, iç içe. Test adı birebir korunuyor,
içeriği gerçek sözleşmeyi doğruluyor. Yol haritasının doğrulama SQL'i de aynı hatayı
taşıyor (`v.durum`, `v.olusturma_zamani`); doğrusu `v.status`, `v.created_at` — Gün
17+18'de düzeltilmişti.

### K10 — "Bekleyen Sorular" bugün gerçek veriye bağlanmıyor

`frontend/app.py:26-30` sabit kodlanmış iki sahte soru tutuyor ("Dr. Berkay",
"Hemşire Sude") ve `:307` başlığı **"Gün 19'da gerçek veriye bağlanacak"** diye söz
veriyor. Yol haritasının Gün 19 bölümü bundan hiç söz etmiyor.

Karar: **yapılmıyor.** Gerçek veriye bağlamak yeni bir tablo, yeni uçlar ve kendi test
seti demek — kritik yol üstünde olmayan, bir günlük ayrı bir iş. Bugünün kritik yolu
hasta→doktor döngüsü.

Ama yanıltıcı söz kaldırılıyor: başlık, bunun bir demo yer tutucusu olduğunu dürüstçe
söyleyecek şekilde değiştirilir. Özelliğin kendisi silinmiyor — "Bilgi Tabanına Ekle"
akışı gerçekten çalışıyor ve `/document/upload`'a yazıyor; sahte olan yalnızca soru
listesi.

### K11 — Uçtan uca test iki kimlikle koşar

`test_sikayetten_doktor_onayina_tam_dongu`, `/ai/analiz`'i `user` rolüyle, `/doctor/*`'ı
`doctor` rolüyle çağırır. Tek bir `admin` jetonuyla da geçerdi ama iki kimlik kullanmak
rol ayrımının (K2, Gün 17+18) uçtan uca gerçekten çalıştığını da kanıtlar — hasta girer,
doktor kapatır.

Ollama ve ChromaDB testte **çağrılmaz**: `esik_ustu` deseniyle `app.api.ai` ad alanında
`retrieve_and_rerank` ve `get_structured_completion` sahtelerle değiştirilir
(`tests/yardimcilar/sahte_llm.py`, `CLAUDE.md`'deki monkeypatch kuralı).

### K12 — Streamlit'in kendisi otomatik test edilmiyor

Panelin arkasındaki her şey test ediliyor, panelin kendisi edilmiyor. Bu bilinçli:
Streamlit için UI testi kurmak (AppTest ya da tarayıcı sürücüsü) bugünün bütçesini yer ve
kırılgan olur. Bunun yerine bugünün dört testi **backend sözleşmesini kilitler** — panelin
okuduğu alan adları, onay sonrası listeden düşme davranışı ve rol bilgisi sessizce
değişemez.

Panelin kendisi tarayıcıda elle doğrulanır ve ekran görüntüsü alınır (aşağıda).

## Testler

Dört test, hepsi önce kırmızı görülecek. Adlar yol haritasından birebir alınmıştır.

**`tests/api/test_doctor_api.py`** (mevcut dosyaya eklenir)
- `test_bekleyen_liste_yaniti_panelin_bekledigi_alanlari_icerir` — panelin okuduğu her
  alanın yanıtta bulunduğunu, `ai_onerisi`'nin iç içe geldiğini doğrular (K9)
- `test_onay_sonrasi_vaka_bekleyen_listesinde_gorunmez` — panelin "listeden düşme"
  davranışının kanıtı

**`tests/api/test_auth_api.py`** (mevcut dosyaya eklenir)
- `test_rol_bilgisi_auth_me_ile_donuyor` — `/auth/me` kullanıcı adı ve rolü döndürür,
  parola hash'i dönmez

**`tests/api/test_uctan_uca_dongu.py`** (yeni dosya)
- `test_sikayetten_doktor_onayina_tam_dongu` — analiz çağır → `visit_id` al → bekleyen
  listede gör → onayla → listeden düştüğünü ve durumun `tamamlandi` olduğunu doğrula

Beklenen toplam: **86 → 90**.

## Panelin sözleşmesi

**Liste:** `GET /doctor/bekleyen?limit=<limit>&offset=0`. Her vaka bir `st.expander`;
başlıkta K7 işareti + yaş/cinsiyet + yapay zekânın triyaj kodu, içinde şikayet metni,
kronik hastalık, vitaller, giriş kanalı, yapay zekâ notu ve kaynak dokümanlar.

**Form:** `st.form` içinde `st.radio` (Kırmızı/Sarı/Yeşil — `Belirsiz` yok, K8/Gün 17+18),
`st.multiselect` (K5), `st.text_area` (not, opsiyonel), `st.form_submit_button`.

Her vakanın form anahtarları `visit_id` ile benzersizleştirilir; aksi hâlde Streamlit aynı
anahtarı iki kez görüp hata verir.

**Gönderim:** `POST /doctor/inceleme`. Yanıt kodlarının karşılıkları:

| Kod | Kullanıcıya ne denir |
|---|---|
| 201 | Başarı mesajı + liste tazelenir (K3) |
| 409 | "Bu vaka başka bir doktor tarafından incelenmiş." + liste tazelenir |
| 404 | "Vaka bulunamadı, liste tazeleniyor." + liste tazelenir |
| 401 | "Oturum süreniz dolmuş, lütfen çıkıp yeniden girin." |
| diğer | Genel hata; ham kod gösterilmez |

409 ve 404 hata değil, yarış durumudur: başka bir doktor önce davranmıştır. Doğru tepki
kullanıcıyı suçlamak değil, listeyi tazelemektir.

## Kapsam dışı

- "Bekleyen Sorular"ın gerçek veriye bağlanması (K10)
- Mevcut hasta ve admin bloklarının fonksiyona çıkarılması (K8) — Gün 22
- Streamlit UI'ın otomatik testi (K12)
- İncelenmiş vakaların geçmişini görüntüleyen ekran — doktor onayladıktan sonra vakayı
  geri göremiyor. Bilinçli: bugünün işi kuyruğu kapatmak. Geçmiş görünümü Gün 23'ün
  ölçüm ihtiyacıyla birlikte tasarlanmalı.
- `st.cache_data` (K4)

## Bitti sayılır

- [ ] Dört test önce kırmızı görüldü, şimdi yeşil; toplam 90
- [ ] Mevcut 86 test hâlâ yeşil
- [ ] `doctor` rolü kendi panelini görüyor, hasta sekmesine düşmüyor
- [ ] `admin` üç sekmeyi de görüyor
- [ ] Tam döngü tarayıcıda çalıştı ve ekran görüntüleri alındı
- [ ] Doktorun değiştirdiği kod ile yapay zekânın önerdiği kod veritabanında ayrı ayrı
      duruyor (SQL kanıtı)
- [ ] Her yeni fonksiyon/blok yanında tek cümlelik Türkçe açıklama var
- [ ] Dal `main`'e birleşti

**Kullanıcıya kalan tek adım:** mikrofonla ses girişinin gerçek tarayıcıda denenmesi
(Gün 16'dan kalan borç). Gerçek mikrofon ve insan sesi gerektirdiği için otomatikleştirilemez;
`st.audio_input` güvenli bağlam ister, bu yüzden `127.0.0.1` yerine `localhost` kullanılmalı.
