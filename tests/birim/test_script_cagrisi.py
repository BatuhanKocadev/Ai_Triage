"""Gün 27 kurulum provasının bulduğu hatayı kilitler."""
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
    """Repo kökünden `-m` ile çağrıldığında `app` bulunmalı."""
    sonuc = subprocess.run(
        [sys.executable, "-c", f"import scripts.{ad}"],
        cwd=KOK,
        capture_output=True,
        text=True,
    )
    assert sonuc.returncode == 0, sonuc.stderr[-400:]


@pytest.mark.parametrize("ad", SCRIPTLER)
def test_script_import_edilince_yan_etki_uretmez(ad):
    """Import, hiçbir şey yazdırmamalı ve global durumu değiştirmemeli."""
    sonuc = subprocess.run(
        [sys.executable, "-c", f"import scripts.{ad}; print('SESSIZ')"],
        cwd=KOK,
        capture_output=True,
        text=True,
    )
    assert sonuc.returncode == 0, sonuc.stderr[-400:]
    assert sonuc.stdout.strip() == "SESSIZ", f"import ciktisi: {sonuc.stdout!r}"
