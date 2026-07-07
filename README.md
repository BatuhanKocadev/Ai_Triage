# AI Triage (Yapay Zeka Destekli Triage Uygulaması)

Bu proje, sağlık süreçlerini optimize etmek amacıyla geliştirilen, yapay zeka destekli bir ses tabanlı tıbbi triage (önceliklendirme) prototipidir. Kullanıcılardan alınan ses verilerini metne dökerek aciliyet analizi ve yönlendirme yapmayı hedefler.

## 📂 Proje Yapısı

Proje, modüler ve sürdürülebilir bir mimari sağlamak amacıyla aşağıdaki klasör yapısına uygun olarak geliştirilmektedir:

```text
app/
│
├── api/          # API uç noktaları (Route tanımlamaları)
├── services/     # OpenAI, FastAPI ve iş mantığı (business logic) servisleri
├── models/       # Veritabanı modelleri (ORM)
├── schemas/      # Pydantic veri doğrulama şemaları
├── utils/        # Yardımcı fonksiyonlar ve araçlar
├── config/       # Çevresel değişkenler ve genel konfigürasyonlar
├── tests/        # Birim (Unit) ve entegrasyon testleri
└── main.py       # Uygulamanın ana giriş noktası