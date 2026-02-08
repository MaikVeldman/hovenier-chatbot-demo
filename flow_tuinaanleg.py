# flow_tuinaanleg.py
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, Optional, Tuple, List


_M2_RE = re.compile(r"(?P<num>\d+(?:[.,]\d+)?)\s*(?:m2|m²)?", re.IGNORECASE)
_NUM_RE = re.compile(r"(?P<num>\d+(?:[.,]\d+)?)", re.IGNORECASE)


def parse_m2(text: str) -> Optional[float]:
    t = text.strip().lower().replace(" ", "").replace("±", "")
    m = _M2_RE.search(t)
    if not m:
        return None
    try:
        val = float(m.group("num").replace(",", "."))
    except ValueError:
        return None
    if val <= 0 or val > 100000:
        return None
    return val


def parse_number(text: str, *, min_v: float = 0.0, max_v: float = 100000.0) -> Optional[float]:
    t = text.strip().lower().replace(" ", "").replace("±", "")
    m = _NUM_RE.search(t)
    if not m:
        return None
    try:
        val = float(m.group("num").replace(",", "."))
    except ValueError:
        return None
    if val <= min_v or val > max_v:
        return None
    return val


def parse_choice(text: str, allowed: Tuple[str, ...]) -> Optional[str]:
    t = text.strip()
    return t if t in allowed else None


def parse_yesno(text: str) -> Optional[bool]:
    t = text.strip().lower()
    if t in ("ja", "j", "yes", "y"):
        return True
    if t in ("nee", "n", "no"):
        return False
    return None


def parse_pct(text: str) -> Optional[int]:
    t = text.strip().replace("%", "").strip()
    if not t.isdigit():
        return None
    v = int(t)
    if v < 0 or v > 100:
        return None
    return v


def format_eur_range(min_v: int, max_v: int) -> str:
    return f"€{min_v:,}".replace(",", ".") + "–" + f"€{max_v:,}".replace(",", ".")


@dataclass
class Step:
    key: str
    kind: str
    prompt: str
    allowed: Tuple[str, ...] = ()
    error_prompt: Optional[str] = None


@dataclass
class TuinaanlegFlow:
    prijzen: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    step_index: int = 0
    answers: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.steps = self._build_steps()
        self._init_answers()

    def _init_answers(self) -> None:
        self.answers = {
            "tuin_m2": None,

            "verhouding_bestrating_groen": None,
            "bestrating_pct": None,
            "groen_pct": None,
            "confirm_bestrating_groen": None,  # ✅ NEW

            "verhouding_gazon_beplanting": None,
            "gazon_pct": None,
            "beplanting_pct": None,
            "confirm_gazon_beplanting": None,  # ✅ NEW

            "verhouding_oprit_paden_terras": None,
            "oprit_pct": None,
            "paden_pct": None,
            "terras_pct": None,
            "confirm_oprit_paden_terras": None,  # ✅ NEW

            "materiaal_oprit": None,
            "materiaal_paden": None,
            "materiaal_terras": None,

            "onkruidwerend_gevoegd": None,
            "overkapping": None,
            "verlichting": None,

            # wensen
            "overige_wensen": [],

            # beregening
            "beregening_scope": None,  # "gazon" | "beplanting" | "allebei"

            # vlonder
            "vlonder_type": None,

            # erfafscheiding (MEERDERE)
            "erfafscheiding_items": [],  # list[{"type":..., "meter":..., "poortdeur":...}]

            # interne flow-state
            "_pending_extras": [],
            "_erfafscheiding_types_selected": [],
            "_erfafscheiding_idx": 0,
            "_erfafscheiding_current_type": None,
            "_erfafscheiding_current_meter": None,
        }

    def is_done(self) -> bool:
        return self.step_index >= len(self.steps)

    # -------------------------
    # Mini confirms / labels
    # -------------------------
    def _confirm_prefix(self, title: str, items: List[str]) -> str:
        items = [str(x).strip() for x in items if str(x).strip()]
        if not items:
            return ""
        return f"Gekozen {title}: " + ", ".join(items) + ".\n\n"

    def _erf_type_pretty(self, t: Optional[str]) -> str:
        m = {
            "haag": "haag",
            "betonschutting": "betonschutting",
            "design_schutting": "design schutting",
        }
        return m.get((t or "").strip().lower(), "erfafscheiding")

    def get_question(self) -> str:
        if self.is_done():
            return ""

        step = self.steps[self.step_index]

        # ✅ Confirm-vragen (auto-berekende laatste %)
        if step.key == "confirm_bestrating_groen":
            b = int(self.answers.get("bestrating_pct") or 0)
            g = int(self.answers.get("groen_pct") or 0)
            return f"Ik kom uit op {b}% bestrating en {g}% groen. Klopt dit? (ja/nee)"

        if step.key == "confirm_gazon_beplanting":
            ga = int(self.answers.get("gazon_pct") or 0)
            bp = int(self.answers.get("beplanting_pct") or 0)
            return f"Ik kom uit op {ga}% gazon en {bp}% beplanting. Klopt dit? (ja/nee)"

        if step.key == "confirm_oprit_paden_terras":
            o = int(self.answers.get("oprit_pct") or 0)
            p = int(self.answers.get("paden_pct") or 0)
            t = int(self.answers.get("terras_pct") or 0)
            return f"Ik kom uit op {o}% oprit, {p}% paden en {t}% terras. Klopt dit? (ja/nee)"

        # erfafscheiding special-cases
        if step.key == "erfafscheiding_meter":
            t = self._erf_type_pretty(self.answers.get("_erfafscheiding_current_type"))
            return f"Hoeveel meter {t} is het ongeveer? (bijv. 10)"

        if step.key == "poortdeur":
            t = self._erf_type_pretty(self.answers.get("_erfafscheiding_current_type"))
            return f"Wilt u bij deze {t} ook een poortdeur opnemen? (ja/nee)"

        return step.prompt

    def _goto_step(self, key: str) -> None:
        for i, s in enumerate(self.steps):
            if s.key == key:
                self.step_index = i
                return

    def _append_overige_once(self, tag: str) -> None:
        tag = str(tag).strip().lower()
        arr = self.answers.get("overige_wensen") or []
        arr_norm = [str(x).strip().lower() for x in arr]
        if tag and tag not in arr_norm:
            arr.append(tag)
        self.answers["overige_wensen"] = arr

    # -------------------------
    # Multi-select parsing
    # -------------------------
    def _parse_multi_digits(self, user_text: str, *, allowed: Tuple[str, ...]) -> Optional[Tuple[str, ...]]:
        t = (user_text or "").strip().lower()
        if not t:
            return None

        if t in ("nee", "n", "no"):
            return ("nee",)

        digits = re.findall(r"\d", t)
        if not digits:
            return None

        out: List[str] = []
        seen = set()
        for d in digits:
            if d in allowed and d not in seen:
                out.append(d)
                seen.add(d)

        if not out:
            return None

        return tuple(out)

    # -------------------------
    # Pending extras queue helpers
    # -------------------------
    def _start_pending_extras(self, selected: Tuple[str, ...]) -> Tuple[str, bool]:
        wanted = set(selected)

        chosen_labels: List[str] = []
        pending: List[str] = []

        if "1" in wanted:
            self._append_overige_once("erfafscheiding")
            chosen_labels.append("Erfafscheiding")
            pending.append("erfafscheiding_type")

        if "2" in wanted:
            self._append_overige_once("vlonder")
            chosen_labels.append("Vlonder")
            pending.append("vlonder_type")

        if "3" in wanted:
            self._append_overige_once("beregening")
            chosen_labels.append("Beregening")
            pending.append("beregening_scope")

        self.answers["_pending_extras"] = pending

        prefix = self._confirm_prefix("opties", chosen_labels)

        if pending:
            self._goto_step(pending[0])
            return prefix + self.get_question(), False

        self.step_index = len(self.steps)
        return self.get_question(), True

    def _advance_pending_extras(self) -> Tuple[str, bool]:
        pending: List[str] = list(self.answers.get("_pending_extras") or [])
        if not pending:
            self.step_index = len(self.steps)
            return self.get_question(), True

        pending = pending[1:]
        self.answers["_pending_extras"] = pending

        if not pending:
            self.step_index = len(self.steps)
            return self.get_question(), True

        self._goto_step(pending[0])
        return self.get_question(), False

    # -------------------------
    # Main handler
    # -------------------------
    def handle(self, user_text: str) -> Tuple[str, bool]:
        if self.is_done():
            return self.get_question(), True

        step = self.steps[self.step_index]
        ok, value = self._validate(step, user_text)
        if not ok:
            return (step.error_prompt or step.prompt), False

        # -------------------------
        # ✅ Confirm handlers (auto %)
        # -------------------------
        if step.key == "confirm_bestrating_groen":
            self.answers["confirm_bestrating_groen"] = value
            if value is True:
                self.step_index += 1
                return self.get_question(), False

            # reset groep en opnieuw
            self.answers["bestrating_pct"] = None
            self.answers["groen_pct"] = None
            self.answers["confirm_bestrating_groen"] = None
            self._goto_step("bestrating_pct")
            return "Helemaal goed. Vul het opnieuw in: welk percentage wordt bestrating? (0–100%)", False

        if step.key == "confirm_gazon_beplanting":
            self.answers["confirm_gazon_beplanting"] = value
            if value is True:
                self.step_index += 1
                return self.get_question(), False

            self.answers["gazon_pct"] = None
            self.answers["beplanting_pct"] = None
            self.answers["confirm_gazon_beplanting"] = None
            self._goto_step("gazon_pct")
            return "Helemaal goed. Vul het opnieuw in: welk percentage van het groen wordt gazon? (0–100%)", False

        if step.key == "confirm_oprit_paden_terras":
            self.answers["confirm_oprit_paden_terras"] = value
            if value is True:
                self.step_index += 1
                return self.get_question(), False

            self.answers["oprit_pct"] = None
            self.answers["paden_pct"] = None
            self.answers["terras_pct"] = None
            self.answers["confirm_oprit_paden_terras"] = None
            self._goto_step("oprit_pct")
            return "Helemaal goed. Vul het opnieuw in: welk percentage wordt oprit? (0–100%)", False

        # -------------------------
        # Overige wensen confirmed
        # -------------------------
        if step.key == "overige_wensen":
            if value == ("nee",):
                self.step_index = len(self.steps)
                return self.get_question(), True
            return self._start_pending_extras(value)

        if step.key == "beregening_scope":
            self.answers["beregening_scope"] = value
            return self._advance_pending_extras()

        if step.key == "vlonder_type":
            self.answers["vlonder_type"] = value
            return self._advance_pending_extras()

        if step.key == "erfafscheiding_type":
            mapping = {"1": "haag", "2": "betonschutting", "3": "design_schutting"}
            types = [mapping[c] for c in value if c in mapping]

            if not types:
                return (step.error_prompt or step.prompt), False

            self.answers["_erfafscheiding_types_selected"] = types
            self.answers["_erfafscheiding_idx"] = 0
            self.answers["_erfafscheiding_current_type"] = types[0]
            self.answers["_erfafscheiding_current_meter"] = None

            pretty_map = {
                "haag": "Haag",
                "betonschutting": "Betonschutting",
                "design_schutting": "Design schutting",
            }
            prefix = self._confirm_prefix("erfafscheiding", [pretty_map.get(t, t) for t in types])

            self._goto_step("erfafscheiding_meter")
            return prefix + self.get_question(), False

        if step.key == "erfafscheiding_meter":
            cur_type = (self.answers.get("_erfafscheiding_current_type") or "").strip().lower()
            self.answers["_erfafscheiding_current_meter"] = value

            if cur_type in ("betonschutting", "design_schutting"):
                self._goto_step("poortdeur")
                return self.get_question(), False

            self.answers["erfafscheiding_items"].append({"type": cur_type, "meter": value, "poortdeur": None})
            return self._next_erfafscheiding_or_advance()

        if step.key == "poortdeur":
            cur_type = (self.answers.get("_erfafscheiding_current_type") or "").strip().lower()
            meter = self.answers.get("_erfafscheiding_current_meter")

            self.answers["erfafscheiding_items"].append({"type": cur_type, "meter": meter, "poortdeur": value})
            return self._next_erfafscheiding_or_advance()

        # -------------------------
        # Generic store
        # -------------------------
        self.answers[step.key] = value

        # -------------------------
        # ✅ Presets (niet-custom)
        # -------------------------
        if step.key == "verhouding_bestrating_groen":
            presets = {"70_30": (70, 30), "50_50": (50, 50), "30_70": (30, 70)}
            if value in presets:
                b, g = presets[value]
                self.answers["bestrating_pct"] = b
                self.answers["groen_pct"] = g
            else:
                # custom -> percentages later
                self.answers["bestrating_pct"] = None
                self.answers["groen_pct"] = None
                self.answers["confirm_bestrating_groen"] = None

        if step.key == "verhouding_gazon_beplanting":
            presets = {"70_30": (70, 30), "50_50": (50, 50), "30_70": (30, 70)}
            if value in presets:
                ga, bp = presets[value]
                self.answers["gazon_pct"] = ga
                self.answers["beplanting_pct"] = bp
            else:
                self.answers["gazon_pct"] = None
                self.answers["beplanting_pct"] = None
                self.answers["confirm_gazon_beplanting"] = None

        if step.key == "verhouding_oprit_paden_terras":
            presets = {
                "50_30_20": (50, 30, 20),
                "40_30_30": (40, 30, 30),
                "30_30_40": (30, 30, 40),
                "20_30_50": (20, 30, 50),
            }
            if value in presets:
                o, p, t = presets[value]
                self.answers["oprit_pct"] = o
                self.answers["paden_pct"] = p
                self.answers["terras_pct"] = t
            else:
                self.answers["oprit_pct"] = None
                self.answers["paden_pct"] = None
                self.answers["terras_pct"] = None
                self.answers["confirm_oprit_paden_terras"] = None

        # -------------------------
        # ✅ Custom: auto-bereken laatste % + confirm
        # -------------------------
        if step.key == "bestrating_pct" and self.answers.get("verhouding_bestrating_groen") == "custom":
            b = int(value)
            self.answers["groen_pct"] = 100 - b
            self._goto_step("confirm_bestrating_groen")
            return self.get_question(), False

        if step.key == "gazon_pct" and self.answers.get("verhouding_gazon_beplanting") == "custom":
            ga = int(value)
            self.answers["beplanting_pct"] = 100 - ga
            self._goto_step("confirm_gazon_beplanting")
            return self.get_question(), False

        # Oprit/paden/terras custom:
        # na paden_pct berekenen we terras_pct automatisch en vragen confirm
        if step.key == "paden_pct" and self.answers.get("verhouding_oprit_paden_terras") == "custom":
            o = int(self.answers.get("oprit_pct") or 0)
            p = int(value)
            s = o + p

            if s > 100:
                # reset groep en opnieuw
                self.answers["oprit_pct"] = None
                self.answers["paden_pct"] = None
                self.answers["terras_pct"] = None
                self.answers["confirm_oprit_paden_terras"] = None
                self._goto_step("oprit_pct")
                return (
                    f"Dit is samen {s}%. Dat kan niet (max 100%). "
                    f"Laten we opnieuw beginnen: welk % wordt oprit? (0–100%)",
                    False
                )

            self.answers["terras_pct"] = 100 - s
            self._goto_step("confirm_oprit_paden_terras")
            return self.get_question(), False

        # -------------------------
        # advance
        # -------------------------
        self.step_index += 1

        # -------------------------
        # ✅ Skip logic (niet-custom: sla custom-velden + confirms over)
        # -------------------------
        while not self.is_done():
            k = self.steps[self.step_index].key

            # custom percent/confirm steps overslaan als verhouding niet custom is
            if k in ("bestrating_pct", "confirm_bestrating_groen") and self.answers.get("verhouding_bestrating_groen") != "custom":
                self.step_index += 1
                continue

            if k in ("gazon_pct", "confirm_gazon_beplanting") and self.answers.get("verhouding_gazon_beplanting") != "custom":
                self.step_index += 1
                continue

            if k in ("oprit_pct", "paden_pct", "confirm_oprit_paden_terras") and self.answers.get("verhouding_oprit_paden_terras") != "custom":
                self.step_index += 1
                continue

            # materialen overslaan als pct=0
            if k == "materiaal_oprit" and int(self.answers.get("oprit_pct") or 0) == 0:
                self.answers["materiaal_oprit"] = None
                self.step_index += 1
                continue

            if k == "materiaal_paden" and int(self.answers.get("paden_pct") or 0) == 0:
                self.answers["materiaal_paden"] = None
                self.step_index += 1
                continue

            if k == "materiaal_terras" and int(self.answers.get("terras_pct") or 0) == 0:
                self.answers["materiaal_terras"] = None
                self.step_index += 1
                continue

            break

        if self.is_done():
            return (self.get_question(), True)

        return self.get_question(), False

    def _next_erfafscheiding_or_advance(self) -> Tuple[str, bool]:
        types: List[str] = list(self.answers.get("_erfafscheiding_types_selected") or [])
        idx = int(self.answers.get("_erfafscheiding_idx") or 0)
        idx += 1
        self.answers["_erfafscheiding_idx"] = idx

        if idx < len(types):
            self.answers["_erfafscheiding_current_type"] = types[idx]
            self.answers["_erfafscheiding_current_meter"] = None
            self._goto_step("erfafscheiding_meter")
            return self.get_question(), False

        self.answers["_erfafscheiding_current_type"] = None
        self.answers["_erfafscheiding_current_meter"] = None
        self.answers["_erfafscheiding_types_selected"] = []
        self.answers["_erfafscheiding_idx"] = 0
        return self._advance_pending_extras()

    # -------------------------
    # Validation
    # -------------------------
    def _validate(self, step: Step, user_text: str) -> Tuple[bool, Any]:
        if step.kind == "m2":
            v = parse_m2(user_text)
            return (v is not None), v

        if step.kind == "number":
            v = parse_number(user_text, min_v=0.0, max_v=100000.0)
            return (v is not None), v

        if step.kind == "pct":
            v = parse_pct(user_text)
            return (v is not None), v

        if step.kind == "yesno":
            v = parse_yesno(user_text)
            return (v is not None), v

        if step.kind == "choice":
            v = parse_choice(user_text, step.allowed)
            if v is None:
                return False, None

            if step.key == "verhouding_bestrating_groen":
                return True, {"1": "70_30", "2": "50_50", "3": "30_70", "4": "custom"}[v]
            if step.key == "verhouding_gazon_beplanting":
                return True, {"1": "70_30", "2": "50_50", "3": "30_70", "4": "custom"}[v]
            if step.key == "verhouding_oprit_paden_terras":
                return True, {"1": "50_30_20", "2": "40_30_30", "3": "30_30_40", "4": "20_30_50", "5": "custom"}[v]

            # ✅ materiaal mapping (goedkoop -> duur): 1=grind, 2=beton, 3=gebakken, 4=keramiek
            if step.key in ("materiaal_oprit", "materiaal_paden", "materiaal_terras"):
                return True, {"1": "grind", "2": "beton", "3": "gebakken", "4": "keramiek"}[v]

            if step.key == "beregening_scope":
                return True, {"1": "gazon", "2": "beplanting", "3": "allebei"}[v]

            # ✅ FIX: vlonder mapping
            if step.key == "vlonder_type":
                return True, {"1": "zachthout", "2": "hardhout", "3": "composiet"}[v]

            return True, v

        if step.key == "overige_wensen":
            parsed = self._parse_multi_digits(user_text, allowed=("1", "2", "3"))
            if parsed is None:
                return False, None
            return True, parsed

        if step.key == "erfafscheiding_type":
            parsed = self._parse_multi_digits(user_text, allowed=("1", "2", "3"))
            if parsed is None or parsed == ("nee",):
                return False, None
            return True, parsed

        return True, user_text.strip()

    # -------------------------
    # Steps
    # -------------------------
    def _build_steps(self) -> Tuple[Step, ...]:
        overkapping_txt = self._overkapping_price_text()
        verlichting_txt = self._verlichting_price_text()

        return (
            Step(
                "tuin_m2", "m2",
                "Hoe groot is uw tuin in m²? (geef een getal)",
                error_prompt="Ik heb alleen een getal nodig, bijvoorbeeld 60. Hoe groot is uw tuin in m²?"
            ),

            Step("verhouding_bestrating_groen", "choice", (
                "Hoe wilt u de tuin verdelen tussen bestrating en groen?\n"
                "1) 70% bestrating / 30% groen\n"
                "2) 50% bestrating / 50% groen\n"
                "3) 30% bestrating / 70% groen\n"
                "4) Zelf invullen\n"
                "\n"
                "Reageer met 1, 2, 3 of 4."
            ), allowed=("1", "2", "3", "4"),
            error_prompt="Kies 1, 2, 3 of 4. Hoe wilt u de verhouding bestrating/groen?"),

            # ✅ CUSTOM: gebruiker vult alleen bestrating in; groen wordt automatisch 100-bestrating
            Step("bestrating_pct", "pct", "Welk percentage van de tuin wordt bestrating? (0–100%)",
                 error_prompt="Geef een percentage tussen 0 en 100, bijvoorbeeld 50."),
            Step("confirm_bestrating_groen", "yesno", "Klopt dit? (ja/nee)",
                 error_prompt="Antwoord met ja of nee."),

            Step("verhouding_gazon_beplanting", "choice", (
                "Hoe wilt u het groen verdelen tussen gazon en beplanting?\n"
                "1) 70% gazon / 30% beplanting\n"
                "2) 50% gazon / 50% beplanting\n"
                "3) 30% gazon / 70% beplanting\n"
                "4) Zelf invullen\n"
                "\n"
                "Reageer met 1, 2, 3 of 4."
            ), allowed=("1", "2", "3", "4"),
            error_prompt="Kies 1, 2, 3 of 4. Hoe wilt u het groen verdelen tussen gazon en beplanting?"),

            # ✅ CUSTOM: gebruiker vult alleen gazon in; beplanting wordt automatisch 100-gazon
            Step("gazon_pct", "pct", "Welk percentage van het groen wordt gazon? (0–100%)",
                 error_prompt="Geef een percentage tussen 0 en 100, bijvoorbeeld 50."),
            Step("confirm_gazon_beplanting", "yesno", "Klopt dit? (ja/nee)",
                 error_prompt="Antwoord met ja of nee."),

            Step("verhouding_oprit_paden_terras", "choice", (
                "Hoe wilt u de bestrating verdelen tussen oprit, paden en terras?\n"
                "1) 50% oprit / 30% paden / 20% terras\n"
                "2) 40% oprit / 30% paden / 30% terras\n"
                "3) 30% oprit / 30% paden / 40% terras\n"
                "4) 20% oprit / 30% paden / 50% terras\n"
                "5) Zelf invullen\n"
                "Reageer met 1 t/m 5."
            ), allowed=("1", "2", "3", "4", "5"),
            error_prompt="Kies 1 t/m 5. Hoe wilt u de bestrating verdelen tussen oprit/paden/terras?"),

            # ✅ CUSTOM: gebruiker vult oprit + paden in; terras wordt automatisch 100-(oprit+paden)
            Step("oprit_pct", "pct", "Welk percentage van de bestrating wordt oprit? (0–100%)",
                 error_prompt="Geef een percentage tussen 0 en 100, bijvoorbeeld 40."),
            Step("paden_pct", "pct", "Welk percentage van de bestrating wordt paden? (0–100%)",
                 error_prompt="Geef een percentage tussen 0 en 100, bijvoorbeeld 20."),
            Step("confirm_oprit_paden_terras", "yesno", "Klopt dit? (ja/nee)",
                 error_prompt="Antwoord met ja of nee."),

            Step("materiaal_oprit", "choice", (
                "Welk materiaal wilt u voor de oprit?\n"
                "1) Grind € – natuurlijke uitstraling, waterdoorlatend geschikt voor auto's\n"
                "2) Beton klinker €€ – betaalbaar, praktisch en geschikt voor auto's\n"
                "3) Gebakken klinker €€€ – warm, klasiek en sfeervol, geschikt voor auto's\n"
                "4) Keramische tegels €€€€ – strak en onderhoudsarm (alleen geschikt met juiste onderbouw)\n"
                "\n"
                "Reageer met 1, 2, 3 of 4."
            ), allowed=("1", "2", "3", "4"),
            error_prompt="Kies 1, 2, 3 of 4. Welk materiaal wilt u voor de oprit?"),

            Step("materiaal_paden", "choice", (
                "Welk materiaal wilt u voor de paden?\n"
                "1) Grind € – natuurlijke uitstraling, waterdoorlatend\n"
                "2) Beton tegel/klinker €€ – betaalbaar, praktisch en strak\n"
                "3) Gebakken klinker €€€ – warm, klasiek en sfeervol\n"
                "4) Keramische tegels €€€€ – luxe uitstraling, zeer onderhoudsarm\n"
                "\n"
                "Reageer met 1, 2, 3 of 4."
            ), allowed=("1", "2", "3", "4"),
            error_prompt="Kies 1, 2, 3 of 4. Welk materiaal wilt u voor de paden?"),

            Step("materiaal_terras", "choice", (
                "Welk materiaal wilt u voor het terras?\n"
                "1) Grind € – natuurlijke uitstraling, waterdoorlatend\n"
                "2) Beton tegel/klinker €€ – betaalbaar, praktisch en strak\n"
                "3) Gebakken klinker €€€ – warm, klasiek en sfeervol\n"
                "4) Keramische tegels €€€€ – luxe uitstraling, zeer onderhoudsarm\n"
                "\n"
                "Reageer met 1, 2, 3 of 4."
            ), allowed=("1", "2", "3", "4"),
            error_prompt="Kies 1, 2, 3 of 4. Welk materiaal wilt u voor het terras?"),

            Step("onkruidwerend_gevoegd", "yesno", "Wilt u de bestrating gevoegd hebben tegen onkruid? (ja/nee)",
                 error_prompt="Antwoord met ja of nee. Wilt u de bestrating gevoegd hebben tegen onkruid?"),

            Step("overkapping", "yesno", f"Wilt u een overkapping in de tuin? {overkapping_txt} (ja/nee)".strip(),
                 error_prompt="Antwoord met ja of nee. Wilt u een overkapping in de tuin?"),

            Step("verlichting", "yesno", f"Wilt u een basispakket tuinverlichting? {verlichting_txt} (ja/nee)".strip(),
                 error_prompt="Antwoord met ja of nee. Wilt u een basispakket tuinverlichting?"),

            Step("overige_wensen", "menu", (
                "Heeft u nog overige wensen?\n"
                "1) Erfafscheiding\n"
                "2) Vlonder\n"
                "3) Beregening\n"
                "\n"
                "U kunt meerdere opties tegelijk kiezen, bijv. 1,3.\n"
                "Of typ 'nee' als u geen extra wensen hebt."
            ), error_prompt="Kies 1, 2, 3 (eventueel meerdere tegelijk, bijv. 1,3 of 13) of typ 'nee'."),

            Step("beregening_scope", "choice", (
                "Voor welk deel wilt u beregening?\n"
                "1) Alleen gazon\n"
                "2) Alleen beplanting\n"
                "3) Gazon én beplanting\n"
                "\n"
                "Reageer met 1, 2 of 3."
            ), allowed=("1", "2", "3"),
            error_prompt="Kies 1, 2 of 3. Voor welk deel wilt u beregening?"),

            Step("erfafscheiding_type", "menu", (
                "Welk type erfafscheiding wilt u toevoegen?\n"
                "1) Haag\n"
                "2) Betonschutting\n"
                "3) Design schutting\n"
                "\n"
                "U kunt meerdere opties tegelijk kiezen, bijv. 1,3.\n"
                "Reageer met 1, 2 of 3."
            ), error_prompt="Kies 1, 2 of 3 (eventueel meerdere tegelijk, bijv. 1,3 of 13)."),

            Step("erfafscheiding_meter", "number",
                 "Hoeveel meter is deze erfafscheiding ongeveer? (bijv. 10)",
                 error_prompt="Geef een getal, bijvoorbeeld 10."),

            Step("poortdeur", "yesno",
                 "Wilt u bij deze erfafscheiding ook een poortdeur opnemen? (ja/nee)",
                 error_prompt="Antwoord met ja of nee."),

            Step("vlonder_type", "choice", (
                "Welk type vlonder wilt u?\n"
                "1) Zachthout € ±10–15 jaar – voordeliger, kortere levensduur, natuurlijke look\n"
                "2) Hardhout €€ ±20–25 jaar – langere levensduur, kan mooi egaal vergrijzen\n"
                "3) Composiet €€€ ±25–30 jaar – minste onderhoud, splintert niet\n"
                "\n"
                "Reageer met 1, 2 of 3."
            ), allowed=("1", "2", "3"),
            error_prompt="Kies 1, 2 of 3. Welk type vlonder wilt u?"),
        )

    def _overkapping_price_text(self) -> str:
        key = "overkapping_basis_per_stuk"
        if key in self.prijzen and isinstance(self.prijzen[key], tuple) and len(self.prijzen[key]) == 2:
            lo, hi = self.prijzen[key]
            return f"Wilt u een basis overkapping (bijvoorbeeld 5×3 m)? Uiteraard zijn andere afmetingen ook mogelijk"
        return "Een basis overkapping 5×3 m is vaak mogelijk in verschillende prijsklassen (indicatief)."

    def _verlichting_price_text(self) -> str:
        key = "verlichting_basis_per_stuk"
        if key in self.prijzen and isinstance(self.prijzen[key], tuple) and len(self.prijzen[key]) == 2:
            lo, hi = self.prijzen[key]
            return f"Een basispakket is vaak {format_eur_range(int(lo), int(hi))} (indicatief; afhankelijk van spots, trafo, bekabeling en montage)."
        return "Een basispakket varieert op basis van aantal spots, trafo, bekabeling en montage (indicatief)."
