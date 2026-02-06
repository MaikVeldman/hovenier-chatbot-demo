# main.py

import os
import json
from dotenv import load_dotenv

from pricing import (
    PRIJZEN,
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
post_offer_stage = None  # "menu" | "lower_costs" | "limit_followup" | "contact_details" | "end"
last_answers = None
last_costs = None

# ✅ Recalc limiter (intern)
MAX_RECALC = 3
recalc_count = 0

# ✅ onthoud welke bespaar-opties al zijn toegepast (bijv. {"1","2"})
applied_savings: set[str] = set()

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


def remaining_recalcs() -> int:
    return max(0, MAX_RECALC - recalc_count)


def yn(v) -> str:
    if v is True:
        return "ja"
    if v is False:
        return "nee"
    return "—"


def soft_limit_message() -> str:
    return (
        "We kunnen samen een paar varianten bekijken. Daarna kijken we liever persoonlijk mee, "
        "zodat het echt goed aansluit bij uw situatie."
    )


def post_offer_choices_text() -> str:
    return (
        "Hoe wilt u verder?\n"
        "1) Kijken of er keuzes zijn om de kosten te verlagen\n"
        "2) Contact voor offerte op maat (vrijblijvend)\n"
        "3) Het hierbij laten\n\n"
        "Reageer met 1, 2 of 3."
    )


def lower_costs_menu_text() -> str:
    return (
        "Goed idee. Welke aanpassing wilt u proberen om de kosten te verlagen?\n"
        "1) Kies voordeliger materialen (waar mogelijk)\n"
        "2) Iets meer groen, iets minder bestrating\n"
        "3) Extra’s weglaten (voegen/overkapping/verlichting en extra opties)\n\n"
        "Reageer met 1, 2 of 3."
    )


def limit_followup_text() -> str:
    return (
        "Hoe wilt u verder?\n"
        "1) Contact voor offerte op maat (vrijblijvend)\n"
        "2) Het hierbij laten\n\n"
        "Reageer met 1 of 2."
    )


def _eur(v: int) -> str:
    return f"€{int(v):,}".replace(",", ".")


def _total_range(costs: dict) -> tuple[int, int] | None:
    tr = costs.get("total_range_eur")
    if not tr or len(tr) != 2:
        return None
    return int(tr[0]), int(tr[1])


def _materials_downgrade(mat: str) -> str:
    m = (mat or "").strip().lower()
    if m == "keramiek":
        return "gebakken"
    if m == "gebakken":
        return "beton"
    return m or "beton"


def apply_savings_option(answers: dict, option: str) -> tuple[dict, str]:
    """
    Past één 'bespaar-optie' toe op answers en geeft een uitleg terug.
    Belangrijk: we muteren niet-in-place (kopie).
    """
    a = dict(answers or {})
    expl = ""

    # Zorg dat list velden goed blijven
    overige = a.get("overige_wensen") or []
    if not isinstance(overige, list):
        overige = [str(overige)]
    overige_clean = [str(x).strip().lower() for x in overige if str(x).strip()]

    if option == "1":
        # Voordeliger materialen
        a["materiaal_oprit"] = _materials_downgrade(a.get("materiaal_oprit"))
        a["materiaal_paden"] = _materials_downgrade(a.get("materiaal_paden"))
        a["materiaal_terras"] = _materials_downgrade(a.get("materiaal_terras"))

        # Vlonder type (als gekozen)
        vt = (a.get("vlonder_type") or "").strip().lower()
        if "vlonder" in overige_clean and vt in ("hardhout", "composiet"):
            a["vlonder_type"] = "zachthout"

        expl = (
            "Ik heb gekeken waar we (zonder functies te veranderen) materialen iets voordeliger kunnen kiezen "
            "— bijvoorbeeld keramiek → gebakken, gebakken → beton."
        )

    elif option == "2":
        # Minder bestrating (ratio één stap richting meer groen)
        ratio = (a.get("verhouding_bestrating_groen") or "").strip().lower()
        if ratio == "70_30":
            a["verhouding_bestrating_groen"] = "50_50"
        elif ratio == "50_50":
            a["verhouding_bestrating_groen"] = "30_70"
        elif ratio == "30_70":
            a["verhouding_bestrating_groen"] = "30_70"
        else:
            # custom/unknown -> zet naar 30/70 als veilige bespaar-variant
            a["verhouding_bestrating_groen"] = "30_70"

        expl = (
            "Ik heb de verhouding iets verschoven naar meer groen en minder bestrating. "
            "Dat verlaagt vaak de kosten, omdat verharding (incl. onderbouw/grondwerk) relatief zwaar meetelt."
        )

    elif option == "3":
        # Extra's weglaten
        a["onkruidwerend_gevoegd"] = False
        a["overkapping"] = False
        a["verlichting"] = False

        # verwijder extra wensen die vaak extra kosten geven
        remove_tags = {"vlonder", "beregening", "erfafscheiding"}
        overige_clean = [x for x in overige_clean if x not in remove_tags]
        a["overige_wensen"] = overige_clean

        # reset gerelateerde velden
        a["vlonder_type"] = None
        a["beregening_scope"] = None
        a["erfafscheiding_items"] = []

        expl = (
            "Ik heb de extra’s uitgezet (voegen/overkapping/verlichting en extra opties zoals vlonder/beregening/erfafscheiding). "
            "Dat geeft vaak direct de grootste besparing."
        )

    else:
        expl = "Onbekende keuze — er is niets aangepast."

    return a, expl


# =====================
# Intake summary
# =====================
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

    overige = ans.get("overige_wensen") or []
    if isinstance(overige, list) and overige:
        lines.append(f"- Overige wensen: {', '.join([str(x) for x in overige])}")

    return "\n".join(lines)


def db_reply_or_none(user_input: str) -> str | None:
    t = user_input.strip().lower()

    if "openingstijd" in t or "open" in t:
        return "We werken op afspraak. Wilt u tuinaanleg, onderhoud of ontwerp?"
    if "telefoon" in t or "nummer" in t:
        return "Wilt u tuinaanleg, onderhoud of ontwerp? Dan kan ik u verder helpen via de juiste flow."
    if "prijs" in t or "kosten" in t:
        return "Voor een prijsindicatie kan ik u helpen via de juiste intake. Gaat het om tuinaanleg of onderhoud?"

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
        # Post-offer menu
        # -------------------------
        if post_offer_mode:
            t_raw = user_input.strip()
            t_low = t_raw.lower()

            # ✅ "contact/offerte" overal in post-offer laten werken
            if t_low in {"contact", "offerte", "advies"}:
                post_offer_stage = "contact_details"
                print("Chatbot: Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?\n")
                continue

            # ✅ limiet follow-up
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

            # menu
            if post_offer_stage == "menu":
                if t_raw == "1":
                    if remaining_recalcs() <= 0:
                        print("Chatbot:", soft_limit_message(), "\n")
                        post_offer_stage = "limit_followup"
                        print("Chatbot:", limit_followup_text(), "\n")
                        continue

                    post_offer_stage = "lower_costs"
                    print("Chatbot:", lower_costs_menu_text(), "\n")
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

            # lower_costs wizard
            if post_offer_stage == "lower_costs":
                if t_raw not in {"1", "2", "3"}:
                    print("Chatbot:", lower_costs_menu_text(), "\n")
                    continue

                # ✅ al toegepast => NIET meetellen in recalc_count
                # ✅ en direct terug naar hoofdmenu (geen verwarring)
                if t_raw in applied_savings:
                    print("Chatbot: Deze kostenbesparing is al doorgevoerd in de huidige indicatie.\n")
                    post_offer_stage = "menu"
                    print("Chatbot:", post_offer_choices_text(), "\n")
                    continue

                # ✅ pas nu checken of er nog 'tegoed' is
                if remaining_recalcs() <= 0:
                    print("Chatbot:", soft_limit_message(), "\n")
                    post_offer_stage = "limit_followup"
                    print("Chatbot:", limit_followup_text(), "\n")
                    continue

                # ✅ nu pas telt het als een echte herberekening
                recalc_count += 1
                applied_savings.add(t_raw)

                new_answers, explanation = apply_savings_option(last_answers or {}, t_raw)
                new_costs = estimate_tuinaanleg_costs(new_answers)

                old_tr = _total_range(last_costs or {}) or (0, 0)
                new_tr = _total_range(new_costs or {}) or (0, 0)

                print("Chatbot:", explanation)
                print("Chatbot: Hieronder ziet u een aangepaste indicatie op basis van uw keuze.\n")

                print(
                    f"Chatbot: Oude indicatie: {_eur(old_tr[0])} – {_eur(old_tr[1])}\n"
                    f"Chatbot: Nieuwe indicatie: {_eur(new_tr[0])} – {_eur(new_tr[1])}\n"
                )

                if DEBUG_COSTS_JSON:
                    print("📌 Debug kostenindicatie — JSON:")
                    print(json.dumps(new_costs, ensure_ascii=False, indent=2))
                    print()

                customer_text = format_tuinaanleg_costs_for_customer(new_costs)
                print(customer_text)
                print()

                # update last_* zodat je verder kunt itereren
                last_answers = dict(new_answers)
                last_costs = dict(new_costs)

                # terug naar hoofdmenu
                post_offer_stage = "menu"
                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            # contact details
            if post_offer_stage == "contact_details":
                # Hier later: opslaan / mailen / CRM
                print("Chatbot: Dank u wel! We nemen zo snel mogelijk contact met u op!\n")
                print("Chatbot: Tot ziens! 👋\n")

                post_offer_mode = False
                post_offer_stage = "end"
                break

        # -------------------------
        # Flow start detectie
        # -------------------------
        if flow is None and looks_like_tuinaanleg_intent(user_input):
            recalc_count = 0
            applied_savings = set()
            flow = TuinaanlegFlow(prijzen=PRIJZEN)
            print("\nChatbot: Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.")
            print("Chatbot:", flow.get_question(), "\n")
            continue

        # -------------------------
        # Als flow actief is -> handle via flow
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

                print("Chatbot: Iedere tuin is uniek. Deze indicatie is bedoeld als richting, niet als definitieve offerte.\n")

                customer_text = format_tuinaanleg_costs_for_customer(costs)
                print("💬 Klantweergave:")
                print(customer_text)
                print()

                last_answers = dict(flow.answers)
                last_costs = dict(costs)
                applied_savings = set()

                # Flow uit en post-offer menu starten
                flow = None
                post_offer_mode = True
                post_offer_stage = "menu"

                print("Chatbot:", post_offer_choices_text(), "\n")
                continue

            continue

        # -------------------------
        # Geen flow actief -> GEEN AI (alleen database/regels)
        # -------------------------
        reply = db_reply_or_none(user_input)
        if reply:
            print("\nChatbot:", reply, "\n")
        else:
            print("\nChatbot:", no_ai_fallback_message(), "\n")

    except Exception:
        print("Chatbot: Oeps, er ging iets mis. Probeer het later opnieuw.\n")
