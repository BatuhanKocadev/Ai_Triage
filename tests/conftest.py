"""Tüm testlerin gördüğü ortak yapılandırma ve fixture'lar."""

# DİKKAT: Bu blok her `app` import'undan ÖNCE gelmek zorunda.
# app/db/database.py import edilir edilmez create_engine(settings.database_url)
# çalışıyor; ortam burada ayarlanmazsa testler gerçek `ai_triage` veritabanına bağlanır.
import os

os.environ.setdefault("DATABASE_URL", "postgresql://triage:triage@localhost:5432/ai_triage_test")
os.environ.setdefault("JWT_SECRET_KEY", "test-anahtari-sadece-testler-icin")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")

import pytest  # noqa: E402
