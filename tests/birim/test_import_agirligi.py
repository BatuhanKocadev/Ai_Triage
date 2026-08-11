"""`app.main` import edildiğinde ağır kütüphanelerin YÜKLENMEDİĞİNİ dondurur.

Bu testin var oluş sebebi ölçüldü: tembelleştirmeden önce `app.main` import'u
**28,5 saniye** sürüyor ve torch, transformers, sentence_transformers, chromadb,
faster_whisper dahil **5215 modül** yüklüyordu; sonrasında 1,85 saniye ve 1077
modül. Ayrıca bu kütüphaneler CI ortamını büyütüyordu: minimal listeyle kurulan
ortam **498 MB**, tam listeyle kurulan geliştirme ortamı **1694 MB** — torch tek
başına 497 MB. (Kurulum SÜRESİ hiç ölçülmedi, o yüzden iddia edilmiyor.)

Test olmadan, birinin `rag_service`'e modül düzeyinde bir `import torch` geri
koyması hiçbir şeyi kırmaz ve CI sessizce yavaşlar — yol haritasının önceden
uyardığı yere geri dönülür.

Alt süreçte koşuyor (tasarım K10): pytest oturumunun kendi içinde `sys.modules`
sorulamaz, çünkü başka testler `torch`'u zaten yüklemiş olur.
"""

import json
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent.parent

# CI ortam boyutunu ve `app.main` açılışının ~25 saniyesini belirleyen kütüphaneler.
# `transformers` listede çünkü lazy bir `__init__` kullanıyor: modül düzeyinde bir
# `from transformers import ...` bugün fark edilmeden eklenebilir ve muhafız yeşil
# kalırdı. Liste bir dize eklemekle genişler; genişletirken aşağıdaki `%` biçimini
# de demet olarak bıraktığımıza dikkat edin.
AGIR_MODULLER = [
    "torch",
    "transformers",
    "sentence_transformers",
    "faster_whisper",
    "chromadb",
]

# Alt süreçte koşacak betik: app.main'i import eder ve hangi ağır modüllerin
# yüklendiğini JSON olarak basar.
BETIK = """
import json
import os
import sys

os.environ.setdefault(
    "DATABASE_URL", "postgresql://triage:triage@localhost:5432/ai_triage_test"
)
os.environ.setdefault("JWT_SECRET_KEY", "import-agirligi-testi")

import app.main  # noqa: F401

print(json.dumps([m for m in %s if m in sys.modules]))
"""


def test_app_import_agir_kutuphaneleri_cekmiyor():
    sonuc = subprocess.run(
        # Demet olarak veriliyor: `BETIK % AGIR_MODULLER` yalnızca bu ad bir
        # LİSTE olduğu sürece çalışır, demete çevrilirse TypeError verir.
        [sys.executable, "-c", BETIK % (AGIR_MODULLER,)],
        capture_output=True,
        text=True,
        cwd=str(KOK),
    )

    assert sonuc.returncode == 0, f"alt süreç patladı:\n{sonuc.stderr}"
    yuklenen = json.loads(sonuc.stdout.strip().splitlines()[-1])
    assert yuklenen == [], (
        f"app.main şu ağır kütüphaneleri import zinciriyle çekiyor: {yuklenen}. "
        "Modül düzeyinde import edilmiş olabilirler; fonksiyon içine taşıyın."
    )
