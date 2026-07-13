# infrastructure/db/repositories/user_repository.py
from __future__ import annotations

from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash


class UserRepository:

    def find_by_id(self, user_id: int):
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbUser
            with SessionLocal() as db:
                return db.get(DbUser, user_id)
        except Exception as exc:
            print(f"[UserRepository] find_by_id fout: {exc}")
            return None

    def find_by_email(self, email: str):
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbUser
            with SessionLocal() as db:
                return db.query(DbUser).filter_by(email=email.lower().strip()).first()
        except Exception as exc:
            print(f"[UserRepository] find_by_email fout: {exc}")
            return None

    def verify_password(self, user, plain_password: str) -> bool:
        try:
            return check_password_hash(user.wachtwoord_hash, plain_password)
        except Exception:
            return False

    def create(
        self,
        tenant_id: int,
        email: str,
        plain_password: str,
        is_superadmin: bool = False,
    ) -> Optional[int]:
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbUser
            with SessionLocal() as db:
                user = DbUser(
                    tenant_id=tenant_id,
                    email=email.lower().strip(),
                    wachtwoord_hash=generate_password_hash(plain_password),
                    is_superadmin=is_superadmin,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                return user.id
        except Exception as exc:
            print(f"[UserRepository] create fout: {exc}")
            return None

    def update_password(self, user_id: int, plain_password: str) -> bool:
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbUser
            with SessionLocal() as db:
                user = db.get(DbUser, user_id)
                if user:
                    user.wachtwoord_hash = generate_password_hash(plain_password)
                    db.commit()
                    return True
            return False
        except Exception as exc:
            print(f"[UserRepository] update_password fout: {exc}")
            return False

    def create_reset_token(self, email: str) -> str | None:
        """Maakt een reset-token aan voor het e-mailadres. Geeft token terug, of None als email onbekend."""
        import secrets
        from datetime import datetime, timezone, timedelta
        from infrastructure.db.database import SessionLocal
        from infrastructure.db.db_models import DbPasswordReset
        try:
            user = self.find_by_email(email)
            if not user:
                return None
            token = secrets.token_urlsafe(48)
            verloopt = datetime.now(timezone.utc) + timedelta(hours=2)
            with SessionLocal() as db:
                db.add(DbPasswordReset(user_id=user.id, token=token, verloopt_op=verloopt))
                db.commit()
            return token
        except Exception as exc:
            print(f"[UserRepository] create_reset_token fout: {exc}")
            return None

    def use_reset_token(self, token: str, nieuw_wachtwoord: str) -> bool:
        """Verifieert token en zet nieuw wachtwoord. Geeft True terug bij succes."""
        from datetime import datetime, timezone
        from infrastructure.db.database import SessionLocal
        from infrastructure.db.db_models import DbPasswordReset
        try:
            with SessionLocal() as db:
                rec = db.query(DbPasswordReset).filter_by(token=token, gebruikt=False).first()
                if not rec:
                    return False
                if rec.verloopt_op.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                    return False
                user = db.get(__import__("infrastructure.db.db_models", fromlist=["DbUser"]).DbUser, rec.user_id)
                if not user:
                    return False
                from werkzeug.security import generate_password_hash
                user.wachtwoord_hash = generate_password_hash(nieuw_wachtwoord)
                rec.gebruikt = True
                db.commit()
                return True
        except Exception as exc:
            print(f"[UserRepository] use_reset_token fout: {exc}")
            return False

    def exists_for_tenant(self, tenant_id: int) -> bool:
        try:
            from infrastructure.db.database import SessionLocal
            from infrastructure.db.db_models import DbUser
            with SessionLocal() as db:
                return db.query(DbUser).filter_by(tenant_id=tenant_id).first() is not None
        except Exception:
            return False
