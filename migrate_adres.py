"""
migrate_adres.py — eenmalig uitvoeren: voegt adresvelden toe aan tenant_configs.

Voegt toe aan de tenant_configs-tabel:
  - straat    (VARCHAR(200), nullable)
  - postcode  (VARCHAR(20),  nullable)
  - plaats    (VARCHAR(100), nullable)

(contact_telefoon bestond al vanaf de oorspronkelijke multi-tenant migratie
en hoeft hier niet apart te worden toegevoegd.)

Gebruik:
  python migrate_adres.py
  DATABASE_URL=postgresql://... python migrate_adres.py   (op de server)

Verwijder dit bestand na gebruik (eenmalige migratie, zoals migrate_trial.py).
"""
from __future__ import annotations

from sqlalchemy import text
from infrastructure.db.database import engine

ALTERS = [
    ("straat",   "ALTER TABLE tenant_configs ADD COLUMN straat VARCHAR(200)"),
    ("postcode", "ALTER TABLE tenant_configs ADD COLUMN postcode VARCHAR(20)"),
    ("plaats",   "ALTER TABLE tenant_configs ADD COLUMN plaats VARCHAR(100)"),
]

with engine.connect() as conn:
    for kolom, sql in ALTERS:
        try:
            conn.execute(text(sql))
            conn.commit()
            print(f"OK: kolom {kolom} toegevoegd.")
        except Exception as exc:
            msg = str(exc).lower()
            if "duplicate" in msg or "already exists" in msg:
                print(f"Kolom {kolom} bestaat al — niets te doen.")
            else:
                print(f"Fout bij {kolom}: {exc}")

print("\nMigratie klaar. Verwijder dit bestand nu uit de repo (git rm migrate_adres.py).")
