"""Gün 27 kurulum provasının bulduğu hatayı kilitler.

Temiz klonda `python scripts/seed_users.py` çağrısı `ModuleNotFoundError: No
module named 'app'` veriyordu: dosya yolu verilerek çağrıldığında `sys.path[0]`
repo kökü değil `scripts/` klasörü oluyor. Hem README hem CLAUDE.md o sırada
yanlış komutu gösteriyordu, yani belge kurulum yapan kişiyi çalışmayan bir
komuta yönlendiriyordu.

Çözüm `scripts/` paketi + `python -m scripts.<ad>`. Bu testler o çözümü bağlar;
`scripts/__init__.py` silinirse ikisi de kırmızıya döner.
"""
import subprocess
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[2]
# `app` import eden, yani yol sorununa duyarlı script'ler.
SCRIPTLER = ["seed_users", "bilgi_tabani_kur", "kalibre_esik"]


def test_scripts_bir_pakettir():
    """`__init__.py` yoksa `-m scripts.<ad>` çağrısı da çalışmaz."""
    assert (KOK / "scripts" / "__init__.py").is_file()


@pytest.mark.parametrize("ad", SCRIPTLER)
def test_script_modul_olarak_import_edilebilir(ad):
    """Repo kökünden `-m` ile çağrıldığında `app` bulunmalı.

    Alt süreçte koşuyor çünkü sınanan şey bu testin değil, **temiz bir
    yorumlayıcının** `sys.path`'i. Aynı süreçte `import` etmek pytest'in
    hâlihazırda ayarladığı yolu ölçerdi ve hatayı hiç göremezdi.

    `import` yeterli: hata modül düzeyindeki `from app...` satırında çıkıyordu.
    `main()` çağrılmıyor — canlı veritabanına yazardı.
    """
    sonuc = subprocess.run(
        [sys.executable, "-c", f"import scripts.{ad}"],
        cwd=KOK,
        capture_output=True,
        text=True,
    )
    assert sonuc.returncode == 0, sonuc.stderr[-400:]


@pytest.mark.parametrize("ad", SCRIPTLER)
def test_script_import_edilince_yan_etki_uretmez(ad):
    """Import, hiçbir şey yazdırmamalı ve global durumu değiştirmemeli.

    `seed_users` eskiden modül düzeyinde `sys.stdout`'u sarmalıyordu; dosyayı
    import etmek global çıktı akışını bozuyor ve script'i pytest altında test
    edilemez kılıyordu (yakalanmış akış kapanıyor).
    """
    sonuc = subprocess.run(
        [sys.executable, "-c", f"import scripts.{ad}; print('SESSIZ')"],
        cwd=KOK,
        capture_output=True,
        text=True,
    )
    assert sonuc.returncode == 0, sonuc.stderr[-400:]
    assert sonuc.stdout.strip() == "SESSIZ", f"import ciktisi: {sonuc.stdout!r}"
