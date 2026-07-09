"""
test_bot.py — handmatige smoke test voor alle drie flows.
Gebruik: python test_bot.py
Verwacht: geen crashes, elke flow eindigt met een prijs of bevestiging.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from bot_logic import handle_message, make_initial_state

def run(inputs: list, label: str):
    state = make_initial_state()
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    for tekst in inputs:
        state, replies = handle_message(state, tekst)
        print(f"\n> {tekst}")
        for r in replies:
            preview = r[:120].replace("\n", " ")
            print(f"  BOT: {preview}{'...' if len(r) > 120 else ''}")

# Flow 1 — Gehele tuin
run([
    "1",                  # gehele tuin
    "80",                 # oppervlakte
    "keramisch",          # bestrating
    "60",                 # bestrating m2
    "ja",                 # graszoden
    "30",                 # graszoden m2
    "nee",                # beplanting border
    "nee",                # haag
    "nee",                # boom
    "nee",                # vlonder
    "nee",                # overkapping
    "nee",                # verlichting
    "nee",                # beregening
    "nee",                # erfafscheiding
], "Flow 1: Gehele tuin aanleggen")

# Flow 2 — Losse onderdelen
run([
    "2",                  # losse onderdelen
    "bestrating",         # keuze
    "keramisch",          # soort
    "40",                 # m2
    "klaar",              # klaar
], "Flow 2: Losse onderdelen")

# Flow 3 — Tuinontwerp
run([
    "3",                  # tuinontwerp
    "75",                 # oppervlakte
], "Flow 3: Tuinontwerp")

print(f"\n{'='*50}")
print("  Smoke test klaar — geen crashes gevonden")
print(f"{'='*50}\n")
