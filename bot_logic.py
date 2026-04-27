# bot_logic.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from flow_tuinaanleg import TuinaanlegFlow
from pricing import PRIJZEN, estimate_tuinaanleg_costs, format_tuinaanleg_costs_for_customer
from savings import (
    MAX_RECALC_DEFAULT,
    post_offer_choices_text,
    lower_costs_menu_text,
    more_green_choice_text,
    extras_select_menu_text,
    material_part_menu_text,
    material_choice_menu_text_cheaper,
    vlonder_choice_menu_text,
    erf_remove_select_menu_text,
    apply_set_ratio,
    apply_remove_selected_extras,
    apply_material_change,
    apply_vlonder_change,
    apply_erf_changes,
    parse_multi_digits,
    parse_single_digit,
    parse_material_parts,
    is_back,
    has_vlonder,
    has_erfafscheiding,
    soft_limit_message,
    limit_followup_text,
)

MAX_RECALC = MAX_RECALC_DEFAULT

INITIAL_GREETING = (
    "Hallo! 👋 Ik help u graag met een vrijblijvende prijsindicatie voor uw tuinaanleg. "
    "In een paar korte vragen kom ik tot een inschatting op maat.\n\n"
    "Hoe groot is uw tuin in m²? (bijv. 80)"
)


@dataclass
class ChatState:
    flow: Optional[TuinaanlegFlow] = None
    post_offer_mode: bool = False
    post_offer_stage: Optional[str] = None  # "menu"|"lower_costs_menu"|"lc_*"|"limit_followup"|"contact_details"|"end"
    last_answers: Optional[Dict[str, Any]] = None
    last_costs: Optional[Dict[str, Any]] = None
    recalc_count: int = 0
    pending_material_part: Optional[Tuple] = None
    ended: bool = False


def make_initial_state() -> ChatState:
    return ChatState(flow=TuinaanlegFlow(prijzen=PRIJZEN))


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


def _remaining_recalcs(state: ChatState) -> int:
    return max(0, MAX_RECALC - state.recalc_count)


def _eur(v) -> str:
    return f"€{int(v):,}".replace(",", ".")


def _recalc_messages(before_costs: dict, after_costs: dict, explanation: str) -> List[str]:
    old_tr = before_costs.get("total_range_eur") or (0, 0)
    new_tr = after_costs.get("total_range_eur") or (0, 0)
    return [
        ensure_prefix(explanation),
        f"Oude indicatie: {_eur(old_tr[0])} – {_eur(old_tr[1])}",
        f"Nieuwe indicatie: {_eur(new_tr[0])} – {_eur(new_tr[1])}",
        format_tuinaanleg_costs_for_customer(after_costs),
    ]


# ============================================================
# Publieke entrypoint
# ============================================================

def handle_message(state: ChatState, user_text: str) -> Tuple[ChatState, List[str]]:
    """Verwerk één gebruikersbericht. Geeft (nieuwe_state, lijst_berichten) terug."""
    if state.ended:
        return state, []

    t_raw = user_text.strip()

    if state.post_offer_mode:
        return _handle_post_offer(state, t_raw)

    if state.flow is not None:
        return _handle_intake(state, t_raw)

    return state, []


# ============================================================
# Intake flow
# ============================================================

def _handle_intake(state: ChatState, user_text: str) -> Tuple[ChatState, List[str]]:
    flow = state.flow
    reply, done = flow.handle(user_text)
    msgs: List[str] = [reply]

    if done:
        costs = estimate_tuinaanleg_costs(flow.answers)
        msgs.append(format_tuinaanleg_costs_for_customer(costs))
        state.last_answers = dict(flow.answers)
        state.last_costs = dict(costs)
        state.flow = None
        state.post_offer_mode = True
        state.post_offer_stage = "menu"
        msgs.append(post_offer_choices_text())

    return state, msgs


# ============================================================
# Post-offer state machine
# ============================================================

def _handle_post_offer(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    t_low = t_raw.lower()

    # Globale snelkoppeling
    if t_low in {"contact", "offerte", "advies"}:
        state.post_offer_stage = "contact_details"
        return state, ["Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?"]

    stage = state.post_offer_stage

    if stage == "limit_followup":
        return _handle_limit_followup(state, t_raw)
    if stage == "menu":
        return _handle_main_menu(state, t_raw)
    if stage == "lower_costs_menu":
        return _handle_lower_costs_menu(state, t_raw)
    if stage == "lc_more_green_choice":
        return _handle_more_green_choice(state, t_raw)
    if stage == "lc_extras_select":
        return _handle_extras_select(state, t_raw)
    if stage == "lc_material_part":
        return _handle_material_part(state, t_raw)
    if stage == "lc_material_choice":
        return _handle_material_choice(state, t_raw)
    if stage == "lc_vlonder_choice":
        return _handle_vlonder_choice(state, t_raw)
    if stage == "lc_erf_remove_select":
        return _handle_erf_remove_select(state, t_raw)

    if stage == "contact_details":
        state.post_offer_mode = False
        state.post_offer_stage = "end"
        state.ended = True
        return state, ["Dank u wel! We nemen zo snel mogelijk contact met u op!"]

    # Fallback
    return state, [post_offer_choices_text()]


def _handle_limit_followup(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if t_raw == "1":
        state.post_offer_stage = "contact_details"
        return state, ["Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?"]
    if t_raw == "2":
        state.post_offer_mode = False
        state.post_offer_stage = "end"
        state.ended = True
        return state, ["Helemaal goed. Fijn dat u even heeft gekeken. 👋"]
    return state, [limit_followup_text()]


def _handle_main_menu(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if t_raw == "1":
        if _remaining_recalcs(state) <= 0:
            state.post_offer_stage = "limit_followup"
            return state, [soft_limit_message(), limit_followup_text()]
        state.post_offer_stage = "lower_costs_menu"
        return state, [lower_costs_menu_text(state.last_answers)]
    if t_raw == "2":
        state.post_offer_stage = "contact_details"
        return state, ["Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?"]
    if t_raw == "3":
        state.post_offer_mode = False
        state.post_offer_stage = "end"
        state.ended = True
        return state, ["Helemaal goed. Fijn dat u even heeft gekeken. 👋"]
    return state, [post_offer_choices_text()]


def _handle_lower_costs_menu(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if is_back(t_raw):
        state.post_offer_stage = "menu"
        return state, [post_offer_choices_text()]

    allowed = {"1", "2", "3"}
    dyn_v = dyn_e = None
    idx = 4
    if has_vlonder(state.last_answers):
        dyn_v = str(idx); allowed.add(dyn_v); idx += 1
    if has_erfafscheiding(state.last_answers):
        dyn_e = str(idx); allowed.add(dyn_e)

    if t_raw not in allowed:
        return state, [lower_costs_menu_text(state.last_answers)]

    if t_raw == "1":
        menu, mapping = more_green_choice_text(state.last_answers, state.last_costs)
        if not mapping:
            return state, [menu, lower_costs_menu_text(state.last_answers)]
        state.post_offer_stage = "lc_more_green_choice"
        return state, [menu]

    if t_raw == "2":
        menu, mapping = extras_select_menu_text(state.last_answers, state.last_costs)
        if not mapping:
            return state, [menu, lower_costs_menu_text(state.last_answers)]
        state.post_offer_stage = "lc_extras_select"
        return state, [menu]

    if t_raw == "3":
        state.post_offer_stage = "lc_material_part"
        return state, [material_part_menu_text(state.last_answers)]

    if dyn_v and t_raw == dyn_v:
        menu, mapping = vlonder_choice_menu_text(state.last_answers, state.last_costs)
        if not mapping:
            return state, [menu, lower_costs_menu_text(state.last_answers)]
        state.post_offer_stage = "lc_vlonder_choice"
        return state, [menu]

    if dyn_e and t_raw == dyn_e:
        menu, mapping = erf_remove_select_menu_text(state.last_answers, state.last_costs)
        if not mapping:
            return state, [menu, lower_costs_menu_text(state.last_answers)]
        state.post_offer_stage = "lc_erf_remove_select"
        return state, [menu]

    return state, [lower_costs_menu_text(state.last_answers)]


# ---- Herberekening helpers ----

def _check_recalc_limit(state: ChatState) -> Optional[Tuple[ChatState, List[str]]]:
    if _remaining_recalcs(state) <= 0:
        state.post_offer_stage = "limit_followup"
        return state, [soft_limit_message(), limit_followup_text()]
    return None


def _apply_recalc(state: ChatState, new_answers: dict, explanation: str) -> Tuple[ChatState, List[str]]:
    before_costs = dict(state.last_costs or {})
    new_costs = estimate_tuinaanleg_costs(new_answers)
    msgs = _recalc_messages(before_costs, new_costs, explanation)
    state.recalc_count += 1
    state.last_answers = dict(new_answers)
    state.last_costs = dict(new_costs)
    state.post_offer_stage = "menu"
    msgs.append(post_offer_choices_text())
    return state, msgs


# ---- Sub-handlers ----

def _handle_more_green_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = more_green_choice_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, lower_costs_menu_text(state.last_answers)]

    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        state.post_offer_stage = "lower_costs_menu"
        return state, [lower_costs_menu_text(state.last_answers)]

    limit = _check_recalc_limit(state)
    if limit:
        return limit

    new_a, expl = apply_set_ratio(dict(state.last_answers or {}), mapping[picked])
    return _apply_recalc(state, new_a, expl)


def _handle_extras_select(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = extras_select_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, lower_costs_menu_text(state.last_answers)]

    if is_back(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [lower_costs_menu_text(state.last_answers)]

    parsed = parse_multi_digits(t_raw, allowed=tuple(mapping.keys()))
    if parsed is None:
        return state, [menu]
    if parsed == ("nee",):
        state.post_offer_stage = "lower_costs_menu"
        return state, [lower_costs_menu_text(state.last_answers)]

    actions = [mapping[d] for d in parsed if d in mapping]
    if not actions:
        return state, [menu]

    limit = _check_recalc_limit(state)
    if limit:
        return limit

    new_a, expl = apply_remove_selected_extras(dict(state.last_answers or {}), actions)
    return _apply_recalc(state, new_a, expl)


def _handle_material_part(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    if is_back(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [lower_costs_menu_text(state.last_answers)]

    picked_parts = parse_material_parts(t_raw)
    if picked_parts is None:
        return state, [material_part_menu_text(state.last_answers)]
    if picked_parts == ("nee",):
        state.post_offer_stage = "lower_costs_menu"
        return state, [lower_costs_menu_text(state.last_answers)]

    state.pending_material_part = picked_parts
    menu, allowed_choices = material_choice_menu_text_cheaper(
        state.last_answers, state.last_costs, picked_parts
    )
    if not allowed_choices:
        state.post_offer_stage = "lc_material_part"
        return state, [menu, material_part_menu_text(state.last_answers)]

    state.post_offer_stage = "lc_material_choice"
    return state, [menu]


def _handle_material_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    part = state.pending_material_part or ("1", "2", "3")
    menu, allowed_choices = material_choice_menu_text_cheaper(
        state.last_answers, state.last_costs, part
    )
    if not allowed_choices:
        state.post_offer_stage = "lc_material_part"
        return state, [menu, material_part_menu_text(state.last_answers)]

    picked = parse_single_digit(t_raw, allowed=tuple(sorted(allowed_choices)))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        state.post_offer_stage = "lc_material_part"
        return state, [material_part_menu_text(state.last_answers)]

    limit = _check_recalc_limit(state)
    if limit:
        return limit

    new_a, expl = apply_material_change(dict(state.last_answers or {}), part, picked)
    state.pending_material_part = None
    return _apply_recalc(state, new_a, expl)


def _handle_vlonder_choice(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = vlonder_choice_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, lower_costs_menu_text(state.last_answers)]

    picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
    if picked is None:
        return state, [menu]
    if picked == "nee":
        state.post_offer_stage = "lower_costs_menu"
        return state, [lower_costs_menu_text(state.last_answers)]

    limit = _check_recalc_limit(state)
    if limit:
        return limit

    new_a, expl = apply_vlonder_change(dict(state.last_answers or {}), mapping[picked])
    return _apply_recalc(state, new_a, expl)


def _handle_erf_remove_select(state: ChatState, t_raw: str) -> Tuple[ChatState, List[str]]:
    menu, mapping = erf_remove_select_menu_text(state.last_answers, state.last_costs)
    if not mapping:
        state.post_offer_stage = "lower_costs_menu"
        return state, [menu, lower_costs_menu_text(state.last_answers)]

    if is_back(t_raw):
        state.post_offer_stage = "lower_costs_menu"
        return state, [lower_costs_menu_text(state.last_answers)]

    parsed = parse_multi_digits(t_raw, allowed=tuple(mapping.keys()))
    if parsed is None:
        return state, [menu]
    if parsed == ("nee",):
        state.post_offer_stage = "lower_costs_menu"
        return state, [lower_costs_menu_text(state.last_answers)]

    actions = [mapping[d] for d in parsed if d in mapping]
    if not actions:
        return state, [menu]

    limit = _check_recalc_limit(state)
    if limit:
        return limit

    new_a, expl = apply_erf_changes(dict(state.last_answers or {}), actions)
    return _apply_recalc(state, new_a, expl)
