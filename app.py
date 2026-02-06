import streamlit as st

from flow_tuinaanleg import TuinaanlegFlow
from pricing import PRIJZEN, estimate_tuinaanleg_costs, format_tuinaanleg_costs_for_customer
from bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON


st.set_page_config(page_title=f"{BEDRIJFSNAAM} – Tuinaanleg demo", page_icon="🌿")

st.title("🌿 Tuinaanleg prijsindicatie (demo)")
st.caption(f"{BEDRIJFSNAAM} • {REGIO}")


# =========================
# Helpers (UI-teksten)
# =========================
def start_message() -> str:
    return (
        "Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.\n\n"
        "Hoe groot is uw tuin in m²? (geef een getal)"
    )


def post_offer_choices_text() -> str:
    return (
        "Hoe wilt u verder?\n"
        "1) Kijken of er keuzes zijn om de kosten te verlagen\n"
        "2) Contact voor offerte op maat (vrijblijvend)\n"
        "3) Het hierbij laten\n\n"
        "Reageer met 1, 2 of 3."
    )


def is_choice(text: str, v: str) -> bool:
    return (text or "").strip() == v


# =========================
# Session init
# =========================
if "flow" not in st.session_state:
    st.session_state.flow = TuinaanlegFlow(prijzen=PRIJZEN)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": start_message()}]

if "done" not in st.session_state:
    st.session_state.done = False

# post-offer state (na kostenindicatie)
if "post_offer_mode" not in st.session_state:
    st.session_state.post_offer_mode = False
if "post_offer_stage" not in st.session_state:
    st.session_state.post_offer_stage = None  # "menu" | "contact_details" | "end"
if "last_answers" not in st.session_state:
    st.session_state.last_answers = None
if "last_costs" not in st.session_state:
    st.session_state.last_costs = None


# =========================
# Sidebar
# =========================
with st.sidebar:
    st.subheader("Demo controls")
    if st.button("🔄 Reset gesprek", use_container_width=True):
        st.session_state.flow = TuinaanlegFlow(prijzen=PRIJZEN)
        st.session_state.messages = [{"role": "assistant", "content": start_message()}]
        st.session_state.done = False

        st.session_state.post_offer_mode = False
        st.session_state.post_offer_stage = None
        st.session_state.last_answers = None
        st.session_state.last_costs = None

        st.rerun()

    st.divider()
    st.write("**Contact (voor demo):**")
    st.write(f"- Email: {CONTACT_EMAIL}")
    st.write(f"- Telefoon: {CONTACT_TELEFOON}")


# =========================
# Render chat history
# =========================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# =========================
# Chat input
# =========================
user_text = st.chat_input("Typ je antwoord…")

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})

    # -------------------------
    # Post-offer flow (na prijsindicatie)
    # -------------------------
    if st.session_state.post_offer_mode:
        stage = st.session_state.post_offer_stage

        if stage == "menu":
            if is_choice(user_text, "1"):
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": (
                        "Helemaal goed. We kunnen meestal besparen door keuzes aan te passen "
                        "(bijv. materiaal, verdeling groen/bestrating of extra’s).\n\n"
                        "Wilt u dat ik een nieuwe indicatie maak met aangepaste keuzes? "
                        "Zo ja: start dan opnieuw met de intake (Reset gesprek) of zeg wat u wilt aanpassen."
                    )
                })
                # (Later kun je hier een echte “kosten verlagen” wizard bouwen)
                st.session_state.post_offer_mode = False
                st.session_state.post_offer_stage = None

            elif is_choice(user_text, "2"):
                st.session_state.post_offer_stage = "contact_details"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": (
                        "Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?\n\n"
                        f"Dan nemen we binnen 1 werkdag contact op via {CONTACT_EMAIL} of {CONTACT_TELEFOON}."
                    )
                })

            elif is_choice(user_text, "3"):
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Helemaal goed. Fijn dat u even heeft gekeken. 👋"
                })
                st.session_state.post_offer_mode = False
                st.session_state.post_offer_stage = "end"

            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": post_offer_choices_text()
                })

            st.rerun()

        if stage == "contact_details":
            # Hier kun je later opslaan naar CRM/mail/Google Sheet/etc.
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Dank u wel! We nemen zo snel mogelijk contact met u op."
            })
            st.session_state.post_offer_mode = False
            st.session_state.post_offer_stage = "end"
            st.rerun()

    # -------------------------
    # Normale intake flow
    # -------------------------
    if not st.session_state.done and not st.session_state.post_offer_mode:
        reply, done = st.session_state.flow.handle(user_text)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.session_state.done = done

        if done:
            ans = st.session_state.flow.answers
            costs = estimate_tuinaanleg_costs(ans)
            klanttekst = format_tuinaanleg_costs_for_customer(costs)

            # Intake summary (compact)
            summary_lines = []
            summary_lines.append("✅ **Intake samenvatting**")
            summary_lines.append(f"- Oppervlakte: {ans.get('tuin_m2')} m²")
            summary_lines.append(f"- Verhouding bestrating/groen: {ans.get('verhouding_bestrating_groen')}")
            summary_lines.append(f"- Groen verdeling (gazon/beplanting): {ans.get('verhouding_gazon_beplanting')}")
            summary_lines.append(f"- Oprit/paden/terras: {ans.get('oprit_pct')}/{ans.get('paden_pct')}/{ans.get('terras_pct')}")
            summary_lines.append(
                f"- Materialen: oprit={ans.get('materiaal_oprit')}, paden={ans.get('materiaal_paden')}, terras={ans.get('materiaal_terras')}"
            )
            summary_lines.append(f"- Onkruidwerend gevoegd: {ans.get('onkruidwerend_gevoegd')}")
            summary_lines.append(f"- Overkapping: {ans.get('overkapping')}")
            summary_lines.append(f"- Verlichting: {ans.get('verlichting')}")
            summary_lines.append(f"- Overige wensen: {ans.get('overige_wensen')}")

            st.session_state.messages.append({"role": "assistant", "content": "\n".join(summary_lines)})

            # (optioneel) 1 geruststellende zin vóór de prijs
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Iedere tuin is uniek. Deze indicatie is bedoeld als richting, niet als definitieve offerte."
            })

            st.session_state.messages.append({"role": "assistant", "content": klanttekst})

            # Post-offer menu starten
            st.session_state.last_answers = dict(ans)
            st.session_state.last_costs = dict(costs)

            st.session_state.post_offer_mode = True
            st.session_state.post_offer_stage = "menu"

            st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})

        st.rerun()
