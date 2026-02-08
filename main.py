# main.py

import os
import json
from dotenv import load_dotenv

from pricing import (
    PRIJZEN,
    estimate_tuinaanleg_costs,
    format_tuinaanleg_costs_for_customer,
)
from flow_tuinaanleg import TuinaanlegFlow

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
    parse_material_parts,   # ✅ NEW
    is_back,
    has_vlonder,
    has_erfafscheiding,
    soft_limit_message,
    limit_followup_text,
)

load_dotenv()

DEBUG_COSTS_JSON = os.getenv("DEBUG_COSTS_JSON", "").strip() in {"1", "true", "True", "yes", "YES"}

# =====================
# Flow / state
# =====================
flow = None

post_offer_mode = False
post_offer_stage = None  # "menu" | "lower_costs_menu" | "lc_*" | "limit_followup" | "contact_details" | "end"

last_answers = None
last_costs = None

MAX_RECALC = 5
recalc_count = 0

_pending_material_part = None  # ✅ kan nu str OF tuple zijn ("2" of ("2","3"))


def remaining_recalcs() -> int:
    return max(0, MAX_RECALC - recalc_count)


def looks_like_tuinaanleg_intent(text: str) -> bool:
    t = text.lower()
    triggers = [
        "tuinaanleg", "tuin aanleggen", "tuin aanleg", "tuin renoveren",
        "herinrichten", "nieuwe tuin", "aanleg", "tuin vernieuwen"
    ]
    return any(w in t for w in triggers)


def pretty_intake_summary(ans: dict) -> str:
    # (ongewijzigd, beknopt gehouden)
    return json.dumps(ans, ensure_ascii=False, indent=2)


def _ensure_prefix(explanation: str) -> str:
    """
    Zorgt dat de eerste zin overal consistent start met:
    '✅ Doorgevoerde kostenbesparing: ...'
    (ook als een apply_* functie nog oude tekst teruggeeft).
    """
    t = (explanation or "").strip()
    if not t:
        return "✅ Doorgevoerde kostenbesparing."
    low = t.lower()

    # als er al een "doorgevoerde kostenbesparing" in staat: laat met rust
    if "doorgevoerde kostenbesparing" in low:
        return t

    # veelvoorkomende oude starts omzetten
    if low.startswith("ik heb aangepast:"):
        rest = t.split(":", 1)[1].strip() if ":" in t else t
        return f"✅ Doorgevoerde kostenbesparing: {rest}"

    if low.startswith("ik heb de ") or low.startswith("ik heb het "):
        # bv "Ik heb de verhouding..." -> netjes prefixen
        return f"✅ Doorgevoerde kostenbesparing: {t[0].lower() + t[1:]}" if len(t) > 1 else "✅ Doorgevoerde kostenbesparing."

    # default
    return f"✅ Doorgevoerde kostenbesparing: {t}"


def _show_recalc_result(before_costs: dict, after_costs: dict, explanation: str) -> None:
    old_tr = before_costs.get("total_range_eur") or (0, 0)
    new_tr = after_costs.get("total_range_eur") or (0, 0)

    def eur(v):
        return f"€{int(v):,}".replace(",", ".")

    explanation = _ensure_prefix(explanation)

    print("Chatbot:", explanation)
    print()
    print(f"Chatbot: Oude indicatie: {eur(old_tr[0])} – {eur(old_tr[1])}")
    print(f"Chatbot: Nieuwe indicatie: {eur(new_tr[0])} – {eur(new_tr[1])}\n")

    if DEBUG_COSTS_JSON:
        print("📌 Debug kostenindicatie — JSON:")
        print(json.dumps(after_costs, ensure_ascii=False, indent=2))
        print()

    print(format_tuinaanleg_costs_for_customer(after_costs))
    print()


print("🤖 Hovenier-chatbot gestart (typ 'stop' om te stoppen)\n")
print("Chatbot: Hallo! 👋 Waar kan ik u mee helpen: ontwerp, aanleg of onderhoud?\n")

while True:
    user_input = input("U: ").strip()
    if not user_input:
        continue
    if user_input.lower() == "stop":
        print("Chatbot: Tot ziens! 👋")
        break

    try:
        # -------------------------
        # Post-offer menu
        # -------------------------
        if post_offer_mode:
            t_raw = user_input.strip()
            t_low = t_raw.lower()

            if t_low in {"contact", "offerte", "advies"}:
                post_offer_stage = "contact_details"
                print("Chatbot: Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?\n")
                continue

            if post_offer_stage == "limit_followup":
                if t_raw == "1":
                    post_offer_stage = "contact_details"
                    print("Chatbot: Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?\n")
                    continue
                if t_raw == "2":
                    print("Chatbot: Helemaal goed. Fijn dat u even heeft gekeken. 👋\n")
                    post_offer_mode = False
                    post_offer_stage = "end"
                    break

                print("Chatbot:", limit_followup_text(), "\n")
                continue

            if post_offer_stage == "menu":
                if t_raw == "1":
                    if remaining_recalcs() <= 0:
                        print("Chatbot:", soft_limit_message(), "\n")
                        post_offer_stage = "limit_followup"
                        print("Chatbot:", limit_followup_text(), "\n")
                        continue
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                if t_raw == "2":
                    post_offer_stage = "contact_details"
                    print("Chatbot: Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?\n")
                    continue

                if t_raw == "3":
                    print("Chatbot: Helemaal goed. Fijn dat u even heeft gekeken. 👋\n")
                    post_offer_mode = False
                    post_offer_stage = "end"
                    break

                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            # -------------------------
            # Categorie menu
            # -------------------------
            if post_offer_stage == "lower_costs_menu":
                if is_back(t_raw):
                    post_offer_stage = "menu"
                    print("Chatbot:", post_offer_choices_text(), "\n")
                    continue

                # dynamisch: 1..3 + optioneel vlonder/erf
                allowed = {"1", "2", "3"}
                dyn_v = None
                dyn_e = None

                idx = 4
                if has_vlonder(last_answers):
                    dyn_v = str(idx)
                    allowed.add(dyn_v)
                    idx += 1
                if has_erfafscheiding(last_answers):
                    dyn_e = str(idx)
                    allowed.add(dyn_e)

                if t_raw not in allowed:
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                if t_raw == "1":
                    menu, mapping = more_green_choice_text(last_answers, last_costs)
                    if not mapping:
                        print("Chatbot:", menu, "\n")
                        post_offer_stage = "lower_costs_menu"
                        print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                        continue
                    post_offer_stage = "lc_more_green_choice"
                    print("Chatbot:", menu, "\n")
                    continue

                if t_raw == "2":
                    menu, mapping = extras_select_menu_text(last_answers, last_costs)
                    if not mapping:
                        print("Chatbot:", menu, "\n")
                        post_offer_stage = "lower_costs_menu"
                        print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                        continue
                    post_offer_stage = "lc_extras_select"
                    print("Chatbot:", menu, "\n")
                    continue

                if t_raw == "3":
                    post_offer_stage = "lc_material_part"
                    print("Chatbot:", material_part_menu_text(last_answers), "\n")
                    continue

                if dyn_v and t_raw == dyn_v:
                    menu, mapping = vlonder_choice_menu_text(last_answers, last_costs)
                    if not mapping:
                        print("Chatbot:", menu, "\n")
                        post_offer_stage = "lower_costs_menu"
                        print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                        continue
                    post_offer_stage = "lc_vlonder_choice"
                    print("Chatbot:", menu, "\n")
                    continue

                if dyn_e and t_raw == dyn_e:
                    menu, mapping = erf_remove_select_menu_text(last_answers, last_costs)
                    if not mapping:
                        print("Chatbot:", menu, "\n")
                        post_offer_stage = "lower_costs_menu"
                        print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                        continue
                    post_offer_stage = "lc_erf_remove_select"
                    print("Chatbot:", menu, "\n")
                    continue

            # -------------------------
            # (1) ratio
            # -------------------------
            if post_offer_stage == "lc_more_green_choice":
                menu, mapping = more_green_choice_text(last_answers, last_costs)
                if not mapping:
                    print("Chatbot:", menu, "\n")
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
                if picked is None:
                    print("Chatbot:", menu, "\n")
                    continue
                if picked == "nee":
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                if remaining_recalcs() <= 0:
                    print("Chatbot:", soft_limit_message(), "\n")
                    post_offer_stage = "limit_followup"
                    print("Chatbot:", limit_followup_text(), "\n")
                    continue

                before_a = dict(last_answers or {})
                before_c = dict(last_costs or {})
                new_a, expl = apply_set_ratio(before_a, mapping[picked])

                recalc_count += 1
                new_c = estimate_tuinaanleg_costs(new_a)

                _show_recalc_result(before_c, new_c, expl)

                last_answers = dict(new_a)
                last_costs = dict(new_c)

                post_offer_stage = "menu"
                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            # -------------------------
            # (2) extras multi-select
            # -------------------------
            if post_offer_stage == "lc_extras_select":
                menu, mapping = extras_select_menu_text(last_answers, last_costs)
                if not mapping:
                    print("Chatbot:", menu, "\n")
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                if is_back(t_raw):
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                allowed_digits = tuple(mapping.keys())
                parsed = parse_multi_digits(t_raw, allowed=allowed_digits)
                if parsed is None:
                    print("Chatbot:", menu, "\n")
                    continue
                if parsed == ("nee",):
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                actions = [mapping[d] for d in parsed if d in mapping]
                if not actions:
                    print("Chatbot:", menu, "\n")
                    continue

                if remaining_recalcs() <= 0:
                    print("Chatbot:", soft_limit_message(), "\n")
                    post_offer_stage = "limit_followup"
                    print("Chatbot:", limit_followup_text(), "\n")
                    continue

                before_a = dict(last_answers or {})
                before_c = dict(last_costs or {})
                new_a, expl = apply_remove_selected_extras(before_a, actions)

                recalc_count += 1
                new_c = estimate_tuinaanleg_costs(new_a)
                _show_recalc_result(before_c, new_c, expl)

                last_answers = dict(new_a)
                last_costs = dict(new_c)

                post_offer_stage = "menu"
                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            # -------------------------
            # (3) materiaal: onderdelen (✅ multi-select 1/2/3, geen 4 meer)
            # -------------------------
            if post_offer_stage == "lc_material_part":
                if is_back(t_raw):
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                picked_parts = parse_material_parts(t_raw)  # ✅ NEW
                if picked_parts is None:
                    print("Chatbot:", material_part_menu_text(last_answers), "\n")
                    continue
                if picked_parts == ("nee",):
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                _pending_material_part = picked_parts  # ✅ tuple, bv ("2","3")
                menu, allowed_choices = material_choice_menu_text_cheaper(last_answers, last_costs, _pending_material_part)

                if not allowed_choices:
                    print("Chatbot:", menu, "\n")
                    post_offer_stage = "lc_material_part"
                    print("Chatbot:", material_part_menu_text(last_answers), "\n")
                    continue

                post_offer_stage = "lc_material_choice"
                print("Chatbot:", menu, "\n")
                continue

            # -------------------------
            # (3) materiaal: keuze (materiaaltype kiezen)
            # -------------------------
            if post_offer_stage == "lc_material_choice":
                menu, allowed_choices = material_choice_menu_text_cheaper(
                    last_answers,
                    last_costs,
                    _pending_material_part or ("1", "2", "3"),  # fallback (zou normaal niet nodig zijn)
                )
                if not allowed_choices:
                    print("Chatbot:", menu, "\n")
                    post_offer_stage = "lc_material_part"
                    print("Chatbot:", material_part_menu_text(last_answers), "\n")
                    continue

                picked = parse_single_digit(t_raw, allowed=tuple(sorted(allowed_choices)))
                if picked is None:
                    print("Chatbot:", menu, "\n")
                    continue
                if picked == "nee":
                    post_offer_stage = "lc_material_part"
                    print("Chatbot:", material_part_menu_text(last_answers), "\n")
                    continue

                if remaining_recalcs() <= 0:
                    print("Chatbot:", soft_limit_message(), "\n")
                    post_offer_stage = "limit_followup"
                    print("Chatbot:", limit_followup_text(), "\n")
                    continue

                before_a = dict(last_answers or {})
                before_c = dict(last_costs or {})
                new_a, expl = apply_material_change(before_a, _pending_material_part, picked)

                recalc_count += 1
                new_c = estimate_tuinaanleg_costs(new_a)
                _show_recalc_result(before_c, new_c, expl)

                last_answers = dict(new_a)
                last_costs = dict(new_c)
                _pending_material_part = None

                post_offer_stage = "menu"
                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            # -------------------------
            # (4) vlonder
            # -------------------------
            if post_offer_stage == "lc_vlonder_choice":
                menu, mapping = vlonder_choice_menu_text(last_answers, last_costs)
                if not mapping:
                    print("Chatbot:", menu, "\n")
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
                if picked is None:
                    print("Chatbot:", menu, "\n")
                    continue
                if picked == "nee":
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                if remaining_recalcs() <= 0:
                    print("Chatbot:", soft_limit_message(), "\n")
                    post_offer_stage = "limit_followup"
                    print("Chatbot:", limit_followup_text(), "\n")
                    continue

                before_a = dict(last_answers or {})
                before_c = dict(last_costs or {})
                new_a, expl = apply_vlonder_change(before_a, mapping[picked])

                recalc_count += 1
                new_c = estimate_tuinaanleg_costs(new_a)
                _show_recalc_result(before_c, new_c, expl)

                last_answers = dict(new_a)
                last_costs = dict(new_c)

                post_offer_stage = "menu"
                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            # -------------------------
            # (5) erf multi-select
            # -------------------------
            if post_offer_stage == "lc_erf_remove_select":
                menu, mapping = erf_remove_select_menu_text(last_answers, last_costs)
                if not mapping:
                    print("Chatbot:", menu, "\n")
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                if is_back(t_raw):
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                allowed_digits = tuple(mapping.keys())
                parsed = parse_multi_digits(t_raw, allowed=allowed_digits)
                if parsed is None:
                    print("Chatbot:", menu, "\n")
                    continue
                if parsed == ("nee",):
                    post_offer_stage = "lower_costs_menu"
                    print("Chatbot:", lower_costs_menu_text(last_answers), "\n")
                    continue

                actions = [mapping[d] for d in parsed if d in mapping]
                if not actions:
                    print("Chatbot:", menu, "\n")
                    continue

                if remaining_recalcs() <= 0:
                    print("Chatbot:", soft_limit_message(), "\n")
                    post_offer_stage = "limit_followup"
                    print("Chatbot:", limit_followup_text(), "\n")
                    continue

                before_a = dict(last_answers or {})
                before_c = dict(last_costs or {})
                new_a, expl = apply_erf_changes(before_a, actions)

                recalc_count += 1
                new_c = estimate_tuinaanleg_costs(new_a)
                _show_recalc_result(before_c, new_c, expl)

                last_answers = dict(new_a)
                last_costs = dict(new_c)

                post_offer_stage = "menu"
                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            if post_offer_stage == "contact_details":
                print("Chatbot: Dank u wel! We nemen zo snel mogelijk contact met u op!\n")
                post_offer_mode = False
                post_offer_stage = "end"
                break

        # -------------------------
        # Flow start detectie
        # -------------------------
        if flow is None and looks_like_tuinaanleg_intent(user_input):
            recalc_count = 0
            _pending_material_part = None
            flow = TuinaanlegFlow(prijzen=PRIJZEN)
            print("\nChatbot: Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.")
            print("Chatbot:", flow.get_question(), "\n")
            continue

        # -------------------------
        # Flow actief
        # -------------------------
        if flow is not None:
            reply, done = flow.handle(user_input)
            print("Chatbot:", reply, "\n")

            if done:
                costs = estimate_tuinaanleg_costs(flow.answers)

                if DEBUG_COSTS_JSON:
                    print("📌 Debug kostenindicatie — JSON:")
                    print(json.dumps(costs, ensure_ascii=False, indent=2))
                    print()

                print(format_tuinaanleg_costs_for_customer(costs))
                print()

                last_answers = dict(flow.answers)
                last_costs = dict(costs)
                flow = None

                post_offer_mode = True
                post_offer_stage = "menu"
                print("Chatbot:", post_offer_choices_text(), "\n")
            continue

        # fallback
        print("\nChatbot: Typ bijvoorbeeld: tuinaanleg\n")

    except Exception:
        print("Chatbot: Oeps, er ging iets mis. Probeer het later opnieuw.\n")
