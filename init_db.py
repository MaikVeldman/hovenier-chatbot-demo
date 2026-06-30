"""
init_db.py — eenmalig uitvoeren om alle tabellen aan te maken.

Lokaal (SQLite):
    python init_db.py

Op de server (PostgreSQL):
    DATABASE_URL=postgresql://chatbot_user:wachtwoord@localhost/chatbot_db python init_db.py
"""
from database import engine, Base
import models  # noqa: F401 — zorgt dat alle modellen geregistreerd zijn

Base.metadata.create_all(bind=engine)
print("Tabellen aangemaakt:", list(Base.metadata.tables.keys()))
