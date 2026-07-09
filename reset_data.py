"""
reset_data.py — verwijdert alle sessie-data uit de database.
Accounts, instellingen en tenant-configuratie blijven behouden.

Uitvoeren op de server:
    python reset_data.py
"""
from infrastructure.db.database import SessionLocal
from infrastructure.db.db_models import DbSession, DbMessage, DbFlowEvent, DbPriceCalculation

db = SessionLocal()
try:
    deleted = db.query(DbSession).delete()
    db.commit()
    print(f"Reset geslaagd: {deleted} sessies verwijderd.")
    print("Berichten, events en berekeningen zijn automatisch meeverwijderd.")
except Exception as e:
    db.rollback()
    print(f"Fout: {e}")
finally:
    db.close()
