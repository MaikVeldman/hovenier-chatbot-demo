import streamlit as st

from flow_tuinaanleg import TuinaanlegFlow
from pricing import PRIJZEN, estimate_tuinaanleg_costs, format_tuinaanleg_costs_for_customer
from bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON


# =====================
# Config
# =====================
st.set_page_config(page_title=f"{BEDRIJFSNAAM} – Tuinaanleg demo", page_icon="🌿")

st.title("🌿 Tuinaanleg prijsindicatie (demo)")
st.caption(f"{BEDRIJFSNAAM} • {REGIO}")


# =====================
# Helpers (zelfde logica als main)
# =====================
MAX_RECALC = 3  # intern

def remaining_recalcs() -> int:
    return max(0, MAX_RECALC - st.session_state.recalc_count)

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

def _eur(v: int) -> str:
    return f"€{int(v):,}".replace(",", ".")

def _total_range(costs: dict):
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

def apply_savings_option(answers: dict, option: str):
    """
    Past één bespaar-optie toe op answers en geeft een uitleg terug.
    (kopie, niet muteren in-place)
    """
    a = dict(answers or {})
    expl = ""

    overige = a.get("overige_wensen") or []
    if not isinstance(overige, list):
        overige = [str(overige)]
    overige_clean = [str(x).strip().lower() for x in overige if str(x).strip()]

    if option == "1":
        a["materiaal_oprit"] = _materials_downgrade(a.get("materiaal_oprit"))
        a["materiaal_paden"] = _materials_downgrade(a.get("materiaal_paden"))
        a["materiaal_terras"] = _materials_downgrade(a.get("materiaal_terras"))

        vt = (a.get("vlonder_type") or "").strip().lower()
        if "vlonder" in overige_clean and vt in ("hardhout", "composiet"):
            a["vlonder_type"] = "zachthout"

        expl = (
            "Ik heb gekeken waar we (zonder functies te veranderen) materialen iets voordeliger kunnen kiezen "
            "— bijvoorbeeld keramiek → gebakken, gebakken → beton. Als u geen keramiek had gekozen, kan het effect beperkt zijn."
        )

    elif option == "2":
        ratio = (a.get("verhouding_bestrating_groen") or "").strip().lower()
        if ratio == "70_30":
            a["verhouding_bestrating_groen"] = "50_50"
        elif ratio == "50_50":
            a["verhouding_bestrating_groen"] = "30_70"
        elif ratio == "30_70":
            a["verhouding_bestrating_groen"] = "30_70"
        else:
            a["verhouding_bestrating_groen"] = "30_70"

        expl = (
            "Ik heb de verhouding iets verschoven naar meer groen en minder bestrating. "
            "Dat verlaagt vaak de kosten, omdat verharding (incl. onderbouw/grondwerk) relatief zwaar meetelt."
        )

    elif option == "3":
        a["onkruidwerend_gevoegd"] = False
        a["overkapping"] = False
        a["verlichting"] = False

        remove_tags = {"vlonder", "beregening", "erfafscheiding"}
        overige_clean = [x for x in overige_clean if x not in remove_tags]
        a["overige_wensen"] = overige_clean

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
# Session init
# =====================
if "flow" not in st.session_state:
    st.session_state.flow = TuinaanlegFlow(prijzen=PRIJZEN)

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            "Hoi! Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.\n\n"
            "Hoe groot is uw tuin in m²? (geef een getal)"
        )
    })

if "done" not in st.session_state:
    st.session_state.done = False

# Post-offer menu state (zelfde als main)
if "post_offer_mode" not in st.session_state:
    st.session_state.post_offer_mode = False
if "post_offer_stage" not in st.session_state:
    st.session_state.post_offer_stage = None  # "menu" | "lower_costs" | "contact_details" | "end"

if "last_answers" not in st.session_state:
    st.session_state.last_answers = None
if "last_costs" not in st.session_state:
    st.session_state.last_costs = None

if "recalc_count" not in st.session_state:
    st.session_state.recalc_count = 0


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

        st.rerun()

    st.divider()
    st.write("**Contact (voor demo):**")
    st.write(f"- Email: {CONTACT_EMAIL}")
    st.write(f"- Telefoon: {CONTACT_TELEFOON}")


# =====================
# Render chat history
# =====================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# =====================
# Chat input
# =====================
user_text = st.chat_input("Typ je antwoord…")
if user_text:
    # toon user
    st.session_state.messages.append({"role": "user", "content": user_text})

    # -----------------------------------------
    # Post-offer menu logic (zelfde als main)
    # -----------------------------------------
    if st.session_state.post_offer_mode:
        t = user_text.strip()

        # menu
        if st.session_state.post_offer_stage == "menu":
            if t == "1":
                if remaining_recalcs() <= 0:
                    st.session_state.messages.append({"role": "assistant", "content": soft_limit_message()})
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": (
                            "Wilt u dat we dit samen verder verfijnen in een vrijblijvende offerte?\n\n"
                            "Stuur dan naam + postcode + telefoon/e-mail + een korte omschrijving."
                        )
                    })
                    st.session_state.post_offer_mode = False
                    st.session_state.post_offer_stage = "end"
                    st.rerun()

                st.session_state.post_offer_stage = "lower_costs"
                st.session_state.messages.append({"role": "assistant", "content": lower_costs_menu_text()})
                st.rerun()

            elif t == "2":
                st.session_state.post_offer_stage = "contact_details"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?"
                })
                st.rerun()

            elif t == "3":
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Helemaal goed. Fijn dat u even heeft gekeken. 👋"
                })
                st.session_state.post_offer_mode = False
                st.session_state.post_offer_stage = "end"
                st.rerun()
            else:
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

        # lower_costs wizard
        if st.session_state.post_offer_stage == "lower_costs":
            if t not in {"1", "2", "3"}:
                st.session_state.messages.append({"role": "assistant", "content": lower_costs_menu_text()})
                st.rerun()

            if remaining_recalcs() <= 0:
                st.session_state.messages.append({"role": "assistant", "content": soft_limit_message()})
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": (
                        "Wilt u dat we dit samen verder verfijnen in een vrijblijvende offerte?\n\n"
                        "Stuur dan naam + postcode + telefoon/e-mail + een korte omschrijving."
                    )
                })
                st.session_state.post_offer_mode = False
                st.session_state.post_offer_stage = "end"
                st.rerun()

            st.session_state.recalc_count += 1

            new_answers, explanation = apply_savings_option(st.session_state.last_answers or {}, t)
            new_costs = estimate_tuinaanleg_costs(new_answers)

            old_tr = _total_range(st.session_state.last_costs or {}) or (0, 0)
            new_tr = _total_range(new_costs or {}) or (0, 0)

            st.session_state.messages.append({"role": "assistant", "content": explanation})
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    "Hieronder ziet u een aangepaste indicatie op basis van uw keuze.\n\n"
                    f"**Oude indicatie:** {_eur(old_tr[0])} – {_eur(old_tr[1])}\n\n"
                    f"**Nieuwe indicatie:** {_eur(new_tr[0])} – {_eur(new_tr[1])}"
                )
            })

            klanttekst = format_tuinaanleg_costs_for_customer(new_costs)
            st.session_state.messages.append({"role": "assistant", "content": klanttekst})

            # update last_*
            st.session_state.last_answers = dict(new_answers)
            st.session_state.last_costs = dict(new_costs)

            # terug naar menu
            st.session_state.post_offer_stage = "menu"
            st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
            st.rerun()

        # contact details
        if st.session_state.post_offer_stage == "contact_details":
            contact_text = user_text.strip()
            # Hier later: opslaan / mailen / CRM
            # st.write(contact_text)

            st.session_state.messages.append({
                "role": "assistant",
                "content": "Dank u wel! We nemen zo snel mogelijk contact met u op!"
            })
            st.session_state.post_offer_mode = False
            st.session_state.post_offer_stage = "end"
            st.rerun()

    # -----------------------------------------
    # Flow logic
    # -----------------------------------------
    if not st.session_state.done and not st.session_state.post_offer_mode:
        reply, done = st.session_state.flow.handle(user_text)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.session_state.done = done

        if done:
            ans = st.session_state.flow.answers
            costs = estimate_tuinaanleg_costs(ans)
            klanttekst = format_tuinaanleg_costs_for_customer(costs)

            # geruststellende zin vóór prijs
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Iedere tuin is uniek. Deze indicatie is bedoeld als richting, niet als definitieve offerte."
            })

            # kostenweergave
            st.session_state.messages.append({"role": "assistant", "content": klanttekst})

            # bewaar voor “kosten verlagen”
            st.session_state.last_answers = dict(ans)
            st.session_state.last_costs = dict(costs)

            # start post-offer menu
            st.session_state.post_offer_mode = True
            st.session_state.post_offer_stage = "menu"
            st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})

        st.rerun()
