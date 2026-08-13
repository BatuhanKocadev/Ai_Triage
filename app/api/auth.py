from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserInfo
from app.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SAHTE_PAROLA_HASH,
    create_access_token,
    get_current_user,
    get_user,
    verify_password,
)
from app.utils.hiz_sinirlayici import giris_ip_sinirlayici, giris_sinirlayici, hiz_siniri

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


def _giris_hiz_anahtari(kullanici_adi: str) -> str:
    """Hız sınırı anahtarını normalize eder; "yok", "YOK" ve " yok " aynı kovaya düşer.

    Ham kullanıcı adı anahtar olsaydı saldırgan yalnızca yazımı değiştirerek
    sınırı istediği kadar katlardı. Sayaç anahtarı ile arama aynı strip'i
    paylaşır; casefold yalnızca kovada (kullanıcı adları büyük/küçük duyarlı).
    """
    return kullanici_adi.strip().casefold()


# Parola deneme saldırısına karşı İKİ KATMANLI sınır (Gün 21). İkisi de geçilmek
# zorunda; biri diğerinin yerine geçmiyor:
#   1) Aşağıdaki `dependencies` — IP başına toplam HACİM (`rate_limit_giris_ip`).
#      Uç gövdesinden önce çalışır. Bu katman olmadan saldırgan her istekte farklı
#      bir kullanıcı adı deneyerek (parola serpme, kullanıcı adı numaralandırma)
#      hiçbir kovayı doldurmadan sınırsız hızda vurabilirdi.
#   2) Gövdedeki kontrol — KULLANICI ADI başına ve yalnızca BAŞARISIZ denemeler
#      (`rate_limit_giris`). Sayaç IP'ye bağlansaydı, Streamlit backend'i sunucu
#      tarafından çağırdığı için tüm girişler tek IP'den gelir ve bir hemşirenin
#      üç kez parolasını yanlış girmesi tüm sistemi kilitlerdi.
# `X-Forwarded-For` hiç okunmuyor — sahte başlıkla sınır aşılabildiği için o
# başlığa güvenmemek bilinçli bir tercih.
@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(hiz_siniri(giris_ip_sinirlayici))],
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    kullanici_adi = form_data.username.strip()
    hiz_anahtari = _giris_hiz_anahtari(kullanici_adi)
    if not giris_sinirlayici.izin_var_mi(hiz_anahtari):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla istek. Lütfen biraz bekleyin.",
            headers={"Retry-After": str(giris_sinirlayici.pencere_sn)},
        )

    user = get_user(db, kullanici_adi)
    # Zamanlama oracle'ı: kullanıcı yokken bcrypt atlanırsa yanıt süresi geçerli
    # adları sızdırır. Sahte hash her başarısız yolda aynı maliyeti üretir.
    parola_hash = user.hashed_password if user is not None else SAHTE_PAROLA_HASH
    parola_dogru = verify_password(form_data.password, parola_hash)
    if user is None or not parola_dogru:
        # Yalnızca başarısızlıkta sayılıyor: KULLANICI ADI kovasında doğru
        # parolayla giren kullanıcı kota tüketmiyor, yani kendi hesabını
        # kilitlemesi mümkün değil. Bu, UÇ seviyesinde "meşru kullanım sınıra
        # hiç yaklaşmaz" demek DEĞİLDİR — yukarıdaki IP katmanı başarılı
        # girişleri de sayıyor ve o kovayı tüm klinik paylaşıyor.
        giris_sinirlayici.istegi_kaydet(hiz_anahtari)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserInfo)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """Giriş yapmış kullanıcının bilgisi.

    Arayüz rolü kullanıcı adından tahmin etmek yerine buradan öğrenir.
    """
    return current_user