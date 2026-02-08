## Waar pas ik wat aan?

Deze chatbot bestaat uit 3 lagen:
1) **Intake (vragen stellen)**  
2) **Prijsberekening (kosten + breakdown)**  
3) **Kostenbesparing / varianten (post-offer menu’s)**  

Om te voorkomen dat logica dubbel staat of uit elkaar loopt, geldt deze afspraak:

---

### ✅ Intake aanpassen → `flow_tuinaanleg.py`
Voorbeelden:
- Nieuwe vragen toevoegen/verwijderen
- Validatie of “dummy-proof” input parsing veranderen
- Nieuwe extra opties toevoegen (erfafscheiding/vlonder/beregening etc.)

---

### ✅ Prijslogica aanpassen → `pricing.py`
Voorbeelden:
- Prijstabel (`PRIJZEN`) wijzigen
- Nieuwe kostenposten toevoegen aan breakdown
- Hoe m² / m¹ / m³ berekend worden
- Relaties: verhouding bestrating/groen beïnvloedt grondwerk/voegen/beregening, etc.

---

### ✅ Kostenbesparing / varianten aanpassen → `savings.py`
**Alle post-offer logica staat hier.**  
Voorbeelden:
- Menu-teksten en nummering (altijd starten bij 1)
- “Nee/terug” gedrag (overal consistent)
- Welke bespaaropties beschikbaar zijn per situatie
- “Ik toon alleen goedkopere opties” filtering
- Besparingsteksten (bedrag dat je weglaat / verschil in gekoppelde posten)
- Apply-functies die antwoorden aanpassen (materialen, verhouding, extras, vlonder, erfafscheiding)

**Belangrijk:** vanaf nu wijzigen we bespaarlogica niet meer in `main.py` of `app.py`, alleen in `savings.py`.

---

### ✅ Console gedrag / debug → `main.py`
Voorbeelden:
- Print-output of debug JSON tonen
- Hoe de console-flow loopt
- Overige non-UI glue code

> `main.py` roept alleen functies aan uit `flow_tuinaanleg.py`, `pricing.py` en `savings.py`.

---

### ✅ Streamlit UI / rendering → `app.py`
Voorbeelden:
- Weergave in chat bubbles
- Tekst netjes onder elkaar tonen (markdown / newline handling)
- Buttons, sidebar, reset, session_state

> `app.py` bevat geen inhoudelijke bespaarlogica. Het gebruikt `savings.py` als bron van waarheid.

---

## Snelle checklist

- Wil je een vraag aanpassen? → `flow_tuinaanleg.py`
- Wil je een prijs/berekening aanpassen? → `pricing.py`
- Wil je kostenbesparing-menu’s of “besparing: …” aanpassen? → `savings.py`
- Wil je alleen hoe het eruit ziet in Streamlit? → `app.py`
- Wil je alleen console-output? → `main.py`
