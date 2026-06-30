# flow_losse_onderdelen.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from flow_tuinaanleg import parse_m2, parse_yesno, _is_dont_know

# ----------------------------------------------------------------
# Constants
# ----------------------------------------------------------------

_CANCEL_HINT = "\n\nTyp **'terug'** om terug te gaan naar het menu."


def _is_cancel(text: str) -> bool:
    return (text or "").strip().lower() in ("0", "terug", "annuleer", "cancel")

MENU_MAPPING: Dict[int, str] = {
    1: "oprit", 2: "paden", 3: "terras",
    4: "gazon", 5: "beplanting",
    6: "erfafscheiding", 7: "vlonder",
    8: "beregening", 9: "overkapping", 10: "verlichting",
}

LABEL: Dict[str, str] = {
    "oprit": "Oprit", "paden": "Paden", "terras": "Terras",
    "gazon": "Gazon", "beplanting": "Beplanting",
    "erfafscheiding": "Erfafscheiding", "vlonder": "Vlonder",
    "beregening": "Beregening", "overkapping": "Overkapping",
    "verlichting": "Verlichting",
}

BESTRATING = {"oprit", "paden", "terras"}
GROEN = {"gazon", "beplanting"}
NO_DETAIL = {"verlichting"}  # geen vervolgvragen, vaste schatting

MAT_LABELS = {"grind": "Grind", "beton": "Beton", "gebakken": "Gebakken", "keramiek": "Keramiek"}
MAT_MAP = {"1": "grind", "2": "beton", "3": "gebakken", "4": "keramiek"}
ERF_MAP = {"1": "haag", "2": "betonschutting", "3": "design_schutting"}
ERF_LABELS = {"haag": "Haag", "betonschutting": "Betonschutting", "design_schutting": "Design schutting"}
ERF_NUM = {v: k for k, v in ERF_MAP.items()}

VLONDER_MAP = {"1": "zachthout", "2": "hardhout", "3": "composiet"}
HAAG_TYPE_MAP = {"1": "voordelig_laag", "2": "voordelig_hoog", "3": "premium_laag", "4": "premium_hoog"}
HAAG_TYPE_QUESTION = (
    "Welk type haag wilt u?\n"
    "1) Voordelig & laag  – ca. 0,5–1m   (bijv. beuk, haagliguster)\n"
    "2) Voordelig & hoog  – ca. 1,5–2m   (bijv. beuk, haagliguster)\n"
    "3) Premium & laag    – ca. 0,5–1m   (Portugese laurier wintergroen)\n"
    "4) Premium & hoog    – ca. 1,5–2m   (Portugese laurier wintergroen)\n\n"
    "Reageer met 1, 2, 3 of 4."
)
VLONDER_LABELS = {"composiet": "Composiet", "hardhout": "Hardhout", "zachthout": "Zachthout"}
VLONDER_QUESTION = (
    "Welk type vlonder wilt u?\n"
    "1) Zachthout (voordelig) ±10–15 jaar – voordeliger, kortere levensduur, natuurlijke look\n"
    "2) Hardhout (middenprijsklasse) ±20–25 jaar – langere levensduur, kan mooi egaal vergrijzen\n"
    "3) Composiet (hoger segment) ±25–30 jaar – minste onderhoud, langste levensduur\n\n"
    "Reageer met 1, 2 of 3."
)

MAT_QUESTION: Dict[str, str] = {
    "oprit": (
        "Welk materiaal wilt u voor de oprit?\n"
        "1) **Grind** – €35–€60/m²\n2) **Beton klinkers** – €60–€90/m²\n3) **Gebakken klinkers** – €80–€130/m²\n4) **Keramische tegels** – €180–€220/m²\n\n_Prijzen zijn inclusief materiaal, arbeid en btw._\n\n"
        "Reageer met 1, 2, 3 of 4."
    ),
    "paden": (
        "Welk materiaal wilt u voor de paden?\n"
        "1) **Grind** – €35–€60/m²\n2) **Beton klinkers** – €60–€90/m²\n3) **Gebakken klinkers** – €80–€130/m²\n4) **Keramische tegels** – €180–€220/m²\n\n_Prijzen zijn inclusief materiaal, arbeid en btw._\n\n"
        "Reageer met 1, 2, 3 of 4."
    ),
    "terras": (
        "Welk materiaal wilt u voor het terras?\n"
        "1) **Grind** – €35–€60/m²\n2) **Beton klinkers** – €60–€90/m²\n3) **Gebakken klinkers** – €80–€130/m²\n4) **Keramische tegels** – €180–€220/m²\n\n_Prijzen zijn inclusief materiaal, arbeid en btw._\n\n"
        "Reageer met 1, 2, 3 of 4."
    ),
}


# ----------------------------------------------------------------
# Parsers
# ----------------------------------------------------------------

def _parse_menu_choice(text: str) -> Optional[int]:
    """Parst één getal 1–10 uit vrije tekst."""
    for p in re.findall(r"\d+", (text or "").strip()):
        n = int(p)
        if 1 <= n <= 10:
            return n
    return None


def _parse_menu_choices(text: str) -> List[int]:
    """Parst één of meerdere getallen 1–10, uniek en gesorteerd."""
    seen: List[int] = []
    for p in re.findall(r"\d+", (text or "").strip()):
        n = int(p)
        if 1 <= n <= 10 and n not in seen:
            seen.append(n)
    return seen


def _parse_overkapping_m2(text: str) -> Optional[float]:
    t = (text or "").strip()
    preset = {"1": 9.0, "2": 15.0, "3": 20.0}
    if t in preset:
        return preset[t]
    try:
        v = float(t.replace(",", "."))
        if 4.0 <= v <= 500.0:
            return v
    except Exception:
        pass
    return None


def _parse_erf_types(text: str) -> Optional[List[str]]:
    parts = re.findall(r"\d", (text or "").strip())
    result: List[str] = []
    seen: set = set()
    for d in parts:
        if d in ERF_MAP and d not in seen:
            result.append(ERF_MAP[d])
            seen.add(d)
    return result if result else None


# ----------------------------------------------------------------
# Flow
# ----------------------------------------------------------------

@dataclass
class LosseOnderdelenFlow:
    """
    Flow voor losse onderdelen met directe m² invoer.

    Stap 1 (menu):   Gegroepeerd keuzemenu, multi-select 1–10
    Stap 2 (detail): Per onderdeel de benodigde details invullen
    Stap 3 (voegen): Eenmalig vragen of bestrating gevoegd moet worden
    Stap 4 (summary): Overzicht + keuze: meer toevoegen / prijs berekenen
    """

    _configured: Dict[str, Any] = field(default_factory=dict)
    # Bestrating (oprit/paden/terras): lijst van {"m2": float, "materiaal": str, "gevoegd": bool}
    # Overige: enkel dict met component-specifieke keys

    _mode: str = "menu"                  # "menu" | "detail" | "summary"

    _detail_queue: List[str] = field(default_factory=list)
    _detail_current: Optional[str] = None
    _detail_sub: Optional[str] = None
    _pending_item: Optional[Dict] = None  # tijdelijk opslag voor bestrating item in bewerking

    _erf_current_type: Optional[str] = None

    _hint_shown: bool = False
    _done: bool = False
    _pending_replace: Optional[str] = None

    # ----------------------------------------------------------------
    # Public interface
    # ----------------------------------------------------------------

    @classmethod
    def from_answers(cls, answers: Dict[str, Any]) -> "LosseOnderdelenFlow":
        """Herstel een flow met eerder geconfigureerde onderdelen vanuit opgeslagen antwoorden."""
        flow = cls()
        cfg: Dict[str, Any] = {}
        for comp in ("oprit", "paden", "terras"):
            items = answers.get(f"{comp}_items") or []
            if items:
                cfg[comp] = list(items)
        gazon_items = answers.get("gazon_items") or []
        if gazon_items:
            cfg["gazon"] = list(gazon_items)
        elif answers.get("gazon_m2", 0):
            cfg["gazon"] = [{"m2": float(answers["gazon_m2"])}]
        beplanting_items = answers.get("beplanting_items") or []
        if beplanting_items:
            cfg["beplanting"] = list(beplanting_items)
        elif answers.get("beplanting_m2", 0):
            cfg["beplanting"] = [{"m2": float(answers["beplanting_m2"])}]
        if answers.get("overkapping"):
            cfg["overkapping"] = {"m2": float(answers.get("overkapping_m2") or 15.0)}
        if answers.get("verlichting"):
            cfg["verlichting"] = {}
        if answers.get("vlonder_m2", 0):
            cfg["vlonder"] = {
                "m2": float(answers["vlonder_m2"]),
                "type": answers.get("vlonder_type", "composiet"),
            }
        if answers.get("beregening_m2", 0):
            cfg["beregening"] = {
                "m2": float(answers["beregening_m2"]),
                "scope": answers.get("beregening_scope", ""),
                "systeem": answers.get("beregening_systeem", "volautomatisch"),
                "gazon_m2": float(answers.get("beregening_gazon_m2") or 0),
                "beplanting_m2": float(answers.get("beregening_beplanting_m2") or 0),
            }
        erf_items = answers.get("erfafscheiding_items") or []
        if erf_items:
            cfg["erfafscheiding"] = {"items": list(erf_items)}
        flow._configured = cfg
        return flow

    def is_done(self) -> bool:
        return self._done

    def start_question(self) -> str:
        return self._menu_text()

    def handle(self, user_text: str) -> Tuple[str, bool]:
        if self._done:
            return "", True
        t = (user_text or "").strip()
        if self._mode == "menu":
            return self._handle_menu(t)
        if self._mode == "detail":
            return self._handle_detail(t)
        if self._mode == "summary":
            return self._handle_summary(t)
        return "", False

    def to_answers(self) -> Dict[str, Any]:
        """Zet interne state om naar het formaat van estimate_losse_onderdelen_costs."""
        overige: List[str] = []
        erf_items: List[Dict] = []

        for comp in ("erfafscheiding", "vlonder", "beregening"):
            if comp in self._configured:
                overige.append(comp)
        if "erfafscheiding" in self._configured:
            erf_items = self._configured["erfafscheiding"].get("items", [])

        oprit_items      = self._configured.get("oprit",      [])
        paden_items      = self._configured.get("paden",      [])
        terras_items     = self._configured.get("terras",     [])
        gazon_items      = self._configured.get("gazon",      [])
        beplanting_items = self._configured.get("beplanting", [])

        return {
            "oprit_m2":      sum(it.get("m2", 0) for it in oprit_items),
            "paden_m2":      sum(it.get("m2", 0) for it in paden_items),
            "terras_m2":     sum(it.get("m2", 0) for it in terras_items),
            "gazon_m2":      sum(it.get("m2", 0) for it in gazon_items),
            "beplanting_m2": sum(it.get("m2", 0) for it in beplanting_items),
            "gazon_items":      gazon_items,
            "beplanting_items": beplanting_items,
            "materiaal_oprit":  oprit_items[0].get("materiaal", "beton")  if oprit_items  else "beton",
            "materiaal_paden":  paden_items[0].get("materiaal", "beton")  if paden_items  else "beton",
            "materiaal_terras": terras_items[0].get("materiaal", "beton") if terras_items else "beton",
            "oprit_items":   oprit_items,
            "paden_items":   paden_items,
            "terras_items":  terras_items,
            "onkruidwerend_gevoegd": any(
                it.get("gevoegd", False)
                for comp in ("paden", "terras")
                for it in self._configured.get(comp, [])
            ),
            "voegen_m2_custom": sum(
                it.get("m2", 0)
                for comp in ("paden", "terras")
                for it in self._configured.get(comp, [])
                if it.get("gevoegd", False)
            ),
            "overkapping":   "overkapping" in self._configured,
            "overkapping_m2": self._configured.get("overkapping", {}).get("m2", 15.0),
            "verlichting":   "verlichting" in self._configured,
            "overige_wensen": overige,
            "beregening_m2": self._configured.get("beregening", {}).get("m2", 0),
            "beregening_scope": self._configured.get("beregening", {}).get("scope", ""),
            "beregening_systeem": self._configured.get("beregening", {}).get("systeem", "volautomatisch"),
            "beregening_gazon_m2": self._configured.get("beregening", {}).get("gazon_m2", 0),
            "beregening_beplanting_m2": self._configured.get("beregening", {}).get("beplanting_m2", 0),
            "vlonder_m2":    self._configured.get("vlonder", {}).get("m2", 0),
            "vlonder_type":  self._configured.get("vlonder", {}).get("type", "composiet"),
            "erfafscheiding_items": erf_items,
            "_flow_type":    "losse_onderdelen",
        }

    # ----------------------------------------------------------------
    # Menu mode
    # ----------------------------------------------------------------

    def _handle_menu(self, text: str) -> Tuple[str, bool]:
        choices = _parse_menu_choices(text)
        if not choices:
            return "Kies één of meerdere nummers (bijv. 1, 3).\n\n" + self._menu_text(), False

        # Enkelvoudige keuze: confirm_replace logica behouden
        if len(choices) == 1:
            comp = MENU_MAPPING[choices[0]]
            if comp in {"vlonder", "overkapping", "beregening"} and comp in self._configured:
                self._pending_replace = comp
                self._detail_current = comp
                self._mode = "detail"
                self._detail_sub = "confirm_replace"
                info = self._config_info_short(comp)
                return f"U heeft al een {info} geconfigureerd. Wilt u dit aanpassen? (ja/nee)", False
            self._detail_queue = [comp]
            self._mode = "detail"
            self._hint_shown = False
            return self._with_hint(self._advance_detail()), False

        # Meerdere keuzes
        comps = [MENU_MAPPING[n] for n in choices]
        labels = [LABEL[c] for c in comps]
        self._detail_queue = comps
        self._mode = "detail"
        self._hint_shown = False
        intro = "Gekozen: " + ", ".join(labels) + ".\n\n"
        return intro + self._with_hint(self._advance_detail()), False

    def _menu_text(self) -> str:
        def _info(comp: str) -> str:
            if comp not in self._configured:
                return ""
            d = self._configured[comp]
            if comp in BESTRATING:
                items = d if isinstance(d, list) else []
                if not items:
                    return ""
                if len(items) > 1:
                    return f" (✓ {len(items)}x geconfigureerd)"
                total_m2 = sum(it.get("m2", 0) for it in items)
                first_mat = MAT_LABELS.get(items[0].get("materiaal", "beton"), "Beton")
                return f" (✓ {int(total_m2)} m² {first_mat})"
            if comp in GROEN:
                items = d if isinstance(d, list) else []
                if not items:
                    return ""
                if len(items) > 1:
                    return f" (✓ {len(items)}x geconfigureerd)"
                return f" (✓ {int(items[0].get('m2', 0))} m²)"
            if comp == "erfafscheiding":
                items = d.get("items", [])
                total_m = sum(float(it.get("meter") or 0) for it in items)
                return f" (✓ {int(total_m)} m)"
            if comp == "beregening":
                return f" (✓ {int(d.get('m2', 0))} m²)"
            if comp == "vlonder":
                type_lbl = VLONDER_LABELS.get(d.get("type", "composiet"), "Composiet")
                return f" (✓ {int(d.get('m2', 0))} m² {type_lbl})"
            if comp == "overkapping":
                return f" (✓ {int(d.get('m2', 15))} m²)"
            return " (✓)"

        lines = [
            "Wat wilt u aanleggen of toevoegen?\n",
            "Verharding:",
            f"1) Oprit{_info('oprit')}",
            f"2) Paden{_info('paden')}",
            f"3) Terras{_info('terras')}",
            "",
            "Groen:",
            f"4) Gazon{_info('gazon')}",
            f"5) Beplanting{_info('beplanting')}",
            "",
            "Extra's:",
            f"6) Erfafscheiding{_info('erfafscheiding')}",
            f"7) Vlonder{_info('vlonder')}",
            f"8) Beregening{_info('beregening')}",
            f"9) Overkapping{_info('overkapping')}",
            f"10) Verlichting{_info('verlichting')}",
            "",
            "Kies één of meerdere nummers (bijv. 1, 3).",
        ]
        return "\n".join(lines)

    # ----------------------------------------------------------------
    # Detail mode
    # ----------------------------------------------------------------

    def _advance_detail(self) -> str:
        """Pop volgend onderdeel uit queue en stel eerste sub-vraag."""
        while self._detail_queue:
            comp = self._detail_queue.pop(0)
            self._detail_current = comp

            if comp in BESTRATING:
                existing = len(self._configured.get(comp) or [])
                num_txt = f" {existing + 1}" if existing > 0 else ""
                self._detail_sub = "m2"
                return f"Hoeveel m² wordt {self._lidwoord(comp)}{LABEL[comp].lower()}{num_txt}? (bijv. 25)"

            if comp in GROEN:
                existing = len(self._configured.get(comp) or [])
                num_txt = f" {existing + 1}" if existing > 0 else ""
                self._detail_sub = "m2"
                return f"Hoeveel m² wordt {self._lidwoord(comp)}{LABEL[comp].lower()}{num_txt}? (bijv. 25)"

            if comp == "erfafscheiding":
                self._detail_sub = "erf_type"
                return self._erf_type_question()

            if comp == "beregening":
                self._detail_sub = "m2"
                return f"Hoeveel m² wilt u beregenen? (bijv. 50)"

            if comp == "vlonder":
                self._detail_sub = "m2"
                return f"Hoeveel m² wordt de vlonder? (bijv. 12)"

            if comp == "overkapping":
                self._detail_sub = "ov_m2"
                return (
                    "Welke afmeting wilt u voor de overkapping?\n"
                    "1) Knus – ca. 3×3 m (9 m²)\n"
                    "2) Standaard – ca. 5×3 m (15 m²)\n"
                    "3) Ruim – ca. 5×4 m (20 m²)\n"
                    "Of typ een oppervlakte in m² (bijv. 12)"
                )

            if comp in NO_DETAIL:
                self._configured[comp] = {}
                continue  # geen sub-stap nodig, direct volgende

        # Queue leeg
        self._detail_current = None
        self._detail_sub = None
        return self._after_detail_queue()

    def _after_detail_queue(self) -> str:
        return self._enter_summary()

    def _dont_know_hint_for_sub(self) -> str:
        sub = self._detail_sub
        comp = self._detail_current or ""
        if sub == "m2":
            lbl = LABEL.get(comp, comp).lower()
            return f"Geef een schatting in m², bijv. 25. Een ronde waarde is prima.\n\nHoeveel m² wordt {self._lidwoord(comp)}{lbl}?"
        if sub == "materiaal":
            return f"Kies optie **2** (Beton klinkers) als gangbare standaardkeuze.\n\n{MAT_QUESTION.get(comp, 'Reageer met 1, 2, 3 of 4.')}"
        if sub == "voegen_item":
            return "Twijfelt u? Typ **nee** als startpunt. Voegen kan altijd besproken worden."
        if sub == "vlonder_type":
            return f"Kies optie **3** (Composiet) als duurzame standaardkeuze.\n\n{VLONDER_QUESTION}"
        if sub == "erf_meter":
            return "Geef een schatting in meters, bijv. **10**."
        if sub == "erf_type":
            return f"Kies **1** (Haag) als meest gangbare keuze.\n\n{self._erf_type_question()}"
        return "Typ uw antwoord of een schatting."

    def _with_hint(self, text: str) -> str:
        if not self._hint_shown:
            self._hint_shown = True
            return text + _CANCEL_HINT
        return text

    def _cancel_detail(self) -> str:
        self._detail_queue = []
        self._detail_current = None
        self._detail_sub = None
        self._pending_item = None
        self._pending_replace = None
        self._erf_current_type = None
        self._hint_shown = False
        self._mode = "menu"
        return "Oké, geannuleerd. Terug naar het menu.\n\n" + self._menu_text()

    def _handle_detail(self, text: str) -> Tuple[str, bool]:
        if _is_cancel(text):
            return self._cancel_detail(), False
        # "Weet ik niet"-escape
        if _is_dont_know(text) and self._detail_sub not in ("erf_more",):
            return self._dont_know_hint_for_sub(), False

        sub = self._detail_sub
        comp = self._detail_current

        if sub == "confirm_replace":
            return self._detail_confirm_replace(text)
        if sub == "m2":
            return self._detail_m2(text, comp)
        if sub == "materiaal":
            return self._detail_materiaal(text, comp)
        if sub == "voegen_item":
            return self._detail_voegen_item(text, comp)
        if sub == "vlonder_type":
            return self._detail_vlonder_type(text)
        if sub == "erf_type":
            return self._detail_erf_type(text)
        if sub == "erf_meter":
            return self._detail_erf_meter(text)
        if sub == "erf_poortdeur":
            return self._detail_erf_poortdeur(text)
        if sub == "erf_more":
            return self._detail_erf_more(text)
        if sub == "erf_haag_type":
            return self._detail_erf_haag_type(text)
        if sub == "ov_m2":
            return self._detail_ov_m2(text)
        if sub == "beregening_scope":
            return self._detail_beregening_scope(text)
        if sub == "beregening_split":
            return self._detail_beregening_split(text)
        if sub == "beregening_systeem":
            return self._detail_beregening_systeem(text)

        nxt = self._advance_detail()
        return nxt, False

    def _config_info_short(self, comp: str) -> str:
        d = self._configured.get(comp) or {}
        if comp == "vlonder":
            type_lbl = VLONDER_LABELS.get(d.get("type", ""), "")
            return f"vlonder ({int(d.get('m2', 0))} m² {type_lbl})"
        if comp == "overkapping":
            return f"overkapping ({int(d.get('m2', 15))} m²)"
        if comp == "beregening":
            return f"beregening ({int(d.get('m2', 0))} m²)"
        return LABEL.get(comp, comp).lower()

    def _detail_confirm_replace(self, text: str) -> Tuple[str, bool]:
        v = parse_yesno(text)
        comp = self._pending_replace or ""
        if v is None:
            return f"Antwoord met ja of nee. Wilt u de {LABEL.get(comp, comp).lower()} aanpassen?", False
        self._pending_replace = None
        self._detail_current = None
        self._detail_sub = None
        self._hint_shown = False
        if not v:
            self._mode = "menu"
            return "Oké, geen wijziging. Terug naar het menu.\n\n" + self._menu_text(), False
        self._configured.pop(comp, None)
        self._mode = "detail"
        self._detail_queue = [comp]
        return self._with_hint(self._advance_detail()), False

    def _detail_m2(self, text: str, comp: str) -> Tuple[str, bool]:
        v = parse_m2(text)
        if v is None:
            lbl = LABEL.get(comp, comp).lower()
            return f"Ik heb een getal nodig, bijv. 25. Hoeveel m² wordt {self._lidwoord(comp)}{lbl}?", False
        if comp in BESTRATING:
            self._pending_item = {"m2": v}
            self._detail_sub = "materiaal"
            return MAT_QUESTION[comp], False
        if comp in GROEN:
            if comp not in self._configured:
                self._configured[comp] = []
            self._configured[comp].append({"m2": v})
            nxt = self._advance_detail()
            return nxt, False
        if comp not in self._configured:
            self._configured[comp] = {}
        self._configured[comp]["m2"] = v
        if comp == "vlonder":
            self._detail_sub = "vlonder_type"
            return VLONDER_QUESTION, False
        if comp == "beregening":
            self._detail_sub = "beregening_scope"
            return (
                "Voor welk deel wilt u beregening?\n"
                "1) Alleen gazon\n"
                "2) Alleen beplanting\n"
                "3) Gazon én beplanting\n\n"
                "Reageer met 1, 2 of 3."
            ), False
        nxt = self._advance_detail()
        return nxt, False

    def _detail_materiaal(self, text: str, comp: str) -> Tuple[str, bool]:
        t = (text or "").strip()
        if t not in MAT_MAP:
            return MAT_QUESTION.get(comp, "Reageer met 1, 2, 3 of 4."), False
        mat = MAT_MAP[t]
        if comp in BESTRATING:
            self._pending_item = dict(self._pending_item or {})
            self._pending_item["materiaal"] = mat
            # Voegen alleen uitvragen voor paden/terras met beton of keramiek
            if comp in ("paden", "terras") and mat in ("beton", "keramiek"):
                self._detail_sub = "voegen_item"
                lidwoord = "het " if comp == "terras" else "de "
                return f"Wilt u {lidwoord}{LABEL[comp].lower()} gevoegd hebben? (ja/nee)", False
            # Overige bestrating (oprit, grind, gebakken): geen voegen
            self._pending_item["gevoegd"] = False
            if comp not in self._configured:
                self._configured[comp] = []
            self._configured[comp].append(self._pending_item)
            self._pending_item = None
        else:
            self._configured[comp]["materiaal"] = mat
        nxt = self._advance_detail()
        return nxt, False

    def _detail_voegen_item(self, text: str, comp: str) -> Tuple[str, bool]:
        v = parse_yesno(text)
        if v is None:
            lidwoord = "het " if comp == "terras" else "de "
            return f"Antwoord met ja of nee. Wilt u {lidwoord}{LABEL[comp].lower()} gevoegd hebben?", False
        self._pending_item["gevoegd"] = v
        if comp not in self._configured:
            self._configured[comp] = []
        self._configured[comp].append(self._pending_item)
        self._pending_item = None
        nxt = self._advance_detail()
        return nxt, False

    def _detail_vlonder_type(self, text: str) -> Tuple[str, bool]:
        t = (text or "").strip()
        if t not in VLONDER_MAP:
            return VLONDER_QUESTION, False
        self._configured["vlonder"]["type"] = VLONDER_MAP[t]
        nxt = self._advance_detail()
        return nxt, False

    def _erf_type_question(self) -> str:
        items = (self._configured.get("erfafscheiding") or {}).get("items", [])
        type_counts: Dict[str, int] = {}
        for it in items:
            t = it.get("type", "")
            type_counts[t] = type_counts.get(t, 0) + 1
        lines = ["Welk type erfafscheiding wilt u toevoegen?"]
        for key, label in ERF_LABELS.items():
            num = ERF_NUM.get(key, "?")
            count = type_counts.get(key, 0)
            indicator = f" ({count}×)" if count > 0 else ""
            lines.append(f"{num}) {label}{indicator}")
        lines.append("\nReageer met 1, 2 of 3.")
        return "\n".join(lines)

    def _detail_erf_type(self, text: str) -> Tuple[str, bool]:
        chosen = None
        for d in re.findall(r"\d", (text or "").strip()):
            if d in ERF_MAP:
                chosen = ERF_MAP[d]
                break
        if not chosen:
            return self._erf_type_question(), False
        if "erfafscheiding" not in self._configured:
            self._configured["erfafscheiding"] = {"items": []}
        self._erf_current_type = chosen
        self._detail_sub = "erf_meter"
        lbl = ERF_LABELS.get(chosen, chosen)
        return f"Hoeveel meter {lbl.lower()} is het ongeveer? (bijv. 10)", False

    def _detail_erf_meter(self, text: str) -> Tuple[str, bool]:
        v = parse_m2(text)
        if v is None:
            return "Geef een getal, bijv. 10.", False
        if self._erf_current_type == "haag":
            self._pending_item = {"type": self._erf_current_type, "meter": v, "poortdeur": None}
            self._detail_sub = "erf_haag_type"
            return HAAG_TYPE_QUESTION, False
        self._pending_item = {"type": self._erf_current_type, "meter": v}
        lbl = ERF_LABELS.get(self._erf_current_type, self._erf_current_type)
        self._detail_sub = "erf_poortdeur"
        return f"Wilt u bij deze {lbl.lower()} ook een poortdeur opnemen?\n1) Ja\n2) Nee", False

    def _detail_erf_poortdeur(self, text: str) -> Tuple[str, bool]:
        v = parse_yesno(text)
        if v is None:
            lbl = ERF_LABELS.get(self._erf_current_type or "", "schutting").lower()
            return f"Antwoord met 1 (ja) of 2 (nee). Wilt u bij deze {lbl} een poortdeur opnemen?", False
        item = dict(self._pending_item or {})
        item["poortdeur"] = v
        self._configured["erfafscheiding"]["items"].append(item)
        self._pending_item = None
        self._erf_current_type = None
        return self._erf_overzicht_and_more()

    def _detail_erf_haag_type(self, text: str) -> Tuple[str, bool]:
        t = (text or "").strip()
        if t not in HAAG_TYPE_MAP:
            return HAAG_TYPE_QUESTION, False
        item = dict(self._pending_item or {})
        item["haag_type"] = HAAG_TYPE_MAP[t]
        self._configured["erfafscheiding"]["items"].append(item)
        self._pending_item = None
        self._erf_current_type = None
        return self._erf_overzicht_and_more()

    def _erf_overzicht_and_more(self) -> Tuple[str, bool]:
        items = self._configured["erfafscheiding"]["items"]
        overzicht = ["Toegevoegd. Uw erfafscheiding tot nu toe:"]
        for it in items:
            t = (it.get("type") or "").strip().lower()
            lbl = ERF_LABELS.get(t, t)
            m = int(it.get("meter") or 0)
            if t == "haag":
                haag_type = (it.get("haag_type") or "klassiek").strip()
                overzicht.append(f"- {lbl} ({haag_type}): {m} m")
            else:
                poort_txt = ", met poortdeur" if it.get("poortdeur") else ""
                overzicht.append(f"- {lbl}: {m} m{poort_txt}")
        overzicht.append("\nWilt u nog een erfafscheiding toevoegen? (ja/nee)")
        self._detail_sub = "erf_more"
        return "\n".join(overzicht), False

    def _detail_erf_more(self, text: str) -> Tuple[str, bool]:
        v = parse_yesno(text)
        if v is None:
            return "Antwoord met ja of nee. Wilt u nog een erfafscheiding toevoegen?", False
        if v:
            self._detail_sub = "erf_type"
            return self._erf_type_question(), False
        nxt = self._advance_detail()
        return nxt, False

    def _detail_ov_m2(self, text: str) -> Tuple[str, bool]:
        v = _parse_overkapping_m2(text)
        if v is None:
            return "Reageer met 1, 2 of 3, of typ een oppervlakte in m² (bijv. 12).", False
        self._configured["overkapping"] = {"m2": v}
        nxt = self._advance_detail()
        return nxt, False

    def _detail_beregening_scope(self, text: str) -> Tuple[str, bool]:
        mapping = {"1": "gazon", "2": "beplanting", "3": "allebei"}
        v = (text or "").strip()
        if v not in mapping:
            return (
                "Reageer met 1, 2 of 3.\n"
                "1) Alleen gazon\n"
                "2) Alleen beplanting\n"
                "3) Gazon én beplanting"
            ), False
        self._configured["beregening"]["scope"] = mapping[v]
        if v == "3":
            total_m2 = int(self._configured["beregening"].get("m2", 0))
            self._detail_sub = "beregening_split"
            return (
                f"Hoeveel m² van de {total_m2} m² is **gazon**?\n"
                f"(het restant wordt als beplanting gerekend)"
            ), False
        self._detail_sub = "beregening_systeem"
        return (
            "Welk type beregeningssysteem heeft u in gedachten?\n"
            "1) Basis – deels handmatig instellen\n"
            "2) Volautomatisch – loopt op een tijdschema\n"
            "3) Smart – via app te bedienen (wifi/weer-gestuurd)\n\n"
            "Reageer met 1, 2 of 3."
        ), False

    def _detail_beregening_split(self, text: str) -> Tuple[str, bool]:
        total_m2 = float(self._configured["beregening"].get("m2", 0))
        v = parse_m2(text)
        if v is None or v < 0 or v > total_m2:
            return (
                f"Geef een getal tussen 0 en {int(total_m2)} "
                f"(bijv. {int(total_m2 // 2)})."
            ), False
        self._configured["beregening"]["gazon_m2"] = v
        self._configured["beregening"]["beplanting_m2"] = total_m2 - v
        self._detail_sub = "beregening_systeem"
        return (
            "Welk type beregeningssysteem heeft u in gedachten?\n"
            "1) Basis – deels handmatig instellen\n"
            "2) Volautomatisch – loopt op een tijdschema\n"
            "3) Smart – via app te bedienen (wifi/weer-gestuurd)\n\n"
            "Reageer met 1, 2 of 3."
        ), False

    def _detail_beregening_systeem(self, text: str) -> Tuple[str, bool]:
        mapping = {"1": "basis", "2": "volautomatisch", "3": "highend"}
        v = (text or "").strip()
        if v not in mapping:
            return (
                "Reageer met 1, 2 of 3.\n"
                "1) Basis – deels handmatig instellen\n"
                "2) Volautomatisch – loopt op een tijdschema\n"
                "3) Smart – via app te bedienen (wifi/weer-gestuurd)"
            ), False
        self._configured["beregening"]["systeem"] = mapping[v]
        nxt = self._advance_detail()
        return nxt, False


    # ----------------------------------------------------------------
    # Summary mode
    # ----------------------------------------------------------------

    def _enter_summary(self) -> str:
        self._mode = "summary"
        return self._summary_text()

    def _handle_summary(self, text: str) -> Tuple[str, bool]:
        t = (text or "").strip()
        if t == "1":
            self._mode = "menu"
            return self._menu_text(), False
        if t == "2":
            self._done = True
            return "", True
        return self._summary_text(), False

    def _summary_text(self) -> str:
        lines = ["Uw huidige selectie:"]

        for comp, d in self._configured.items():
            if comp in BESTRATING:
                items_list = d  # d is een lijst van items
                for i, item in enumerate(items_list):
                    num = f" {i + 1}" if len(items_list) > 1 else ""
                    mat_lbl = MAT_LABELS.get(item.get("materiaal", "beton"), "Beton")
                    voegen_txt = ", gevoegd" if item.get("gevoegd", False) else ""
                    lines.append(f"- {LABEL[comp]}{num}: {int(item.get('m2', 0))} m² ({mat_lbl}{voegen_txt})")
            elif comp in GROEN:
                items_list = d if isinstance(d, list) else [{"m2": d.get("m2", 0)}]
                for i, item in enumerate(items_list):
                    num = f" {i + 1}" if len(items_list) > 1 else ""
                    lines.append(f"- {LABEL[comp]}{num}: {int(item.get('m2', 0))} m²")
            elif comp == "erfafscheiding":
                for it in d.get("items", []):
                    t = (it.get("type") or "").strip().lower()
                    m = int(it.get("meter") or 0)
                    if t == "haag":
                        haag_type = (it.get("haag_type") or "klassiek").strip()
                        lines.append(f"- Haag ({haag_type}): {m} m")
                    elif t == "betonschutting":
                        lines.append(f"- Betonschutting: {m} m")
                    elif t == "design_schutting":
                        lines.append(f"- Design schutting: {m} m")
            elif comp == "overkapping":
                lines.append(f"- Overkapping: ca. {int(d.get('m2', 15))} m²")
            elif comp == "vlonder":
                m2 = int(d.get("m2", 0))
                type_lbl = VLONDER_LABELS.get(d.get("type", "composiet"), "Composiet")
                lines.append(f"- Vlonder: {m2} m² ({type_lbl})")
            elif comp == "beregening":
                scope = d.get("scope", "")
                g_m2 = d.get("gazon_m2", 0)
                b_m2 = d.get("beplanting_m2", 0)
                if scope == "allebei" and (g_m2 or b_m2):
                    lines.append(f"- Beregening: {int(g_m2)} m² gazon + {int(b_m2)} m² beplanting")
                else:
                    lines.append(f"- Beregening: {int(d.get('m2', 0))} m²")
            elif comp == "verlichting":
                lines.append("- Verlichting (basispakket)")

        if not self._configured:
            lines.append("(nog niets geselecteerd)")

        lines += ["", "1) Nog een onderdeel toevoegen", "2) Prijs berekenen"]
        return "\n".join(lines)

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    @staticmethod
    def _lidwoord(comp: str) -> str:
        return {
            "oprit": "de ", "paden": "de ", "terras": "het ",
            "gazon": "het ", "beplanting": "de ",
        }.get(comp, "de ")
