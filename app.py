# app.py

import streamlit as st
import streamlit.components.v1 as components

from infrastructure.config.bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON
from core.controllers.chat_controller import ChatController, INITIAL_GREETING
from core.models.chat_state import make_initial_state

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

if "scroll_to_msg_idx" not in st.session_state:
    st.session_state.scroll_to_msg_idx = None


# =====================
# Sidebar
# =====================
with st.sidebar:
    st.subheader("Demo controls")
    if st.button("🔄 Reset gesprek", use_container_width=True):
        st.session_state.chat_state = make_initial_state()
        st.session_state.messages = _initial_messages()
        st.session_state.scroll_to_msg_idx = None
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

# Scroll naar het begin van het eerste nieuwe bericht
if st.session_state.scroll_to_msg_idx is not None:
    idx = st.session_state.scroll_to_msg_idx
    st.session_state.scroll_to_msg_idx = None
    components.html(
        f"<script>"
        f"(function() {{"
        f"  function scrollToMsg() {{"
        f"    var msgs = window.parent.document.querySelectorAll('[data-testid=\"stChatMessage\"]');"
        f"    if (msgs.length > {idx}) {{"
        f"      msgs[{idx}].scrollIntoView({{behavior: 'smooth', block: 'start'}});"
        f"    }}"
        f"  }}"
        f"  setTimeout(scrollToMsg, 100);"
        f"}})();"
        f"</script>",
        height=0,
    )


# =====================
# Chat input
# =====================
user_text = st.chat_input("Typ je antwoord…")
if not user_text:
    st.stop()

first_new_idx = len(st.session_state.messages)
st.session_state.messages.append({"role": "user", "content": user_text})

state = st.session_state.chat_state
ctrl = ChatController(state)
state, new_messages = ctrl.handle(user_text)
st.session_state.chat_state = state

for msg in new_messages:
    st.session_state.messages.append({"role": "assistant", "content": msg})

st.session_state.scroll_to_msg_idx = first_new_idx
st.rerun()
