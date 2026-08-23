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

    def delete(self, tenant_id: int) -> None:
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenant, DbSession
            with SessionLocal() as db:
                # Ontkoppel sessies zodat de FK geen problemen geeft
                db.query(DbSession).filter_by(tenant_id=tenant_id).update({"tenant_id": None})
                tenant = db.get(DbTenant, tenant_id)
                if tenant:
                    db.delete(tenant)
                db.commit()
        except Exception as e:
            print(f"[TenantRepository] delete fout: {e}")

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
            from datetime import datetime, timezone
            nu = datetime.now(timezone.utc).replace(tzinfo=None)
            with SessionLocal() as db:
                tenants = db.query(DbTenant).order_by(DbTenant.aangemaakt_op.desc()).all()
                result = []
                for t in tenants:
                    cfg = t.config
                    dagen_resterend = (t.trial_eindigt_op - nu).days if t.trial_eindigt_op else None
                    result.append({
                        "id":           t.id,
                        "slug":         t.slug,
                        "naam":         t.naam,
                        "actief":       t.actief,
                        "aangemaakt_op": t.aangemaakt_op,
                        "email":        cfg.contact_email if cfg else "",
                        "regio":        cfg.regio if cfg else "",
                        "trial_eindigt_op":      t.trial_eindigt_op,
                        "is_betalend":           t.is_betalend,
                        "trial_dagen_resterend": dagen_resterend,
                    })
                return result
        except Exception as e:
            print(f"[TenantRepository] list_all fout: {e}")
            return []

    # ── Proefperiode ──────────────────────────────────────────

    def start_trial(self, tenant_id: int, dagen: int = 30):
        """Start een proefperiode van `dagen` dagen vanaf nu. Retourneert de einddatum, of None bij fout."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenant
            from datetime import datetime, timezone, timedelta
            with SessionLocal() as db:
                t = db.get(DbTenant, tenant_id)
                if not t:
                    return None
                eindigt_op = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=dagen)
                t.trial_eindigt_op = eindigt_op
                t.trial_herinnering_verzonden = False
                db.commit()
                return eindigt_op
        except Exception as e:
            print(f"[TenantRepository] start_trial fout: {e}")
            return None

    def mark_betalend(self, tenant_id: int, betalend: bool = True) -> None:
        """Markeert tenant als (niet-)betalend. Betalend maken heractiveert de tenant meteen."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenant
            with SessionLocal() as db:
                t = db.get(DbTenant, tenant_id)
                if t:
                    t.is_betalend = betalend
                    if betalend:
                        t.actief = True
                    db.commit()
        except Exception as e:
            print(f"[TenantRepository] mark_betalend fout: {e}")

    def mark_herinnering_verzonden(self, tenant_id: int) -> None:
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenant
            with SessionLocal() as db:
                t = db.get(DbTenant, tenant_id)
                if t:
                    t.trial_herinnering_verzonden = True
                    db.commit()
        except Exception as e:
            print(f"[TenantRepository] mark_herinnering_verzonden fout: {e}")

    def _tenant_trial_dict(self, t) -> Dict:
        cfg = t.config
        return {
            "id": t.id, "slug": t.slug, "naam": t.naam,
            "email": cfg.contact_email if cfg else "",
            "trial_eindigt_op": t.trial_eindigt_op,
        }

    def list_trials_binnenkort_verlopen(self, dagen: int = 5):
        """Trials die binnen `dagen` dagen aflopen, nog actief, niet betalend, nog geen herinnering gehad."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenant
            from datetime import datetime, timezone, timedelta
            nu = datetime.now(timezone.utc).replace(tzinfo=None)
            with SessionLocal() as db:
                rows = (
                    db.query(DbTenant)
                    .filter(
                        DbTenant.actief == True,                       # noqa: E712
                        DbTenant.is_betalend == False,                 # noqa: E712
                        DbTenant.trial_herinnering_verzonden == False,  # noqa: E712
                        DbTenant.trial_eindigt_op.isnot(None),
                        DbTenant.trial_eindigt_op > nu,
                        DbTenant.trial_eindigt_op <= nu + timedelta(days=dagen),
                    )
                    .all()
                )
                return [self._tenant_trial_dict(t) for t in rows]
        except Exception as e:
            print(f"[TenantRepository] list_trials_binnenkort_verlopen fout: {e}")
            return []

    def list_trials_verlopen(self):
        """Trials waarvan de einddatum al gepasseerd is, nog actief=True en niet betalend."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenant
            from datetime import datetime, timezone
            nu = datetime.now(timezone.utc).replace(tzinfo=None)
            with SessionLocal() as db:
                rows = (
                    db.query(DbTenant)
                    .filter(
                        DbTenant.actief == True,        # noqa: E712
                        DbTenant.is_betalend == False,   # noqa: E712
                        DbTenant.trial_eindigt_op.isnot(None),
                        DbTenant.trial_eindigt_op <= nu,
                    )
                    .all()
                )
                return [self._tenant_trial_dict(t) for t in rows]
        except Exception as e:
            print(f"[TenantRepository] list_trials_verlopen fout: {e}")
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

    def get_instellingen(self, tenant_id: int) -> Dict:
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenantConfig
            with SessionLocal() as db:
                cfg = db.query(DbTenantConfig).filter_by(tenant_id=tenant_id).first()
                return dict(cfg.instellingen or {}) if cfg else {}
        except Exception as e:
            print(f"[TenantRepository] get_instellingen fout: {e}")
            return {}

    def save_instellingen(self, tenant_id: int, inst: Dict) -> None:
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenantConfig
            from datetime import datetime, timezone
            from sqlalchemy.orm.attributes import flag_modified
            with SessionLocal() as db:
                cfg = db.query(DbTenantConfig).filter_by(tenant_id=tenant_id).first()
                if cfg:
                    cfg.instellingen = dict(inst) or None
                    flag_modified(cfg, "instellingen")
                    cfg.bijgewerkt_op = datetime.now(timezone.utc)
                    db.commit()
        except Exception as e:
            print(f"[TenantRepository] save_instellingen fout: {e}")

    def get_volume_kortingen(self, tenant_id: int) -> Dict:
        """Laadt huidige volume korting overrides uit DbTenantConfig.volume_kortingen."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenantConfig
            with SessionLocal() as db:
                cfg = db.query(DbTenantConfig).filter_by(tenant_id=tenant_id).first()
                if not cfg or not cfg.volume_kortingen:
                    return {}
                result = {}
                for cat, rows in cfg.volume_kortingen.items():
                    parsed = [(float(r[0]), float(r[1])) for r in rows if len(r) == 2]
                    if parsed:
                        result[cat] = parsed
                return result
        except Exception as e:
            print(f"[TenantRepository] get_volume_kortingen fout: {e}")
            return {}

    def save_volume_kortingen(self, tenant_id: int, vk: Dict) -> None:
        """Slaat volume korting instellingen op in DbTenantConfig.volume_kortingen."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenantConfig
            from datetime import datetime, timezone
            from sqlalchemy.orm.attributes import flag_modified
            with SessionLocal() as db:
                cfg = db.query(DbTenantConfig).filter_by(tenant_id=tenant_id).first()
                if cfg:
                    cfg.volume_kortingen = {k: [[r[0], r[1]] for r in v] for k, v in vk.items()} or None
                    flag_modified(cfg, "volume_kortingen")
                    cfg.bijgewerkt_op = datetime.now(timezone.utc)
                    db.commit()
        except Exception as e:
            print(f"[TenantRepository] save_volume_kortingen fout: {e}")

    def save_prijzen(self, tenant_id: int, overrides: Dict[str, Tuple[int, int]]) -> None:
        """Slaat prijsoverrides op in DbTenantConfig.prijzen."""
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbTenantConfig
            from datetime import datetime, timezone

            with SessionLocal() as db:
                from sqlalchemy.orm.attributes import flag_modified
                cfg = db.query(DbTenantConfig).filter_by(tenant_id=tenant_id).first()
                if cfg:
                    cfg.prijzen = {k: list(v) for k, v in overrides.items()} or None
                    flag_modified(cfg, "prijzen")
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

                volume_kortingen = {}
                for cat, rows in (cfg.volume_kortingen or {}).items():
                    parsed = [(float(r[0]), float(r[1])) for r in rows if len(r) == 2]
                    if parsed:
                        volume_kortingen[cat] = parsed

                return TenantConfig(
                    slug=slug,
                    bedrijfsnaam=cfg.bedrijfsnaam,
                    regio=cfg.regio or "",
                    contact_email=cfg.contact_email or "",
                    contact_telefoon=cfg.contact_telefoon or "",
                    begroeting=cfg.begroeting,
                    primaire_kleur=cfg.primaire_kleur or "#5c6b1e",
                    prijzen=prijzen,
                    volume_kortingen=volume_kortingen,
                    instellingen=dict(cfg.instellingen or {}),
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
