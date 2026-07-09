"""
migrate_fase2.py — eenmalig uitvoeren voor de multi-tenant migratie.

Wat dit doet:
  1. Nieuwe tabellen aanmaken (tenants, users, tenant_configs)
  2. Kolom tenant_id toevoegen aan bestaande sessions-tabel
  3. Veldman Hoveniers aanmaken als eerste tenant (id=1)
  4. Alle bestaande sessies koppelen aan tenant 1
  5. TenantConfig aanmaken vanuit huidige bedrijf.py + pricing.py
  6. Eerste gebruiker aanmaken (superadmin)

Gebruik:
  python migrate_fase2.py
  python migrate_fase2.py --admin-email jouw@email.nl --admin-wachtwoord geheim
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from infrastructure.db.database import engine, Base, SessionLocal
from infrastructure.db import db_models  # noqa: registreert alle modellen


# ============================================================
# Prijzen uit de huidige pricing.py
# ============================================================
try:
    from core.pricing.pricing import PRIJZEN
    _prijzen = {k: list(v) for k, v in PRIJZEN.items()}
except Exception as e:
    print(f"[WARN] pricing.py niet geladen: {e}")
    _prijzen = {}

# Bedrijfsinfo uit de huidige bedrijf.py
try:
    from bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON
except Exception:
    BEDRIJFSNAAM     = "Veldman Hoveniers"
    REGIO            = "regio Balkbrug (binnen 30 km)"
    CONTACT_EMAIL    = "info@veldmanhoveniers.nl"
    CONTACT_TELEFOON = "06-18906921"


def run(admin_email: str, admin_wachtwoord: str) -> None:

    # ── Stap 1: nieuwe tabellen aanmaken ──────────────────────
    print("Stap 1: nieuwe tabellen aanmaken...")
    Base.metadata.create_all(bind=engine)
    print("  OK:", list(Base.metadata.tables.keys()))

    # ── Stap 2: tenant_id kolom toevoegen aan sessions ────────
    print("Stap 2: tenant_id kolom toevoegen aan sessions...")
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE sessions ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)"
            ))
            conn.commit()
            print("  OK: kolom toegevoegd")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  OK: kolom bestond al")
            else:
                raise

    with SessionLocal() as db:

        # ── Stap 3: Veldman als eerste tenant ─────────────────
        print("Stap 3: Veldman Hoveniers aanmaken als tenant...")
        tenant = db.query(models.DbTenant).filter_by(slug="veldman-hoveniers").first()
        if not tenant:
            tenant = models.DbTenant(
                slug="veldman-hoveniers",
                naam=BEDRIJFSNAAM,
                actief=True,
            )
            db.add(tenant)
            db.flush()
            print(f"  OK: tenant aangemaakt (id={tenant.id})")
        else:
            print(f"  OK: tenant bestond al (id={tenant.id})")

        # ── Stap 4: bestaande sessies koppelen ────────────────
        print("Stap 4: bestaande sessies koppelen aan tenant...")
        bijgewerkt = (
            db.query(models.DbSession)
            .filter(models.DbSession.tenant_id == None)  # noqa: E711
            .update({"tenant_id": tenant.id})
        )
        print(f"  OK: {bijgewerkt} sessies bijgewerkt")

        # ── Stap 5: TenantConfig aanmaken ─────────────────────
        print("Stap 5: TenantConfig aanmaken...")
        config = db.query(models.DbTenantConfig).filter_by(tenant_id=tenant.id).first()
        if not config:
            config = models.DbTenantConfig(
                tenant_id=tenant.id,
                bedrijfsnaam=BEDRIJFSNAAM,
                regio=REGIO,
                contact_email=CONTACT_EMAIL,
                contact_telefoon=CONTACT_TELEFOON,
                primaire_kleur="#5c6b1e",
                prijzen=_prijzen,
            )
            db.add(config)
            print("  OK: config aangemaakt")
        else:
            print("  OK: config bestond al")

        # ── Stap 6: eerste gebruiker aanmaken ─────────────────
        print("Stap 6: admin gebruiker aanmaken...")
        user = db.query(models.DbUser).filter_by(email=admin_email).first()
        if not user:
            user = models.DbUser(
                tenant_id=tenant.id,
                email=admin_email,
                wachtwoord_hash=generate_password_hash(admin_wachtwoord),
                is_superadmin=True,
            )
            db.add(user)
            print(f"  OK: gebruiker aangemaakt ({admin_email})")
        else:
            print(f"  OK: gebruiker bestond al ({admin_email})")

        db.commit()

    print("\nMigratie klaar.")
    print(f"  Tenant:     {BEDRIJFSNAAM} (slug: veldman-hoveniers)")
    print(f"  Admin login: {admin_email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fase 2 migratie")
    parser.add_argument("--admin-email",      default="info@veldmanhoveniers.nl")
    parser.add_argument("--admin-wachtwoord", default=None)
    args = parser.parse_args()

    if not args.admin_wachtwoord:
        import getpass
        args.admin_wachtwoord = getpass.getpass("Wachtwoord voor admin gebruiker: ")

    if len(args.admin_wachtwoord) < 8:
        print("Fout: wachtwoord moet minimaal 8 tekens zijn.")
        sys.exit(1)

    run(args.admin_email, args.admin_wachtwoord)
