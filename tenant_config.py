# tenant_config.py
"""
Laadt bedrijfsinstellingen per tenant uit de database.
Valt terug op bedrijf.py + pricing.py als er geen DB-config is.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from core.models.tenant import TenantConfig


def laad_tenant(slug: str) -> Optional[TenantConfig]:
    """Laad config voor een tenant-slug uit de database. Geeft None als niet gevonden."""
    try:
        from database import SessionLocal
        from models import DbTenant, DbTenantConfig

        with SessionLocal() as db:
            tenant = db.query(DbTenant).filter_by(slug=slug, actief=True).first()
            if not tenant or not tenant.config:
                return None

            cfg = tenant.config
            prijzen: Dict[str, Tuple[int, int]] = {}
            for k, v in (cfg.prijzen or {}).items():
                if isinstance(v, (list, tuple)) and len(v) == 2:
                    prijzen[k] = (int(v[0]), int(v[1]))

            return TenantConfig(
                slug=slug,
                bedrijfsnaam=cfg.bedrijfsnaam,
                regio=cfg.regio or "",
                contact_email=cfg.contact_email or "",
                contact_telefoon=cfg.contact_telefoon or "",
                begroeting=cfg.begroeting,
                primaire_kleur=cfg.primaire_kleur or "#5c6b1e",
                prijzen=prijzen,
            )
    except Exception as e:
        print(f"[tenant_config] Fout bij laden tenant '{slug}': {e}")
        return None


def laad_tenant_of_default(slug: str) -> TenantConfig:
    """
    Laad config voor slug. Valt terug op bedrijf.py + pricing.py
    als de tenant niet in de database staat (bijv. lokaal zonder DB).
    """
    config = laad_tenant(slug)
    if config:
        return config

    # Fallback voor Veldman / lokale ontwikkeling
    try:
        from bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON
        from pricing import PRIJZEN
        prijzen = {k: tuple(v) for k, v in PRIJZEN.items()}
    except Exception:
        BEDRIJFSNAAM     = "Hoveniersbedrijf"
        REGIO            = ""
        CONTACT_EMAIL    = ""
        CONTACT_TELEFOON = ""
        prijzen          = {}

    return TenantConfig(
        slug=slug,
        bedrijfsnaam=BEDRIJFSNAAM,
        regio=REGIO,
        contact_email=CONTACT_EMAIL,
        contact_telefoon=CONTACT_TELEFOON,
        begroeting=None,
        primaire_kleur="#5c6b1e",
        prijzen=prijzen,
    )
