"""Gün 23 ölçüm sürücüsü."""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

from degerlendirme.olcum import (
    Ozet,
    Senaryo,
    SenaryoHatasi,
    Sonuc,
    kaynak_adlarini_ayikla,
    kok_neden,
    ozet,
    senaryolari_yukle,
    tetkik_ortusmesi,
    wer,
)

BACKEND = "http://localhost:8000"
# Ollama uca değil doğrudan sorulan tek dış servis; `app` import edilmiyor (K5).
OLLAMA = "http://localhost:11434"
MODEL = "qwen2.5:7b-instruct"
BURASI = Path(__file__).resolve().parent
SONUCLAR = BURASI / "sonuclar"
# Ön uçuşun beklediği bilgi tabanı; Gün 20'de kurulan derlemenin boyutu.
BEKLENEN_CHUNK = 49
BEKLENEN_DOSYA = 15
# WER bu eşiğin üstüne çıkarsa sorun tanıma değil, ses-metin eşleşmesidir.
WER_HIZALAMA_ESIGI = 0.6
# Sıfır paydalı oranlarda basılan işaret; "%0.0" yanlış okunurdu (Görev 5, M4).
TANIMSIZ = "n/d"


class OnUcusHatasi(Exception):
    """Ön uçuş kontrolü düştüğünde atılır; koşum hiç başlamaz."""


def _konsolu_utf8_yap() -> None:
    """Windows konsolunda Türkçe çıktının bozulmasını engeller."""
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            # Yeniden yapılandırılamayan bir akışta ölçümü durdurmaya değmez.
            pass


def jeton_al(kullanici: str, parola: str) -> str:
    """OAuth2 password flow ile jeton alır (form-data, JSON değil)."""
    yanit = requests.post(
        f"{BACKEND}/auth/login",
        data={"username": kullanici, "password": parola},
        timeout=15,
    )
    if yanit.status_code != 200:
        raise OnUcusHatasi(
            f"Giriş başarısız ({kullanici}): {yanit.status_code} {yanit.text[:200]}"
        )
    return yanit.json()["access_token"]


def on_ucus() -> tuple[str, str, list[dict]]:
    """Koşum öncesi dört kontrol; biri düşerse hiç başlamayız."""
    try:
        saglik = requests.get(f"{BACKEND}/health/", timeout=10)
    except requests.RequestException as exc:
        raise OnUcusHatasi(f"Backend'e ulaşılamıyor ({BACKEND}): {exc}") from exc
    if saglik.status_code != 200:
        raise OnUcusHatasi(f"/health/ {saglik.status_code} döndü")

    hasta_jetonu = jeton_al("hasta", "hasta123")
    admin_jetonu = jeton_al("admin", "admin123")

    liste = requests.get(
        f"{BACKEND}/document/liste",
        headers={"Authorization": f"Bearer {admin_jetonu}"},
        timeout=30,
    )
    if liste.status_code != 200:
        raise OnUcusHatasi(f"/document/liste {liste.status_code} döndü")
    kayitlar = liste.json()
    toplam_chunk = sum(k["chunk_sayisi"] for k in kayitlar)
    if len(kayitlar) != BEKLENEN_DOSYA or toplam_chunk != BEKLENEN_CHUNK:
        raise OnUcusHatasi(
            f"Bilgi tabanı beklenenden farklı: {len(kayitlar)} dosya / "
            f"{toplam_chunk} chunk (beklenen {BEKLENEN_DOSYA}/{BEKLENEN_CHUNK}). "
            "Doğru derleme yüklüyse bu dosyadaki BEKLENEN_* sabitlerini "
            "ölçülen değerle güncelleyin; değilse "
            "scripts/bilgi_tabani_kur.py ile yeniden kurun."
        )

    # Ollama ayakta mı? `/health/` sabit bir dize döndürüyor ve LLM hakkında
    # HİÇBİR şey kanıtlamıyor — Gün 20'nin dersi tam buydu. Ollama kapalıyken
    try:
        etiketler = requests.get(f"{OLLAMA}/api/tags", timeout=10)
        etiketler.raise_for_status()
    except requests.RequestException as exc:
        raise OnUcusHatasi(
            f"Ollama'ya ulaşılamıyor ({OLLAMA}): {exc}. `ollama serve` çalışıyor mu?"
        ) from exc
    modeller = {m.get("name") for m in etiketler.json().get("models", [])}
    if MODEL not in modeller:
        raise OnUcusHatasi(
            f"Ollama'da {MODEL} yok (bulunanlar: {sorted(modeller)}). "
            f"`ollama pull {MODEL}` ile indirin."
        )

    print(
        f"Ön uçuş tamam: {len(kayitlar)} dosya / {toplam_chunk} chunk, "
        f"Ollama {MODEL} hazır"
    )
    # Dosya kırılımı çağırana veriliyor ve rapora basılıyor: bilgi tabanının
    # hangi sürümüne karşı ölçtüğümüz aksi hâlde hiçbir yerde kayıtlı olmuyor,
    kirilim = sorted(
        ({"kaynak": k["kaynak"], "chunk_sayisi": k["chunk_sayisi"]} for k in kayitlar),
        key=lambda k: k["kaynak"],
    )
    return hasta_jetonu, admin_jetonu, kirilim


def _429_bekleyerek_gonder(gonder, aciklama: str, deneme_sayisi: int = 4):
    """429 alınca artan aralıklarla bekler; sınırı kapatmıyoruz (K10)."""
    bekleme = 20
    son_hata = "tükenen 429 denemesi"
    for deneme in range(deneme_sayisi):
        try:
            yanit = gonder()
        except requests.RequestException as exc:
            # Zaman aşımı/bağlantı kopması tek senaryoyu düşürür, koşumu değil.
            return None, f"{type(exc).__name__}: {exc}"
        if yanit.status_code != 429:
            return yanit, None
        # Son denemeden sonra beklemenin anlamı yok; 160 sn boşa gitmesin.
        if deneme == deneme_sayisi - 1:
            break
        print(f"  429 alındı ({aciklama}), {bekleme} sn bekleniyor…")
        time.sleep(bekleme)
        bekleme *= 2
    return None, son_hata


def senaryoyu_sor(senaryo: Senaryo, jeton: str) -> Sonuc:
    """Tek senaryoyu /ai/analiz'e gönderir ve Sonuc'a çevirir."""
    govde = {
        "patient_age": senaryo.yas,
        "gender": senaryo.cinsiyet,
        "symptom_text": senaryo.sikayet,
        "chronic_disease": senaryo.kronik_hastalik,
        # Kör senaryonun sesi ayrıca transkript ediliyor ama analize giden metin
        # senaryonun yazılı hâli; kanalı "ses" demek olmayan bir yolu iddia ederdi.
        "giris_tipi": "metin",
    }
    if senaryo.vitals:
        govde["vitals"] = senaryo.vitals

    yanit, ag_hatasi = _429_bekleyerek_gonder(
        lambda: requests.post(
            f"{BACKEND}/ai/analiz",
            json=govde,
            headers={"Authorization": f"Bearer {jeton}"},
            timeout=180,
        ),
        senaryo.id,
    )

    if yanit is None:
        print(f"  Ağ hatası ({senaryo.id}): {ag_hatasi}")
        return Sonuc(senaryo_id=senaryo.id, hata=ag_hatasi)
    if yanit.status_code != 200:
        return Sonuc(
            senaryo_id=senaryo.id,
            hata=f"{yanit.status_code}: {yanit.text[:200]}",
        )

    veri = yanit.json()
    visit_id = veri.get("visit_id")
    return Sonuc(
        senaryo_id=senaryo.id,
        cikan_triage_code=veri.get("triage_code"),
        cikan_bolum=veri.get("department"),
        cikan_tetkikler=veri.get("onerilen_tetkikler") or [],
        # ZORUNLU AYIKLAMA: uç `sources`'ı "[Kaynak: dosya] belge" biçiminde
        # döndürüyor. Ham yazılırsa beklenen kaynak hiçbir zaman bulunamaz,
        sources=kaynak_adlarini_ayikla(veri.get("sources") or []),
        # Ziyaret silinmiyor: video demosunun denetim izi buradan bulunacak (K14).
        visit_id=str(visit_id) if visit_id else None,
    )


def sesi_transkript_et(senaryo: Senaryo, jeton: str) -> str | None:
    """Kör senaryonun ses kaydını /speech/transkript'e gönderir."""
    if not senaryo.ses_dosyasi:
        return None
    yol = BURASI / senaryo.ses_dosyasi
    if not yol.exists():
        # Kayıtlar gitignore'da ve yalnızca ana checkout'ta; eksikse WER atlanır,
        # koşum durmaz — triyaj ölçümü sesten bağımsızdır.
        print(f"  Ses dosyası yok, WER atlanıyor: {yol}")
        return None

    icerik = yol.read_bytes()

    yanit, ag_hatasi = _429_bekleyerek_gonder(
        lambda: requests.post(
            f"{BACKEND}/speech/transkript",
            files={"file": (yol.name, icerik, "audio/mp4")},
            headers={"Authorization": f"Bearer {jeton}"},
            timeout=300,
        ),
        f"{senaryo.id} ses",
    )
    if yanit is None:
        # WER'in düşmesi triyaj ölçümünü durdurmaz; senaryo sesli olmasa da ölçülür.
        print(f"  Transkript ağ hatası ({senaryo.id}): {ag_hatasi}")
        return None
    if yanit.status_code != 200:
        print(f"  Transkript hatası ({senaryo.id}): {yanit.status_code}")
        return None
    return yanit.json().get("transcript")


def seti_kosur(senaryolar: list[Senaryo], jeton: str, etiket: str) -> list[Sonuc]:
    """Bir seti baştan sona koşar ve her senaryodan sonra diske yazar (K15)."""
    sonuclar: list[Sonuc] = []
    SONUCLAR.mkdir(parents=True, exist_ok=True)
    ara_dosya = SONUCLAR / f"{date.today().isoformat()}-{etiket}-ham.json"

    for sira, senaryo in enumerate(senaryolar, start=1):
        print(f"[{etiket} {sira}/{len(senaryolar)}] {senaryo.id}")
        sonuc = senaryoyu_sor(senaryo, jeton)
        if senaryo.ses_dosyasi:
            sonuc.transkript = sesi_transkript_et(senaryo, jeton)
        sonuclar.append(sonuc)
        # Kısmi kayıt: 20. senaryoda çöken koşum 19 ölçümü kaybetmesin.
        ara_dosya.write_text(
            json.dumps([s.__dict__ for s in sonuclar], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return sonuclar


def _yuzde(oran: float, payda: int) -> str:
    """Oranı yüzde olarak biçimler; payda sıfırsa 'n/d' basar."""
    return TANIMSIZ if not payda else f"%{oran * 100:.1f}"


def _ondalik(deger: float | None, payda: int) -> str:
    """Ondalık bir ortalamayı biçimler; payda sıfırsa 'n/d' basar."""
    return TANIMSIZ if not payda or deger is None else f"{deger:.2f}"


def _wer_tablosu(senaryolar: list[Senaryo], sonuclar: list[Sonuc]) -> tuple[list, float]:
    """Kör senaryolar için WER; referans metin senaryonun kendi şikayetidir."""
    harita = {s.senaryo_id: s for s in sonuclar}
    satirlar = []
    for senaryo in senaryolar:
        sonuc = harita.get(senaryo.id)
        if not sonuc or not sonuc.transkript:
            continue
        oran = wer(senaryo.sikayet, sonuc.transkript)
        satirlar.append((senaryo.id, oran, sonuc.transkript))
    ortalama = sum(o for _, o, _ in satirlar) / len(satirlar) if satirlar else 0.0
    return satirlar, ortalama


def _ozet_tablosu(o: Ozet) -> list[str]:
    """Bir bloğun manşet sayılarını markdown tablosu olarak üretir."""
    return [
        "| Ölçü | Değer |",
        "|---|---|",
        f"| Ölçülen senaryo (kapsam içi) | {o.toplam} |",
        f"| Doğru triyaj | {o.dogru} |",
        f"| **Genel doğruluk (tüm)** | **{_yuzde(o.dogruluk_tum, o.toplam)}** |",
        f"| **Genel doğruluk (cevaplananlar)** | "
        f"**{_yuzde(o.dogruluk_cevaplananlar, o.cevaplanan)}** |",
        f"| **Kırmızı duyarlılık** | "
        f"**{_yuzde(o.kirmizi_duyarlilik, o.kirmizi_toplam)}** "
        f"({o.kirmizi_yakalanan}/{o.kirmizi_toplam}) |",
        f"| Eşik altı oranı | {_yuzde(o.esik_alti_orani, o.toplam)} ({o.esik_alti}) |",
        f"| Tetkik Jaccard (ort.) | {_ondalik(o.jaccard_ortalama, o.jaccard_sayisi)} "
        f"({o.jaccard_sayisi} senaryodan) |",
        f"| Kök neden A/B/C | {o.kok_neden_dagilimi['A']} / "
        f"{o.kok_neden_dagilimi['B']} / {o.kok_neden_dagilimi['C']} |",
        f"| Şanslı doğru | {o.sansli_dogru} |",
        f"| Ölçülemedi (altyapı) | {o.olculemedi} |",
        f"| Sonucu yazılmamış | {o.sonucsuz} |",
        f"| Kapsam dışı (doğru/toplam) | {o.kapsam_disi_dogru}/{o.kapsam_disi_toplam} |",
    ]


def _kirilim_tablosu(senaryolar: list[Senaryo], sonuclar: list[Sonuc]) -> list[str]:
    """Senaryo kırılımı; beklenen-vs-çıkan tetkikler artefaktı görünür kılsın."""
    satirlar = [
        "| id | Beklenen | Çıkan | Kaynak geldi mi | Kutu | Beklenen tetkikler | Çıkan tetkikler | J |",
        "|---|---|---|---|---|---|---|---|",
    ]
    harita = {s.senaryo_id: s for s in sonuclar}
    for senaryo in senaryolar:
        sonuc = harita.get(senaryo.id)
        if not sonuc:
            continue
        # Ayıklama etkisiz eleman; sürücü bir gün ham yazarsa tablo yine doğru kalsın.
        gelen = kaynak_adlarini_ayikla(sonuc.sources)
        kaynak_geldi = (
            "—"
            if not senaryo.beklenen_kaynak
            else ("evet" if senaryo.beklenen_kaynak in gelen else "HAYIR")
        )
        kutu = kok_neden(senaryo, sonuc) or "doğru"
        # Kapsam dışı senaryoda tetkik PUANLANMIYOR (kok_neden ile aynı kural):
        # cevap vermeyi reddetmiş sistemde derecelendirilecek tetkik yoktur.
        kapsam_disi = senaryo.beklenen_triage_code == "Belirsiz"
        jaccard = (
            "—"
            if kapsam_disi
            else f"{tetkik_ortusmesi(senaryo.beklenen_tetkikler, sonuc.cikan_tetkikler):.2f}"
        )
        satirlar.append(
            f"| {senaryo.id} | {senaryo.beklenen_triage_code} | "
            f"{sonuc.cikan_triage_code or 'HATA'} | {kaynak_geldi} | {kutu} | "
            f"{', '.join(senaryo.beklenen_tetkikler) or '—'} | "
            f"{', '.join(sonuc.cikan_tetkikler) or '—'} | {jaccard} |"
        )
    return satirlar


def rapor_yaz(
    bloklar: list[tuple[str, list[Senaryo], list[Sonuc]]],
    kirilim: list[dict] | None = None,
    etiket: str | None = None,
) -> Path:
    """Markdown raporu ve ham JSON'u sonuclar/ altına yazar."""
    SONUCLAR.mkdir(parents=True, exist_ok=True)
    bugun = date.today().isoformat()
    dosya_kok = f"{bugun}-{etiket}" if etiket else bugun
    md = [f"# Gün 24 değerlendirme sonuçları — {dosya_kok}", ""]
    if etiket:
        md.append(f"Koşum etiketi: `{etiket}`. Ollama belirlenimsizdir; ortalama alınır.")
    else:
        md.append("Tek koşum. Ollama belirlenimsizdir; birden fazla koşum ortalaması gerekir.")
    md.append("")

    ham: dict = {"tarih": bugun, "kosum_etiketi": etiket, "bloklar": {}}

    # Bilgi tabanının parmak izi: bu sayılar HANGİ derlemeye karşı ölçüldü.
    # Derleme değişince retrieval de değişir, yani parmak izi olmayan bir ölçüm
    if kirilim:
        toplam = sum(k["chunk_sayisi"] for k in kirilim)
        md.append("## Ölçülen bilgi tabanı")
        md.append("")
        md.append(f"{len(kirilim)} dosya / {toplam} chunk.")
        md.append("")
        md.append("| Protokol | chunk |")
        md.append("|---|---|")
        for k in kirilim:
            md.append(f"| {k['kaynak']} | {k['chunk_sayisi']} |")
        md.append("")
        ham["bilgi_tabani"] = {"dosya": len(kirilim), "chunk": toplam, "kirilim": kirilim}

    for blok_etiket, senaryolar, sonuclar in bloklar:
        o = ozet(senaryolar, sonuclar)
        md.append(f"## {blok_etiket}")
        md.append("")
        md.append(f"Sette {len(senaryolar)} senaryo var. Aşağıdaki paydalar bunun "
                  "alt kümeleridir; hangi senaryonun hangi kovaya düştüğü "
                  "kırılım tablosunda.")
        md.append("")
        md.extend(_ozet_tablosu(o))
        md.append("")
        # A/B/C hiçbir başka sayıyla denkleştirilemez; not olmadan tablo
        # kendi kendisiyle çelişiyor görünür (Görev 5 incelemesi, M5).
        md.append(
            "> A/B/C dağılımı kapsam içi **ve** kapsam dışı senaryoları kapsar, "
            "oysa \"Ölçülen senaryo\" yalnızca kapsam içini sayar; ayrıca C kutusu "
            "triyaj kodu doğru olan senaryoları içerir. Bu üç sayı doğruluk "
            "sayılarıyla toplanarak denkleştirilemez."
        )
        md.append("")
        # Yarım koşum sessizce tam koşum gibi okunmasın; bu alan asıl soruyu
        # cevaplayan tek alandır (Görev 5 re-review, totoloji notu).
        if o.sonucsuz:
            md.append(
                f"> UYARI: {o.sonucsuz} senaryonun sonucu hiç yazılmamış — bu "
                "koşum YARIM. Aşağıdaki oranlar alt kümede hesaplanmıştır."
            )
            md.append("")

        md.append("### Senaryo kırılımı")
        md.append("")
        md.extend(_kirilim_tablosu(senaryolar, sonuclar))
        md.append("")

        ham["bloklar"][blok_etiket] = {
            "ozet": o.__dict__,
            "sonuclar": [s.__dict__ for s in sonuclar],
        }

    # WER yalnızca ses kaydı olan blokta anlamlı.
    for etiket, senaryolar, sonuclar in bloklar:
        satirlar, ortalama = _wer_tablosu(senaryolar, sonuclar)
        if not satirlar:
            continue
        md.append(f"## Ses tanıma (WER) — {etiket}")
        md.append("")
        md.append("| id | WER | Transkript |")
        md.append("|---|---|---|")
        for sid, oran, metin in satirlar:
            md.append(f"| {sid} | {oran:.3f} | {metin[:80]}… |")
        md.append("")
        md.append(f"**Ortalama WER: {ortalama:.3f}** ({len(satirlar)} kayıt)")
        md.append("")
        if ortalama > WER_HIZALAMA_ESIGI:
            md.append(
                f"> UYARI: ortalama WER {WER_HIZALAMA_ESIGI}'ın üstünde. Bu genellikle "
                "tanıma kalitesini değil, ses dosyalarının yanlış senaryoyla "
                "eşleştirilmiş olduğunu gösterir — eşleşmeyi doğrulayın."
            )
            md.append("")
        # Rakam normalizasyonu yok: kullanıcı sayıları kelimeyle yazdı ("Üç
        # gündür") ama whisper "3" yazabilir. Bu tanıma hatası değil ölçüm
        rakamlilar = [sid for sid, _, metin in satirlar if re.search(r"\d", metin)]
        if rakamlilar:
            md.append(
                f"> NORMALİZASYON ARTEFAKTI: {', '.join(rakamlilar)} "
                "transkriptlerinde rakam var. Referans metinlerde sayılar "
                "kelimeyle yazılmışsa bu fark tanıma hatası değildir ve WER'i "
                "haksız yere şişirir. Sayıyı düzeltmeyin, sınırı raporlayın."
            )
            md.append("")
        md.append(
            "Dürüst sınır: kullanıcı kendi yazdığı metni okudu. Okunan konuşma, "
            "telaşlı bir hastanın konuşmasından kolaydır; bu WER iyimser taraflıdır."
        )
        md.append("")
        ham["bloklar"][etiket]["wer_ortalama"] = ortalama

    md_yolu = SONUCLAR / f"{dosya_kok}.md"
    md_yolu.write_text("\n".join(md), encoding="utf-8")
    (SONUCLAR / f"{dosya_kok}.json").write_text(
        json.dumps(ham, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return md_yolu


def main(argv: list[str] | None = None) -> int:
    """Ön uçuş → iki seti koş → rapor yaz. Ön uçuş düşerse hiçbir şey koşulmaz."""
    import argparse

    parser = argparse.ArgumentParser(description="Gün 23/24 değerlendirme sürücüsü")
    parser.add_argument(
        "--etiket",
        default=None,
        help="Çıktı dosya adına eklenen koşum etiketi (ör. kosum1)",
    )
    args = parser.parse_args(argv)

    _konsolu_utf8_yap()
    try:
        hasta_jetonu, _admin_jetonu, kirilim = on_ucus()
    except OnUcusHatasi as exc:
        print(f"ÖN UÇUŞ DÜŞTÜ: {exc}")
        return 1

    try:
        kor = senaryolari_yukle(BURASI / "kor_senaryolar.json")
        turetilmis = senaryolari_yukle(BURASI / "senaryolar.json")
    except SenaryoHatasi as exc:
        # Ucuz kontrol pahalı olanlardan sonra geliyordu; en azından temiz düşsün.
        print(f"SENARYO DOSYASI BOZUK: {exc}")
        return 1

    kor_sonuclari = seti_kosur(kor, hasta_jetonu, "kor")
    turetilmis_sonuclari = seti_kosur(turetilmis, hasta_jetonu, "turetilmis")

    yol = rapor_yaz(
        [
            ("Kör set", kor, kor_sonuclari),
            ("Türetilmiş set", turetilmis, turetilmis_sonuclari),
        ],
        kirilim,
        etiket=args.etiket,
    )
    print(f"\nRapor yazıldı: {yol}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
