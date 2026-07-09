# flow_tuinaanleg.py
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, Optional, Tuple, List

from infrastructure.config.bedrijf import CONTACT_TELEFOON, CONTACT_EMAIL
from pricing import PRIJZEN
from core.flows.base import BaseFlow


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


_DONT_KNOW_PHRASES = frozenset({
    "weet ik niet", "weet niet", "geen idee", "?", "niet zeker",
    "onbekend", "weet het niet", "help", "geen idee", "??",
})


def _is_dont_know(text: str) -> bool:
    return (text or "").strip().lower() in _DONT_KNOW_PHRASES


@dataclass
class Step:
    key: str
    kind: str
    prompt: str
    allowed: Tuple[str, ...] = ()
    error_prompt: Optional[str] = None


# ============================================================
# FLOW V2: directe m²-vragen per onderdeel
# ============================================================

@dataclass
class TuinaanlegFlowV2(BaseFlow):
    """Verbeterde gehele-tuin flow: stelt directe m²-vragen per onderdeel."""
    step_index: int = 0
    answers: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.steps = self._build_steps()
        self._init_answers()

    def _init_answers(self) -> None:
        self.answers = {
            "style_tuin": None,
            "tuin_m2": None,
            "heeft_oprit": None,
            "oprit_m2": 0.0,
            "heeft_terras": None,
            "terras_m2": 0.0,
            "heeft_paden": None,
            "paden_m2": 0.0,
            "gazon_m2": 0.0,
            "materiaal_oprit": None,
            "materiaal_terras": None,
            "terras_extra_items": [],
            "materiaal_paden": None,
            "paden_extra_items": [],
            "onkruidwerend_gevoegd": None,
            "overkapping": False,
            "overkapping_m2": None,
            "verlichting": False,
            "stijl_voorkeur": None,
            "prioriteit": None,
            "fase": None,
            "overige_wensen": [],
            "beregening_scope": None,
            "beregening_systeem": None,
            "vlonder_type": None,
            "vlonder_extra_items": [],
            "erfafscheiding_items": [],
            "_pending_extras": [],
            "_erfafscheiding_types_selected": [],
            "_erfafscheiding_idx": 0,
            "_erfafscheiding_current_type": None,
            "_erfafscheiding_current_meter": None,
            "_prev_step_index": None,
            "_prev_answers": None,
            "_tip_shown": False,
        }

    def is_done(self) -> bool:
        return self.step_index >= len(self.steps)

    # -------------------------
    # m² helpers
    # -------------------------
    def _tuin_m2(self) -> float:
        return float(self.answers.get("tuin_m2") or 0)

    def _oprit_m2(self) -> float:
        return float(self.answers.get("oprit_m2") or 0)

    def _terras_m2(self) -> float:
        return float(self.answers.get("terras_m2") or 0)

    def _paden_m2(self) -> float:
        return float(self.answers.get("paden_m2") or 0)

    def _groen_m2(self) -> float:
        tr_extra = sum(float(it.get("m2") or 0) for it in (self.answers.get("terras_extra_items") or []))
        p_extra = sum(float(it.get("m2") or 0) for it in (self.answers.get("paden_extra_items") or []))
        return max(0.0, self._tuin_m2() - self._oprit_m2() - self._terras_m2() - tr_extra - self._paden_m2() - p_extra)

    # -------------------------
    # Conversion to pricing format
    # -------------------------
    def to_answers(self) -> Dict[str, Any]:
        """Convert V2 direct-m² answers to the format expected by estimate_tuinaanleg_costs."""
        t = self._tuin_m2()
        o = self._oprit_m2()
        p = self._paden_m2()
        tr = self._terras_m2()
        tr_extra_total = sum(float(it.get("m2") or 0) for it in (self.answers.get("terras_extra_items") or []))
        p_extra_total = sum(float(it.get("m2") or 0) for it in (self.answers.get("paden_extra_items") or []))
        g = float(self.answers.get("gazon_m2") or 0)
        groen = self._groen_m2()
        b = max(0.0, groen - g)

        p_total = p + p_extra_total
        tr_total = tr + tr_extra_total
        paving_m2 = min(o + p_total + tr_total, t)
        green_m2 = g + b

        if t > 0:
            bestrating_pct = max(0, min(100, int(round(paving_m2 / t * 100))))
        else:
            bestrating_pct = 50
        groen_pct = 100 - bestrating_pct

        if paving_m2 > 0:
            oprit_pct = max(0, min(100, int(round(o / paving_m2 * 100))))
            paden_pct = max(0, min(100, int(round(p_total / paving_m2 * 100))))
            terras_pct = max(0, 100 - oprit_pct - paden_pct)
        else:
            oprit_pct = paden_pct = terras_pct = 0

        if green_m2 > 0:
            gazon_pct = max(0, min(100, int(round(g / green_m2 * 100))))
        else:
            gazon_pct = 100
        beplanting_pct = 100 - gazon_pct

        out = dict(self.answers)
        out.update({
            "verhouding_bestrating_groen": "custom",
            "bestrating_pct": bestrating_pct,
            "groen_pct": groen_pct,
            "verhouding_gazon_beplanting": "custom",
            "gazon_pct": gazon_pct,
            "beplanting_pct": beplanting_pct,
            "oprit_pct": oprit_pct,
            "paden_pct": paden_pct,
            "terras_pct": terras_pct,
            "_flow_version": "v2",
            "_direct_oprit_m2": o,
            "_direct_terras_m2": tr,
            "_direct_paden_m2": p,
            "_direct_gazon_m2": g,
            "_direct_beplanting_m2": b,
            "stijl_voorkeur": self.answers.get("stijl_voorkeur"),
            "fase": self.answers.get("fase"),
        })
        return out

    def get_question(self) -> str:
        if self.is_done():
            return ""
        return self._build_question_text(self.steps[self.step_index])

    def _build_question_text(self, step: Step) -> str:
        if step.key == "oprit_m2":
            return (
                "Hoeveel m² is de oprit ongeveer?\n"
                "_(tip: voor 1 auto ca. 15–20 m², voor 2 auto's ca. 25–35 m²)_"
            )
        if step.key == "terras_m2":
            target = int(self.answers.get("terras_target_count") or 1)
            if target > 1:
                return f"**Terras 1 van {target}**\nHoeveel m² wordt terras 1?\n_(tip: een standaard terras is ca. 15–30 m²)_"
            return (
                "Hoeveel m² wordt het terras?\n"
                "_(tip: een standaard terras is ca. 15–30 m²)_"
            )
        if step.key == "terras_extra_m2":
            n = len(self.answers.get("terras_extra_items") or []) + 2
            target = int(self.answers.get("terras_target_count") or n)
            return f"**Terras {n} van {target}**\nHoeveel m² wordt terras {n}? _(bijv. 10)_"
        if step.key == "paden_m2":
            target = int(self.answers.get("paden_target_count") or 1)
            if target > 1:
                return (
                    f"**Pad 1 van {target}**\n"
                    "Hoeveel m² is pad 1?\n"
                    "_(tip: gemiddelde tuinpaden zijn ca. 10–20 m²)_"
                )
            return (
                "Hoeveel m² aan paden wilt u?\n"
                "_(tip: gemiddelde tuinpaden zijn ca. 10–20 m²)_"
            )
        if step.key == "paden_extra_m2":
            n = len(self.answers.get("paden_extra_items") or []) + 2
            target = int(self.answers.get("paden_target_count") or n)
            return f"**Pad {n} van {target}**\nHoeveel m² is pad {n}? _(bijv. 8)_"
        if step.key == "vlonder_extra_m2":
            n = len(self.answers.get("vlonder_extra_items") or []) + 2
            return f"Hoeveel m² wordt vlonder {n}? _(bijv. 10)_"
        if step.key == "vlonder_extra_type":
            n = len(self.answers.get("vlonder_extra_items") or []) + 2
            return (
                f"Welk type is vlonder {n}?\n"
                "1) Zachthout (voordelig)\n"
                "2) Hardhout (middenprijsklasse)\n"
                "3) Composiet (hoger segment)\n\n"
                "Reageer met 1, 2 of 3."
            )
        if step.key == "gazon_m2":
            groen = self._groen_m2()
            g = int(round(groen))
            return (
                f"Na uw bestrating blijft er {g} m² over. Hoe wilt u dit verdelen?\n\n"
                f"1) **Veel gazon** – ca. {int(round(groen * 0.70))} m² gazon / {int(round(groen * 0.30))} m² border\n"
                f"2) **Gelijk verdeeld** – ca. {int(round(groen * 0.50))} m² gazon / {int(round(groen * 0.50))} m² border\n"
                f"3) **Veel border** – ca. {int(round(groen * 0.30))} m² gazon / {int(round(groen * 0.70))} m² border\n"
                f"4) **Alleen gazon** – ca. {g} m²\n"
                f"5) **Alleen border** – ca. {g} m²\n"
                f"6) **Zelf invullen** – ik geef zelf de verdeling aan\n\n"
                f"Reageer met 1 t/m 6."
            )
        if step.key in ("materiaal_oprit", "materiaal_terras", "terras_extra_mat",
                        "materiaal_paden", "paden_extra_mat"):
            return self._materiaal_question(step.key)
        if step.key == "onkruidwerend_gevoegd":
            return self._voegen_question()
        if step.key == "extra_wensen":
            return self._extra_wensen_question()
        if step.key == "erfafscheiding_type":
            target = int(self.answers.get("erfafscheiding_target_count") or 1)
            done = len(self.answers.get("erfafscheiding_items") or [])
            prefix = f"**Erfafscheiding {done + 1} van {target}**\n" if target > 1 else ""
            return (
                f"{prefix}Welk type erfafscheiding wilt u?\n"
                "1) Haag\n"
                "2) Betonschutting\n"
                "3) Design schutting\n\n"
                "Reageer met 1, 2 of 3."
            )
        if step.key == "erfafscheiding_meter":
            t = self._erf_type_pretty(self.answers.get("_erfafscheiding_current_type"))
            return f"Hoeveel meter {t} is het ongeveer? (bijv. 10)"
        if step.key == "poortdeur":
            t = self._erf_type_pretty(self.answers.get("_erfafscheiding_current_type"))
            return f"Wilt u bij deze {t} ook een poortdeur opnemen?\n1) Ja\n2) Nee"
        return step.prompt

    def _materiaal_question(self, step_key: str) -> str:
        n_terras = len(self.answers.get("terras_extra_items") or []) + 2
        n_paden = len(self.answers.get("paden_extra_items") or []) + 2
        target_terras = int(self.answers.get("terras_target_count") or 1)
        target_paden = int(self.answers.get("paden_target_count") or 1)
        terras_lbl = "terras 1" if target_terras > 1 else "het terras"
        paden_lbl = "pad 1" if target_paden > 1 else "de paden"
        parts = {
            "materiaal_oprit": "de oprit",
            "materiaal_terras": terras_lbl,
            "terras_extra_mat": f"terras {n_terras}",
            "materiaal_paden": paden_lbl,
            "paden_extra_mat": f"pad {n_paden}",
        }
        part = parts.get(step_key, "de verharding")
        prefix_map = {
            "materiaal_terras": f"**Terras 1 van {target_terras}**\n" if target_terras > 1 else "",
            "terras_extra_mat": f"**Terras {n_terras} van {target_terras}**\n" if target_terras > 1 else "",
            "materiaal_paden":  f"**Pad 1 van {target_paden}**\n" if target_paden > 1 else "",
            "paden_extra_mat":  f"**Pad {n_paden} van {target_paden}**\n" if target_paden > 1 else "",
        }
        prefix = prefix_map.get(step_key, "")

        def fmt(key: str) -> str:
            lo, hi = PRIJZEN.get(key, (0, 0))
            return f"€{lo}–€{hi}/m²"

        return (
            f"{prefix}Welk materiaal wilt u voor {part}?\n"
            f"1) **Grind** – {fmt('grind_per_m2')}\n"
            f"2) **Beton klinkers** – {fmt('beton_straatwerk_per_m2')}\n"
            f"3) **Gebakken klinkers** – {fmt('gebakken_straatwerk_per_m2')}\n"
            f"4) **Keramische tegels** – {fmt('keramisch_straatwerk_per_m2')}\n\n"
            f"_Prijzen zijn inclusief materiaal, arbeid en btw._\n\n"
            f"Reageer met 1, 2, 3 of 4."
        )

    def _voegen_question(self) -> str:
        # Oprit is excluded from voegen in pricing — only paden + terras
        terras_voegbaar = (
            (self.answers.get("materiaal_terras") or "").strip().lower() in ("beton", "keramiek")
            or any((it.get("materiaal") or "").strip().lower() in ("beton", "keramiek")
                   for it in (self.answers.get("terras_extra_items") or []))
        )
        paden_voegbaar = (
            (self.answers.get("materiaal_paden") or "").strip().lower() in ("beton", "keramiek")
            or any((it.get("materiaal") or "").strip().lower() in ("beton", "keramiek")
                   for it in (self.answers.get("paden_extra_items") or []))
        )
        voegbaar = []
        if terras_voegbaar:
            voegbaar.append("terras")
        if paden_voegbaar:
            voegbaar.append("paden")
        onderdelen = " en ".join(voegbaar) if voegbaar else "de verharding"
        return (
            f"Wilt u de bestrating gevoegd hebben tegen onkruid?\n"
            f"_(Voegen is mogelijk bij **beton tegels** en **keramische tegels** op paden en terras. "
            f"Van toepassing op: {onderdelen})_\n"
            f"1) Ja\n2) Nee"
        )

    def _erf_type_pretty(self, t: Optional[str]) -> str:
        return {
            "haag": "haag",
            "betonschutting": "betonschutting",
            "design_schutting": "design schutting",
        }.get((t or "").strip().lower(), "erfafscheiding")

    def _confirm_prefix(self, title: str, items: List[str]) -> str:
        items = [str(x).strip() for x in items if str(x).strip()]
        if not items:
            return ""
        return f"Gekozen {title}: " + ", ".join(items) + ".\n\n"

    def _append_overige_once(self, tag: str) -> None:
        tag = str(tag).strip().lower()
        arr = self.answers.get("overige_wensen") or []
        arr_norm = [str(x).strip().lower() for x in arr]
        if tag and tag not in arr_norm:
            arr.append(tag)
        self.answers["overige_wensen"] = arr

    def _goto_step(self, key: str) -> None:
        for i, s in enumerate(self.steps):
            if s.key == key:
                self.step_index = i
                return

    # -------------------------
    # "Weet ik niet" hints
    # -------------------------
    def _dont_know_hint(self, step: Step) -> str:
        base = self._build_question_text(step)
        k = step.key
        if k == "style_tuin":
            hint = "Kies optie **2** (gemengd) als startpunt – een combi van verharding én groen."
        elif k == "stijl_voorkeur":
            hint = "Kies optie **4** (nog geen voorkeur) – we bespreken dit graag in het gesprek."
        elif k == "fase":
            hint = "Kies optie **1** (oriënterend) als startpunt – er zijn geen verplichtingen."
        elif k == "tuin_m2":
            hint = "Geef een schatting – ronde waarden zijn prima. Een gemiddelde achtertuin is ca. 50–100 m²."
        elif k in ("heeft_oprit", "terras_extra_vraag",
                   "paden_extra_vraag", "erfafscheiding_extra_vraag"):
            hint = "Twijfelt u? Kies **2** (nee) als startpunt – u kunt dit altijd bespreken met ons."
        elif k in ("heeft_terras", "heeft_paden", "heeft_erfafscheiding"):
            hint = "Twijfelt u? Kies **3** (nee) als startpunt – u kunt dit altijd bespreken met ons."
        elif k in ("terras_count", "paden_count", "erfafscheiding_count"):
            hint = "Geef een schatting, bijv. **2**."
        elif k == "oprit_m2":
            hint = "Geef een schatting. Één auto: ca. 15–20 m², twee auto's: ca. 25–35 m²."
        elif k == "terras_m2":
            hint = "Geef een schatting. Een standaard terras is ca. 15–30 m²."
        elif k == "terras_extra_m2":
            hint = "Geef een schatting in m², bijv. 10."
        elif k == "paden_extra_m2":
            hint = "Geef een schatting in m², bijv. 8."
        elif k == "paden_m2":
            hint = "Geef een schatting. Gemiddelde tuinpaden zijn ca. 10–20 m²."
        elif k == "gazon_m2":
            hint = "Kies optie **2** (Gelijk) als startpunt – fifty-fifty gazon en border."
        elif k in ("materiaal_oprit", "materiaal_terras", "terras_extra_mat",
                   "materiaal_paden", "paden_extra_mat"):
            hint = "Kies optie **2** (beton klinkers) – een gangbare standaardkeuze."
        elif k == "onkruidwerend_gevoegd":
            hint = "Twijfelt u? Kies **1** (ja) – voegen houdt uw bestrating langer onkruidvrij."
        elif k == "prioriteit":
            hint = "Kies optie **2** (balans) als startpunt – u kunt dit altijd bespreken met ons."
        elif k == "extra_wensen":
            hint = "Kies de nummers die van toepassing zijn (bijv. **1,3**) of kies **6** voor geen extra's."
        elif step.kind == "m2":
            hint = "Geef een schatting in m². Een ronde waarde is prima."
        else:
            hint = "Typ het nummer dat het beste past, of typ **nee** als startpunt."
        return f"_{hint}_\n\n{base}"

    # -------------------------
    # Pending extras queue
    # -------------------------
    def _start_pending_extras(self, selected: Tuple[str, ...]) -> Tuple[str, bool]:
        wanted = set(selected)
        chosen_labels: List[str] = []
        pending: List[str] = []

        if "1" in wanted:
            self.answers["overkapping"] = True
            chosen_labels.append("Overkapping")
            pending.append("overkapping_m2")

        if "2" in wanted:
            self.answers["verlichting"] = True
            chosen_labels.append("Tuinverlichting")

        if "3" in wanted:
            self._append_overige_once("erfafscheiding")
            chosen_labels.append("Erfafscheiding")
            pending.append("heeft_erfafscheiding")

        if "4" in wanted:
            self._append_overige_once("vlonder")
            chosen_labels.append("Vlonder")
            pending.append("vlonder_m2")
            pending.append("vlonder_type")

        if "5" in wanted:
            self._append_overige_once("beregening")
            chosen_labels.append("Beregening")
            pending.append("beregening_scope")
            pending.append("beregening_systeem")

        self.answers["_pending_extras"] = pending
        prefix = self._confirm_prefix("opties", chosen_labels)

        if pending:
            self._goto_step(pending[0])
            return prefix + self.get_question(), False

        return self._check_more_extra_wensen()

    def _advance_pending_extras(self) -> Tuple[str, bool]:
        pending: List[str] = list(self.answers.get("_pending_extras") or [])
        if not pending:
            return self._check_more_extra_wensen()
        pending = pending[1:]
        self.answers["_pending_extras"] = pending
        if not pending:
            return self._check_more_extra_wensen()
        self._goto_step(pending[0])
        return self.get_question(), False

    def _next_erfafscheiding_or_advance(self) -> Tuple[str, bool]:
        items = self.answers.get("erfafscheiding_items") or []
        target = int(self.answers.get("erfafscheiding_target_count") or 1)
        if len(items) < target:
            self._goto_step("erfafscheiding_type")
            return self.get_question(), False
        return self._advance_pending_extras()

    # -------------------------
    # Extra wensen loop-back helpers
    # -------------------------
    def _chosen_extra_keys(self) -> set:
        chosen: set = set()
        if self.answers.get("overkapping") is True:
            chosen.add("1")
        if self.answers.get("verlichting") is True:
            chosen.add("2")
        wensen = self.answers.get("overige_wensen") or []
        if "erfafscheiding" in wensen:
            chosen.add("3")
        if "vlonder" in wensen:
            chosen.add("4")
        if "beregening" in wensen:
            chosen.add("5")
        return chosen

    def _extra_wensen_question(self) -> str:
        chosen = self._chosen_extra_keys()
        all_opts = {
            "1": "Overkapping (indicatief €650–€1.000/m²)",
            "2": "Tuinverlichting (indicatief €1.000–€1.500)",
            "3": "Erfafscheiding",
            "4": "Vlonder",
            "5": "Beregening",
        }
        remaining = [k for k in ("1", "2", "3", "4", "5") if k not in chosen]
        lines = ["Heeft u nog extra wensen?"]
        for k in remaining:
            lines.append(f"{k}) {all_opts[k]}")
        lines.append("6) Geen extra wensen")
        if chosen:
            al = ", ".join(all_opts[k] for k in ("1", "2", "3", "4", "5") if k in chosen)
            lines.append(f"\n_(Al gekozen: {al})_")
        lines.append("\nKies één of meerdere nummers (bijv. 1, 3).")
        return "\n".join(lines)

    def _check_more_extra_wensen(self) -> Tuple[str, bool]:
        remaining = [k for k in ("1", "2", "3", "4", "5") if k not in self._chosen_extra_keys()]
        if not remaining:
            self.step_index = len(self.steps)
            return self.get_question(), True
        self._goto_step("extra_wensen")
        return self.get_question(), False

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
        seen: set = set()
        for d in digits:
            if d in allowed and d not in seen:
                out.append(d)
                seen.add(d)
        return tuple(out) if out else None

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

        if step.kind == "yesno":
            t = (user_text or "").strip()
            if t == "1":
                return True, True
            if t == "2":
                return True, False
            v = parse_yesno(t)
            return (v is not None), v

        if step.kind == "overkapping_m2":
            t = (user_text or "").strip()
            preset = {"1": 9.0, "2": 15.0, "3": 20.0}
            if t in preset:
                return True, preset[t]
            try:
                v = float(t.replace(",", "."))
                if 4.0 <= v <= 500.0:
                    return True, v
            except Exception:
                pass
            return False, None

        if step.kind == "choice":
            # "nee" → laatste optie, "ja" → eerste optie voor 3-opties vragen
            if step.key in ("heeft_terras", "heeft_paden", "heeft_erfafscheiding"):
                t = (user_text or "").strip().lower()
                if t in ("nee", "n", "no", "geen"):
                    return True, "3"
                if t in ("ja", "j", "yes", "y"):
                    return True, "1"
            v = parse_choice(user_text, step.allowed)
            if v is None:
                return False, None
            if step.key == "style_tuin":
                return True, {"1": "verharding", "2": "gemengd", "3": "groen"}[v]
            if step.key == "stijl_voorkeur":
                return True, {"1": "modern", "2": "natuurlijk", "3": "klassiek", "4": "geen_voorkeur"}[v]
            if step.key == "prioriteit":
                return True, {"1": "prijsbewust", "2": "balans", "3": "kwaliteit"}[v]
            if step.key == "fase":
                return True, {"1": "oriënterend", "2": "concrete_plannen"}[v]
            if step.key in ("materiaal_oprit", "materiaal_terras", "terras_extra_mat",
                            "materiaal_paden", "paden_extra_mat"):
                return True, {"1": "grind", "2": "beton", "3": "gebakken", "4": "keramiek"}[v]
            if step.key == "beregening_scope":
                return True, {"1": "gazon", "2": "beplanting", "3": "allebei"}[v]
            if step.key == "beregening_systeem":
                return True, {"1": "basis", "2": "volautomatisch", "3": "highend"}[v]
            if step.key in ("vlonder_type", "vlonder_extra_type"):
                return True, {"1": "zachthout", "2": "hardhout", "3": "composiet"}[v]
            if step.key == "haag_type":
                return True, {"1": "voordelig_laag", "2": "voordelig_hoog", "3": "premium_laag", "4": "premium_hoog"}[v]
            return True, v

        if step.key == "extra_wensen":
            parsed = self._parse_multi_digits(user_text, allowed=("1", "2", "3", "4", "5", "6"))
            if parsed is None:
                return False, None
            return True, parsed

        if step.key == "erfafscheiding_count":
            try:
                n = int(float((user_text or "").strip().replace(",", ".")))
                if n >= 1:
                    return True, float(n)
            except Exception:
                pass
            return False, None

        return True, user_text.strip()

    # -------------------------
    # Skip logic
    # -------------------------
    def _apply_skip(self) -> None:
        while not self.is_done():
            k = self.steps[self.step_index].key

            if k == "oprit_m2" and self.answers.get("heeft_oprit") is not True:
                self.answers["oprit_m2"] = 0.0
                self.step_index += 1
                continue
            if k == "materiaal_oprit" and float(self.answers.get("oprit_m2") or 0) <= 0.01:
                self.answers["materiaal_oprit"] = None
                self.step_index += 1
                continue
            if k == "terras_count" and (
                self.answers.get("heeft_terras") is not True
                or self.answers.get("terras_target_count") is not None
            ):
                self.step_index += 1
                continue
            if k == "terras_m2" and self.answers.get("heeft_terras") is not True:
                self.answers["terras_m2"] = 0.0
                self.step_index += 1
                continue
            if k == "materiaal_terras" and float(self.answers.get("terras_m2") or 0) <= 0.01:
                self.answers["materiaal_terras"] = None
                self.step_index += 1
                continue
            if k in ("terras_extra_m2", "terras_extra_mat") \
                    and float(self.answers.get("terras_m2") or 0) <= 0.01:
                self.step_index += 1
                continue
            if k == "terras_extra_vraag":
                if float(self.answers.get("terras_m2") or 0) <= 0.01:
                    self.step_index += 1
                    continue
                target_count = self.answers.get("terras_target_count")
                if target_count is not None:
                    extra_items = self.answers.get("terras_extra_items") or []
                    if len(extra_items) < int(target_count) - 1:
                        self.step_index += 1  # auto-advance to terras_extra_m2
                        break
                    else:
                        self._goto_step("heeft_paden")
                        continue
                break
            if k == "paden_count" and (
                self.answers.get("heeft_paden") is not True
                or self.answers.get("paden_target_count") is not None
            ):
                self.step_index += 1
                continue
            if k == "paden_m2" and self.answers.get("heeft_paden") is not True:
                self.answers["paden_m2"] = 0.0
                self.step_index += 1
                continue
            if k == "materiaal_paden" and float(self.answers.get("paden_m2") or 0) <= 0.01:
                self.answers["materiaal_paden"] = None
                self.step_index += 1
                continue
            if k in ("paden_extra_m2", "paden_extra_mat") \
                    and float(self.answers.get("paden_m2") or 0) <= 0.01:
                self.step_index += 1
                continue
            if k == "paden_extra_vraag":
                if float(self.answers.get("paden_m2") or 0) <= 0.01:
                    self.step_index += 1
                    continue
                target_count = self.answers.get("paden_target_count")
                if target_count is not None:
                    extra_items = self.answers.get("paden_extra_items") or []
                    if len(extra_items) < int(target_count) - 1:
                        self.step_index += 1  # auto-advance to paden_extra_m2
                        break
                    else:
                        self._goto_step("onkruidwerend_gevoegd")
                        continue
                break
            if k == "gazon_m2" and self._groen_m2() <= 0.01:
                self.answers["gazon_m2"] = 0.0
                self.step_index += 1
                continue
            if k == "onkruidwerend_gevoegd":
                # Voegen is only applied to paden + terras in pricing (oprit excluded)
                voegbaar_aanwezig = (
                    (self.answers.get("materiaal_paden") or "").strip().lower() in ("beton", "keramiek")
                    or (self.answers.get("materiaal_terras") or "").strip().lower() in ("beton", "keramiek")
                    or any((it.get("materiaal") or "").strip().lower() in ("beton", "keramiek")
                           for it in (self.answers.get("paden_extra_items") or []))
                    or any((it.get("materiaal") or "").strip().lower() in ("beton", "keramiek")
                           for it in (self.answers.get("terras_extra_items") or []))
                )
                if not voegbaar_aanwezig:
                    self.answers["onkruidwerend_gevoegd"] = False
                    self.step_index += 1
                    continue
            if k in ("heeft_erfafscheiding", "erfafscheiding_count", "erfafscheiding_extra_vraag") \
                    and "erfafscheiding" not in [w for w in (self.answers.get("overige_wensen") or [])]:
                self.step_index += 1
                continue
            if k == "erfafscheiding_count" and (
                self.answers.get("erfafscheiding_target_count") is not None
            ):
                self.step_index += 1
                continue
            if k == "erfafscheiding_extra_vraag" \
                    and self.answers.get("erfafscheiding_target_count") is not None:
                self.step_index += 1
                continue
            if k in ("vlonder_extra_vraag", "vlonder_extra_m2", "vlonder_extra_type") \
                    and "vlonder" not in [w for w in (self.answers.get("overige_wensen") or [])]:
                self.step_index += 1
                continue
            if k == "overkapping_m2" and self.answers.get("overkapping") is not True:
                self.answers["overkapping_m2"] = None
                self.step_index += 1
                continue

            break

    # -------------------------
    # Main handler
    # -------------------------
    def handle(self, user_text: str) -> Tuple[str, bool]:
        import copy as _copy

        if self.is_done():
            return self.get_question(), True

        # "Terug" escape — herstel vorige stap
        if (user_text or "").strip().lower() in ("terug", "back", "vorige"):
            if self.answers.get("_prev_step_index") is None:
                return "Dit is al de eerste vraag – er is niets om naar terug te gaan.", False
            self.step_index = self.answers["_prev_step_index"]
            self.answers = self.answers["_prev_answers"]
            return self.get_question(), False

        prev_idx = self.step_index
        prev_ans = _copy.deepcopy(self.answers)
        tip_was_shown = self.answers.get("_tip_shown", False)

        question, done = self._process_answer(user_text)

        if self.step_index != prev_idx or done:
            self.answers["_prev_step_index"] = prev_idx
            self.answers["_prev_answers"] = prev_ans
            if not tip_was_shown and not done:
                self.answers["_tip_shown"] = True
                question = question + "\n\n_Tip: typ **'terug'** als u een vorige vraag wilt aanpassen._"

        return question, done

    def _process_answer(self, user_text: str) -> Tuple[str, bool]:
        _MAX_EXTRA = 3

        if self.is_done():
            return self.get_question(), True

        step = self.steps[self.step_index]

        # "Weet ik niet" escape
        if _is_dont_know(user_text) and step.key not in ("extra_wensen",):
            return self._dont_know_hint(step), False

        # gazon_m2: preset keuze of vrije invoer (met bevestiging bij vrije invoer)
        if step.key == "gazon_m2":
            groen = self._groen_m2()
            _preset = {"1": 0.70, "2": 0.50, "3": 0.30, "4": 1.0, "5": 0.0}
            t = (user_text or "").strip()

            # Bevestiging afhandelen na vrije invoer
            if self.answers.get("_gazon_confirm_pending") is not None:
                pending_v = self.answers["_gazon_confirm_pending"]
                yn = parse_yesno(user_text)
                if yn is None:
                    border = int(round(groen - pending_v))
                    return (
                        f"Antwoord met ja of nee. "
                        f"Klopt het dat u **{int(round(pending_v))} m² gazon** en **{border} m² border** wilt?",
                        False,
                    )
                self.answers.pop("_gazon_confirm_pending", None)
                if not yn:
                    return self.get_question(), False  # terug naar de keuze
                v = pending_v
                self.answers["gazon_m2"] = v
                self.step_index += 1
                self._apply_skip()
                return self.get_question(), self.is_done()

            if t == "6":
                return (
                    f"Hoeveel m² gazon wilt u? "
                    f"(van de {int(round(groen))} m² beschikbaar – het resterende deel wordt border)",
                    False,
                )

            if t in _preset:
                v = round(groen * _preset[t], 1)
                self.answers["gazon_m2"] = v
                self.step_index += 1
                self._apply_skip()
                return self.get_question(), self.is_done()

            v = parse_m2(user_text)
            if v is None:
                return self.get_question(), False
            if v > groen + 0.5:
                return (
                    f"Dat is meer dan het beschikbare groene deel (ca. {int(round(groen))} m²). "
                    f"Typ een getal van 0 t/m {int(round(groen))} of kies een optie (1–6).",
                    False,
                )
            # Vraag bevestiging bij vrije invoer
            self.answers["_gazon_confirm_pending"] = v
            border = int(round(groen - v))
            return (
                f"Klopt het dat u **{int(round(v))} m² gazon** en **{border} m² border** wilt? (ja/nee)",
                False,
            )

        ok, value = self._validate(step, user_text)
        if not ok:
            err = step.error_prompt or step.prompt
            if self.answers.get("_tip_shown"):
                err += "\n\n_(Typ **'terug'** om de vorige vraag aan te passen.)_"
            return err, False

        # tuin_m2 > 2000 check
        if step.key == "tuin_m2" and isinstance(value, (int, float)) and value > 2000:
            return (
                f"Voor projecten groter dan 2.000 m² nemen we graag persoonlijk contact op voor een offerte op maat.\n\n"
                f"📞 {CONTACT_TELEFOON}  |  ✉️ {CONTACT_EMAIL}\n\n"
                "Heeft u een kleinere tuin? Geef dan de afmeting opnieuw in.",
                False,
            )

        # m² upper-bound: deeloppervlakken mogen tuin_m2 niet overschrijden
        _HARDSCAPE_KEYS = {"oprit_m2", "terras_m2", "terras_extra_m2", "paden_m2", "paden_extra_m2"}
        if step.key in _HARDSCAPE_KEYS and isinstance(value, (int, float)):
            tuin = self._tuin_m2()
            if tuin > 0:
                already = (
                    self._oprit_m2()
                    + self._terras_m2()
                    + sum(float(it.get("m2") or 0) for it in (self.answers.get("terras_extra_items") or []))
                    + self._paden_m2()
                    + sum(float(it.get("m2") or 0) for it in (self.answers.get("paden_extra_items") or []))
                )
                remaining = tuin - already
                if value > remaining + 0.5:
                    return (
                        f"Dat is meer dan beschikbaar. Uw tuin is {int(round(tuin))} m² en er is nog "
                        f"ca. **{int(round(max(0.0, remaining)))} m²** beschikbaar voor verharding. "
                        f"Geef een getal van 0 t/m {int(round(max(0.0, remaining)))} m².",
                        False,
                    )

        # extra_wensen: "6" of "nee" = geen extra's
        if step.key == "extra_wensen":
            if value == ("nee",) or "6" in value:
                self.step_index = len(self.steps)
                return self.get_question(), True
            chosen = self._chosen_extra_keys()
            valid = tuple(v for v in value if v in ("1", "2", "3", "4", "5") and v not in chosen)
            if not valid:
                return self._extra_wensen_question(), False
            return self._start_pending_extras(valid)

        # Pending extras sub-handlers
        if step.key == "overkapping_m2":
            self.answers["overkapping_m2"] = value
            return self._advance_pending_extras()

        if step.key == "beregening_scope":
            self.answers["beregening_scope"] = value
            return self._advance_pending_extras()

        if step.key == "beregening_systeem":
            self.answers["beregening_systeem"] = value
            return self._advance_pending_extras()

        if step.key == "vlonder_m2":
            self.answers["vlonder_m2"] = value
            return self._advance_pending_extras()

        if step.key == "vlonder_type":
            self.answers["vlonder_type"] = value
            self._goto_step("vlonder_extra_vraag")
            return self.get_question(), self.is_done()

        if step.key == "vlonder_extra_vraag":
            if value is False:
                return self._advance_pending_extras()
            else:
                self.step_index += 1  # → vlonder_extra_m2
            return self.get_question(), self.is_done()

        if step.key == "vlonder_extra_m2":
            self.answers["_vlonder_extra_pending_m2"] = value
            self.step_index += 1  # → vlonder_extra_type
            return self.get_question(), False

        if step.key == "vlonder_extra_type":
            items = list(self.answers.get("vlonder_extra_items") or [])
            items.append({
                "m2": float(self.answers.get("_vlonder_extra_pending_m2") or 0),
                "type": value,
            })
            self.answers["vlonder_extra_items"] = items
            if len(items) < _MAX_EXTRA:
                self._goto_step("vlonder_extra_vraag")
            else:
                return self._advance_pending_extras()
            return self.get_question(), self.is_done()

        if step.key == "heeft_erfafscheiding":
            if value == "3":
                overige = self.answers.get("overige_wensen") or []
                self.answers["overige_wensen"] = [w for w in overige if w != "erfafscheiding"]
                return self._advance_pending_extras()
            if value == "1":
                self.answers["erfafscheiding_target_count"] = 1
                self._goto_step("erfafscheiding_type")
            else:  # value == "2"
                self._goto_step("erfafscheiding_count")
            return self.get_question(), False

        if step.key == "erfafscheiding_count":
            count = max(1, int(value))
            self.answers["erfafscheiding_target_count"] = count
            self._goto_step("erfafscheiding_type")
            return self.get_question(), False

        if step.key == "erfafscheiding_extra_vraag":
            if value is False:
                return self._advance_pending_extras()
            else:
                self._goto_step("erfafscheiding_type")
                return self.get_question(), False

        if step.key == "erfafscheiding_type":
            mapping = {"1": "haag", "2": "betonschutting", "3": "design_schutting"}
            t = mapping.get(str(value).strip())
            if not t:
                return (step.error_prompt or step.prompt), False
            self.answers["_erfafscheiding_current_type"] = t
            self.answers["_erfafscheiding_current_meter"] = None
            self._goto_step("erfafscheiding_meter")
            return self.get_question(), False

        if step.key == "erfafscheiding_meter":
            cur_type = (self.answers.get("_erfafscheiding_current_type") or "").strip().lower()
            self.answers["_erfafscheiding_current_meter"] = value
            if cur_type in ("betonschutting", "design_schutting"):
                self._goto_step("poortdeur")
                return self.get_question(), False
            if cur_type == "haag":
                self._goto_step("haag_type")
                return self.get_question(), False
            self.answers["erfafscheiding_items"].append({"type": cur_type, "meter": value, "poortdeur": None})
            return self._next_erfafscheiding_or_advance()

        if step.key == "haag_type":
            cur_type = (self.answers.get("_erfafscheiding_current_type") or "").strip().lower()
            meter = self.answers.get("_erfafscheiding_current_meter")
            self.answers["erfafscheiding_items"].append({
                "type": cur_type, "meter": meter, "poortdeur": None, "haag_type": value,
            })
            return self._next_erfafscheiding_or_advance()

        if step.key == "poortdeur":
            cur_type = (self.answers.get("_erfafscheiding_current_type") or "").strip().lower()
            meter = self.answers.get("_erfafscheiding_current_meter")
            self.answers["erfafscheiding_items"].append({"type": cur_type, "meter": meter, "poortdeur": value})
            return self._next_erfafscheiding_or_advance()

        # Terras/paden count-based loop

        if step.key == "heeft_terras":
            if value == "3":
                self.answers["heeft_terras"] = False
                self.answers["terras_m2"] = 0.0
            else:
                tuin = self._tuin_m2()
                already = self._oprit_m2()
                remaining = tuin - already if tuin > 0 else 0.0
                if remaining <= 0.5:
                    self.answers["heeft_terras"] = False
                    self.answers["terras_m2"] = 0.0
                    self.step_index += 1
                    self._apply_skip()
                    return (
                        "Uw oprit beslaat al de volledige tuinoppervlakte. "
                        "Er is geen ruimte meer voor een terras — we slaan dit over.\n\n"
                        + self.get_question()
                    ), self.is_done()
                self.answers["heeft_terras"] = True
                if value == "1":
                    self.answers["terras_target_count"] = 1
            self.step_index += 1
            self._apply_skip()
            return self.get_question(), self.is_done()

        if step.key == "terras_count":
            count = max(1, int(value))
            self.answers["terras_target_count"] = count
            self.step_index += 1
            self._apply_skip()
            return self.get_question(), self.is_done()

        if step.key == "terras_extra_vraag":
            if value is False:
                self._goto_step("heeft_paden")
                self._apply_skip()
            else:
                self.step_index += 1  # → terras_extra_m2
            return self.get_question(), self.is_done()

        if step.key == "terras_extra_m2":
            self.answers["_terras_extra_pending_m2"] = value
            self.step_index += 1  # → terras_extra_mat
            return self.get_question(), False

        if step.key == "terras_extra_mat":
            items = list(self.answers.get("terras_extra_items") or [])
            items.append({
                "m2": float(self.answers.get("_terras_extra_pending_m2") or 0),
                "materiaal": value,
            })
            self.answers["terras_extra_items"] = items
            target_count = self.answers.get("terras_target_count")
            if target_count is not None:
                if len(items) < int(target_count) - 1:
                    self._goto_step("terras_extra_m2")
                else:
                    self._goto_step("heeft_paden")
                    self._apply_skip()
            elif len(items) < _MAX_EXTRA:
                self._goto_step("terras_extra_vraag")
            else:
                self._goto_step("heeft_paden")
                self._apply_skip()
            return self.get_question(), self.is_done()

        if step.key == "heeft_paden":
            if value == "3":
                self.answers["heeft_paden"] = False
                self.answers["paden_m2"] = 0.0
            else:
                tuin = self._tuin_m2()
                already = (
                    self._oprit_m2() + self._terras_m2()
                    + sum(float(it.get("m2") or 0) for it in (self.answers.get("terras_extra_items") or []))
                )
                remaining = tuin - already if tuin > 0 else 0.0
                if remaining <= 0.5:
                    self.answers["heeft_paden"] = False
                    self.answers["paden_m2"] = 0.0
                    self.step_index += 1
                    self._apply_skip()
                    return (
                        "Uw verharding beslaat al de volledige tuinoppervlakte. "
                        "Er is geen ruimte meer voor paden — we slaan dit over.\n\n"
                        + self.get_question()
                    ), self.is_done()
                self.answers["heeft_paden"] = True
                if value == "1":
                    self.answers["paden_target_count"] = 1
            self.step_index += 1
            self._apply_skip()
            return self.get_question(), self.is_done()

        if step.key == "paden_count":
            count = max(1, int(value))
            self.answers["paden_target_count"] = count
            self.step_index += 1
            self._apply_skip()
            return self.get_question(), self.is_done()

        if step.key == "paden_extra_vraag":
            if value is False:
                self._goto_step("onkruidwerend_gevoegd")
                self._apply_skip()
            else:
                self.step_index += 1  # → paden_extra_m2
            return self.get_question(), self.is_done()

        if step.key == "paden_extra_m2":
            self.answers["_paden_extra_pending_m2"] = value
            self.step_index += 1  # → paden_extra_mat
            return self.get_question(), False

        if step.key == "paden_extra_mat":
            items = list(self.answers.get("paden_extra_items") or [])
            items.append({
                "m2": float(self.answers.get("_paden_extra_pending_m2") or 0),
                "materiaal": value,
            })
            self.answers["paden_extra_items"] = items
            target_count = self.answers.get("paden_target_count")
            if target_count is not None:
                if len(items) < int(target_count) - 1:
                    self._goto_step("paden_extra_m2")
                else:
                    self._goto_step("onkruidwerend_gevoegd")
                    self._apply_skip()
            elif len(items) < _MAX_EXTRA:
                self._goto_step("paden_extra_vraag")
            else:
                self._goto_step("onkruidwerend_gevoegd")
                self._apply_skip()
            return self.get_question(), self.is_done()

        # Generic store + advance
        self.answers[step.key] = value
        self.step_index += 1
        self._apply_skip()
        return self.get_question(), self.is_done()

    # -------------------------
    # Steps
    # -------------------------
    def _build_steps(self) -> Tuple[Step, ...]:
        return (
            Step(
                "tuin_m2", "m2",
                "Hoe groot is uw tuin in m²? _(bijv. 80 of 120)_",
                error_prompt="Geef een getal, bijv. 80. Hoe groot is uw tuin in m²?",
            ),
            Step(
                "heeft_oprit", "yesno",
                "We berekenen verharding in drie stappen: oprit, terras en losse paden. Elk onderdeel kunt u overslaan.\n_Alle getoonde prijzen zijn inclusief materiaal en arbeid._\n\nHeeft u een oprit nodig (parkeerplaats voor auto's)?\n1) Ja\n2) Nee",
                error_prompt="Antwoord met 1 (ja) of 2 (nee).",
            ),
            Step(
                "oprit_m2", "m2",
                "",  # dynamic
                error_prompt="Geef een getal in m², bijv. 20.",
            ),
            Step(
                "materiaal_oprit", "choice", "",  # dynamic
                allowed=("1", "2", "3", "4"),
                error_prompt="Reageer met 1, 2, 3 of 4.",
            ),
            Step(
                "heeft_terras", "choice",
                "Wilt u een terras aanleggen?\n1) Ja, 1 terras\n2) Ja, meerdere terrassen\n3) Nee",
                allowed=("1", "2", "3"),
                error_prompt="Reageer met 1, 2 of 3.",
            ),
            Step(
                "terras_count", "m2",
                "Hoeveel terrassen wilt u aanleggen? (bijv. 2)",
                error_prompt="Geef een getal, bijv. 2.",
            ),
            Step(
                "terras_m2", "m2",
                "",  # dynamic
                error_prompt="Geef een getal in m², bijv. 20.",
            ),
            Step(
                "materiaal_terras", "choice", "",  # dynamic
                allowed=("1", "2", "3", "4"),
                error_prompt="Reageer met 1, 2, 3 of 4.",
            ),
            Step(
                "terras_extra_vraag", "yesno",
                "Wilt u nog een extra terras toevoegen?\n1) Ja\n2) Nee",
                error_prompt="Antwoord met 1 (ja) of 2 (nee).",
            ),
            Step(
                "terras_extra_m2", "m2",
                "",  # dynamic
                error_prompt="Geef een getal in m², bijv. 10.",
            ),
            Step(
                "terras_extra_mat", "choice", "",  # dynamic
                allowed=("1", "2", "3", "4"),
                error_prompt="Reageer met 1, 2, 3 of 4.",
            ),
            Step(
                "heeft_paden", "choice",
                "Wilt u verharde paden aanleggen?\n1) Ja, 1 pad\n2) Ja, meerdere paden\n3) Nee",
                allowed=("1", "2", "3"),
                error_prompt="Reageer met 1, 2 of 3.",
            ),
            Step(
                "paden_count", "m2",
                "Hoeveel paden wilt u aanleggen? (bijv. 2)",
                error_prompt="Geef een getal, bijv. 2.",
            ),
            Step(
                "paden_m2", "m2",
                "",  # dynamic
                error_prompt="Geef een getal in m², bijv. 15.",
            ),
            Step(
                "materiaal_paden", "choice", "",  # dynamic
                allowed=("1", "2", "3", "4"),
                error_prompt="Reageer met 1, 2, 3 of 4.",
            ),
            Step(
                "paden_extra_vraag", "yesno",
                "Wilt u nog een extra pad toevoegen?\n1) Ja\n2) Nee",
                error_prompt="Antwoord met 1 (ja) of 2 (nee).",
            ),
            Step(
                "paden_extra_m2", "m2",
                "",  # dynamic
                error_prompt="Geef een getal in m², bijv. 8.",
            ),
            Step(
                "paden_extra_mat", "choice", "",  # dynamic
                allowed=("1", "2", "3", "4"),
                error_prompt="Reageer met 1, 2, 3 of 4.",
            ),
            Step(
                "onkruidwerend_gevoegd", "yesno",
                "",  # dynamic (_voegen_question)
                error_prompt="Reageer met 1 (ja) of 2 (nee).",
            ),
            Step(
                "gazon_m2", "m2",
                "",  # dynamic
                error_prompt="Geef een getal in m², bijv. 30.",
            ),
            Step(
                "extra_wensen", "menu",
                "Heeft u nog extra wensen?\n"
                "1) Overkapping (indicatief €650–€1.000/m²)\n"
                "2) Tuinverlichting (indicatief €1.000–€1.500)\n"
                "3) Erfafscheiding\n"
                "4) Vlonder\n"
                "5) Beregening\n"
                "6) Geen extra wensen\n\n"
                "Kies één of meerdere nummers (bijv. 1, 3).",
                error_prompt="Reageer met 1 t/m 6 (of meerdere tegelijk, bijv. 1, 3).",
            ),
            Step(
                "overkapping_m2", "overkapping_m2",
                "Welke afmeting wilt u voor de overkapping?\n"
                "1) Knus – ca. 3×3 m (9 m²)\n"
                "2) Standaard – ca. 5×3 m (15 m²)\n"
                "3) Ruim – ca. 5×4 m (20 m²)\n"
                "Of typ een oppervlakte in m² (bijv. 12)",
                error_prompt="Reageer met 1, 2 of 3, of typ een oppervlakte in m² (bijv. 12).",
            ),
            Step(
                "beregening_scope", "choice",
                "Voor welk deel wilt u beregening?\n"
                "1) Alleen gazon\n"
                "2) Alleen beplanting\n"
                "3) Gazon én beplanting\n\n"
                "Reageer met 1, 2 of 3.",
                allowed=("1", "2", "3"),
                error_prompt="Reageer met 1, 2 of 3.",
            ),
            Step(
                "beregening_systeem", "choice",
                "Welk type beregeningssysteem heeft u in gedachten?\n"
                "1) Basis – deels handmatig instellen\n"
                "2) Volautomatisch – loopt op een tijdschema\n"
                "3) Smart – via app te bedienen (wifi/weer-gestuurd)\n\n"
                "Reageer met 1, 2 of 3.",
                allowed=("1", "2", "3"),
                error_prompt="Reageer met 1, 2 of 3.",
            ),
            Step(
                "heeft_erfafscheiding", "choice",
                "Wilt u een erfafscheiding aanleggen?\n"
                "1) Ja, 1 erfafscheiding\n"
                "2) Ja, meerdere erfafscheidingen\n"
                "3) Nee\n\n"
                "Reageer met 1, 2 of 3.",
                allowed=("1", "2", "3"),
                error_prompt="Reageer met 1, 2 of 3.",
            ),
            Step(
                "erfafscheiding_count", "m2",
                "Hoeveel erfafscheidingen wilt u aanleggen? (bijv. 2)",
                error_prompt="Geef een getal, bijv. 2.",
            ),
            Step(
                "erfafscheiding_type", "choice",
                "",  # dynamic (_build_question_text)
                allowed=("1", "2", "3"),
                error_prompt="Reageer met 1, 2 of 3.",
            ),
            Step(
                "erfafscheiding_meter", "number",
                "Hoeveel meter is deze erfafscheiding ongeveer? (bijv. 10)",
                error_prompt="Geef een getal, bijv. 10.",
            ),
            Step(
                "haag_type", "choice",
                "Welk type haag wilt u?\n"
                "1) Voordelig & laag  – ca. 0,5–1m   (bijv. beuk, haagliguster)\n"
                "2) Voordelig & hoog  – ca. 1,5–2m   (bijv. beuk, haagliguster)\n"
                "3) Premium & laag    – ca. 0,5–1m   (Portugese laurier wintergroen)\n"
                "4) Premium & hoog    – ca. 1,5–2m   (Portugese laurier wintergroen)\n\n"
                "Reageer met 1, 2, 3 of 4.",
                allowed=("1", "2", "3", "4"),
                error_prompt="Reageer met 1, 2, 3 of 4.",
            ),
            Step(
                "poortdeur", "yesno",
                "",  # dynamic (_build_question_text)
                error_prompt="Reageer met 1 (ja) of 2 (nee).",
            ),
            Step(
                "erfafscheiding_extra_vraag", "yesno",
                "Wilt u nog een stuk erfafscheiding toevoegen (ander type of andere afmetingen)?\n1) Ja\n2) Nee",
                error_prompt="Antwoord met 1 (ja) of 2 (nee).",
            ),
            Step(
                "vlonder_m2", "m2",
                "Hoeveel m² wordt de vlonder? (bijv. 12)",
                error_prompt="Geef een getal in m², bijv. 12.",
            ),
            Step(
                "vlonder_type", "choice",
                "Welk type vlonder wilt u?\n"
                "1) Zachthout (voordelig) ±10–15 jaar – voordeliger, kortere levensduur\n"
                "2) Hardhout (middenprijsklasse) ±20–25 jaar – langere levensduur\n"
                "3) Composiet (hoger segment) ±25–30 jaar – minste onderhoud\n\n"
                "Reageer met 1, 2 of 3.",
                allowed=("1", "2", "3"),
                error_prompt="Reageer met 1, 2 of 3.",
            ),
            Step(
                "vlonder_extra_vraag", "yesno",
                "Wilt u nog een vlonder toevoegen?\n1) Ja\n2) Nee",
                error_prompt="Antwoord met 1 (ja) of 2 (nee).",
            ),
            Step(
                "vlonder_extra_m2", "m2",
                "",  # dynamic
                error_prompt="Geef een getal in m², bijv. 10.",
            ),
            Step(
                "vlonder_extra_type", "choice",
                "",  # dynamic
                allowed=("1", "2", "3"),
                error_prompt="Reageer met 1, 2 of 3.",
            ),
        )
