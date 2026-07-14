# core/models/chat_state.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from flow_tuinaanleg import TuinaanlegFlowV2
    from flow_losse_onderdelen import LosseOnderdelenFlow
    from flow_tuinontwerp import TuinontWerpFlow


@dataclass
class ChatState:
    flow_type: Optional[str] = None
    flow: Optional[TuinaanlegFlowV2] = None
    losse_flow: Optional[LosseOnderdelenFlow] = None
    tuinontwerp_flow: Optional[TuinontWerpFlow] = None
    post_offer_mode: bool = False
    post_offer_stage: Optional[str] = None
    last_answers: Optional[Dict[str, Any]] = None
    last_costs: Optional[Dict[str, Any]] = None
    recalc_count: int = 0
    pending_material_part: Optional[Tuple] = None
    ended: bool = False
    # DB / contact
    session_id: Optional[str] = None
    last_calc_id: Optional[int] = None
    contact_naam: Optional[str] = None
    contact_telefoon: Optional[str] = None
    contact_email: Optional[str] = None
    contact_adres: Optional[str] = None
    contact_woonplaats: Optional[str] = None
    contact_opmerking: Optional[str] = None
    end_reason: Optional[str] = None
    # Erfafscheiding twee-laags menu
    erf_item_index: Optional[int] = None
    # Leadscore-signalen
    prijs_gezien_en_doorgegaan: bool = False
    heeft_herberekend: bool = False
    # Actieve flows voor deze sessie
    actieve_flows: List[str] = field(
        default_factory=lambda: ["tuinaanleg", "losse_onderdelen", "tuinontwerp"]
    )
    # Tenant-context voor e-mail routing
    tenant_notify_email: Optional[str] = None
    tenant_bedrijfsnaam: Optional[str] = None


def make_initial_state(session_id: str = None, actieve_flows: List[str] = None) -> ChatState:
    return ChatState(
        session_id=session_id,
        actieve_flows=actieve_flows or ["tuinaanleg", "losse_onderdelen", "tuinontwerp"],
    )
