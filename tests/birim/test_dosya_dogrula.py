"""dosyayi_dogrula'nın yeşil yolunu ve kenar senaryolarını uç üzerinden değil,
doğrudan fonksiyon çağrısıyla test eder (hızlı olsun).

tests/api/test_guvenlik.py yalnızca ret senaryolarını (ve /document/upload
üzerinden yalnızca .txt'yi) kanıtlıyor; gerçek .pdf/.docx hiç yüklenmiyor.
IMZALAR sözlüğünde bir yazım hatası (ör. b"%PDFX") olsa paket yine de yeşil
kalırdı — bu dosya tam da o boşluğu kapatıyor.
"""

import io
import zipfile

import pytest
from fastapi import HTTPException

from app.config.config import settings
from app.utils.dosya_dogrula import dosyayi_dogrula


def test_gecerli_pdf_kabul_edilir():
    uzanti = dosyayi_dogrula("rapor.pdf", b"%PDF-1.7 gecerli pdf icerigi")
    assert uzanti == "pdf"


def test_gecerli_docx_kabul_edilir():
    # Yalnızca PK imzası yetmez; gerçek DOCX Content_Types taşıyan ZIP olmalı.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        zf.writestr("word/document.xml", "<w:document/>")
    uzanti = dosyayi_dogrula("rapor.docx", buf.getvalue())
    assert uzanti == "docx"


def test_duz_zip_docx_diye_reddedilir():
    # Herhangi bir ZIP PK ile başlar; Office Open XML değilse reddedilmeli.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "bu bir docx degil")
    with pytest.raises(HTTPException) as exc_info:
        dosyayi_dogrula("sahte.docx", buf.getvalue())
    assert exc_info.value.status_code == 400


def test_bozuk_zip_docx_reddedilir():
    # PK imzası var ama ZipFile açılamaz → BadZipFile dalı.
    with pytest.raises(HTTPException) as exc_info:
        dosyayi_dogrula("bozuk.docx", b"PK\x03\x04" + b"\x00" * 20)
    assert exc_info.value.status_code == 400


def test_asiri_buyuk_dosya_reddedilir():
    asiri = b"a" * (settings.max_upload_mb * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as exc_info:
        dosyayi_dogrula("buyuk.txt", asiri)
    assert exc_info.value.status_code == 413


def test_gecersiz_utf8_txt_reddedilir():
    with pytest.raises(HTTPException) as exc_info:
        dosyayi_dogrula("bozuk.txt", b"\xff\xfe gecersiz")
    assert exc_info.value.status_code == 400


def test_dosya_adi_yoksa_reddedilir():
    with pytest.raises(HTTPException) as exc_info:
        dosyayi_dogrula(None, b"metin")  # type: ignore[arg-type]
    assert exc_info.value.status_code == 400


def test_gecerli_txt_kabul_edilir():
    uzanti = dosyayi_dogrula("rapor.txt", "geçerli türkçe metin".encode("utf-8"))
    assert uzanti == "txt"


def test_cift_uzantili_sahte_dosya_reddedilir():
    # Özelliğin var oluş sebebi bu senaryo: saldırgan çift uzantıyla (.exe.pdf)
    # yükleyip son uzantıya güvenilmesini umuyor; içerik imzası yine de yakalar.
    with pytest.raises(HTTPException) as exc_info:
        dosyayi_dogrula("zararli.exe.pdf", b"MZ\x90\x00")
    assert exc_info.value.status_code == 400


def test_buyuk_harfli_uzanti_kabul_edilir():
    uzanti = dosyayi_dogrula("RAPOR.PDF", b"%PDF-1.7 gecerli pdf icerigi")
    assert uzanti == "pdf"


def test_tam_sinirdaki_boyut_kabul_edilir():
    # Sınır dahil (`>` kullanıldığı için `>=` değil): bu, `>` -> `>=`
    # mutasyonunu öldürür.
    tam_sinirda = b"a" * (settings.max_upload_mb * 1024 * 1024)
    uzanti = dosyayi_dogrula("tam_sinir.txt", tam_sinirda)
    assert uzanti == "txt"


def test_imzasi_taninmayan_uzanti_reddedilir(monkeypatch):
    # settings.izinli_uzantilar'a IMZALAR'da karşılığı olmayan bir uzantı
    # (csv) eklenirse, fail-closed tasarım gereği imza kontrolü sessizce
    # atlanmak yerine dosya reddedilmeli.
    monkeypatch.setattr(settings, "izinli_uzantilar", "pdf,docx,txt,csv")
    with pytest.raises(HTTPException) as exc_info:
        dosyayi_dogrula("a.csv", b"kolon1,kolon2\nderger1,deger2")
    assert exc_info.value.status_code == 400
