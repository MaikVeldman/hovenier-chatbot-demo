# Migratieplan: OOP / MVC / SaaS refactor

> Backup gemaakt voor start. Branch: `refactor/oop-mvc-saas`
> Gouden regel: **bot werkt na elke fase**. Nooit twee fasen tegelijk.

---

## Doelarchitectuur

```
chatbot/
├── core/                          ← framework-onafhankelijk, testbaar
│   ├── models/                    ← pure datastructuren, geen logica
│   │   ├── chat_state.py          # ChatState dataclass
│   │   ├── cost_result.py         # CostResult, BreakdownItem dataclasses
│   │   ├── tenant.py              # TenantConfig dataclass
│   │   └── tenant_context.py      # TenantContext (config + price_table + repo)
│   ├── flows/                     ← conversatieflows (al OOP)
│   │   ├── base.py                # BaseFlow abstracte klasse
│   │   ├── tuinaanleg.py
│   │   ├── losse_onderdelen.py
│   │   └── tuinontwerp.py
│   ├── pricing/                   ← alles wat met berekenen te maken heeft
│   │   ├── constants.py           # PRIJZEN, VOLUME_KORTINGEN, GRONDWERK_DIEPTES, PRICE_META
│   │   ├── price_table.py         # PriceTable(tenant_config) — de SaaS-schakelaar
│   │   ├── tuinaanleg_pricer.py   # TuinaanlegPricer(price_table)
│   │   ├── losse_pricer.py        # LossePricer(price_table)
│   │   ├── tuinontwerp_pricer.py  # TuinontWerpPricer(price_table)
│   │   └── savings_service.py     # SavingsService (van savings.py, LAATSTE)
│   ├── controllers/               ← bot_logic.py opgesplitst
│   │   ├── chat_controller.py     # ChatController(state, tenant_ctx)
│   │   ├── post_offer_controller.py
│   │   └── contact_controller.py
│   └── services/
│       ├── leadscore_service.py
│       └── mailer_service.py
├── infrastructure/                ← alles wat I/O doet
│   ├── db/
│   │   ├── database.py            # van database.py
│   │   ├── db_models.py           # van models.py
│   │   └── repositories/
│   │       ├── session_repository.py   # van db_logger.py
│   │       └── tenant_repository.py   # van tenant_config.py
│   └── config/
│       └── bedrijf.py             # van bedrijf.py
└── interfaces/                    ← UI lagen
    ├── streamlit/
    │   └── app.py                 # van app.py
    ├── flask/
    │   └── server.py              # van server.py
    └── formatters/
        └── price_formatter.py     # format_* functies uit pricing.py
```

---

## Fase 0 — Voorbereiding ☐
**Tijd: 15 min**

- [ ] Backup gemaakt ✅
- [ ] `git checkout -b refactor/oop-mvc-saas`
- [ ] Handmatige testscript schrijven: alle 3 flows doorlopen (gehele tuin, losse onderdelen, tuinontwerp) + kostenbesparing + contactformulier

---

## Fase 1 — Mappenstructuur aanmaken ☐
**Tijd: 15 min | Risico: geen**

Alleen mappen en lege `__init__.py` bestanden aanmaken. Geen code aanraken.

```
mkdir core core/models core/flows core/pricing core/controllers core/services
mkdir infrastructure infrastructure/db infrastructure/db/repositories infrastructure/config
mkdir interfaces interfaces/streamlit interfaces/flask interfaces/formatters
```
Maak in elke map een leeg `__init__.py`.

**Verificatie:** `python app.py` start zonder fouten.

---

## Fase 2 — Infrastructure laag verplaatsen ☐
**Tijd: 1 uur | Risico: laag**

### Bestanden verplaatsen
| Van | Naar |
|---|---|
| `database.py` | `infrastructure/db/database.py` |
| `models.py` | `infrastructure/db/db_models.py` |
| `bedrijf.py` | `infrastructure/config/bedrijf.py` |
| `mailer.py` | `infrastructure/services/mailer.py` |

### Imports bijwerken in
- `db_logger.py` → `from infrastructure.db.database import ...` en `from infrastructure.db.db_models import ...`
- `bot_logic.py`, `init_db.py`, `migrate_fase2.py`, `leadscore.py`, `tenant_config.py`, `app.py`, `server.py`, `flow_tuinaanleg.py`

**Verificatie:** bot volledig doorlopen — alle drie flows tot contactformulier.
**Commit:** `git commit -m "fase 2: infrastructure bestanden verplaatst"`

---

## Fase 3 — Core models ☐
**Tijd: 30 min | Risico: laag**

### 3a — ChatState verplaatsen
- Kopieer `ChatState` dataclass uit `bot_logic.py` → `core/models/chat_state.py`
- Verwijder uit `bot_logic.py`
- Voeg toe in `bot_logic.py`: `from core.models.chat_state import ChatState`

### 3b — TenantConfig verplaatsen
- Kopieer `TenantConfig` dataclass uit `tenant_config.py` → `core/models/tenant.py`
- Verwijder uit `tenant_config.py`
- Voeg toe in `tenant_config.py`: `from core.models.tenant import TenantConfig`

### 3c — CostResult aanmaken (nieuw bestand)
Maak `core/models/cost_result.py`:
```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class BreakdownItem:
    key: str
    label: str
    unit: str
    qty: Any
    range_eur: Optional[Tuple[int, int]]
    notes: str = ""

@dataclass
class CostResult:
    flow_type: str
    total_range_eur: Tuple[int, int]
    breakdown: List[BreakdownItem] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
```
Nog geen bestaande code aanpassen — dit wordt later gebruikt door de pricers.

**Verificatie:** bot volledig doorlopen.
**Commit:** `git commit -m "fase 3: core models geïsoleerd"`

---

## Fase 4 — Repositories als klassen ☐
**Tijd: 1 uur | Risico: laag**

### 4a — SessionRepository
Maak `infrastructure/db/repositories/session_repository.py`:
```python
class SessionRepository:
    def log_session_created(self, session_id: str, user_agent: str = None) -> None: ...
    def update_session_flow(self, session_id: str, flow_type: str) -> None: ...
    def update_session_completed(self, session_id: str) -> None: ...
    def update_session_ended(self, session_id: str) -> None: ...
    def log_event(self, session_id: str, event_type: str, data: dict) -> None: ...
    def log_price_calculation(self, ...) -> int: ...
    def log_contact_submission(self, ...) -> None: ...
    def save_leadscore(self, ...) -> None: ...
    def increment_terug_actie(self, ...) -> None: ...
    def log_prijs_gezien(self, ...) -> None: ...
    def log_drop_off(self, ...) -> None: ...
    def log_offerte_aangevraagd(self, ...) -> None: ...
```
De `_db()` context manager en `_safe()` helper worden private methoden van de klasse.

Houd `db_logger.py` als tijdelijke doorgeef-laag (verwijder in fase 12):
```python
# db_logger.py — tijdelijk, verwijder in fase 12
_repo = SessionRepository()
def log_session_created(session_id, user_agent=None):
    return _repo.log_session_created(session_id, user_agent)
# ... voor elke functie
```

### 4b — TenantRepository
Maak `infrastructure/db/repositories/tenant_repository.py`:
```python
class TenantRepository:
    def get(self, slug: str) -> Optional[TenantConfig]: ...       # laad_tenant()
    def get_or_default(self, slug: str) -> TenantConfig: ...      # laad_tenant_of_default()
```

**Verificatie:** bot volledig doorlopen.
**Commit:** `git commit -m "fase 4: db_logger en tenant_config als repository klassen"`

---

## Fase 5 — PriceTable (de SaaS-schakelaar) ☐
**Tijd: 2–3 uur | Risico: medium**

Dit is de kritieke stap. Na deze fase werkt de bot met per-tenant-prijzen.

### 5a — Constanten isoleren
Maak `core/pricing/constants.py`:
- Kopieer `PRIJZEN`, `VOLUME_KORTINGEN`, `GRONDWERK_DIEPTES`, `PRICE_META`, `PRIJSTOELICHTING`, `_PRIJSTOELICHTING_ZONDER_GRONDWERK` uit `pricing.py`
- Verwijder ze uit `pricing.py`
- Zet bovenaan `pricing.py`: `from core.pricing.constants import *`

### 5b — PriceTable klasse
Maak `core/pricing/price_table.py`:
```python
from core.pricing.constants import PRIJZEN, VOLUME_KORTINGEN, GRONDWERK_DIEPTES
from core.models.tenant import TenantConfig

class PriceTable:
    def __init__(self, tenant_config: TenantConfig = None):
        overrides = (tenant_config.prijzen or {}) if tenant_config else {}
        self._data = {**PRIJZEN, **overrides}
        self.volume_kortingen = VOLUME_KORTINGEN
        self.grondwerk_dieptes = GRONDWERK_DIEPTES

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def schaal_factor(self, volume: float, soort: str) -> float:
        for drempel, factor in self.volume_kortingen.get(soort, []):
            if volume >= drempel:
                return factor
        return 1.0

DEFAULT_PRICE_TABLE = PriceTable()
```

### 5c — estimate_* functies backward compatible maken
Pas elke `estimate_*` functie aan:
```python
def estimate_tuinaanleg_costs(answers: dict, price_table: PriceTable = None) -> dict:
    p = price_table or DEFAULT_PRICE_TABLE
    # Vervang: PRIJZEN.get(key, x)     → p.get(key, x)
    # Vervang: _schaal_factor(vol, s)  → p.schaal_factor(vol, s)
    # Vervang: GRONDWERK_DIEPTES       → p.grondwerk_dieptes
```
Doe hetzelfde voor `estimate_losse_onderdelen_costs` en `estimate_tuinontwerp_costs`.

**Verificatie:** bot volledig doorlopen. Prijzen moeten identiek zijn als vóór de refactor.
**Commit:** `git commit -m "fase 5: PriceTable klasse — SaaS-schakelaar actief"`

---

## Fase 6 — Pricers als klassen ☐
**Tijd: 1 uur | Risico: laag**

Maak `core/pricing/tuinaanleg_pricer.py`:
```python
class TuinaanlegPricer:
    def __init__(self, price_table: PriceTable):
        self.prices = price_table

    def estimate(self, answers: dict) -> dict:
        # inhoud van estimate_tuinaanleg_costs, maar p = self.prices
```
Houd in `pricing.py` backward-compatible wrapper:
```python
def estimate_tuinaanleg_costs(answers, price_table=None):
    return TuinaanlegPricer(price_table or DEFAULT_PRICE_TABLE).estimate(answers)
```

Doe hetzelfde voor `LossePricer` en `TuinontWerpPricer`.

**Verificatie:** bot volledig doorlopen.
**Commit:** `git commit -m "fase 6: pricers als klassen"`

---

## Fase 7 — PriceFormatter ☐
**Tijd: 30 min | Risico: laag**

Maak `interfaces/formatters/price_formatter.py`:
```python
class PriceFormatter:
    def to_chat_html(self, costs: dict, flow_type: str) -> str: ...       # format_costs_as_chat_html
    def to_customer_summary(self, costs: dict) -> str: ...                # format_tuinaanleg_choices_for_customer
    def to_tuinontwerp_html(self, costs: dict) -> str: ...                # format_tuinontwerp_costs_as_chat_html
    def breakdown_grouped(self, breakdown: list) -> str: ...              # format_breakdown_grouped
```

Houd in `pricing.py` wrappers voor backward compatibility:
```python
_formatter = PriceFormatter()
def format_costs_as_chat_html(costs, flow_type):
    return _formatter.to_chat_html(costs, flow_type)
```

**Verificatie:** bot volledig doorlopen, prijsweergave identiek.
**Commit:** `git commit -m "fase 7: PriceFormatter geïsoleerd"`

---

## Fase 8 — ChatController (bot_logic.py opsplitsen) ☐
**Tijd: 3–4 uur | Risico: medium**

### 8a — ContactController
Maak `core/controllers/contact_controller.py`:
```python
class ContactController:
    def __init__(self, state: ChatState, repo: SessionRepository, mailer):
        self.state = state
        self.repo = repo
        self.mailer = mailer

    def handle_naam(self, t_raw: str) -> List[str]: ...
    def handle_telefoon(self, t_raw: str) -> List[str]: ...
    def handle_email(self, t_raw: str) -> List[str]: ...
    def handle_adres(self, t_raw: str) -> List[str]: ...
    def handle_woonplaats(self, t_raw: str) -> List[str]: ...
    def handle_opmerking(self, t_raw: str) -> List[str]: ...
    def submit(self) -> None: ...
```
Kopieer de `_handle_contact_*` functies als methoden. `state` wordt `self.state` (niet meer als parameter doorgeven, niet meer als return waarde).

### 8b — PostOfferController
Maak `core/controllers/post_offer_controller.py`:
```python
class PostOfferController:
    def __init__(self, state: ChatState, pricer, formatter, repo: SessionRepository):
        self.state = state

    def handle(self, t_raw: str) -> List[str]: ...
    def _handle_main_menu(self, t_raw: str) -> List[str]: ...
    def _handle_lower_costs_menu(self, t_raw: str) -> List[str]: ...
    def _handle_more_green_choice(self, t_raw: str) -> List[str]: ...
    # ... alle _handle_lc_* en overige post-offer handlers
```

### 8c — ChatController
Maak `core/controllers/chat_controller.py`:
```python
class ChatController:
    def __init__(self, state: ChatState, tenant_ctx: TenantContext):
        self.state = state
        self.tenant = tenant_ctx
        self._repo = tenant_ctx.repo
        self._pricer = TuinaanlegPricer(tenant_ctx.price_table)  # + losse + tuinontwerp
        self._formatter = PriceFormatter()
        self._post_offer = PostOfferController(state, self._pricer, self._formatter, self._repo)
        self._contact = ContactController(state, self._repo, MailerService())

    def handle(self, user_text: str) -> List[str]:
        # inhoud van handle_message()
```

Houd `bot_logic.py` als doorgeef-laag (verwijder in fase 12):
```python
def handle_message(state, user_text):
    from infrastructure.db.repositories.tenant_repository import TenantRepository
    from core.pricing.price_table import PriceTable
    from core.models.tenant_context import TenantContext
    tenant = TenantRepository().get_or_default("veldman-hoveniers")
    ctx = TenantContext(config=tenant, price_table=PriceTable(tenant))
    ctrl = ChatController(state, ctx)
    return ctrl.handle(user_text)
```

**Verificatie:** bot volledig doorlopen, alle drie flows + kostenbesparing + contact.
**Commit:** `git commit -m "fase 8: ChatController, PostOfferController, ContactController"`

---

## Fase 9 — TenantContext wiring in server.py ☐
**Tijd: 1 uur | Risico: medium**

Maak `core/models/tenant_context.py`:
```python
from dataclasses import dataclass, field
from core.models.tenant import TenantConfig
from core.pricing.price_table import PriceTable
from infrastructure.db.repositories.session_repository import SessionRepository

@dataclass
class TenantContext:
    config: TenantConfig
    price_table: PriceTable
    repo: SessionRepository = field(default_factory=SessionRepository)
```

Update `server.py` zodat elke request zijn eigen TenantContext krijgt:
```python
@app.route("/chat", methods=["POST"])
def chat():
    slug = request.headers.get("X-Tenant-Slug", "veldman-hoveniers")
    tenant_cfg = TenantRepository().get_or_default(slug)
    tenant_ctx = TenantContext(
        config=tenant_cfg,
        price_table=PriceTable(tenant_cfg),
    )
    state = _get_or_create_state(session_id)
    ctrl = ChatController(state, tenant_ctx)
    response = ctrl.handle(user_input)
    ...
```

**Verificatie:** bot volledig doorlopen. Test ook met een fictieve tenant-override in de DB.
**Commit:** `git commit -m "fase 9: TenantContext per request — multi-tenant pricing actief"`

---

## Fase 10 — Flows opschonen ☐
**Tijd: 30 min | Risico: laag**

Maak `core/flows/base.py`:
```python
from abc import ABC, abstractmethod
from typing import Tuple

class BaseFlow(ABC):
    @abstractmethod
    def get_question(self) -> str: ...

    @abstractmethod
    def handle(self, user_text: str) -> Tuple[str, bool]: ...

    @abstractmethod
    def to_answers(self) -> dict: ...
```

- Verplaats `flow_tuinaanleg.py` → `core/flows/tuinaanleg.py`, laat `TuinaanlegFlowV2` erven van `BaseFlow`
- Verplaats `flow_losse_onderdelen.py` → `core/flows/losse_onderdelen.py`
- Verplaats `flow_tuinontwerp.py` → `core/flows/tuinontwerp.py`
- Verwijder de directe `from pricing import PRIJZEN` import uit de flows — de flows hebben die niet nodig (de pricer doet de berekening)

**Verificatie:** alle drie intake flows doorlopen.
**Commit:** `git commit -m "fase 10: flows opgeschoond en BaseFlow toegevoegd"`

---

## Fase 11 — SavingsService ☐
**Tijd: 3–4 uur | Risico: hoog**

Dit is het gevaarlijkste bestand. Bewaar voor het einde.

Maak `core/pricing/savings_service.py`:
```python
class SavingsService:
    def __init__(self, price_table: PriceTable):
        self.prices = price_table
        self._tuinaanleg_pricer = TuinaanlegPricer(price_table)
        self._losse_pricer = LossePricer(price_table)

    def post_offer_choices_text(self) -> str: ...
    def post_offer_choices_losse_text(self) -> str: ...
    def post_offer_choices_tuinontwerp_text(self) -> str: ...
    def lower_costs_menu_text(self, answers: dict, costs: dict) -> tuple: ...
    def lower_costs_menu_losse_text(self, answers: dict, costs: dict) -> tuple: ...
    def apply_material_change(self, answers: dict, part, choice: str) -> tuple: ...
    def apply_vlonder_change(self, answers: dict, choice: str) -> tuple: ...
    # ... alle functies uit savings.py
```

Houd `savings.py` als backward-compatible wrapper totdat alles migreert.

**Verificatie:** kostenbesparing volledig testen — alle sub-menu's doorlopen (materiaal, groen, vlonder, overkapping, voegen, verlichting, beregening, erfafscheiding).
**Commit:** `git commit -m "fase 11: SavingsService klasse"`

---

## Fase 12 — Cleanup ☐
**Tijd: 1 uur | Risico: laag**

Nu alle wrappers verwijderen en oude bestanden opruimen.

- [ ] Verwijder `bot_logic.py` (leeg na migratie)
- [ ] Verwijder `db_logger.py` (vervangen door SessionRepository)
- [ ] Verwijder `tenant_config.py` (vervangen door TenantRepository)
- [ ] Verwijder `pricing.py` (vervangen door `core/pricing/`)
- [ ] Verwijder `savings.py` (vervangen door SavingsService)
- [ ] Verplaats `app.py` → `interfaces/streamlit/app.py`
- [ ] Verplaats `server.py` → `interfaces/flask/server.py`
- [ ] Controleer alle imports projectbreed (`grep -r "from pricing import"`, etc.)

**Verificatie:** bot volledig doorlopen. Alle drie flows. Dan definitieve commit.
**Commit:** `git commit -m "refactor compleet: OOP/MVC/SaaS architectuur"`

---

## Tijdsschatting totaal

| Fase | Tijd |
|---|---|
| 0–1 Voorbereiding + mappen | 30 min |
| 2 Infrastructure | 1 uur |
| 3 Core models | 30 min |
| 4 Repositories | 1 uur |
| 5 PriceTable | 2–3 uur |
| 6 Pricers | 1 uur |
| 7 PriceFormatter | 30 min |
| 8 ChatController | 3–4 uur |
| 9 TenantContext wiring | 1 uur |
| 10 Flows | 30 min |
| 11 SavingsService | 3–4 uur |
| 12 Cleanup | 1 uur |
| **Totaal** | **~15–18 uur** |

---

## Regels om je aan te houden

1. **Commit na elke fase** — dan kun je altijd terug
2. **Na elke fase handmatig testen** — alle drie flows, kostenbesparing, contact
3. **Nooit twee fasen tegelijk** — ook al voelt het efficiënter
4. **Backward-compatible wrappers** — gooi ze pas weg in fase 12
5. **savings.py altijd als laatste** — het is het meest gekoppelde bestand

---

## SaaS eindresultaat

Na fase 12 kun je een nieuwe hovenier onboarden door:
1. Een `DbTenant` record aanmaken
2. Een `DbTenantConfig` aanmaken met zijn eigen prijzen in het `prijzen` JSON veld
3. De chatbot embedden op zijn website met `X-Tenant-Slug: zijn-bedrijfsnaam` header

Geen code aanpassen per klant. Prijzen, huisstijlkleur en contact volledig per tenant instelbaar via de database.
