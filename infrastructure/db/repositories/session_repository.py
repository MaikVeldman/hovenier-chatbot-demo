# infrastructure/db/repositories/session_repository.py
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from infrastructure.db.database import SessionLocal
from infrastructure.db.db_models import (
    DbSession, DbMessage, DbFlowEvent,
    DbPriceCalculation, DbContactSubmission,
)


class SessionRepository:

    @contextmanager
    def _db(self):
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _safe(self, fn, *args, **kwargs) -> Any:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            print(f"[SessionRepository] WARNING: {exc}")
            return None

    # ── Sessions ──────────────────────────────────────────────

    def log_session_created(self, session_id: str, user_agent: str = None, tenant_id: int = None) -> None:
        def _do():
            with self._db() as db:
                if not db.get(DbSession, session_id):
                    db.add(DbSession(id=session_id, user_agent=user_agent, tenant_id=tenant_id))
        self._safe(_do)

    def update_session_flow(self, session_id: str, flow_type: str) -> None:
        def _do():
            with self._db() as db:
                s = db.get(DbSession, session_id)
                if s:
                    s.flow_type = flow_type
        self._safe(_do)

    def update_session_completed(self, session_id: str) -> None:
        def _do():
            with self._db() as db:
                s = db.get(DbSession, session_id)
                if s:
                    s.completed = True
        self._safe(_do)

    def update_session_ended(self, session_id: str) -> None:
        def _do():
            with self._db() as db:
                s = db.get(DbSession, session_id)
                if s:
                    s.ended_at = datetime.now(timezone.utc)
        self._safe(_do)

    # ── Berichten ─────────────────────────────────────────────

    def log_message(self, session_id: str, role: str, content: str, flow_step: str = None) -> None:
        def _do():
            with self._db() as db:
                db.add(DbMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    flow_step=flow_step,
                ))
        self._safe(_do)

    # ── Events ────────────────────────────────────────────────

    def log_event(self, session_id: str, event_type: str, event_data: Dict = None) -> None:
        def _do():
            with self._db() as db:
                db.add(DbFlowEvent(
                    session_id=session_id,
                    event_type=event_type,
                    event_data=event_data or {},
                ))
        self._safe(_do)

    def log_prijs_gezien(self, session_id: str, min_eur: int, max_eur: int) -> None:
        self.log_event(session_id, "prijs_gezien", {"min": min_eur, "max": max_eur})

    def log_drop_off(self, session_id: str, stap: str) -> None:
        self.log_event(session_id, "drop_off", {"stap": stap})

    def log_offerte_aangevraagd(self, session_id: str) -> None:
        self.log_event(session_id, "offerte_aangevraagd", {})

    def increment_terug_actie(self, session_id: str, stap: str = None) -> None:
        def _do():
            with self._db() as db:
                s = db.get(DbSession, session_id)
                if s:
                    s.terug_acties = (s.terug_acties or 0) + 1
                db.add(DbFlowEvent(
                    session_id=session_id,
                    event_type="terug_actie",
                    event_data={"stap": stap},
                ))
        self._safe(_do)

    # ── Prijsberekeningen ─────────────────────────────────────

    def log_price_calculation(
        self,
        session_id: str,
        flow_type: str,
        costs: Dict[str, Any],
    ) -> Optional[int]:
        calc_id: Optional[int] = None

        def _do():
            nonlocal calc_id
            tr = costs.get("total_range_eur") or [0, 0]
            with self._db() as db:
                calc = DbPriceCalculation(
                    session_id=session_id,
                    flow_type=flow_type,
                    inputs=costs.get("inputs", {}),
                    total_min_eur=int(tr[0]),
                    total_max_eur=int(tr[1]),
                    breakdown=costs.get("breakdown", []),
                )
                db.add(calc)
                db.flush()
                calc_id = calc.id

        self._safe(_do)
        return calc_id

    # ── Leadscore ─────────────────────────────────────────────

    def save_leadscore(self, session_id: str, score: int, label: str, breakdown: dict) -> None:
        def _do():
            with self._db() as db:
                s = db.get(DbSession, session_id)
                if s:
                    s.leadscore = score
                    s.lead_label = label
                    s.score_breakdown = breakdown
        self._safe(_do)

    # ── Contact ───────────────────────────────────────────────

    def log_contact_submission(
        self,
        session_id: str,
        naam: str,
        telefoon: str,
        email: str,
        adres: str = None,
        woonplaats: str = None,
        notitie: str = None,
        price_calculation_id: int = None,
        email_sent_at: datetime = None,
    ) -> Optional[str]:
        import uuid as _uuid_mod
        token: Optional[str] = None

        def _do():
            nonlocal token
            token = str(_uuid_mod.uuid4())
            with self._db() as db:
                db.add(DbContactSubmission(
                    session_id=session_id,
                    naam=naam,
                    telefoon=telefoon,
                    email=email,
                    adres=adres,
                    woonplaats=woonplaats,
                    notitie=notitie,
                    price_calculation_id=price_calculation_id,
                    email_sent_at=email_sent_at,
                    bekijk_token=token,
                ))
                s = db.get(DbSession, session_id)
                if s:
                    s.contact_submitted = True

        self._safe(_do)
        return token
