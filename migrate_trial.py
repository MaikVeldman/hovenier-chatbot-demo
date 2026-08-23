"""
migrate_trial.py — eenmalig uitvoeren: voegt trial-proefperiode kolommen toe aan tenants.

Voegt toe aan de tenants-tabel:
  - trial_eindigt_op              (TIMESTAMP, nullable)
  - is_betalend                   (BOOLEAN, default False)
  - trial_herinnering_verzonden   (BOOLEAN, default False)

Bestaande tenants met actief=True worden gemarkeerd als is_betalend=True
("gegrandfathered"), zodat ze niet per ongeluk als verlopen trial worden
gedeactiveerd door scripts/check_trials.py.

Gebruik:
  python migrate_trial.py
  DATABASE_URL=postgresql://... python migrate_trial.py   (op de server)

Verwijder dit bestand na gebruik (eenmalige migratie, zoals migrate_fase2.py/migrate_fase4.py).
"""
from __future__ import annotations

from sqlalchemy import text
from infrastructure.db.database import engine

ALTERS = [
    ("trial_eindigt_op",
     "ALTER TABLE tenants ADD COLUMN trial_eindigt_op TIMESTAMP"),
    ("is_betalend",
     "ALTER TABLE tenants ADD COLUMN is_betalend BOOLEAN NOT NULL DEFAULT FALSE"),
    ("trial_herinnering_verzonden",
     "ALTER TABLE tenants ADD COLUMN trial_herinnering_verzonden BOOLEAN NOT NULL DEFAULT FALSE"),
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

    # Bestaande actieve tenants zijn handmatig gevetted door de superadmin
    # (het oude activatie-systeem) -> als betalend beschouwen.
    try:
        result = conn.execute(text("UPDATE tenants SET is_betalend = TRUE WHERE actief = TRUE"))
        conn.commit()
        print(f"OK: {result.rowcount} bestaande actieve tenant(s) gemarkeerd als betalend.")
    except Exception as exc:
        print(f"Fout bij backfill is_betalend: {exc}")

print("\nMigratie klaar. Verwijder dit bestand nu uit de repo (git rm migrate_trial.py).")
