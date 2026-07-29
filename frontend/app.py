import streamlit as st
import requests
import io
import os
from datetime import datetime

# Docker network için dinamik backend URL'i alınır
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

API_LOGIN_URL = f"{BACKEND_URL}/auth/login"
API_ME_URL = f"{BACKEND_URL}/auth/me"
API_ANALYSIS_URL = f"{BACKEND_URL}/ai/analiz"
API_UPLOAD_URL = f"{BACKEND_URL}/document/upload"

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

if st.session_state.access_token is None:
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
                st.error(f"Bağlantı hatası: {str(e)}")
else:
    st.title("🏥 AI Triage System")
    
    with st.sidebar:
        st.write(f"Hoş geldin, **{st.session_state.user_role.upper()}**")
        if st.button("Çıkış Yap"):
            st.session_state.access_token = None
            st.session_state.user_role = None
            st.rerun()
            
    auth_headers = {"Authorization": f"Bearer {st.session_state.access_token}"}

    if st.session_state.user_role == "admin":
        tab_chat, tab_admin = st.tabs(["Kullanıcı Sohbet Ekranı", "Yönetici Paneli"])
        chat_container = tab_chat
        admin_container = tab_admin
    else:
        tab_chat, = st.tabs(["Kullanıcı Sohbet Ekranı"])
        chat_container = tab_chat
        admin_container = None

    with chat_container:
        with st.sidebar:
            st.header("Patient Information")
            age = st.number_input("Age", min_value=0, max_value=120, value=30)
            gender = st.selectbox("Gender", ["Erkek", "Kadın", "Diğer"])
            fever = st.number_input("Fever (°C)", min_value=30.0, max_value=45.0, value=36.5, step=0.1)
            pulse = st.number_input("Pulse (bpm)", min_value=30, max_value=250, value=80)
            chronic_disease = st.text_input("Chronic Diseases (Optional)")
            source_document = st.text_input("Source Document Filter (Optional)")

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
                "source_document": source_document if source_document else None
            }

            with st.chat_message("assistant"):
                with st.spinner("AI analiz ediyor..."):
                    try:
                        analysis_response = requests.post(API_ANALYSIS_URL, json=payload, headers=auth_headers)
                        if analysis_response.status_code == 200:
                            data = analysis_response.json()
                            
                            response_text = f"**Triyaj Kodu:** {data['triage_code']}\n\n"
                            response_text += f"**Yönlendirilecek Birim:** {data['department']}\n\n"
                            response_text += f"**Yapay Zeka Notu:** {data['ai_note']}"
                            
                            st.markdown(response_text)
                            
                            sources = data.get("sources", [])
                            if sources:
                                with st.expander("Kaynak Dokümanlar"):
                                    for source in sources:
                                        st.info(source)
                                        
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
            st.header("Bekleyen Sorular (geçici — Gün 19'da gerçek veriye bağlanacak)")
            
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