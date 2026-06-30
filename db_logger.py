# db_logger.py
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from database import SessionLocal
from models import (
    DbSession,
    DbMessage,
    DbFlowEvent,
    DbPriceCalculation,
    DbContactSubmission,
)


@contextmanager
def _db():
    """Context manager: commit on success, rollback on error, always close."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _safe(fn, *args, **kwargs) -> Any:
    """Nooit de chat breken door een DB-fout."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        print(f"[db_logger] WARNING: {exc}")
        return None


# ============================================================
# Sessions
# ============================================================

def log_session_created(session_id: str, user_agent: str = None) -> None:
    def _do():
        with _db() as db:
            if not db.get(DbSession, session_id):
                db.add(DbSession(id=session_id, user_agent=user_agent))
    _safe(_do)


def update_session_flow(session_id: str, flow_type: str) -> None:
    def _do():
        with _db() as db:
            s = db.get(DbSession, session_id)
            if s:
                s.flow_type = flow_type
    _safe(_do)


def update_session_completed(session_id: str) -> None:
    def _do():
        with _db() as db:
            s = db.get(DbSession, session_id)
            if s:
                s.completed = True
    _safe(_do)


def update_session_ended(session_id: str) -> None:
    def _do():
        with _db() as db:
            s = db.get(DbSession, session_id)
            if s:
                s.ended_at = datetime.now(timezone.utc)
    _safe(_do)


# ============================================================
# Messages
# ============================================================

def log_message(session_id: str, role: str, content: str, flow_step: str = None) -> None:
    def _do():
        with _db() as db:
            db.add(DbMessage(
                session_id=session_id,
                role=role,
                content=content,
                flow_step=flow_step,
            ))
    _safe(_do)


# ============================================================
# Flow events
# ============================================================

def log_event(session_id: str, event_type: str, event_data: Dict = None) -> None:
    def _do():
        with _db() as db:
            db.add(DbFlowEvent(
                session_id=session_id,
                event_type=event_type,
                event_data=event_data or {},
            ))
    _safe(_do)


# ============================================================
# Prijsberekeningen
# ============================================================

def log_price_calculation(
    session_id: str,
    flow_type: str,
    costs: Dict[str, Any],
) -> Optional[int]:
    """Slaat de berekening op en geeft het gegenereerde id terug."""
    calc_id: Optional[int] = None

    def _do():
        nonlocal calc_id
        tr = costs.get("total_range_eur") or [0, 0]
        with _db() as db:
            calc = DbPriceCalculation(
                session_id=session_id,
                flow_type=flow_type,
                inputs=costs.get("inputs", {}),
                total_min_eur=int(tr[0]),
                total_max_eur=int(tr[1]),
                breakdown=costs.get("breakdown", []),
            )
            db.add(calc)
            db.flush()          # vult calc.id vóór commit
            calc_id = calc.id

    _safe(_do)
    return calc_id


# ============================================================
# Leadscore
# ============================================================

def save_leadscore(session_id: str, score: int, label: str, breakdown: dict) -> None:
    def _do():
        with _db() as db:
            s = db.get(DbSession, session_id)
            if s:
                s.leadscore = score
                s.lead_label = label
                s.score_breakdown = breakdown
    _safe(_do)


def increment_terug_actie(session_id: str, stap: str = None) -> None:
    def _do():
        with _db() as db:
            s = db.get(DbSession, session_id)
            if s:
                s.terug_acties = (s.terug_acties or 0) + 1
            db.add(DbFlowEvent(
                session_id=session_id,
                event_type="terug_actie",
                event_data={"stap": stap},
            ))
    _safe(_do)


def log_prijs_gezien(session_id: str, min_eur: int, max_eur: int) -> None:
    log_event(session_id, "prijs_gezien", {"min": min_eur, "max": max_eur})


def log_drop_off(session_id: str, stap: str) -> None:
    log_event(session_id, "drop_off", {"stap": stap})


def log_offerte_aangevraagd(session_id: str) -> None:
    log_event(session_id, "offerte_aangevraagd", {})


# ============================================================
# Contact aanvragen
# ============================================================

def log_contact_submission(
    session_id: str,
    naam: str,
    telefoon: str,
    email: str,
    adres: str = None,
    woonplaats: str = None,
    notitie: str = None,
    price_calculation_id: int = None,
    email_sent_at: datetime = None,
) -> None:
    def _do():
        with _db() as db:
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
            ))
            s = db.get(DbSession, session_id)
            if s:
                s.contact_submitted = True
    _safe(_do)
