# app.py

import streamlit as st

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


# =====================
# Sidebar
# =====================
with st.sidebar:
    st.subheader("Demo controls")
    if st.button("🔄 Reset gesprek", use_container_width=True):
        st.session_state.chat_state = make_initial_state()
        st.session_state.messages = _initial_messages()
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


# =====================
# Chat input
# =====================
user_text = st.chat_input("Typ je antwoord…")
if not user_text:
    st.stop()

st.session_state.messages.append({"role": "user", "content": user_text})

state = st.session_state.chat_state
state, new_messages = handle_message(state, user_text)
st.session_state.chat_state = state

for msg in new_messages:
    st.session_state.messages.append({"role": "assistant", "content": msg})

st.rerun()
