# app.py

import streamlit as st

from flow_tuinaanleg import TuinaanlegFlow
from pricing import PRIJZEN, estimate_tuinaanleg_costs, format_tuinaanleg_costs_for_customer
from bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON

from savings import (
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
    parse_material_parts,   # ✅ NEW
    is_back,
    has_vlonder,
    has_erfafscheiding,
    soft_limit_message,
    limit_followup_text,
)

# =====================
# Config
# =====================
st.set_page_config(page_title=f"{BEDRIJFSNAAM} – Tuinaanleg demo", page_icon="🌿")
st.title("🌿 Tuinaanleg prijsindicatie (demo)")
st.caption(f"{BEDRIJFSNAAM} • {REGIO}")

MAX_RECALC = 5


# =====================
# Render helper (fix: netjes onder elkaar)
# =====================
def render_text(text: str) -> None:
    """
    Streamlit markdown kan soms newlines 'samenvoegen' afhankelijk van context.
    Met '  \\n' forceren we harde line breaks.
    """
    safe = (text or "").replace("\n", "  \n")
    st.markdown(safe)


def remaining_recalcs() -> int:
    return max(0, MAX_RECALC - st.session_state.recalc_count)


def ensure_prefix(explanation: str) -> str:
    """
    Zorgt dat de eerste zin overal consistent start met:
    '✅ Doorgevoerde kostenbesparing: ...'
    (ook als een apply_* functie nog oude tekst teruggeeft).
    """
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


# =====================
# Session init
# =====================
if "flow" not in st.session_state:
    st.session_state.flow = TuinaanlegFlow(prijzen=PRIJZEN)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": (
            "Hallo! Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.\n\n"
            "Hoe groot is uw tuin in m²? (geef een getal)"
        )
    }]

if "done" not in st.session_state:
    st.session_state.done = False

if "post_offer_mode" not in st.session_state:
    st.session_state.post_offer_mode = False

if "post_offer_stage" not in st.session_state:
    st.session_state.post_offer_stage = None
    # "menu" | "lower_costs_menu" | "lc_more_green_choice" | "lc_extras_select"
    # "lc_material_part" | "lc_material_choice" | "lc_vlonder_choice" | "lc_erf_remove_select"
    # "limit_followup" | "contact_details" | "end"

if "last_answers" not in st.session_state:
    st.session_state.last_answers = None

if "last_costs" not in st.session_state:
    st.session_state.last_costs = None

if "recalc_count" not in st.session_state:
    st.session_state.recalc_count = 0

if "_pending_material_part" not in st.session_state:
    st.session_state._pending_material_part = None  # ✅ kan nu tuple ("2","3")


# =====================
# Sidebar
# =====================
with st.sidebar:
    st.subheader("Demo controls")
    if st.button("🔄 Reset gesprek", use_container_width=True):
        st.session_state.flow = TuinaanlegFlow(prijzen=PRIJZEN)
        st.session_state.messages = [{
            "role": "assistant",
            "content": (
                "Hoi! Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.\n\n"
                "Hoe groot is uw tuin in m²? (geef een getal)"
            )
        }]
        st.session_state.done = False
        st.session_state.post_offer_mode = False
        st.session_state.post_offer_stage = None
        st.session_state.last_answers = None
        st.session_state.last_costs = None
        st.session_state.recalc_count = 0
        st.session_state._pending_material_part = None
        st.rerun()

    st.divider()
    st.write("**Contact:**")
    st.write(f"- Email: {CONTACT_EMAIL}")
    st.write(f"- Telefoon: {CONTACT_TELEFOON}")
    st.caption("Tip: typ **nee** om terug te gaan in de bespaar-menu’s.")


# =====================
# Render chat history
# =====================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        render_text(msg["content"])


# =====================
# Chat input
# =====================
user_text = st.chat_input("Typ je antwoord…")
if not user_text:
    st.stop()

st.session_state.messages.append({"role": "user", "content": user_text})
t_raw = user_text.strip()
t_low = t_raw.lower()


def push_assistant(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})


# -----------------------------------------
# Post-offer menu logic
# -----------------------------------------
if st.session_state.post_offer_mode:
    # global contact shortcut
    if t_low in {"contact", "offerte", "advies"}:
        st.session_state.post_offer_stage = "contact_details"
        push_assistant("Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?")
        st.rerun()

    # limit follow-up
    if st.session_state.post_offer_stage == "limit_followup":
        if t_raw == "1":
            st.session_state.post_offer_stage = "contact_details"
            push_assistant("Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?")
            st.rerun()
        elif t_raw == "2":
            push_assistant("Helemaal goed. Fijn dat u even heeft gekeken. 👋")
            st.session_state.post_offer_mode = False
            st.session_state.post_offer_stage = "end"
            st.rerun()
        else:
            push_assistant(limit_followup_text())
            st.rerun()

    # main menu
    if st.session_state.post_offer_stage == "menu":
        if t_raw == "1":
            if remaining_recalcs() <= 0:
                push_assistant(soft_limit_message())
                st.session_state.post_offer_stage = "limit_followup"
                push_assistant(limit_followup_text())
                st.rerun()

            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        elif t_raw == "2":
            st.session_state.post_offer_stage = "contact_details"
            push_assistant("Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?")
            st.rerun()

        elif t_raw == "3":
            push_assistant("Helemaal goed. Fijn dat u even heeft gekeken. 👋")
            st.session_state.post_offer_mode = False
            st.session_state.post_offer_stage = "end"
            st.rerun()

        else:
            push_assistant(post_offer_choices_text())
            st.rerun()

    # category menu
    if st.session_state.post_offer_stage == "lower_costs_menu":
        if is_back(t_raw):
            st.session_state.post_offer_stage = "menu"
            push_assistant(post_offer_choices_text())
            st.rerun()

        # dynamic numbering 1..3 + optional vlonder/erf
        allowed = {"1", "2", "3"}
        dyn_v = None
        dyn_e = None
        idx = 4
        if has_vlonder(st.session_state.last_answers):
            dyn_v = str(idx)
            allowed.add(dyn_v)
            idx += 1
        if has_erfafscheiding(st.session_state.last_answers):
            dyn_e = str(idx)
            allowed.add(dyn_e)

        if t_raw not in allowed:
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        if t_raw == "1":
            menu, mapping = more_green_choice_text(st.session_state.last_answers, st.session_state.last_costs)
            if not mapping:
                push_assistant(menu)
                push_assistant(lower_costs_menu_text(st.session_state.last_answers))
                st.rerun()
            st.session_state.post_offer_stage = "lc_more_green_choice"
            push_assistant(menu)
            st.rerun()

        if t_raw == "2":
            menu, mapping = extras_select_menu_text(st.session_state.last_answers, st.session_state.last_costs)
            if not mapping:
                push_assistant(menu)
                push_assistant(lower_costs_menu_text(st.session_state.last_answers))
                st.rerun()
            st.session_state.post_offer_stage = "lc_extras_select"
            push_assistant(menu)
            st.rerun()

        if t_raw == "3":
            st.session_state.post_offer_stage = "lc_material_part"
            push_assistant(material_part_menu_text(st.session_state.last_answers))
            st.rerun()

        if dyn_v and t_raw == dyn_v:
            menu, mapping = vlonder_choice_menu_text(st.session_state.last_answers, st.session_state.last_costs)
            if not mapping:
                push_assistant(menu)
                push_assistant(lower_costs_menu_text(st.session_state.last_answers))
                st.rerun()
            st.session_state.post_offer_stage = "lc_vlonder_choice"
            push_assistant(menu)
            st.rerun()

        if dyn_e and t_raw == dyn_e:
            menu, mapping = erf_remove_select_menu_text(st.session_state.last_answers, st.session_state.last_costs)
            if not mapping:
                push_assistant(menu)
                push_assistant(lower_costs_menu_text(st.session_state.last_answers))
                st.rerun()
            st.session_state.post_offer_stage = "lc_erf_remove_select"
            push_assistant(menu)
            st.rerun()

    # (1) ratio
    if st.session_state.post_offer_stage == "lc_more_green_choice":
        menu, mapping = more_green_choice_text(st.session_state.last_answers, st.session_state.last_costs)
        if not mapping:
            push_assistant(menu)
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            push_assistant(menu)
            st.rerun()
        if picked == "nee":
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        if remaining_recalcs() <= 0:
            push_assistant(soft_limit_message())
            st.session_state.post_offer_stage = "limit_followup"
            push_assistant(limit_followup_text())
            st.rerun()

        before_a = dict(st.session_state.last_answers or {})
        new_a, expl = apply_set_ratio(before_a, mapping[picked])

        st.session_state.recalc_count += 1
        new_c = estimate_tuinaanleg_costs(new_a)

        push_assistant(ensure_prefix(expl))
        push_assistant(format_tuinaanleg_costs_for_customer(new_c))

        st.session_state.last_answers = dict(new_a)
        st.session_state.last_costs = dict(new_c)

        st.session_state.post_offer_stage = "menu"
        push_assistant(post_offer_choices_text())
        st.rerun()

    # (2) extras multi-select
    if st.session_state.post_offer_stage == "lc_extras_select":
        menu, mapping = extras_select_menu_text(st.session_state.last_answers, st.session_state.last_costs)
        if not mapping:
            push_assistant(menu)
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        if is_back(t_raw):
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        parsed = parse_multi_digits(t_raw, allowed=tuple(mapping.keys()))
        if parsed is None:
            push_assistant(menu)
            st.rerun()
        if parsed == ("nee",):
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        actions = [mapping[d] for d in parsed if d in mapping]
        if not actions:
            push_assistant(menu)
            st.rerun()

        if remaining_recalcs() <= 0:
            push_assistant(soft_limit_message())
            st.session_state.post_offer_stage = "limit_followup"
            push_assistant(limit_followup_text())
            st.rerun()

        before_a = dict(st.session_state.last_answers or {})
        new_a, expl = apply_remove_selected_extras(before_a, actions)

        st.session_state.recalc_count += 1
        new_c = estimate_tuinaanleg_costs(new_a)

        push_assistant(ensure_prefix(expl))
        push_assistant(format_tuinaanleg_costs_for_customer(new_c))

        st.session_state.last_answers = dict(new_a)
        st.session_state.last_costs = dict(new_c)

        st.session_state.post_offer_stage = "menu"
        push_assistant(post_offer_choices_text())
        st.rerun()

    # (3) material part (✅ multi-select 1/2/3, geen 4 meer)
    if st.session_state.post_offer_stage == "lc_material_part":
        if is_back(t_raw):
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        picked_parts = parse_material_parts(t_raw)  # ✅ NEW
        if picked_parts is None:
            push_assistant(material_part_menu_text(st.session_state.last_answers))
            st.rerun()
        if picked_parts == ("nee",):
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        st.session_state._pending_material_part = picked_parts
        menu, allowed_choices = material_choice_menu_text_cheaper(
            st.session_state.last_answers, st.session_state.last_costs, picked_parts
        )
        if not allowed_choices:
            push_assistant(menu)
            push_assistant(material_part_menu_text(st.session_state.last_answers))
            st.rerun()

        st.session_state.post_offer_stage = "lc_material_choice"
        push_assistant(menu)
        st.rerun()

    # (3) material choice
    if st.session_state.post_offer_stage == "lc_material_choice":
        part = st.session_state._pending_material_part or ("1", "2", "3")
        menu, allowed_choices = material_choice_menu_text_cheaper(
            st.session_state.last_answers, st.session_state.last_costs, part
        )
        if not allowed_choices:
            push_assistant(menu)
            st.session_state.post_offer_stage = "lc_material_part"
            push_assistant(material_part_menu_text(st.session_state.last_answers))
            st.rerun()

        picked = parse_single_digit(t_raw, allowed=tuple(sorted(allowed_choices)))
        if picked is None:
            push_assistant(menu)
            st.rerun()
        if picked == "nee":
            st.session_state.post_offer_stage = "lc_material_part"
            push_assistant(material_part_menu_text(st.session_state.last_answers))
            st.rerun()

        if remaining_recalcs() <= 0:
            push_assistant(soft_limit_message())
            st.session_state.post_offer_stage = "limit_followup"
            push_assistant(limit_followup_text())
            st.rerun()

        before_a = dict(st.session_state.last_answers or {})
        new_a, expl = apply_material_change(before_a, part, picked)

        st.session_state.recalc_count += 1
        new_c = estimate_tuinaanleg_costs(new_a)

        push_assistant(ensure_prefix(expl))
        push_assistant(format_tuinaanleg_costs_for_customer(new_c))

        st.session_state.last_answers = dict(new_a)
        st.session_state.last_costs = dict(new_c)
        st.session_state._pending_material_part = None

        st.session_state.post_offer_stage = "menu"
        push_assistant(post_offer_choices_text())
        st.rerun()

    # (4) vlonder
    if st.session_state.post_offer_stage == "lc_vlonder_choice":
        menu, mapping = vlonder_choice_menu_text(st.session_state.last_answers, st.session_state.last_costs)
        if not mapping:
            push_assistant(menu)
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            push_assistant(menu)
            st.rerun()
        if picked == "nee":
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        if remaining_recalcs() <= 0:
            push_assistant(soft_limit_message())
            st.session_state.post_offer_stage = "limit_followup"
            push_assistant(limit_followup_text())
            st.rerun()

        before_a = dict(st.session_state.last_answers or {})
        new_a, expl = apply_vlonder_change(before_a, mapping[picked])

        st.session_state.recalc_count += 1
        new_c = estimate_tuinaanleg_costs(new_a)

        push_assistant(ensure_prefix(expl))
        push_assistant(format_tuinaanleg_costs_for_customer(new_c))

        st.session_state.last_answers = dict(new_a)
        st.session_state.last_costs = dict(new_c)

        st.session_state.post_offer_stage = "menu"
        push_assistant(post_offer_choices_text())
        st.rerun()

    # (5) erf multi-select
    if st.session_state.post_offer_stage == "lc_erf_remove_select":
        menu, mapping = erf_remove_select_menu_text(st.session_state.last_answers, st.session_state.last_costs)
        if not mapping:
            push_assistant(menu)
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        if is_back(t_raw):
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        parsed = parse_multi_digits(t_raw, allowed=tuple(mapping.keys()))
        if parsed is None:
            push_assistant(menu)
            st.rerun()
        if parsed == ("nee",):
            st.session_state.post_offer_stage = "lower_costs_menu"
            push_assistant(lower_costs_menu_text(st.session_state.last_answers))
            st.rerun()

        actions = [mapping[d] for d in parsed if d in mapping]
        if not actions:
            push_assistant(menu)
            st.rerun()

        if remaining_recalcs() <= 0:
            push_assistant(soft_limit_message())
            st.session_state.post_offer_stage = "limit_followup"
            push_assistant(limit_followup_text())
            st.rerun()

        before_a = dict(st.session_state.last_answers or {})
        new_a, expl = apply_erf_changes(before_a, actions)

        st.session_state.recalc_count += 1
        new_c = estimate_tuinaanleg_costs(new_a)

        push_assistant(ensure_prefix(expl))
        push_assistant(format_tuinaanleg_costs_for_customer(new_c))

        st.session_state.last_answers = dict(new_a)
        st.session_state.last_costs = dict(new_c)

        st.session_state.post_offer_stage = "menu"
        push_assistant(post_offer_choices_text())
        st.rerun()

    # contact details
    if st.session_state.post_offer_stage == "contact_details":
        push_assistant("Dank u wel! We nemen zo snel mogelijk contact met u op!")
        st.session_state.post_offer_mode = False
        st.session_state.post_offer_stage = "end"
        st.rerun()


# -----------------------------------------
# Flow logic (intake)
# -----------------------------------------
if not st.session_state.done and not st.session_state.post_offer_mode:
    reply, done = st.session_state.flow.handle(user_text)
    push_assistant(reply)
    st.session_state.done = done

    if done:
        ans = st.session_state.flow.answers
        costs = estimate_tuinaanleg_costs(ans)

        push_assistant(format_tuinaanleg_costs_for_customer(costs))

        st.session_state.last_answers = dict(ans)
        st.session_state.last_costs = dict(costs)

        st.session_state.post_offer_mode = True
        st.session_state.post_offer_stage = "menu"
        push_assistant(post_offer_choices_text())

    st.rerun()
