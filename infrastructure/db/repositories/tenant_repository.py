# infrastructure/db/repositories/tenant_repository.py
from __future__ import annotations

from typing import Dict, Optional, Tuple

from core.models.tenant import TenantConfig


class TenantRepository:

    # ── Admin helpers ─────────────────────────────────────────

    def get_or_create_id(
        self,
        slug: str,
        bedrijfsnaam: str,
        regio: str = "",
        contact_email: str = "",
        contact_telefoon: str = "",
        actief: bool = True,
    ) -> int:
        """Geeft tenant_id terug, maakt tenant + config aan als ze nog niet bestaan."""
        from infrastructure.db.database import SessionLocal
        from infrastructure.db.db_models import DbTenant, DbTenantConfig
        from datetime import datetime, timezone

        with SessionLocal() as db:
            tenant = db.query(DbTenant).filter_by(slug=slug).first()
            if not tenant:
                tenant = DbTenant(slug=slug, naam=bedrijfsnaam, actief=actief)
                db.add(tenant)
                db.flush()
                db.add(DbTenantConfig(
                    tenant_id=tenant.id,
                    bedrijfsnaam=bedrijfsnaam,
                    regio=regio,
                    contact_email=contact_email,
                    contact_telefoon=contact_telefoon,
                ))
            elif not tenant.config:
                db.add(DbTenantConfig(
                    tenant_id=tenant.id,
                    bedrijfsnaam=bedrijfsnaam,
                ))
            db.commit()
            db.refresh(tenant)
            return tenant.id

    def set_actief(self, tenant_id: int, actief: bool) -> None:
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenant
            with SessionLocal() as db:
                t = db.get(DbTenant, tenant_id)
                if t:
                    t.actief = actief
                    db.commit()
        except Exception as e:
            print(f"[TenantRepository] set_actief fout: {e}")

    def list_all(self):
        """Geeft alle tenants terug voor superadmin-overzicht."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenant, DbTenantConfig
            with SessionLocal() as db:
                tenants = db.query(DbTenant).order_by(DbTenant.aangemaakt_op.desc()).all()
                result = []
                for t in tenants:
                    cfg = t.config
                    result.append({
                        "id":           t.id,
                        "slug":         t.slug,
                        "naam":         t.naam,
                        "actief":       t.actief,
                        "aangemaakt_op": t.aangemaakt_op,
                        "email":        cfg.contact_email if cfg else "",
                        "regio":        cfg.regio if cfg else "",
                    })
                return result
        except Exception as e:
            print(f"[TenantRepository] list_all fout: {e}")
            return []

    def get_prijzen_overrides(self, tenant_id: int) -> Dict[str, Tuple[int, int]]:
        """Laadt huidige prijsoverrides uit DbTenantConfig.prijzen."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenantConfig

            with SessionLocal() as db:
                cfg = db.query(DbTenantConfig).filter_by(tenant_id=tenant_id).first()
                if not cfg or not cfg.prijzen:
                    return {}
                result = {}
                for k, v in cfg.prijzen.items():
                    if isinstance(v, (list, tuple)) and len(v) == 2:
                        result[k] = (int(v[0]), int(v[1]))
                return result
        except Exception as e:
            print(f"[TenantRepository] get_prijzen_overrides fout: {e}")
            return {}

    def save_prijzen(self, tenant_id: int, overrides: Dict[str, Tuple[int, int]]) -> None:
        """Slaat prijsoverrides op in DbTenantConfig.prijzen."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenantConfig
            from datetime import datetime, timezone

            with SessionLocal() as db:
                cfg = db.query(DbTenantConfig).filter_by(tenant_id=tenant_id).first()
                if cfg:
                    cfg.prijzen = {k: list(v) for k, v in overrides.items()}
                    cfg.bijgewerkt_op = datetime.now(timezone.utc)
                    db.commit()
        except Exception as e:
            print(f"[TenantRepository] save_prijzen fout: {e}")

    # ── Chatbot helpers ───────────────────────────────────────

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
