# main.py — command-line interface voor lokaal testen
from core.controllers.chat_controller import ChatController, build_greeting
from core.models.chat_state import make_initial_state

state = make_initial_state()

print("🤖 Hovenier-chatbot gestart (typ 'stop' om te stoppen)\n")
print(f"Chatbot: {build_greeting()}\n")

while True:
    user_input = input("U: ").strip()
    if not user_input:
        continue
    if user_input.lower() == "stop":
        print("Chatbot: Tot ziens! 👋")
        break

    try:
        ctrl = ChatController(state)
        state, messages = ctrl.handle(user_input)
        for msg in messages:
            print(f"Chatbot: {msg}\n")

        if state.ended:
            break

    except Exception:
        print("Chatbot: Oeps, er ging iets mis. Probeer het later opnieuw.\n")
