# bot_logic.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from db_logger import (
        log_event,
        log_price_calculation,
        log_contact_submission,
        update_session_flow,
        update_session_completed,
        update_session_ended,
        save_leadscore,
        increment_terug_actie,
        log_prijs_gezien,
        log_drop_off,
        log_offerte_aangevraagd,
    )
    from mailer import send_contact_email
    from leadscore import bereken_leadscore
    _DB = True
except Exception:
    _DB = False

from flow_tuinaanleg import TuinaanlegFlowV2
from flow_losse_onderdelen import LosseOnderdelenFlow
from flow_tuinontwerp import TuinontWerpFlow
from pricing import (
    estimate_tuinaanleg_costs,
    estimate_losse_onderdelen_costs,
    estimate_tuinontwerp_costs,
    format_costs_as_chat_html,
    format_tuinontwerp_costs_as_chat_html,
)
from savings import (
    post_offer_choices_text,
    post_offer_choices_losse_text,
    post_offer_choices_tuinontwerp_text,
    lower_costs_menu_text,
    lower_costs_menu_losse_text,
    more_green_choice_text,
    extras_select_menu_text,
    material_part_menu_text,
    material_choice_menu_text_cheaper,
    vlonder_choice_menu_text,
    overkapping_choice_menu_text,
    voegen_choice_menu_text,
    verlichting_choice_menu_text,
    erf_remove_select_menu_text,
    erf_item_select_menu_text,
    erf_haag_menu_text,
    erf_schutting_menu_text,
    apply_erf_item_haag_change,
    apply_erf_item_schutting_change,
    losse_component_remove_menu_text,
    apply_set_ratio,
    apply_ratio_proportional,
    apply_remove_selected_extras,
    apply_material_change,
    apply_vlonder_change,
    apply_overkapping_change,
    apply_voegen_change,
    apply_verlichting_change,
    apply_beregening_remove,
    apply_erf_changes,
    apply_remove_losse_component,
    apply_remove_losse_item,
    beregening_systeem_choice_text,
    apply_beregening_systeem_change,
    parse_multi_digits,
    parse_single_digit,
    parse_material_parts,
    is_cancel,
)

INITIAL_GREETING = (
    "Bereken in 2 minuten wat uw tuin kost 👇\n\n"
    "1) De gehele tuin aanleggen – ik stel een paar vragen en reken de totale tuin door\n"
    "2) Losse onderdelen – kies zelf wat u wilt laten aanleggen (bijv. alleen een terras of gazon)\n"
    "3) Tuinontwerp – ik wil eerst een professioneel ontwerp met 3D visualisatie\n\n"
    "Reageer met 1, 2 of 3.\n\n"
    "_Door verder te gaan gaat u akkoord met onze [privacyverklaring](https://www.veldmanhoveniers.nl/privacybeleid/)._"
)


@dataclass
class ChatState:
    flow_type: Optional[str] = None             # "gehele_tuin" | "losse_onderdelen" | "tuinontwerp"
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


def make_initial_state(session_id: str = None) -> ChatState:
    return ChatState(session_id=session_id)


# ============================================================
# Helpers
# ============================================================

def _is_losse(state: ChatState) -> bool:
    return (state.last_answers or {}).get("_flow_type") == "losse_onderdelen"


def _is_tuinontwerp(state: ChatState) -> bool:
    return (state.last_answers or {}).get("_flow_type") == "tuinontwerp"


def _main_menu_text(state: ChatState) -> str:
    if _is_tuinontwerp(state):
        return post_offer_choices_tuinontwerp_text()
    return post_offer_choices_losse_text() if _is_losse(state) else post_offer_choices_text()


def _estimate_costs(answers: dict) -> dict:
    ft = (answers or {}).get("_flow_type")
    if ft == "losse_onderdelen":
        return estimate_losse_onderdelen_costs(answers)
    if ft == "tuinontwerp":
        return estimate_tuinontwerp_costs(answers)
    return estimate_tuinaanleg_costs(answers)


def _format_costs(answers: dict, costs: dict) -> str:
    ft = (answers or {}).get("_flow_type")
    if ft == "tuinontwerp":
        return format_tuinontwerp_costs_as_chat_html(costs)
    flow_type = "losse_onderdelen" if ft == "losse_onderdelen" else "gehele_tuin"
    return format_costs_as_chat_html(costs, flow_type)


def _lower_costs_menu(state: ChatState) -> str:
    if _is_losse(state):
        text, _ = lower_costs_menu_losse_text(state.last_answers)
        return text
    text, _ = lower_costs_menu_text(state.last_answers, state.last_costs)
    return text


def ensure_prefix(explanation: str) -> str:
    t = (explanation or "").strip()
    if not t:
        return "✅ Doorgevoerde kostenbesparing."
    low = t.lower()
    if "doorgevoerde kostenbesparing" in low:
        return t
    if low.startswith("ik heb aangepast:"):
        rest = t.split(":", 1)[1].strip() if ":" in t else t
        return f"✅ Doorgevoerde kostenbesparing: {rest}"
    if low.startswith("ik heb de ") or low.startswith("ik heb het "):
        return f"✅ Doorgevoerde kostenbesparing: {t[0].lower() + t[1:]}" if len(t) > 1 else "✅ Doorgevoerde kostenbesparing."
    return f"✅ Doorgevoerde kostenbesparing: {t}"


def _eur(v) -> str:
    return f"€{int(v):,}".replace(",", ".")


def _recalc_messages(state: ChatState, before_costs: dict, after_costs: dict, explanation: str) -> List[str]:
    old_tr = before_costs.get("total_range_eur") or (0, 0)
    new_tr = after_costs.get("total_range_eur") or (0, 0)
    return [
        ensure_prefix(explanation),
        f"Oude indicatie: {_eur(old_tr[0])} – {_eur(old_tr[1])}",
        f"Nieuwe indicatie: {_eur(new_tr[0])} – {_eur(new_tr[1])}",
        _format_costs(state.last_answers, after_costs),
    ]


# ============================================================
# Publieke entrypoint
# ============================================================

def handle_message(state: ChatState, user_text: str) -> Tuple[ChatState, List[str]]:
    if state.ended:
        if state.end_reason == "contact_submitted":
            msg = "Uw aanvraag is al ontvangen. We nemen zo snel mogelijk contact met u op.\n\n_Ververs de pagina om een nieuwe indicatie te starten._"
        else:
            msg = "Deze sessie is afgesloten. Ververs de pagina om opnieuw een indicatie te starten."
        return state, [msg]

    t_raw = user_text.strip()

    if state.post_offer_mode:
        return _handle_post_offer(state, t_raw)

    if state.flow_type is None:
        return _handle_flow_keuze(state, t_raw)

    if state.flow_type == "gehele_tuin" and state.flow is not None:
        return _handle_intake(state, t_raw)

    if state.flow_type == "losse_onderdelen" and state.losse_flow is not None:
        return _handle_losse_intake(state, t_raw)

    if state.flow_type == "tuinontwerp" and state.tuinontwerp_flow is not None:
        return _handle_tuinontwerp_intake(state, t_raw)

    return state, []


# ============================================================
# Flow-keuze
# ============================================================

def _handle_flow_keuze(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if t_raw == "1":
        state.flow_type = "gehele_tuin"
        state.flow = TuinaanlegFlowV2()
        if _DB and state.session_id:
            update_session_flow(state.session_id, "gehele_tuin")
            log_event(state.session_id, "flow_started", {"flow": "gehele_tuin"})
        return state, [state.flow.get_question()]
    if t_raw == "2":
        state.flow_type = "losse_onderdelen"
        state.losse_flow = LosseOnderdelenFlow()
        if _DB and state.session_id:
            update_session_flow(state.session_id, "losse_onderdelen")
            log_event(state.session_id, "flow_started", {"flow": "losse_onderdelen"})
        return state, [state.losse_flow.start_question()]
    if t_raw == "3":
        state.flow_type = "tuinontwerp"
        state.tuinontwerp_flow = TuinontWerpFlow()
        if _DB and state.session_id:
            update_session_flow(state.session_id, "tuinontwerp")
            log_event(state.session_id, "flow_started", {"flow": "tuinontwerp"})
        return state, [state.tuinontwerp_flow.get_question()]
    return state, ["Typ **1**, **2** of **3** om een keuze te maken."]


# ============================================================
# Intake flows
# ============================================================

def _handle_intake(state: ChatState, user_text: str) -> Tuple[ChatState, List[str]]:
    flow = state.flow
    if user_text.strip().lower() in ("terug", "back", "vorige") and _DB and state.session_id:
        increment_terug_actie(state.session_id, stap=str(flow.step_index))
    reply, done = flow.handle(user_text)
    msgs: List[str] = [reply] if reply else []

    if done:
        answers_for_pricing = flow.to_answers()
        costs = estimate_tuinaanleg_costs(answers_for_pricing)
        msgs.append(_format_costs(answers_for_pricing, costs))
        state.last_answers = dict(answers_for_pricing)
        state.last_costs = dict(costs)
        state.flow = None
        state.post_offer_mode = True
        state.post_offer_stage = "menu"
        if _DB and state.session_id:
            tr = costs.get("total_range_eur") or [0, 0]
            state.last_calc_id = log_price_calculation(state.session_id, "gehele_tuin", costs)
            update_session_completed(state.session_id)
            log_event(state.session_id, "flow_completed", {"flow": "gehele_tuin", "total_min": tr[0], "total_max": tr[1]})
            log_prijs_gezien(state.session_id, int(tr[0]), int(tr[1]))
        msgs.append(post_offer_choices_text())

    return state, msgs


def _handle_losse_intake(state: ChatState, user_text: str) -> Tuple[ChatState, List[str]]:
    flow = state.losse_flow
    if user_text.strip().lower() in ("terug", "back", "vorige") and _DB and state.session_id:
        increment_terug_actie(state.session_id, stap=str(getattr(flow, "step_index", "?")))
    reply, done = flow.handle(user_text)
    msgs: List[str] = [reply] if reply else []

    if done:
        answers = flow.to_answers()  # bevat _flow_type = "losse_onderdelen"
        costs = estimate_losse_onderdelen_costs(answers)
        msgs.append(_format_costs(answers, costs))
        state.last_answers = answers
        state.last_costs = dict(costs)
        state.losse_flow = None
        state.post_offer_mode = True
        state.post_offer_stage = "menu"
        if _DB and state.session_id:
            tr = costs.get("total_range_eur") or [0, 0]
            state.last_calc_id = log_price_calculation(state.session_id, "losse_onderdelen", costs)
            update_session_completed(state.session_id)
            log_event(state.session_id, "flow_completed", {"flow": "losse_onderdelen", "total_min": tr[0], "total_max": tr[1]})
            log_prijs_gezien(state.session_id, int(tr[0]), int(tr[1]))
        msgs.append(post_offer_choices_losse_text())

    return state, msgs


def _handle_tuinontwerp_intake(state: ChatState, user_text: str) -> Tuple[ChatState, List[str]]:
    flow = state.tuinontwerp_flow
    reply, done = flow.handle(user_text)
    msgs: List[str] = [reply] if reply else []

    if done:
        answers = flow.to_answers()
        costs = estimate_tuinontwerp_costs(answers)
        msgs.append(format_tuinontwerp_costs_as_chat_html(costs))
        state.last_answers = answers
        state.last_costs = dict(costs)
        state.tuinontwerp_flow = None
        state.post_offer_mode = True
        state.post_offer_stage = "menu"
        if _DB and state.session_id:
            tr = costs.get("total_range_eur") or [0, 0]
            state.last_calc_id = log_price_calculation(state.session_id, "tuinontwerp", costs)
            update_session_completed(state.session_id)
            log_event(state.session_id, "flow_completed", {"flow": "tuinontwerp", "total_min": tr[0], "total_max": tr[1]})
            log_prijs_gezien(state.session_id, int(tr[0]), int(tr[1]))
        msgs.append(post_offer_choices_tuinontwerp_text())

    return state, msgs


# ============================================================
# Post-offer state machine
# ============================================================

def _handle_post_offer(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    t_low = t_raw.lower()

    if t_low in {"contact", "offerte", "advies"}:
        state.post_offer_stage = "contact_naam"
        return state, ["Uitstekend. Ik noteer graag uw gegevens om de offerte op te stellen.\n\nWat is uw naam?"]

    stage = state.post_offer_stage

    if stage == "menu":
        return _handle_main_menu(state, t_raw)
    if stage == "lower_costs_menu":
        return _handle_lower_costs_menu(state, t_raw)

    # Gehele-tuin specifieke stages
    if stage == "lc_more_green_choice":
        return _handle_more_green_choice(state, t_raw)
    if stage == "lc_extras_select":
        return _handle_extras_select(state, t_raw)
    if stage == "lc_vlonder_choice":
        return _handle_vlonder_choice(state, t_raw)
    if stage == "lc_overkapping_choice":
        return _handle_overkapping_choice(state, t_raw)
    if stage == "lc_voegen_choice":
        return _handle_voegen_choice(state, t_raw)
    if stage == "lc_verlichting_choice":
        return _handle_verlichting_choice(state, t_raw)
    if stage == "lc_erf_remove_select":
        return _handle_erf_remove_select(state, t_raw)
    if stage == "lc_erf_component":
        return _handle_erf_component(state, t_raw)
    if stage == "lc_erf_sub":
        return _handle_erf_sub(state, t_raw)
    if stage == "lc_beregening_systeem_choice":
        return _handle_beregening_systeem_choice(state, t_raw)

    # Gedeeld: materiaal
    if stage == "lc_material_part":
        return _handle_material_part(state, t_raw)
    if stage == "lc_material_choice":
        return _handle_material_choice(state, t_raw)

    # Losse onderdelen specifiek
    if stage == "lc_losse_remove":
        return _handle_losse_component_remove(state, t_raw)

    # Contact flow (5 stappen)
    if stage == "contact_naam":
        return _handle_contact_naam(state, t_raw)
    if stage == "contact_telefoon":
        return _handle_contact_telefoon(state, t_raw)
    if stage == "contact_email":
        return _handle_contact_email(state, t_raw)
    if stage == "contact_adres":
        return _handle_contact_adres(state, t_raw)
    if stage == "contact_woonplaats":
        return _handle_contact_woonplaats(state, t_raw)
    if stage == "contact_opmerking":
        return _handle_contact_opmerking(state, t_raw)

    return state, [_main_menu_text(state)]


_EXIT_MSG = (
    "Helemaal goed. Fijn dat u even heeft gekeken. 👋\n\n"
    "Heeft u later nog vragen of wilt u alsnog een offerte? U kunt altijd een nieuwe berekening starten "
    "of ons direct bereiken via [veldmanhoveniers.nl](https://www.veldmanhoveniers.nl)."
)


def _do_exit(state: ChatState) -> Tuple[ChatState, List[str]]:
    state.post_offer_mode = False
    state.post_offer_stage = "end"
    state.ended = True
    state.end_reason = "no_contact"
    if _DB and state.session_id:
        update_session_ended(state.session_id)
        log_event(state.session_id, "session_ended", {"reason": "no_contact"})
        log_drop_off(state.session_id, "na_prijs_gezien")
        _bereken_en_sla_leadscore(state, sessie_volledig=True, offerte_aangevraagd=False, drop_off=True)
    return state, [_EXIT_MSG]


def _bereken_en_sla_leadscore(
    state: ChatState,
    sessie_volledig: bool,
    offerte_aangevraagd: bool,
    drop_off: bool = False,
) -> tuple:
    """Berekent leadscore, slaat op in DB en geeft (score, label, breakdown) terug."""
    if not (_DB and state.session_id):
        return 0, "", {}
    try:
        from models import DbSession
        from database import SessionLocal
        with SessionLocal() as db:
            sess = db.get(DbSession, state.session_id)
            terug_acties = (sess.terug_acties or 0) if sess else 0
    except Exception:
        terug_acties = 0

    score, label, breakdown = bereken_leadscore(
        answers=state.last_answers,
        costs=state.last_costs,
        sessie_volledig=sessie_volledig,
        offerte_aangevraagd=offerte_aangevraagd,
        terug_acties=terug_acties,
        prijs_gezien_en_doorgegaan=state.prijs_gezien_en_doorgegaan,
        herberekend=state.heeft_herberekend,
        drop_off=drop_off,
    )
    save_leadscore(state.session_id, score, label, breakdown)
    return score, label, breakdown


def _handle_main_menu(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if t_raw == "1":
        state.post_offer_stage = "contact_naam"
        state.prijs_gezien_en_doorgegaan = True
        if _DB and state.session_id:
            log_offerte_aangevraagd(state.session_id)
        return state, ["Uitstekend. We helpen u graag verder. Wat is uw naam?"]
    if _is_tuinontwerp(state):
        if t_raw == "2":
            state.post_offer_mode = False
            state.post_offer_stage = None
            state.flow = TuinaanlegFlowV2()
            state.flow_type = "gehele_tuin"
            state.last_answers = None
            state.last_costs = None
            if _DB and state.session_id:
                update_session_flow(state.session_id, "gehele_tuin")
                log_event(state.session_id, "flow_started", {"flow": "gehele_tuin", "from": "tuinontwerp"})
            return state, [state.flow.get_question()]
        if t_raw == "3":
            state.post_offer_mode = False
            state.post_offer_stage = None
            state.losse_flow = LosseOnderdelenFlow()
            state.flow_type = "losse_onderdelen"
            state.last_answers = None
            state.last_costs = None
            if _DB and state.session_id:
                update_session_flow(state.session_id, "losse_onderdelen")
                log_event(state.session_id, "flow_started", {"flow": "losse_onderdelen", "from": "tuinontwerp"})
            return state, [state.losse_flow.start_question()]
        if t_raw == "4" or is_cancel(t_raw):
            return _do_exit(state)
    elif _is_losse(state):
        if t_raw == "2":
            state.post_offer_mode = False
            state.post_offer_stage = None
            state.losse_flow = LosseOnderdelenFlow.from_answers(state.last_answers or {})
            state.flow_type = "losse_onderdelen"
            return state, [state.losse_flow.start_question()]
        if t_raw == "3":
            state.post_offer_stage = "lower_costs_menu"
            return state, [_lower_costs_menu(state)]
        if t_raw == "4" or is_cancel(t_raw):
            return _do_exit(state)
    else:
        if t_raw == "2":
            state.post_offer_stage = "lower_costs_menu"
            return state, [_lower_costs_menu(state)]
        if t_raw == "3" or is_cancel(t_raw):
            return _do_exit(state)
    return state, [_main_menu_text(state)]


def _handle_lower_costs_menu(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if is_cancel(t_raw):
        state.post_offer_stage = "menu"
        return state, [_main_menu_text(state)]

    # Route naar de juiste sub-handler op basis van flow-type
    if _is_losse(state):
        return _handle_lower_costs_menu_losse(state, t_raw)
    return _handle_lower_costs_menu_gehele(state, t_raw)


def _handle_lower_costs_menu_gehele(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu_text, mapping = lower_costs_menu_text(state.last_answers, state.last_costs)

    if t_raw not in mapping:
        return state, [menu_text]

    action = mapping[t_raw]

    if action == "more_green":
        menu, mg_mapping = more_green_choice_text(state.last_answers, state.last_costs)
        if not mg_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_more_green_choice"
        return state, [menu]

    if action == "material":
        state.post_offer_stage = "lc_material_part"
        menu, _ = material_part_menu_text(state.last_answers)
        return state, [menu]

    if action == "voegen":
        menu, vg_mapping = voegen_choice_menu_text(state.last_answers, state.last_costs)
        if not vg_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_voegen_choice"
        return state, [menu]

    if action == "overkapping":
        menu, ov_mapping = overkapping_choice_menu_text(state.last_answers, state.last_costs)
        if not ov_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_overkapping_choice"
        return state, [menu]

    if action == "verlichting":
        menu, vl_mapping = verlichting_choice_menu_text(state.last_answers, state.last_costs)
        if not vl_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_verlichting_choice"
        return state, [menu]

    if action == "beregening":
        ber_menu, ber_mapping = beregening_systeem_choice_text(state.last_answers, state.last_costs)
        if not ber_mapping:
            return state, [ber_menu, menu_text]
        state.post_offer_stage = "lc_beregening_systeem_choice"
        return state, [ber_menu]

    if action == "vlonder":
        menu, vl_mapping = vlonder_choice_menu_text(state.last_answers, state.last_costs)
        if not vl_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_vlonder_choice"
        return state, [menu]

    if action == "erfafscheiding":
        menu, erf_mapping = erf_item_select_menu_text(state.last_answers, state.last_costs)
        if not erf_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_erf_component"
        return state, [menu]

    return state, [menu_text]


def _handle_lower_costs_menu_losse(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu_text, mapping = lower_costs_menu_losse_text(state.last_answers, state.last_costs)

    if t_raw not in mapping:
        return state, [menu_text]

    action = mapping[t_raw]

    if action == "material":
        state.post_offer_stage = "lc_material_part"
        menu, _ = material_part_menu_text(state.last_answers)
        return state, [menu]

    if action == "beregening":
        ber_menu, ber_mapping = beregening_systeem_choice_text(state.last_answers, state.last_costs)
        if not ber_mapping:
            return state, [ber_menu, menu_text]
        state.post_offer_stage = "lc_beregening_systeem_choice"
        return state, [ber_menu]

    if action in ("oprit_m2", "paden_m2", "terras_m2", "gazon_m2", "beplanting_m2"):
        new_a, expl = apply_remove_losse_component(dict(state.last_answers or {}), action)
        return _apply_recalc(state, new_a, expl)

    _item_match = re.match(r'^(oprit|paden|terras)_item_(\d+)$', action)
    if _item_match:
        comp_base, index = _item_match.group(1), int(_item_match.group(2))
        new_a, expl = apply_remove_losse_item(dict(state.last_answers or {}), comp_base, index)
        return _apply_recalc(state, new_a, expl)

    if action == "erfafscheiding":
        menu, erf_mapping = erf_item_select_menu_text(state.last_answers, state.last_costs)
        if not erf_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_erf_component"
        return state, [menu]

    if action == "vlonder":
        menu, vl_mapping = vlonder_choice_menu_text(state.last_answers, state.last_costs)
        if not vl_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_vlonder_choice"
        return state, [menu]

    if action == "overkapping":
        menu, ov_mapping = overkapping_choice_menu_text(state.last_answers, state.last_costs)
        if not ov_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_overkapping_choice"
        return state, [menu]

    if action == "verlichting":
        menu, vl_mapping = verlichting_choice_menu_text(state.last_answers, state.last_costs)
        if not vl_mapping:
            return state, [menu, menu_text]
        state.post_offer_stage = "lc_verlichting_choice"
        return state, [menu]

    return state, [menu_text]


# ============================================================
# Herberekening helpers
# ============================================================

def _apply_recalc(
    state: ChatState,
    new_answers: dict,
    explanation: str,
    preserve_direct_markers: bool = False,
) -> Tuple[ChatState, List[str]]:
    # Clear V2 direct-m² display markers after a ratio recalculation (values would be stale).
    # Skip when proportional scaling already updated them to correct values.
    if not preserve_direct_markers:
        for _k in ("_flow_version", "_direct_oprit_m2", "_direct_terras_m2",
                   "_direct_paden_m2", "_direct_gazon_m2", "_direct_beplanting_m2"):
            new_answers.pop(_k, None)
    before_costs = dict(state.last_costs or {})
    new_costs = _estimate_costs(new_answers)
    msgs = _recalc_messages(state, before_costs, new_costs, explanation)
    state.recalc_count += 1
    state.heeft_herberekend = True
    state.last_answers = dict(new_answers)
    state.last_costs = dict(new_costs)
    if _DB and state.session_id:
        tr_old = before_costs.get("total_range_eur") or [0, 0]
        tr_new = new_costs.get("total_range_eur") or [0, 0]
        state.last_calc_id = log_price_calculation(state.session_id, state.flow_type or "onbekend", new_costs)
        log_event(state.session_id, "recalc_done", {
            "recalc_count": state.recalc_count,
            "old_min": tr_old[0], "old_max": tr_old[1],
            "new_min": tr_new[0], "new_max": tr_new[1],
            "explanation": explanation,
        })
    state.post_offer_stage = "menu"
    msgs.append(_main_menu_text(state))
    return state, msgs


# ============================================================
# Sub-handlers (gehele tuin)
# ============================================================

def _handle_more_green_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = more_green_choice_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]

    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    a = dict(state.last_answers or {})
    is_items_based = (
        float(a.get("_direct_terras_m2") or 0) > 0
        or float(a.get("_direct_paden_m2") or 0) > 0
        or float(a.get("_direct_oprit_m2") or 0) > 0
        or bool(a.get("terras_extra_items"))
        or bool(a.get("paden_extra_items"))
    )
    if is_items_based:
        # Proportioneel schalen: alle items worden geschaald, materialen blijven behouden.
        new_a, expl = apply_ratio_proportional(a, mapping[picked])
        return _apply_recalc(state, new_a, expl, preserve_direct_markers=True)
    else:
        new_a, expl = apply_set_ratio(a, mapping[picked])
        new_a.pop("terras_extra_items", None)
        new_a.pop("paden_extra_items", None)
        return _apply_recalc(state, new_a, expl)


def _handle_extras_select(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = extras_select_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]

    if is_cancel(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    parsed = parse_multi_digits(t_raw, allowed=tuple(mapping.keys()))
    if parsed is None:
        return state, [menu]
    if parsed == ("nee",):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    actions = [mapping[d] for d in parsed if d in mapping]
    if not actions:
        return state, [menu]

    if "beregening_downgrade" in actions:
        ber_menu, ber_mapping = beregening_systeem_choice_text(state.last_answers, state.last_costs)
        if not ber_mapping:
            return state, [ber_menu, menu]
        state.post_offer_stage = "lc_beregening_systeem_choice"
        return state, [ber_menu]

    new_a, expl = apply_remove_selected_extras(dict(state.last_answers or {}), actions)
    return _apply_recalc(state, new_a, expl)


# ============================================================
# Sub-handlers (gedeeld: materiaal)
# ============================================================

def _handle_material_part(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if is_cancel(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    menu, part_mapping = material_part_menu_text(state.last_answers)
    if not part_mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]

    picked_digits = parse_material_parts(t_raw)
    if picked_digits is None:
        return state, [menu]
    if picked_digits == ("nee",):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    # Zet digits om naar item_specs via de mapping
    item_specs = tuple(part_mapping[d] for d in picked_digits if d in part_mapping)
    if not item_specs:
        return state, [menu]

    state.pending_material_part = item_specs
    menu2, allowed_choices = material_choice_menu_text_cheaper(
        state.last_answers, state.last_costs, item_specs
    )
    if not allowed_choices:
        state.post_offer_stage = "lc_material_part"
        return state, [menu2, menu]

    state.post_offer_stage = "lc_material_choice"
    return state, [menu2]


def _handle_material_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    part = state.pending_material_part or ("terras_0",)
    menu, allowed_choices = material_choice_menu_text_cheaper(
        state.last_answers, state.last_costs, part
    )
    if not allowed_choices:
        part_menu, _ = material_part_menu_text(state.last_answers)
        state.post_offer_stage = "lc_material_part"
        return state, [menu, part_menu]

    picked = parse_single_digit(t_raw, allowed=tuple(sorted(allowed_choices)))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        part_menu, _ = material_part_menu_text(state.last_answers)
        state.post_offer_stage = "lc_material_part"
        return state, [part_menu]

    new_a, expl = apply_material_change(dict(state.last_answers or {}), part, picked)
    state.pending_material_part = None
    return _apply_recalc(state, new_a, expl)


# ============================================================
# Sub-handlers (gehele tuin: vlonder + erfafscheiding)
# ============================================================

def _handle_overkapping_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = overkapping_choice_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]
    if is_cancel(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]
    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    new_a, expl = apply_overkapping_change(dict(state.last_answers or {}), mapping[picked])
    return _apply_recalc(state, new_a, expl)


def _handle_voegen_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = voegen_choice_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]
    if is_cancel(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]
    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    new_a, expl = apply_voegen_change(dict(state.last_answers or {}))
    return _apply_recalc(state, new_a, expl)


def _handle_verlichting_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = verlichting_choice_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]
    if is_cancel(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]
    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    new_a, expl = apply_verlichting_change(dict(state.last_answers or {}))
    return _apply_recalc(state, new_a, expl)


def _handle_vlonder_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = vlonder_choice_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]

    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    new_a, expl = apply_vlonder_change(dict(state.last_answers or {}), mapping[picked])
    return _apply_recalc(state, new_a, expl)


def _handle_erf_remove_select(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = erf_remove_select_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]

    if is_cancel(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    parsed = parse_multi_digits(t_raw, allowed=tuple(mapping.keys()))
    if parsed is None:
        return state, [menu]
    if parsed == ("nee",):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    actions = [mapping[d] for d in parsed if d in mapping]
    if not actions:
        return state, [menu]

    new_a, expl = apply_erf_changes(dict(state.last_answers or {}), actions)
    return _apply_recalc(state, new_a, expl)


def _handle_erf_component(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    """Laag 1: per-item keuze erfafscheiding."""
    menu, mapping = erf_item_select_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]

    if is_cancel(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    item_index = int(mapping[picked])
    state.erf_item_index = item_index

    items = list((state.last_answers or {}).get("erfafscheiding_items") or [])
    if item_index >= len(items):
        return state, [menu]

    t = (items[item_index].get("type") or "").strip().lower()
    if t == "haag":
        sub_menu, sub_mapping = erf_haag_menu_text(state.last_answers, state.last_costs, item_index)
    else:
        sub_menu, sub_mapping = erf_schutting_menu_text(state.last_answers, state.last_costs, item_index)

    if not sub_mapping:
        return state, [sub_menu, menu]

    state.post_offer_stage = "lc_erf_sub"
    return state, [sub_menu]


def _handle_erf_sub(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    """Laag 2: actiekeuze voor specifiek erfafscheiding-item."""
    item_index = state.erf_item_index or 0
    items = list((state.last_answers or {}).get("erfafscheiding_items") or [])

    if item_index >= len(items):
        state.post_offer_stage = "lc_erf_component"
        comp_menu, _ = erf_item_select_menu_text(state.last_answers, state.last_costs)
        return state, [comp_menu]

    t = (items[item_index].get("type") or "").strip().lower()
    if t == "haag":
        menu, mapping = erf_haag_menu_text(state.last_answers, state.last_costs, item_index)
    else:
        menu, mapping = erf_schutting_menu_text(state.last_answers, state.last_costs, item_index)

    if not mapping:
        state.post_offer_stage = "lc_erf_component"
        comp_menu, _ = erf_item_select_menu_text(state.last_answers, state.last_costs)
        return state, [menu, comp_menu]

    if is_cancel(t_raw):
        state.post_offer_stage = "lc_erf_component"
        comp_menu, _ = erf_item_select_menu_text(state.last_answers, state.last_costs)
        return state, [comp_menu]

    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        state.post_offer_stage = "lc_erf_component"
        comp_menu, _ = erf_item_select_menu_text(state.last_answers, state.last_costs)
        return state, [comp_menu]

    action = mapping[picked]
    if t == "haag":
        new_a, expl = apply_erf_item_haag_change(dict(state.last_answers or {}), item_index, action)
    else:
        new_a, expl = apply_erf_item_schutting_change(dict(state.last_answers or {}), item_index, action)

    state.erf_item_index = None
    return _apply_recalc(state, new_a, expl)


# ============================================================
# Sub-handler (gehele tuin: beregening systeem goedkoper)
# ============================================================

def _handle_beregening_systeem_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = beregening_systeem_choice_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, _lower_costs_menu(state)]

    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        state.post_offer_stage = "lower_costs_menu"
        return state, [_lower_costs_menu(state)]

    action = mapping[picked]
    if action == "remove":
        new_a, expl = apply_beregening_remove(dict(state.last_answers or {}))
    else:
        new_a, expl = apply_beregening_systeem_change(dict(state.last_answers or {}), action)
    return _apply_recalc(state, new_a, expl)


# ============================================================
# Sub-handler (losse onderdelen: component verwijderen)
# ============================================================

def _handle_losse_component_remove(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = losse_component_remove_menu_text(state.last_answers, state.last_costs)

    if is_cancel(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        menu_text, _ = lower_costs_menu_losse_text(state.last_answers)
        return state, [menu_text]

    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        menu_text, _ = lower_costs_menu_losse_text(state.last_answers)
        return state, [menu, menu_text]

    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        state.post_offer_stage = "lower_costs_menu"
        menu_text, _ = lower_costs_menu_losse_text(state.last_answers)
        return state, [menu_text]

    comp_key = mapping[picked]
    new_a, expl = apply_remove_losse_component(dict(state.last_answers or {}), comp_key)
    return _apply_recalc(state, new_a, expl)


# ============================================================
# Contact flow (3 stappen: naam → telefoon → email)
# ============================================================

_NAAM_INVALID = frozenset({"nee", "n", "geen", "x", "?", "-", "nvt", "n.v.t.", "onbekend", "anoniem"})
_NAAM_LETTER_RE = re.compile(r"[a-zA-ZÀ-ÖØ-öø-ÿ]")


def _is_terug(t: str) -> bool:
    return t.strip().lower() in {"terug", "back"}


def _handle_contact_naam(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if _is_terug(t_raw):
        state.post_offer_stage = "menu"
        return state, [_main_menu_text(state)]
    naam = t_raw.strip()
    if len(naam) < 2 or naam.lower() in _NAAM_INVALID or not _NAAM_LETTER_RE.search(naam):
        return state, ["Vul alstublieft uw naam in (bijv. Jan de Vries)."]
    state.contact_naam = naam
    state.post_offer_stage = "contact_telefoon"
    return state, [f"Bedankt, {state.contact_naam}! Wat is uw telefoonnummer?\n_(typ 'nee' als u dit liever niet deelt)_"]


def _handle_contact_telefoon(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if _is_terug(t_raw):
        state.post_offer_stage = "contact_naam"
        return state, ["Wat is uw naam?"]
    tel = t_raw.strip()
    if tel.lower() in ("overslaan", "skip", "-", "nvt", "n.v.t.", "nee"):
        state.contact_telefoon = None
    else:
        digits = re.sub(r"[\s\-\+\(\).]", "", tel)
        if len(digits) < 9 or not digits.lstrip("+").isdigit():
            return state, ["Vul alstublieft een geldig telefoonnummer in (bijv. 06-12345678), of typ 'nee'."]
        state.contact_telefoon = tel
    state.post_offer_stage = "contact_email"
    return state, ["En wat is uw e-mailadres?"]


def _handle_contact_email(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if _is_terug(t_raw):
        state.post_offer_stage = "contact_telefoon"
        return state, [f"Wat is uw telefoonnummer?\n_(typ 'nee' als u dit liever niet deelt)_"]
    email = t_raw.strip()
    if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]{2,}$", email):
        return state, ["Dat lijkt geen geldig e-mailadres. Kunt u een geldig adres invoeren? (bijv. naam@voorbeeld.nl)"]
    state.contact_email = email
    state.post_offer_stage = "contact_adres"
    return state, ["Wat is het adres van de tuin (straat + huisnummer)?\n_(typ 'nee' als u dit liever niet deelt)_"]


def _handle_contact_adres(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if _is_terug(t_raw):
        state.post_offer_stage = "contact_email"
        return state, ["En wat is uw e-mailadres?"]
    val = t_raw.strip()
    if val.lower() in ("overslaan", "skip", "-", "nvt", "n.v.t.", "nee"):
        state.contact_adres = None
    elif len(val) < 3:
        return state, ["Vul alstublieft een adres in (bijv. Dorpsstraat 12), of typ 'nee'."]
    else:
        state.contact_adres = val
    state.post_offer_stage = "contact_woonplaats"
    return state, ["In welke woonplaats woont u?"]


def _handle_contact_woonplaats(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if _is_terug(t_raw):
        state.post_offer_stage = "contact_adres"
        return state, ["Wat is het adres van de tuin (straat + huisnummer)?\n_(typ 'nee' als u dit liever niet deelt)_"]
    woonplaats = t_raw.strip()
    if len(woonplaats) < 2:
        return state, ["Vul alstublieft uw woonplaats in (bijv. Balkbrug)."]
    state.contact_woonplaats = woonplaats
    state.post_offer_stage = "contact_opmerking"
    return state, ["Heeft u nog opmerkingen of wensen? (optioneel, typ 'nee' om over te slaan)"]


def _handle_contact_opmerking(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if _is_terug(t_raw):
        state.post_offer_stage = "contact_woonplaats"
        return state, ["In welke woonplaats woont u?"]
    val = t_raw.strip()
    state.contact_opmerking = None if val.lower() == "nee" else val
    _submit_contact(state)
    state.post_offer_mode = False
    state.post_offer_stage = "end"
    state.ended = True
    state.end_reason = "contact_submitted"
    return state, [
        "✅ Aanvraag ontvangen! We nemen zo snel mogelijk contact met u op.\n\n"
        "Bedankt voor uw interesse in Veldman Hoveniers!"
    ]


def _submit_contact(state: ChatState) -> None:
    """Sla contactaanvraag op in DB en stuur notificaties naar de hovenier."""
    score, label, breakdown = _bereken_en_sla_leadscore(
        state, sessie_volledig=True, offerte_aangevraagd=True
    )

    email_sent_at = None
    if _DB:
        try:
            send_contact_email(
                naam=state.contact_naam or "",
                telefoon=state.contact_telefoon or "",
                email=state.contact_email or "",
                adres=state.contact_adres or "",
                woonplaats=state.contact_woonplaats or "",
                opmerking=state.contact_opmerking,
                costs=state.last_costs,
                flow_type=state.flow_type,
                leadscore=score,
                lead_label=label,
                score_breakdown=breakdown,
            )
            from datetime import datetime as _dt, timezone as _tz
            email_sent_at = _dt.now(_tz.utc)
        except Exception as exc:
            print(f"[mailer] Kon e-mail niet versturen: {exc}")

        log_contact_submission(
            session_id=state.session_id or "",
            naam=state.contact_naam or "",
            telefoon=state.contact_telefoon or "",
            email=state.contact_email or "",
            adres=state.contact_adres or "",
            woonplaats=state.contact_woonplaats or "",
            notitie=state.contact_opmerking,
            price_calculation_id=state.last_calc_id,
            email_sent_at=email_sent_at,
        )
        log_event(state.session_id or "", "contact_submitted", {
            "naam": state.contact_naam,
            "email": state.contact_email,
            "email_sent": email_sent_at is not None,
        })
        update_session_ended(state.session_id or "")
