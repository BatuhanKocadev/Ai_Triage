"""Başlangıç kullanıcılarını oluşturur.

Kullanım (proje kökünden):
    .venv\\Scripts\\python.exe -m scripts.seed_users

Tekrar çalıştırılabilir: var olan kullanıcının rolü ve parolası listedeki
değerlerle senkronize edilir (idempotent seed). Canlı `ai_triage` veritabanında
bu üç hesabın rol/parolasını bilinçli olarak yeniden yazar.
"""

import sys

from app.db.database import SessionLocal
from app.models.user import User
from app.services.auth_service import hash_password, verify_password

BASLANGIC_KULLANICILARI = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "doctor", "password": "doctor123", "role": "doctor"},
    # "doctor" artık ayrı bir rol olduğu için /ai/analiz'e girebilen bir hesap
    # kalmıyordu; hasta başvurusu akışı bu hesapla denenir.
    {"username": "hasta", "password": "hasta123", "role": "user"},
]


def main() -> None:
    db = SessionLocal()
    try:
        for veri in BASLANGIC_KULLANICILARI:
            mevcut = db.query(User).filter(User.username == veri["username"]).first()
            if mevcut:
                degisiklikler: list[str] = []
                # Rol listedekinden farklıysa düzeltilir: "doctor" hesabı Gün 17
                # öncesinde "user" rolüyle yazılmıştı.
                if mevcut.role != veri["role"]:
                    eski_rol = mevcut.role
                    mevcut.role = veri["role"]
                    degisiklikler.append(f"rol {eski_rol} -> {veri['role']}")
                # Parola listedekinden farklıysa düzeltilir — aksi hâlde seed
                # "atlandı" derken giriş bilinmeyen bir hash'le kırılır kalır.
                if not verify_password(veri["password"], mevcut.hashed_password):
                    mevcut.hashed_password = hash_password(veri["password"])
                    degisiklikler.append("parola senkron")
                if degisiklikler:
                    print(
                        f"  güncellendi: {veri['username']} ({', '.join(degisiklikler)})"
                    )
                else:
                    print(
                        f"  atlandı    : {veri['username']} "
                        f"(zaten var, rol={mevcut.role}, parola uyumlu)"
                    )
                continue

            db.add(User(
                username=veri["username"],
                hashed_password=hash_password(veri["password"]),
                role=veri["role"],
            ))
            print(f"  eklendi    : {veri['username']} (rol={veri['role']})")

        db.commit()

        print("\nVeritabanındaki kullanıcılar:")
        for kullanici in db.query(User).order_by(User.id).all():
            print(f"  #{kullanici.id}  {kullanici.username:10} {kullanici.role}")
    finally:
        db.close()


def _konsolu_utf8_yap() -> None:
    """Windows konsolunda Türkçe çıktıyı düzeltir; yalnızca script olarak koşarken.

    Eskiden bu, modül düzeyinde `sys.stdout`'u değiştiriyordu — yani dosyayı
    IMPORT ETMEK global çıktı akışını bozuyordu ve script pytest altında hiç
    test edilemiyordu (yakalanmış akış kapanıyor). Import'un yan etkisi olmaz.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass


if __name__ == "__main__":
    _konsolu_utf8_yap()
    main()
