# infrastructure/db/repositories/tenant_repository.py
from __future__ import annotations

from typing import Dict, Optional, Tuple

from core.models.tenant import TenantConfig


class TenantRepository:

    def get(self, slug: str) -> Optional[TenantConfig]:
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenant

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
            print(f"[TenantRepository] Fout bij laden tenant '{slug}': {e}")
            return None

    def get_or_default(self, slug: str) -> TenantConfig:
        config = self.get(slug)
        if config:
            return config

        try:
            from infrastructure.config.bedrijf import (
                BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON,
            )
            from core.pricing.pricing import PRIJZEN
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
