import streamlit as st
import requests
import io
import os
import hashlib  # aynı ses kaydının her etkileşimde yeniden transkript edilmesini önlemek için içerik imzası
from datetime import datetime

# Docker network için dinamik backend URL'i alınır
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

API_LOGIN_URL = f"{BACKEND_URL}/auth/login"
API_ME_URL = f"{BACKEND_URL}/auth/me"
API_ANALYSIS_URL = f"{BACKEND_URL}/ai/analiz"
API_UPLOAD_URL = f"{BACKEND_URL}/document/upload"
# Ses kaydını metne çeviren ucun adresi (sesli giriş sekmesi bunu çağırır).
API_TRANSKRIPT_URL = f"{BACKEND_URL}/speech/transkript"

st.set_page_config(page_title="AI Triage System", page_icon="🏥", layout="wide")

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_questions" not in st.session_state:
    st.session_state.pending_questions = [
        {"id": "S1", "asker": "Dr. Berkay", "date": "2026-07-16", "question": "Yeni varyant virüs vakalarında acil servis izolasyon prosedürü güncellendi mi?"},
        {"id": "S2", "asker": "Hemşire Sude", "date": "2026-07-17", "question": "Pediatrik hastalarda nöbet durumunda kullanılacak alternatif ilaç dozajları nelerdir?"}
    ]

# Sesli giriş akışının durumu: Streamlit her etkileşimde scripti baştan
# çalıştırdığı için transkript ve analiz sonucu session_state'te saklanıyor.
if "ses_kayit_imzasi" not in st.session_state:
    st.session_state.ses_kayit_imzasi = None  # son transkript edilen kaydın MD5 imzası
if "ses_transkript" not in st.session_state:
    st.session_state.ses_transkript = ""  # düzenlenebilir transkript metni (text_area bu anahtara bağlı)
if "ses_transkript_suresi" not in st.session_state:
    st.session_state.ses_transkript_suresi = None  # ses→metin çevriminin kaç saniye sürdüğü
if "ses_analiz_sonucu" not in st.session_state:
    st.session_state.ses_analiz_sonucu = None  # son sesli analiz sonucu (metin düzenlenince ekrandan kaybolmasın)

# Doktor panelinin durumu: Streamlit her etkileşimde scripti baştan çalıştırdığı
# için liste penceresi ve onay sonucu session_state'te saklanıyor.
if "doktor_liste_limiti" not in st.session_state:
    st.session_state.doktor_liste_limiti = 20  # "Daha fazla göster" bunu 20'şer artırır
if "doktor_son_onay" not in st.session_state:
    st.session_state.doktor_son_onay = None  # onay sonrası bir kez gösterilip temizlenir


def istek_at(metot: str, yol: str, jeton: str, **kwargs):
    """Backend'e yetkili istek atar; adres kurma ve başlık ekleme tek yerde toplanır.

    Bağlantı kurulamazsa None döndürür — çağıran taraf kullanıcıya anlaşılır bir
    mesaj gösterir, ham istisna arayüze sızmaz.
    """
    try:
        return requests.request(
            metot,
            f"{BACKEND_URL}{yol}",
            headers={"Authorization": f"Bearer {jeton}"},
            timeout=kwargs.pop("timeout", 30),
            **kwargs,
        )
    except requests.exceptions.RequestException:
        return None


def triyaj_sonucunu_goster(data):
    """Analiz yanıtını (triyaj kodu, birim, not, kaynaklar) ekrana basar;
    yazılı ve sesli akış aynı gösterimi paylaşsın diye fonksiyona alındı."""
    response_text = f"**Triyaj Kodu:** {data['triage_code']}\n\n"
    response_text += f"**Yönlendirilecek Birim:** {data['department']}\n\n"
    response_text += f"**Yapay Zeka Notu:** {data['ai_note']}"

    st.markdown(response_text)

    sources = data.get("sources", [])
    if sources:
        with st.expander("Kaynak Dokümanlar"):
            for source in sources:
                st.info(source)

    return response_text, sources


def hasta_sekmesi(auth_headers):
    """Hastanın yazılı/sesli şikayet girip analiz sonucunu gördüğü sekme.

    Gün 19'da doktor sekmesi eklenirken buraya taşındı: doctor rolünde bu sekme
    hiç oluşturulmadığı için blok koşullu hâle gelmek zorundaydı (tasarım kararı K8).
    Taşıma dışında içeriği değişmedi.
    """
    with st.sidebar:
        st.header("Patient Information")
        age = st.number_input("Age", min_value=0, max_value=120, value=30)
        gender = st.selectbox("Gender", ["Erkek", "Kadın", "Diğer"])
        fever = st.number_input("Fever (°C)", min_value=30.0, max_value=45.0, value=36.5, step=0.1)
        pulse = st.number_input("Pulse (bpm)", min_value=30, max_value=250, value=80)
        chronic_disease = st.text_input("Chronic Diseases (Optional)")
        source_document = st.text_input("Source Document Filter (Optional)")

    # Sohbet ekranı iki sekmeye bölündü: mevcut yazılı akış silinmeden ilk
    # sekmeye taşındı, ikinci sekme mikrofonla sesli giriş (Gün 16).
    tab_yazi, tab_ses = st.tabs(["✍️ Yazarak anlat", "🎤 Konuşarak anlat"])

    with tab_yazi:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "sources" in message and message["sources"]:
                    with st.expander("Kaynak Dokümanlar"):
                        for source in message["sources"]:
                            st.info(source)

        prompt = st.chat_input("Lütfen hastanın şikayetini detaylıca yazın...")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            payload = {
                "patient_age": age,
                "gender": gender,
                "symptom_text": prompt,
                "chronic_disease": chronic_disease if chronic_disease else None,
                "vitals": {
                    "fever": fever,
                    "pulse": pulse
                },
                "source_document": source_document if source_document else None,
                "giris_tipi": "metin"  # yazılı akış giriş tipini veritabanı için açıkça bildiriyor
            }

            with st.chat_message("assistant"):
                with st.spinner("AI analiz ediyor..."):
                    try:
                        analysis_response = requests.post(API_ANALYSIS_URL, json=payload, headers=auth_headers)
                        if analysis_response.status_code == 200:
                            data = analysis_response.json()
                            # Sonuç gösterimi sesli akışla ortak fonksiyondan geliyor.
                            response_text, sources = triyaj_sonucunu_goster(data)
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": response_text,
                                "sources": sources
                            })
                        else:
                            error_text = f"Hata: {analysis_response.status_code}"
                            st.error(error_text)
                            st.session_state.messages.append({"role": "assistant", "content": error_text})
                    except Exception as e:
                        error_text = f"Bağlantı hatası: {str(e)}"
                        st.error(error_text)
                        st.session_state.messages.append({"role": "assistant", "content": error_text})

    with tab_ses:
        st.caption("Kayıt düğmesine basıp şikayetinizi anlatın; tarayıcı mikrofon izni isterse 'İzin ver'i seçin.")
        # Tarayıcıda kayıt düğmesi gösterir, kayıt bitince ses dosyasını döndürür.
        ses_kaydi = st.audio_input("Şikayetinizi anlatın")

        if ses_kaydi is not None:
            kayit_bytes = ses_kaydi.getvalue()
            # İçerik imzası değişmediyse aynı kayıt tekrar transkript edilmez
            # (Streamlit her düğme/metin etkileşiminde scripti baştan çalıştırır).
            kayit_imzasi = hashlib.md5(kayit_bytes).hexdigest()
            if kayit_imzasi != st.session_state.ses_kayit_imzasi:
                with st.spinner("Ses metne çevriliyor..."):
                    try:
                        files = {"file": (ses_kaydi.name or "kayit.wav", kayit_bytes, ses_kaydi.type or "audio/wav")}
                        # Modelin ilk yüklenişi uzun sürebildiği için bekleme payı geniş tutuldu.
                        transkript_response = requests.post(API_TRANSKRIPT_URL, files=files, headers=auth_headers, timeout=600)
                        if transkript_response.status_code == 200:
                            transkript_data = transkript_response.json()
                            st.session_state.ses_kayit_imzasi = kayit_imzasi
                            st.session_state.ses_transkript = transkript_data["transcript"]
                            st.session_state.ses_transkript_suresi = transkript_data["sure_saniye"]
                            st.session_state.ses_analiz_sonucu = None  # yeni kayıt geldi, eski analiz sonucu temizlendi
                        elif transkript_response.status_code == 422:
                            st.error("Ses anlaşılamadı. Lütfen daha net ve biraz daha uzun konuşarak tekrar deneyin.")
                        elif transkript_response.status_code == 401:
                            st.error("Oturum süreniz dolmuş. Lütfen çıkıp yeniden giriş yapın.")
                        else:
                            st.error("Ses işlenemedi. Lütfen tekrar deneyin.")
                    except requests.exceptions.RequestException:
                        st.error("Sunucuya ulaşılamadı. Backend'in çalıştığından emin olup tekrar deneyin.")

        if st.session_state.ses_kayit_imzasi:
            if st.session_state.ses_transkript_suresi is not None:
                st.caption(f"Ses {st.session_state.ses_transkript_suresi} saniyede metne çevrildi.")
            # Transkript doğrudan analize gitmiyor: konuşma tanıma hata yapabilir,
            # kullanıcı yanlış çevrilen kelimeleri göndermeden önce düzeltebilmeli.
            duzeltilmis_metin = st.text_area(
                "Çözümlenen şikayet metni (gerekirse düzeltin)",
                key="ses_transkript",
                height=120,
            )

            if st.button("Analiz Et", type="primary"):
                if len(duzeltilmis_metin.strip()) < 10:
                    # Backend en az 10 karakter istiyor; 422 hatası göstermek
                    # yerine kullanıcıya anlaşılır bir uyarı veriliyor.
                    st.warning("Şikayet metni çok kısa. Lütfen en az bir cümlelik açıklama bırakın.")
                else:
                    payload = {
                        "patient_age": age,
                        "gender": gender,
                        "symptom_text": duzeltilmis_metin,
                        "chronic_disease": chronic_disease if chronic_disease else None,
                        "vitals": {
                            "fever": fever,
                            "pulse": pulse
                        },
                        "source_document": source_document if source_document else None,
                        "giris_tipi": "ses"  # ziyaret veritabanına ses kaynaklı olarak kaydedilsin
                    }
                    with st.spinner("Yapay zekâ analiz ediyor... (yaklaşık 20 saniye)"):
                        try:
                            analysis_response = requests.post(API_ANALYSIS_URL, json=payload, headers=auth_headers, timeout=300)
                            if analysis_response.status_code == 200:
                                st.session_state.ses_analiz_sonucu = analysis_response.json()
                            elif analysis_response.status_code == 401:
                                st.error("Oturum süreniz dolmuş. Lütfen çıkıp yeniden giriş yapın.")
                            else:
                                st.error("Analiz tamamlanamadı. Lütfen kısa bir süre sonra tekrar deneyin.")
                        except requests.exceptions.RequestException:
                            st.error("Sunucuya ulaşılamadı. Backend'in çalıştığından emin olup tekrar deneyin.")

            # Sonuç session_state'ten okunuyor: metin kutusundaki her düzenleme
            # scripti yeniden çalıştırsa da sonuç ekranda kalmaya devam eder.
            if st.session_state.ses_analiz_sonucu:
                triyaj_sonucunu_goster(st.session_state.ses_analiz_sonucu)

    st.markdown("---")
    st.subheader("Yapay Zeka Cevabı Yetersiz mi?")
    with st.form("ask_expert_form"):
        asker_name = st.text_input("Adınız / Ünvanınız")
        expert_question = st.text_area("Yöneticiye / Uzmana Sorulacak Soru")
        if st.form_submit_button("Bekleyen Sorulara Gönder"):
            if asker_name and expert_question:
                new_id = f"S{len(st.session_state.pending_questions) + 1}_{datetime.now().strftime('%S')}"
                new_q = {
                    "id": new_id,
                    "asker": asker_name,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "question": expert_question
                }
                st.session_state.pending_questions.append(new_q)
                st.success("Sorunuz yöneticinin ekranına başarıyla iletildi!")
            else:
                st.warning("Lütfen adınızı ve sorunuzu eksiksiz girin.")


# Triyaj kodunun ekrandaki rengi; expander başlığı HTML kabul etmediği için
# renk emoji ile veriliyor (tasarım kararı K7).
TRIYAJ_ISARETI = {"Kırmızı": "🔴", "Sarı": "🟡", "Yeşil": "🟢", "Belirsiz": "⚪"}

# Doktorun onaylayabileceği kodlar; "Belirsiz" bilerek yok — doktorun işi
# belirsizliği gidermek (backend de 422 ile reddeder).
ONAYLANABILIR_KODLAR = ["Kırmızı", "Sarı", "Yeşil"]

# Vital ölçümlerin Türkçe etiketi ve birimi; panelde ham sözlük yerine bunlar yazılır.
VITAL_ETIKETLERI = {"fever": ("Ateş", "°C"), "pulse": ("Nabız", "/dk")}

# Doktor notunun üst sınırı; backend şeması da aynı sınırı koyuyor (max_length=1000).
DOKTOR_NOTU_SINIRI = 1000


def doktor_sekmesi(jeton: str):
    """Doktorun bekleyen vakaları görüp yapay zekâ önerisini onayladığı panel."""
    st.header("Bekleyen Vakalar")

    # Bir önceki çalıştırmada onay verilmişse mesajı burada gösterip bayrağı
    # HEMEN temizliyoruz; temizlenmezse mesaj her yeniden çizimde tekrar çıkar.
    if st.session_state.doktor_son_onay:
        # Bayrak (seviye, mesaj) taşıyor: yarış durumu bir onay değildir, yeşil
        # banner metni yalanlardı — seviyeye göre yeşil/sarı seçiliyor.
        seviye, mesaj = st.session_state.doktor_son_onay
        if seviye == "basari":
            st.success(mesaj)
        else:
            st.warning(mesaj)
        st.session_state.doktor_son_onay = None

    # Backend limiti 100 ile sınırlıyor (Query(..., le=100)); tavanın üstüne çıkarsak
    # 422 döner ve limit session_state'te takılı kaldığı için panel kalıcı olarak
    # hata ekranında kalırdı. K6'nın büyüyen penceresi tavana kadar aynen korunuyor.
    limit = min(st.session_state.doktor_liste_limiti, 100)
    yanit = istek_at("GET", f"/doctor/bekleyen?limit={limit}&offset=0", jeton)

    if yanit is None:
        st.error("Sunucuya ulaşılamadı. Backend'in çalıştığından emin olup tekrar deneyin.")
        return
    if yanit.status_code == 401:
        st.error("Oturum süreniz dolmuş. Lütfen çıkıp yeniden giriş yapın.")
        return
    if yanit.status_code != 200:
        st.error("Bekleyen vakalar alınamadı. Lütfen kısa bir süre sonra tekrar deneyin.")
        return

    vakalar = yanit.json()
    if not vakalar:
        st.success("Bekleyen vaka yok. Kuyruk temiz.")
        return

    st.caption(f"{len(vakalar)} bekleyen vaka gösteriliyor.")

    for vaka in vakalar:
        _vaka_karti(vaka, jeton)

    # Dönen kayıt sayısı limite eşitse muhtemelen daha fazlası var (tasarım kararı K6).
    if len(vakalar) == limit and limit < 100:
        if st.button("Daha fazla göster"):
            st.session_state.doktor_liste_limiti += 20
            st.rerun()
    elif len(vakalar) == limit:
        # Tavana gelindi: düğme yerine dürüst bir uyarı, çünkü daha fazlasını
        # istemek backend'den 422 alır ve doktora yanlış bir söz vermiş oluruz.
        st.caption("Panelin gösterebileceği en fazla vaka sayısına ulaşıldı; kuyrukta daha fazla vaka olabilir.")


def _vaka_karti(vaka: dict, jeton: str):
    """Tek bir bekleyen vakayı ve onun inceleme formunu çizer."""
    oneri = vaka.get("ai_onerisi") or {}
    ai_kodu = oneri.get("triage_code", "Belirsiz")
    baslik = (
        f"{TRIYAJ_ISARETI.get(ai_kodu, '⚪')} {vaka['patient_age']} yaş, "
        f"{vaka['gender']} — yapay zekâ: {ai_kodu}"
    )

    with st.expander(baslik):
        # Şikayet hastanın serbest metni: markdown olarak yorumlanırsa içindeki
        # '*', '_', '#' gibi karakterler metni sessizce yeniden biçimlendirir.
        # Doktor tam olarak yazılanı görmeli, o yüzden gövde düz metin basılıyor.
        st.markdown("**Şikayet:**")
        st.text(vaka["symptom_text"])
        if vaka.get("chronic_disease"):
            st.markdown(f"**Kronik hastalık:** {vaka['chronic_disease']}")
        if vaka.get("vitals"):
            # Ham Python sözlüğü yerine Türkçe etiketli metin; ölçüm eksikse atlanıyor,
            # tanımadığımız bir ölçüm de kaybolmasın diye ham adıyla yazılıyor.
            parcalar = []
            for anahtar, deger in vaka["vitals"].items():
                if deger is None:
                    continue
                ad, birim = VITAL_ETIKETLERI.get(anahtar, (anahtar, ""))
                parcalar.append(f"{ad} {deger} {birim}".strip())
            if parcalar:
                st.markdown(f"**Vitaller:** {' · '.join(parcalar)}")
        # ISO damgası mikrosaniyeye kadar uzun; doktora okunur tarih gösteriliyor.
        try:
            kayit_zamani = datetime.fromisoformat(vaka["created_at"]).strftime("%d.%m.%Y %H:%M")
        except (TypeError, ValueError):
            kayit_zamani = vaka["created_at"]  # beklenmedik biçim gelirse ham hâliyle
        # Şikayetin sesle mi yazıyla mı geldiği, transkript hatası ihtimalini
        # doktorun bilmesi için gösteriliyor.
        st.caption(f"Giriş kanalı: {vaka['giris_tipi']} · Kayıt: {kayit_zamani}")

        # Yapay zekânın yönlendirdiği birim: doktor bunu değiştiremiyor (onay
        # şemasında karşılığı yok), tam da bu yüzden görmeden onaylamamalı.
        if oneri.get("department"):
            st.markdown(f"**Önerilen birim:** {oneri['department']}")

        if oneri.get("ai_note"):
            st.info(oneri["ai_note"])
        if oneri.get("sources"):
            with st.expander("Kaynak dokümanlar"):
                for kaynak in oneri["sources"]:
                    st.write(kaynak)

        st.markdown("---")

        # Form anahtarları visit_id ile benzersizleştiriliyor; aksi hâlde Streamlit
        # aynı anahtarı iki kez görüp hata verir.
        vid = vaka["visit_id"]
        with st.form(f"inceleme_{vid}"):
            ai_tetkikler = oneri.get("onerilen_tetkikler") or []
            varsayilan_kod = ai_kodu if ai_kodu in ONAYLANABILIR_KODLAR else "Sarı"

            kod = st.radio(
                "Triyaj kodu",
                ONAYLANABILIR_KODLAR,
                index=ONAYLANABILIR_KODLAR.index(varsayilan_kod),
                horizontal=True,
                key=f"kod_{vid}",
            )
            # accept_new_options: doktor yapay zekânın önermediği tetkiki de
            # ekleyebilmeli, yoksa onay ucunun varlık sebebi boşa çıkar (K5).
            tetkikler = st.multiselect(
                "Tetkikler",
                options=ai_tetkikler,
                default=ai_tetkikler,
                accept_new_options=True,
                key=f"tetkik_{vid}",
            )
            # max_chars: backend 1000 karakteri aşan notu 422 ile reddediyor; sınırı
            # tarayıcıda uygulamak, gönderdikten sonra reddedilmekten iyidir.
            not_metni = st.text_area(
                "Doktor notu (opsiyonel)",
                max_chars=DOKTOR_NOTU_SINIRI,
                key=f"not_{vid}",
            )

            if st.form_submit_button("Onayla", type="primary"):
                _onayi_gonder(vid, kod, tetkikler, not_metni, jeton)


def _onayi_gonder(vid: str, kod: str, tetkikler: list, not_metni: str, jeton: str):
    """Onayı backend'e yollar ve sonucuna göre paneli tazeler."""
    yanit = istek_at(
        "POST",
        "/doctor/inceleme",
        jeton,
        json={
            "visit_id": vid,
            "onaylanan_triage_code": kod,
            "onaylanan_tetkikler": tetkikler,
            "doktor_notu": not_metni or None,
        },
    )

    if yanit is None:
        st.error("Sunucuya ulaşılamadı. Onay kaydedilmedi.")
        return

    if yanit.status_code == 201:
        # Mesajı doğrudan basmıyoruz: rerun sonrası kaybolurdu. Bayrağa yazıp
        # listeyi tazeliyoruz, mesaj bir sonraki çizimde gösterilip siliniyor (K3).
        st.session_state.doktor_son_onay = ("basari", f"Vaka onaylandı: {kod}")
        st.rerun()
    elif yanit.status_code == 409:
        # Hata değil, yarış durumu: başka bir doktor önce davranmış. Kullanıcıyı
        # suçlamıyoruz ama "başarı" da demiyoruz — bu yüzden uyarı seviyesi.
        st.session_state.doktor_son_onay = (
            "uyari",
            "Bu vaka başka bir doktor tarafından incelenmiş.",
        )
        st.rerun()
    elif yanit.status_code == 404:
        st.session_state.doktor_son_onay = ("uyari", "Vaka bulunamadı; liste tazelendi.")
        st.rerun()
    elif yanit.status_code == 401:
        st.error("Oturum süreniz dolmuş. Lütfen çıkıp yeniden giriş yapın.")
    elif yanit.status_code == 422:
        # Gövde şemayı geçemedi; en olası sebep notun sınırı aşması. Genel "tekrar
        # deneyin" mesajı burada yanıltıcı olurdu, çünkü aynı içerik hep reddedilir.
        st.error(
            f"Onay gönderilemedi: girdiler geçerli değil. Doktor notu en fazla "
            f"{DOKTOR_NOTU_SINIRI} karakter olabilir."
        )
    else:
        st.error("Onay kaydedilemedi. Lütfen tekrar deneyin.")


# Rol bilgisi de yoksa oturum yarım kalmış demektir (örn. giriş sırasında
# bağlantı koptu); kullanıcıyı tekrar giriş ekranına döndürüyoruz.
if st.session_state.access_token is None or st.session_state.user_role is None:
    st.title("🏥 AI Triage System - Giriş")
    with st.form("login_form"):
        username_input = st.text_input("Kullanıcı Adı")
        password_input = st.text_input("Şifre", type="password")
        submit_button = st.form_submit_button("Giriş Yap")

        if submit_button:
            login_data = {"username": username_input, "password": password_input}
            try:
                response = requests.post(API_LOGIN_URL, data=login_data)
                if response.status_code == 200:
                    token_data = response.json()
                    st.session_state.access_token = token_data["access_token"]
                    # Rol JWT'nin içinde; kullanıcı adından tahmin etmek yerine
                    # gerçek rolü /auth/me'den okuyoruz.
                    me_response = requests.get(
                        API_ME_URL,
                        headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                    )
                    if me_response.status_code == 200:
                        st.session_state.user_role = me_response.json()["role"]
                        st.rerun()
                    else:
                        st.session_state.access_token = None
                        st.error("Kullanıcı bilgisi alınamadı.")
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")
            except Exception as e:
                # Bağlantı yarıda koptuysa token'lı ama rolsüz oturum kalmasın.
                st.session_state.access_token = None
                st.session_state.user_role = None
                st.error(f"Bağlantı hatası: {str(e)}")
else:
    st.title("🏥 AI Triage System")

    with st.sidebar:
        st.write(f"Hoş geldin, **{st.session_state.user_role.upper()}**")
        if st.button("Çıkış Yap"):
            st.session_state.access_token = None
            st.session_state.user_role = None
            # Doktor panelinin durumu oturumdan uzun yaşamamalı: takılı bir liste
            # penceresi ya da gösterilmemiş onay mesajı yeni oturuma sızmasın.
            st.session_state.doktor_liste_limiti = 20
            st.session_state.doktor_son_onay = None
            st.rerun()

    auth_headers = {"Authorization": f"Bearer {st.session_state.access_token}"}

    # Rol -> sekme haritası (tasarım kararı K2): kullanıcıya yalnızca gerçekten
    # yetkisi olan sekmeler gösterilir. Basınca 403 alınacak bir düğme göstermek,
    # arayüzün yetki modeli hakkında yalan söylemesidir.
    rol = st.session_state.user_role
    chat_container = doktor_container = admin_container = None

    if rol == "admin":
        # Admin her üç yetki grubundan da geçer ("admin her şeyi görür").
        chat_container, doktor_container, admin_container = st.tabs(
            ["Kullanıcı Sohbet Ekranı", "Doktor Paneli", "Yönetici Paneli"]
        )
    elif rol == "doctor":
        # Doktor /ai/analiz, /document/upload ve /speech/transkript uçlarının
        # üçünden de 403 alır; ona yalnızca kendi paneli gösterilir.
        doktor_container, = st.tabs(["Doktor Paneli"])
    else:
        chat_container, = st.tabs(["Kullanıcı Sohbet Ekranı"])

    if chat_container is not None:
        with chat_container:
            hasta_sekmesi(auth_headers)

    # Doktor paneli ham jetonu alır: istek_at'in üçüncü parametresi başlık sözlüğü
    # değil jetonun kendisidir, auth_headers geçilirse istek sessizce 401 döner.
    if doktor_container is not None:
        with doktor_container:
            doktor_sekmesi(st.session_state.access_token)

    if admin_container:
        with admin_container:
            st.header("Doküman Yükleme Alanı")
            st.markdown("Sisteme yeni PDF, DOCX veya metin dosyalarını buradan sürükle-bırak yöntemiyle ekleyebilirsiniz.")

            category_input = st.text_input("Doküman Kategorisi (Örn: Protokol, Kılavuz)")
            uploaded_file = st.file_uploader("Dosyayı buraya sürükleyin veya seçin", type=["pdf", "txt", "docx"])

            if st.button("Dokümanı Yükle"):
                if not category_input or not uploaded_file:
                    st.warning("Lütfen hem kategori girin hem de dosya seçin.")
                else:
                    with st.spinner("Dosya yükleniyor ve vektör tabanına işleniyor..."):
                        try:
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                            data = {"category": category_input}

                            upload_response = requests.post(API_UPLOAD_URL, files=files, data=data, headers=auth_headers)

                            if upload_response.status_code == 201:
                                upload_data = upload_response.json()
                                st.success(f"Başarıyla eklendi: {uploaded_file.name} (Toplam {upload_data.get('total_chunks', 0)} parçaya bölündü)")
                            else:
                                st.error(f"Yükleme başarısız: {upload_response.status_code}")
                        except Exception as e:
                            st.error(f"Yükleme sırasında bağlantı hatası: {str(e)}")

            st.markdown("---")
            st.header("Bekleyen Sorular")
            # Bu liste demo amaçlı, bellekte tutulan örnek sorulardır; henüz bir
            # veritabanı tablosuna bağlı değildir. Altındaki "Bilgi Tabanına Ekle"
            # akışı ise gerçektir ve dokümanı ChromaDB'ye yükler.
            st.caption("Örnek veri — sorular henüz kalıcı olarak saklanmıyor.")

            if st.session_state.pending_questions:
                for q in list(st.session_state.pending_questions):
                    with st.expander(f"Tarih: {q['date']} | Soran: {q['asker']}"):
                        st.write(f"**Soru:** {q['question']}")
                        admin_answer = st.text_area("Cevabınız (Kılavuz veya Protokol Detayı)", key=f"ans_{q['id']}")

                        if st.button("Bilgi Tabanına Ekle", key=f"btn_{q['id']}"):
                            if not admin_answer:
                                st.warning("Lütfen bilgi tabanına eklemek için bir cevap yazın.")
                            else:
                                with st.spinner("Soru-Cevap vektör veritabanına ekleniyor..."):
                                    try:
                                        qa_content = f"Soru: {q['question']}\nCevap: {admin_answer}"
                                        qa_bytes = io.BytesIO(qa_content.encode('utf-8'))
                                        file_name = f"qa_{q['id']}_{datetime.now().strftime('%Y%m%d')}.txt"

                                        files = {"file": (file_name, qa_bytes.getvalue(), "text/plain")}
                                        data = {"category": "Soru-Cevap Bilgi Tabanı"}

                                        upload_response = requests.post(API_UPLOAD_URL, files=files, data=data, headers=auth_headers)

                                        if upload_response.status_code == 201:
                                            st.success("Cevap başarıyla bilgi tabanına eklendi!")
                                            st.session_state.pending_questions = [item for item in st.session_state.pending_questions if item["id"] != q["id"]]
                                            st.rerun()
                                        else:
                                            st.error("Bilgi tabanına ekleme başarısız oldu.")
                                    except Exception as e:
                                        st.error(f"Ekleme sırasında hata: {str(e)}")
            else:
                st.success("Tebrikler! Bekleyen soru bulunmuyor.")
