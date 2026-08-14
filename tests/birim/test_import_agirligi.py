"""`app.main` import edildiğinde ağır kütüphanelerin YÜKLENMEDİĞİNİ dondurur."""

import json
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent.parent

# CI ortam boyutunu ve `app.main` açılışının ~25 saniyesini belirleyen kütüphaneler.
# `transformers` listede çünkü lazy bir `__init__` kullanıyor: modül düzeyinde bir
AGIR_MODULLER = [
    "torch",
    "transformers",
    "sentence_transformers",
    "faster_whisper",
    "chromadb",
    # `langchain_text_splitters` LISTEDE OLMAK ZORUNDA ve sebebi ince: kendisi
    # hafif ama `__init__.py`'si bir `sentence_transformers` shim'i tasiyor ve o
    "langchain_text_splitters",
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
