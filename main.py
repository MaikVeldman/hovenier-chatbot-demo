# main.py

import os
import json
from dotenv import load_dotenv

from pricing import (
    PRIJZEN,  # ✅ nodig voor flow prijs-tekst
    get_price_quote,  # (nog niet gebruikt, maar laten staan)
    estimate_tuinaanleg_costs,
    format_tuinaanleg_costs_for_customer,
)
from flow_tuinaanleg import TuinaanlegFlow

load_dotenv()

# =====================
# Flow / state
# =====================
flow = None  # wordt TuinaanlegFlow zodra iemand tuinaanleg-intent heeft

# Post-offer menu (na prijsindicatie)
post_offer_mode = False
post_offer_stage = None  # "choice" | "recalc" | "contact_ask" | "contact_details"
last_answers = None
last_costs = None

# ✅ Recalc limiter
MAX_RECALC = 3          # maximaal aantal herberekeningen
recalc_count = 0        # hoe vaak al herberekend in deze sessie

# =====================
# Debug flags
# =====================
DEBUG_COSTS_JSON = os.getenv("DEBUG_COSTS_JSON", "").strip() in {"1", "true", "True", "yes", "YES"}


# =====================
# Helpers
# =====================
def looks_like_tuinaanleg_intent(text: str) -> bool:
    t = text.lower()
    triggers = [
        "tuinaanleg", "tuin aanleggen", "tuin aanleg", "tuin renoveren",
        "herinrichten", "nieuwe tuin", "aanleg", "tuin vernieuwen"
    ]
    return any(w in t for w in triggers)


def map_numeric_menu_to_valid_input(user_text: str, step_index: int) -> str:
    """Flow handelt mapping/validatie; hier geen mapping nodig."""
    return user_text


def safe_get_price_quote(price_keys: list) -> dict:
    """Voorkomt crashes als er keys niet bestaan."""
    try:
        return get_price_quote(price_keys)
    except Exception as e:
        return {"error": f"get_price_quote failed: {str(e)}", "price_keys": price_keys}


def is_yes(text: str) -> bool:
    return text.strip().lower() in {"ja", "j", "yes", "y"}


def is_no(text: str) -> bool:
    return text.strip().lower() in {"nee", "n", "no"}


def ask_yes_no(question: str) -> str:
    return f"{question} (ja/nee)"


def remaining_recalcs() -> int:
    return max(0, MAX_RECALC - recalc_count)


def ratio_label_bestrating_groen(v: str | None) -> str:
    mapping = {
        "70_30": "70/30 (veel bestrating)",
        "50_50": "50/50 (gemengd)",
        "30_70": "30/70 (veel groen)",
        None: "—",
        "": "—",
    }
    return mapping.get(v, str(v))


def ratio_label_gazon_beplanting(v: str | None) -> str:
    mapping = {
        "70_30": "70/30 (veel gazon)",
        "50_50": "50/50 (gemengd)",
        "30_70": "30/70 (veel beplanting)",
        None: "—",
        "": "—",
    }
    return mapping.get(v, str(v))


def bestrating_label(v: str | None) -> str:
    mapping = {
        "beton": "beton",
        "gebakken": "gebakken klinkers",
        "keramiek": "keramiek",
        "grind": "grind",
        None: "—",
        "": "—",
    }
    return mapping.get(v, str(v))


def vlonder_type_label(v: str | None) -> str:
    mapping = {
        "zachthout": "zachthout (bijv. Douglas)",
        "hardhout": "hardhout",
        "composiet": "composiet",
        None: "—",
        "": "—",
    }
    return mapping.get(v, str(v))


def yn(v) -> str:
    if v is True:
        return "ja"
    if v is False:
        return "nee"
    return "—"


def post_offer_choices_text() -> str:
    return (
        "Hoe wilt u verder?\n"
        "1) Kijken of er keuzes zijn om de kosten te verlagen\n"
        "2) Contact voor offerte op maat (vrijblijvend)\n"
        "3) Het hierbij laten\n"
        "\n"
        "Reageer met 1, 2 of 3."
    )


# =====================
# ✅ UPDATED: Intake summary (incl. erfafscheiding items + beregening scope)
# =====================
def pretty_intake_summary(ans: dict) -> str:
    m2 = ans.get("tuin_m2")
    ratio_bg = ratio_label_bestrating_groen(ans.get("verhouding_bestrating_groen"))
    ratio_gb = ratio_label_gazon_beplanting(ans.get("verhouding_gazon_beplanting"))

    mat_oprit = bestrating_label(ans.get("materiaal_oprit"))
    mat_paden = bestrating_label(ans.get("materiaal_paden"))
    mat_terras = bestrating_label(ans.get("materiaal_terras"))

    voegen = yn(ans.get("onkruidwerend_gevoegd"))
    overkapping = yn(ans.get("overkapping"))
    verlichting = yn(ans.get("verlichting"))

    overige = ans.get("overige_wensen")
    if overige in (None, [], ""):
        overige_list: list[str] = []
        overige_raw_list: list[str] = []
    elif isinstance(overige, list):
        overige_raw_list = [str(x).strip() for x in overige if str(x).strip()]
        overige_list = [x.lower() for x in overige_raw_list]
    else:
        overige_raw_list = [str(overige).strip()]
        overige_list = [str(overige).strip().lower()]

    lines: list[str] = []
    lines.append(f"- Oppervlakte: {m2} m²")
    lines.append(f"- Verhouding bestrating/groen: {ratio_bg}")
    lines.append(f"- Groen verdeling (gazon/beplanting): {ratio_gb}")
    lines.append("- Materialen bestrating:")
    lines.append(f"  - Oprit: {mat_oprit}")
    lines.append(f"  - Paden: {mat_paden}")
    lines.append(f"  - Terras: {mat_terras}")
    lines.append(f"- Voegen (onkruidwerend): {voegen}")
    lines.append(f"- Overkapping: {overkapping}")
    lines.append(f"- Verlichting: {verlichting}")

    overige_set = set(overige_list)

    if "vlonder" in overige_set:
        vt = vlonder_type_label(ans.get("vlonder_type"))
        lines.append(f"- Vlonder ({vt})")

    if "erfafscheiding" in overige_set:
        items = ans.get("erfafscheiding_items") or []
        type_label_map = {
            "haag": "Haag",
            "betonschutting": "Betonschutting",
            "design_schutting": "Design schutting",
        }
        if not items:
            lines.append("- Erfafscheiding")
        else:
            for i, it in enumerate(items, start=1):
                t = (it.get("type") or "").strip().lower()
                meters = it.get("meter")
                poortdeur_val = it.get("poortdeur")

                t_label = type_label_map.get(t, "Erfafscheiding")
                line = f"- Erfafscheiding #{i}: {t_label}"
                if meters not in (None, "", 0):
                    line += f" ({meters} m¹)"
                lines.append(line)

                if t in ("betonschutting", "design_schutting"):
                    lines.append(f"  - Poortdeur: {yn(poortdeur_val)}")

    if "beregening" in overige_set:
        scope = (ans.get("beregening_scope") or "").strip().lower()
        scope_label_map = {
            "gazon": "alleen gazon",
            "beplanting": "alleen beplanting",
            "allebei": "gazon én beplanting",
        }
        scope_label = scope_label_map.get(scope, "—")
        if scope and scope_label != "—":
            lines.append(f"- Beregening ({scope_label})")
        else:
            lines.append("- Beregening")

    known_map = {
        "zwembad": "Zwembad",
        "vijver": "Vijver",
    }
    for key, label in known_map.items():
        if key in overige_set:
            lines.append(f"- {label}")

    skip_tags = {
        "erfafscheiding", "vlonder", "beregening", "zwembad", "vijver", "overig",
        "haag", "betonschutting", "design schutting", "design_schutting", "poort", "poortdeur"
    }
    for item in overige_raw_list:
        low = item.lower().strip()
        if low in skip_tags:
            continue
        if low in overige_set:
            continue
        lines.append(f"- {item}")

    return "\n".join(lines)


def db_reply_or_none(user_input: str) -> str | None:
    """
    ✅ Hier komt straks jouw eigen database/regels.
    Voor nu een simpele, veilige fallback (geen AI).
    """
    t = user_input.strip().lower()

    if "openingstijd" in t or "open" in t:
        return "We werken op afspraak. Wilt u tuinaanleg, onderhoud of ontwerp?"
    if "telefoon" in t or "nummer" in t:
        return "Wilt u tuinaanleg, onderhoud of ontwerp? Dan kan ik u verder helpen via de juiste flow."
    if "prijs" in t or "kosten" in t:
        return "Om u te helpen inschatten of dit bij uw wensen past kan ik een globale indicatie maken. Gaat het om tuinaanleg of onderhoud?"

    return None


def no_ai_fallback_message() -> str:
    return (
        "Ik kan alleen antwoorden via mijn vaste intake/keuzemenu.\n"
        "Typ bijvoorbeeld:\n"
        "- tuinaanleg\n"
        "- onderhoud\n"
        "- ontwerp"
    )


# =====================
# Console demo
# =====================
print("🤖 Hovenier-chatbot gestart (typ 'stop' om te stoppen)\n")
print("Chatbot: Hoi! 👋 Waar kan ik u mee helpen: ontwerp, aanleg of onderhoud?\n")

while True:
    user_input = input("U: ").strip()

    if not user_input:
        continue

    if user_input.lower() == "stop":
        print("Chatbot: Tot ziens! 👋")
        break

    try:
        # -------------------------
        # Post-offer menu (na prijsindicatie)
        # -------------------------
        if post_offer_mode:
            t = user_input.strip().lower()

            if post_offer_stage == "choice":
                if t == "1":
                    if remaining_recalcs() <= 0:
                        print(
                            "Chatbot: Ik kan maximaal 3 nieuwe berekeningen per gesprek doen.\n"
                            "Chatbot: Wilt u dat we dit samen verfijnen en advies op maat geven? (ja/nee)\n"
                        )
                        post_offer_stage = "contact_ask"
                        continue

                    recalc_count += 1
                    flow = TuinaanlegFlow(prijzen=PRIJZEN)
                    post_offer_mode = False
                    post_offer_stage = None
                    print("\nChatbot: Helemaal goed — dan maken we een nieuwe indicatie met een paar korte vragen.")
                    print("Chatbot:", flow.get_question(), "\n")
                    continue

                if t == "2":
                    post_offer_stage = "contact_details"
                    print(
                        "Chatbot: Top. Stuur gerust uw naam + postcode + telefoon/e-mail + een korte omschrijving.\n"
                    )
                    continue

                if t == "3":
                    print("Chatbot: Helemaal goed. Fijn dat u even heeft gekeken. 👋\n")
                    post_offer_mode = False
                    post_offer_stage = None
                    break

                print("Chatbot: Kies 1, 2 of 3.\n")
                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            if post_offer_stage == "contact_ask":
                if is_yes(t):
                    post_offer_stage = "contact_details"
                    print("Chatbot: Top. Stuur gerust uw naam + postcode + telefoon/e-mail + een korte omschrijving.\n")
                    continue

                if is_no(t):
                    post_offer_mode = False
                    post_offer_stage = None
                    print("Chatbot: Helemaal goed. Als u later nog vragen heeft, help ik graag. 👋\n")
                    continue

                print("Chatbot: Antwoord met ja of nee.\nChatbot: Wilt u dat we dit samen verfijnen met advies op maat? (ja/nee)\n")
                continue

            if post_offer_stage == "contact_details":
                contact_text = user_input.strip()

                # Hier kun je later koppelen aan CRM/email/opslaan in bestand:
                # print("DEBUG contact:", contact_text)
                # print("DEBUG last_answers:", last_answers)
                # print("DEBUG last_costs:", last_costs)

                print("Chatbot: Dank u wel! We nemen zo snel mogelijk contact met u op!\n")
                print("Chatbot: Tot ziens! 👋\n")

                post_offer_mode = False
                post_offer_stage = None
                break

        # -------------------------
        # 1) Flow start detectie
        # -------------------------
        if flow is None and looks_like_tuinaanleg_intent(user_input):
            recalc_count = 0
            flow = TuinaanlegFlow(prijzen=PRIJZEN)
            print("\nChatbot: Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.")
            print("Chatbot:", flow.get_question(), "\n")
            continue

        # -------------------------
        # 2) Als flow actief is -> handle via flow
        # -------------------------
        if flow is not None:
            mapped = map_numeric_menu_to_valid_input(user_input, flow.step_index)
            reply, done = flow.handle(mapped)

            print("Chatbot:", reply, "\n")

            if done:
                print("✅ Intake samenvatting:")
                print(pretty_intake_summary(flow.answers))
                print()

                costs = estimate_tuinaanleg_costs(flow.answers)

                if DEBUG_COSTS_JSON:
                    print("📌 Debug kostenindicatie — JSON:")
                    print(json.dumps(costs, ensure_ascii=False, indent=2))
                    print()

                customer_text = format_tuinaanleg_costs_for_customer(costs)
                print("💬 Klantweergave:")
                print(customer_text)
                print()

                last_answers = dict(flow.answers)
                last_costs = dict(costs)

                # Flow uit en post-offer menu starten
                flow = None
                post_offer_mode = True
                post_offer_stage = "choice"

                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            continue

        # -------------------------
        # 3) Geen flow actief -> GEEN AI (alleen database/regels)
        # -------------------------
        reply = db_reply_or_none(user_input)
        if reply:
            print("\nChatbot:", reply, "\n")
        else:
            print("\nChatbot:", no_ai_fallback_message(), "\n")

    except Exception:
        print("Chatbot: Oeps, er ging iets mis. Probeer het later opnieuw.\n")
        # print("DEBUG:", repr(e))
