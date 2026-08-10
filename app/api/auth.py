from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserInfo
from app.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
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
    sınırı istediği kadar katlardı. DİKKAT: burası SADECE sayaç anahtarı;
    kullanıcının veritabanında aranma biçimi bilerek değiştirilmiyor
    (boşluk kırpma Gün 22 borcu olarak kayıtlı).
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
    hiz_anahtari = _giris_hiz_anahtari(form_data.username)
    if not giris_sinirlayici.izin_var_mi(hiz_anahtari):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla istek. Lütfen biraz bekleyin.",
        )

    user = get_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Yalnızca başarısızlıkta sayılıyor; doğru parolayla giren kullanıcı kota
        # tüketmiyor, yani meşru kullanım sınıra hiç yaklaşmıyor.
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