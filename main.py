# main.py

from bot_logic import handle_message, make_initial_state, INITIAL_GREETING

state = make_initial_state()

print("🤖 Hovenier-chatbot gestart (typ 'stop' om te stoppen)\n")
print(f"Chatbot: {INITIAL_GREETING}\n")

while True:
    user_input = input("U: ").strip()
    if not user_input:
        continue
    if user_input.lower() == "stop":
        print("Chatbot: Tot ziens! 👋")
        break

    try:
        state, messages = handle_message(state, user_input)
        for msg in messages:
            print(f"Chatbot: {msg}\n")

        if state.ended:
            break

    except Exception:
        print("Chatbot: Oeps, er ging iets mis. Probeer het later opnieuw.\n")
