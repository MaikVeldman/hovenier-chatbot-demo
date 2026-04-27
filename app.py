# app.py

import streamlit as st
import streamlit.components.v1 as components

from bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON
from bot_logic import handle_message, make_initial_state, INITIAL_GREETING

# =====================
# Config
# =====================
st.set_page_config(page_title=f"{BEDRIJFSNAAM} – Tuinaanleg demo", page_icon="🌿")
st.title("🌿 Tuinaanleg prijsindicatie (demo)")
st.caption(f"{BEDRIJFSNAAM} • {REGIO}")


def render_text(text: str) -> None:
    safe = (text or "").replace("\n", "  \n")
    st.markdown(safe)


def _initial_messages():
    return [{"role": "assistant", "content": INITIAL_GREETING}]


# =====================
# Session init
# =====================
if "chat_state" not in st.session_state:
    st.session_state.chat_state = make_initial_state()

if "messages" not in st.session_state:
    st.session_state.messages = _initial_messages()

if "scroll_to_top" not in st.session_state:
    st.session_state.scroll_to_top = False


# =====================
# Sidebar
# =====================
with st.sidebar:
    st.subheader("Demo controls")
    if st.button("🔄 Reset gesprek", use_container_width=True):
        st.session_state.chat_state = make_initial_state()
        st.session_state.messages = _initial_messages()
        st.session_state.scroll_to_top = False
        st.rerun()

    st.divider()
    st.write("**Contact:**")
    st.write(f"- Email: {CONTACT_EMAIL}")
    st.write(f"- Telefoon: {CONTACT_TELEFOON}")
    st.caption("Tip: typ **nee** om terug te gaan in de bespaar-menu's.")


# =====================
# Render chat history
# =====================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        render_text(msg["content"])

# Scroll naar boven zodra de prijsindicatie voor het eerst verschijnt
if st.session_state.scroll_to_top:
    st.session_state.scroll_to_top = False
    components.html(
        "<script>"
        "window.parent.document.querySelector('section.main').scrollTo({top: 0, behavior: 'smooth'});"
        "</script>",
        height=0,
    )


# =====================
# Chat input
# =====================
user_text = st.chat_input("Typ je antwoord…")
if not user_text:
    st.stop()

st.session_state.messages.append({"role": "user", "content": user_text})

state = st.session_state.chat_state
was_post_offer = state.post_offer_mode

state, new_messages = handle_message(state, user_text)
st.session_state.chat_state = state

# Zet scroll-vlag als we net naar de prijsindicatie overstappen
if not was_post_offer and state.post_offer_mode:
    st.session_state.scroll_to_top = True

for msg in new_messages:
    st.session_state.messages.append({"role": "assistant", "content": msg})

st.rerun()
