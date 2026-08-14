"""Yardımcı script'ler paketi.

`__init__.py` bilerek var: script'ler `python -m scripts.<ad>` biçiminde
çağrılıyor. Dosya yolu vererek (`python scripts/seed_users.py`) çağrıldığında
`sys.path[0]` repo kökü değil `scripts/` klasörü oluyor ve `app` import'u
`ModuleNotFoundError` ile patlıyor — bu, 14 Ağustos 2026 kurulum provasında
temiz klonda gerçekten yaşandı.

Alternatif çözüm her script'in başına `sys.path` yaması koymaktı; Gün 23'te
ölçüm sürücüsü için aynı seçim yapılmış ve elle `sys.path` düzenlemek
reddedilmişti. Aynı karar burada da geçerli: tutarlı olan modül çağrısı.
"""
