# main.py

import os
from dotenv import load_dotenv

from flow_tuinaanleg import TuinaanlegFlow
from pricing import PRIJZEN
from bot_logic import ChatState, handle_message

load_dotenv()

DEBUG_COSTS_JSON = os.getenv("DEBUG_COSTS_JSON", "").strip() in {"1", "true", "True", "yes", "YES"}


def looks_like_tuinaanleg_intent(text: str) -> bool:
    t = text.lower()
    triggers = [
        "tuinaanleg", "tuin aanleggen", "tuin aanleg", "tuin renoveren",
        "herinrichten", "nieuwe tuin", "aanleg", "tuin vernieuwen"
    ]
    return any(w in t for w in triggers)


state = ChatState()

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
        # Intent detectie: start de flow pas als de gebruiker aangeeft dat ze iets willen
        if state.flow is None and not state.post_offer_mode:
            if looks_like_tuinaanleg_intent(user_input):
                state.recalc_count = 0
                state.pending_material_part = None
                state.flow = TuinaanlegFlow(prijzen=PRIJZEN)
                print("\nChatbot: Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.")
                print("Chatbot:", state.flow.get_question(), "\n")
            else:
                print("\nChatbot: Typ bijvoorbeeld: tuinaanleg\n")
            continue

        state, messages = handle_message(state, user_input)
        for msg in messages:
            print(f"Chatbot: {msg}\n")

        if state.ended:
            break

    except Exception:
        print("Chatbot: Oeps, er ging iets mis. Probeer het later opnieuw.\n")
