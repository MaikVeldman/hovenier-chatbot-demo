"""
Fase-4 migratie: voegt bekijk_token toe aan contact_submissions.

Gebruik: python migrate_fase4.py
"""
from infrastructure.db.database import engine

SQL = "ALTER TABLE contact_submissions ADD COLUMN bekijk_token VARCHAR(36)"

with engine.connect() as conn:
    try:
        conn.execute(__import__("sqlalchemy").text(SQL))
        conn.commit()
        print("OK: Kolom bekijk_token toegevoegd aan contact_submissions.")
    except Exception as exc:
        msg = str(exc).lower()
        if "duplicate" in msg or "already exists" in msg:
            print("Kolom bekijk_token bestaat al — niets te doen.")
        else:
            print(f"Fout: {exc}")
