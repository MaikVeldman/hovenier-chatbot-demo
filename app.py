import streamlit as st

from flow_tuinaanleg import TuinaanlegFlow
from pricing import PRIJZEN, estimate_tuinaanleg_costs, format_tuinaanleg_costs_for_customer
from bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON


st.set_page_config(page_title=f"{BEDRIJFSNAAM} – Tuinaanleg demo", page_icon="🌿")

st.title("🌿 Tuinaanleg prijsindicatie (demo)")
st.caption(f"{BEDRIJFSNAAM} • {REGIO}")

# --- Session init ---
if "flow" not in st.session_state:
    st.session_state.flow = TuinaanlegFlow(prijzen=PRIJZEN)

if "messages" not in st.session_state:
    st.session_state.messages = []
    # Startbericht
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Hoi! Ik stel een paar korte vragen en geef daarna een globale kostenindicatie. "
                   "Hoe groot is uw tuin in m²? (geef een getal)"
    })

if "done" not in st.session_state:
    st.session_state.done = False

# --- Sidebar ---
with st.sidebar:
    st.subheader("Demo controls")
    if st.button("🔄 Reset gesprek", use_container_width=True):
        st.session_state.flow = TuinaanlegFlow(prijzen=PRIJZEN)
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hoi! Ik stel een paar korte vragen en geef daarna een globale kostenindicatie. "
                       "Hoe groot is uw tuin in m²? (geef een getal)"
        }]
        st.session_state.done = False
        st.rerun()

    st.divider()
    st.write("**Contact (voor demo):**")
    st.write(f"- Email: {CONTACT_EMAIL}")
    st.write(f"- Telefoon: {CONTACT_TELEFOON}")


# --- Render chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Chat input ---
user_text = st.chat_input("Typ je antwoord…")  # docs: st.chat_input :contentReference[oaicite:0]{index=0}
if user_text and not st.session_state.done:
    # toon user
    st.session_state.messages.append({"role": "user", "content": user_text})

    # flow afhandelen
    reply, done = st.session_state.flow.handle(user_text)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.session_state.done = done

    # als klaar: samenvatting + kosten
    if done:
        ans = st.session_state.flow.answers
        costs = estimate_tuinaanleg_costs(ans)
        klanttekst = format_tuinaanleg_costs_for_customer(costs)

        summary_lines = []
        summary_lines.append("✅ **Intake samenvatting**")
        summary_lines.append("")
        summary_lines.append(f"- Oppervlakte: {ans.get('tuin_m2')} m²")
        summary_lines.append(f"- Verhouding bestrating/groen: {ans.get('verhouding_bestrating_groen')}")
        summary_lines.append(f"- Groen verdeling (gazon/beplanting): {ans.get('verhouding_gazon_beplanting')}")
        summary_lines.append(f"- Oprit/paden/terras: {ans.get('oprit_pct')}/{ans.get('paden_pct')}/{ans.get('terras_pct')}")
        summary_lines.append(f"- Materialen: oprit={ans.get('materiaal_oprit')}, paden={ans.get('materiaal_paden')}, terras={ans.get('materiaal_terras')}")
        summary_lines.append(f"- Onkruidwerend gevoegd: {ans.get('onkruidwerend_gevoegd')}")
        summary_lines.append(f"- Overkapping: {ans.get('overkapping')}")
        summary_lines.append(f"- Verlichting: {ans.get('verlichting')}")
        summary_lines.append(f"- Overige wensen: {ans.get('overige_wensen')}")
        if ans.get("erfafscheiding_type"):
            summary_lines.append(f"- Erfafscheiding type: {ans.get('erfafscheiding_type')}")
        if ans.get("erfafscheiding_meter"):
            summary_lines.append(f"- Haag meters: {ans.get('erfafscheiding_meter')} m")
        if ans.get("vlonder_type"):
            summary_lines.append(f"- Vlonder type: {ans.get('vlonder_type')}")

        st.session_state.messages.append({"role": "assistant", "content": "\n".join(summary_lines)})
        st.session_state.messages.append({"role": "assistant", "content": klanttekst})

        st.session_state.messages.append({
            "role": "assistant",
            "content": "Wilt u dat we contact met u opnemen voor een offerte op maat? "
                       "Stuur dan naam + postcode + telefoon/e-mail + korte omschrijving."
        })

    st.rerun()
