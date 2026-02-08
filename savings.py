# savings.py
from __future__ import annotations

import re
from typing import Dict, Tuple, List, Optional, Set, Any

from pricing import estimate_tuinaanleg_costs


# =====================
# Basics
# =====================
MAX_RECALC_DEFAULT = 5


def _eur(v: int) -> str:
    return f"€{int(v):,}".replace(",", ".")


def _total_range(costs: dict) -> Optional[Tuple[int, int]]:
    tr = costs.get("total_range_eur")
    if not tr or len(tr) != 2:
        return None
    return int(tr[0]), int(tr[1])


def _overige_clean(ans: dict | None) -> List[str]:
    if not ans:
        return []
    overige = ans.get("overige_wensen") or []
    if not isinstance(overige, list):
        overige = [str(overige)]
    return [str(x).strip().lower() for x in overige if str(x).strip()]


def has_vlonder(ans: dict | None) -> bool:
    return "vlonder" in _overige_clean(ans)


def has_erfafscheiding(ans: dict | None) -> bool:
    if not ans:
        return False
    if "erfafscheiding" in _overige_clean(ans):
        return True
    items = ans.get("erfafscheiding_items") or []
    return bool(items)


def is_back(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"nee", "n", "no", "terug", "back"}


def parse_multi_digits(user_text: str, *, allowed: Tuple[str, ...]) -> Optional[Tuple[str, ...]]:
    """
    Dummy-proof multi-select:
    - accepteert: "1,3" "1 3" "13" "31" "1/3" "1-3" etc.
    - verwijdert duplicates, behoudt volgorde
    """
    t = (user_text or "").strip().lower()
    if not t:
        return None
    if is_back(t):
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

    return tuple(out) if out else None


def parse_single_digit(user_text: str, *, allowed: Tuple[str, ...]) -> Optional[str]:
    t = (user_text or "").strip().lower()
    if not t:
        return None
    if is_back(t):
        return "nee"
    return t if t in allowed else None


# ✅ NEW: multi-select voor materiaal-onderdelen (1/2/3)
def parse_material_parts(user_text: str) -> Optional[Tuple[str, ...]]:
    """
    Multi-select voor materiaalonderdelen:
    1=oprit, 2=paden, 3=terras
    Accepteert: "1,3" "13" "1 3" "1-3" etc.
    'nee/terug' => ("nee",)
    """
    parsed = parse_multi_digits(user_text, allowed=("1", "2", "3"))
    if parsed is None:
        return None
    if parsed == ("nee",):
        return ("nee",)
    return parsed


# ============================================================
# ✅ Besparing: delta op breakdown keys (geen total-delta bug)
# ============================================================
def _sum_breakdown_range_allow_zero(costs: dict | None, *, keys: Tuple[str, ...]) -> Tuple[int, int]:
    """
    Sommeer range_eur uit costs['breakdown'] voor opgegeven keys.
    Missende keys tellen als 0.
    """
    if not costs or not isinstance(costs, dict):
        return (0, 0)

    breakdown = costs.get("breakdown") or []
    if not isinstance(breakdown, list):
        return (0, 0)

    mn = 0
    mx = 0

    for it in breakdown:
        if it.get("key") not in keys:
            continue
        r = it.get("range_eur")
        if not r or not isinstance(r, (list, tuple)) or len(r) != 2:
            continue
        try:
            mn += int(r[0])
            mx += int(r[1])
        except Exception:
            continue

    return (mn, mx)


def saving_text_from_delta(base_costs: dict, preview_costs: dict, *, keys: Tuple[str, ...]) -> str:
    """
    Besparing op basis van delta binnen een set gekoppelde posten.
    We tonen alleen goedkoper: als preview niet goedkoper is => "".
    """
    bmin, bmax = _sum_breakdown_range_allow_zero(base_costs, keys=keys)
    pmin, pmax = _sum_breakdown_range_allow_zero(preview_costs, keys=keys)

    save_min = bmin - pmin
    save_max = bmax - pmax

    if save_max <= 0:
        return ""

    save_min = max(0, save_min)
    save_max = max(0, save_max)

    return f"(besparing: −{_eur(save_min)} tot −{_eur(save_max)})"


# =====================
# Keysets (gekoppelde posten)
# =====================
GREEN_LINKED_KEYS = (
    "grond_afvoer_per_m3",
    "zand_aanvoer_per_m3",
    "puin_aanvoer_per_m3",
    "zaagwerk_per_m1",
    "voegen_straatwerk_per_m2",
    "beregening_basis_per_m2",
    "keramisch_straatwerk_per_m2",
    "beton_gebakken_straatwerk_per_m2",
    "grind_per_m2",
    "graszoden_per_m2",
    "beplanting_border_per_m2",
)

MATERIAL_LINKED_KEYS = (
    "keramisch_straatwerk_per_m2",
    "beton_gebakken_straatwerk_per_m2",
    "grind_per_m2",
    "voegen_straatwerk_per_m2",
    "zaagwerk_per_m1",
)

EXTRA_KEYS = {
    "voegen": ("voegen_straatwerk_per_m2",),
    "overkapping": ("overkapping_basis_per_stuk",),
    "verlichting": ("verlichting_basis_per_stuk",),
    "beregening": ("beregening_basis_per_m2",),
}

VLONDER_KEYS = (
    "vlonder_zachthout_per_m2",
    "vlonder_hardhout_per_m2",
    "vlonder_composiet_per_m2",
)

ERF_KEYS = (
    "beplanting_haag_per_m1",
    "plaatsen_betonschutting_per_m1",
    "plaatsen_designschutting_per_m1",
    "plaatsen_poortdeur_per_st",
)


# =====================
# Material / vlonder ranking
# =====================
# ✅ AANGEPAST: 1=goedkoopst -> 4=duurst (zoals je flow-menu)
_MAT_BY_CHOICE_FIXED = {"1": "grind", "2": "beton", "3": "gebakken", "4": "keramiek"}
_MAT_ORDER = {"grind": 1, "beton": 2, "gebakken": 3, "keramiek": 4}

_VLONDER_ORDER = {"composiet": 1, "hardhout": 2, "zachthout": 3}


def _material_rank(mat: str | None) -> int:
    m = (mat or "").strip().lower()
    return _MAT_ORDER.get(m, 2)


def _nice_mat(mat: str | None) -> str:
    m = (mat or "").strip().lower()
    return {
        "keramiek": "Keramiek",
        "gebakken": "Gebakken",
        "beton": "Beton",
        "grind": "Grind",
    }.get(m, "Beton")


def _vlonder_rank(v: str | None) -> int:
    vv = (v or "").strip().lower()
    return _VLONDER_ORDER.get(vv, 2)


def _nice_vlonder(v: str | None) -> str:
    vv = (v or "").strip().lower()
    return {"composiet": "Composiet", "hardhout": "Hardhout", "zachthout": "Zachthout"}.get(vv, "Hardhout")


# =====================
# ✅ Consistente “doorgevoerde kostenbesparing” teksten
# =====================
def _explain_saving(action_text: str) -> str:
    """
    Centrale tekst voor álle bespaar-acties.
    """
    action_text = (action_text or "").strip().rstrip(".")
    if not action_text:
        return "Geen kostenbesparing doorgevoerd (geen wijzigingen)."
    return f"✅ Doorgevoerde kostenbesparing: {action_text}."


# =====================
# Menu teksten (shared)
# =====================
def post_offer_choices_text() -> str:
    return (
        "Hoe wilt u verder?\n"
        "1) Kijken of er keuzes zijn om de kosten te verlagen\n"
        "2) Contact voor offerte op maat (vrijblijvend)\n"
        "3) Het hierbij laten\n\n"
        "Reageer met 1, 2 of 3."
    )


def lower_costs_menu_text(ans: dict | None) -> str:
    lines = [
        "Waar wilt u eventueel op besparen?",
        "1) Minder bestrating, meer groen (kies een voordeligere verhouding)",
        "2) Extra’s aanpassen (kies welke extra’s u wilt weglaten)",
        "3) Bestratingmateriaal goedkoper kiezen (toon besparing per optie)",
    ]
    idx = 4
    if has_vlonder(ans):
        lines.append(f"{idx}) Vlonder goedkoper maken (toon besparing per optie)")
        idx += 1
    if has_erfafscheiding(ans):
        lines.append(f"{idx}) Erfafscheiding aanpassen/verwijderen (incl. poortdeuren, toon besparing per optie)")

    lines.append("")
    lines.append("U kunt hier later terugkomen om eventueel opnieuw een bespaaroptie te kiezen.")
    lines.append("\nReageer met het nummer. (of typ 'nee' om terug te gaan)")
    return "\n".join(lines)


def soft_limit_message() -> str:
    return (
        "We kunnen samen een paar varianten bekijken. Daarna kijken we liever persoonlijk mee, "
        "zodat het echt goed aansluit bij uw situatie."
    )


def limit_followup_text() -> str:
    return (
        "Hoe wilt u verder?\n"
        "1) Contact voor offerte op maat (vrijblijvend)\n"
        "2) Het hierbij laten\n\n"
        "Reageer met 1 of 2."
    )


# =====================
# (1) Meer groen / minder bestrating (renummerd vanaf 1)
# =====================
def more_green_choice_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})

    candidates = [
        ("50_50", "50/50 (gemengd)"),
        ("30_70", "30/70 (veel groen)"),
    ]

    options: List[Tuple[str, str, str]] = []

    for ratio_code, label in candidates:
        preview = dict(a)
        preview["verhouding_bestrating_groen"] = ratio_code
        preview_costs = estimate_tuinaanleg_costs(preview)
        s = saving_text_from_delta(base_costs, preview_costs, keys=GREEN_LINKED_KEYS)
        if s:
            options.append((ratio_code, label, s))

    if not options:
        return (
            "Ik zie op basis van uw invoer geen verhouding die duidelijk goedkoper uitpakt.\n"
            "Kies gerust een andere bespaaroptie.",
            {}
        )

    mapping: Dict[str, str] = {}
    lines = ["Welke verhouding wilt u kiezen? (ik toon alleen opties die goedkoper uitpakken)"]

    for i, (ratio_code, label, s) in enumerate(options, start=1):
        digit = str(i)
        mapping[digit] = ratio_code
        lines.append(f"{digit}) {label} {s}")

    lines.append("\nReageer met het nummer. (of typ 'nee' om terug te gaan)")
    return "\n".join(lines), mapping


# =====================
# (2) Extra’s aanpassen (multi-select, renummerd, incl. 'nee')
# =====================
def extras_select_menu_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})
    overige = _overige_clean(a)

    candidates: List[Tuple[str, str]] = []

    if a.get("onkruidwerend_gevoegd") is True:
        candidates.append(("voegen", "Voegen"))
    if a.get("overkapping") is True:
        candidates.append(("overkapping", "Overkapping"))
    if a.get("verlichting") is True:
        candidates.append(("verlichting", "Verlichting"))
    if "beregening" in overige:
        candidates.append(("beregening", "Beregening"))

    options: List[Tuple[str, str, str]] = []

    for optcode, label in candidates:
        preview = dict(a)
        ov = _overige_clean(preview)

        if optcode == "voegen":
            preview["onkruidwerend_gevoegd"] = False
        elif optcode == "overkapping":
            preview["overkapping"] = False
        elif optcode == "verlichting":
            preview["verlichting"] = False
        elif optcode == "beregening":
            preview["beregening_scope"] = None
            preview["overige_wensen"] = [x for x in ov if x != "beregening"]

        preview_costs = estimate_tuinaanleg_costs(preview)
        s = saving_text_from_delta(base_costs, preview_costs, keys=EXTRA_KEYS[optcode])
        if s:
            options.append((optcode, label, s))

    if not options:
        return (
            "Ik zie geen extra’s die u nu kunt weglaten met een duidelijke besparing (op basis van uw invoer).\n"
            "Kies gerust een andere bespaaroptie.",
            {}
        )

    mapping: Dict[str, str] = {}
    lines = [
        "Welke extra’s wilt u weglaten?",
        "(u kunt meerdere opties tegelijk kiezen, bijv. 1,3)",
        "Ik toon alleen opties die goedkoper uitpakken:",
    ]

    for i, (optcode, label, s) in enumerate(options, start=1):
        digit = str(i)
        mapping[digit] = optcode
        lines.append(f"{digit}) {label} {s}")

    lines.append("")
    lines.append("Reageer met de nummers (bijv. 1,3) of typ 'nee' om terug te gaan.")
    return "\n".join(lines), mapping


# =====================
# (3) Bestratingmateriaal goedkoper (onderdeel -> keuze)
# =====================
def material_part_menu_text(ans: dict) -> str:
    a = ans or {}
    o = int(a.get("oprit_pct") or 0)
    p = int(a.get("paden_pct") or 0)
    t = int(a.get("terras_pct") or 0)

    lines = ["Welke onderdelen wilt u goedkoper maken?"]
    lines.append(f"1) Oprit (nu: {_nice_mat(a.get('materiaal_oprit'))})" + ("" if o > 0 else " (niet van toepassing)"))
    lines.append(f"2) Paden (nu: {_nice_mat(a.get('materiaal_paden'))})" + ("" if p > 0 else " (niet van toepassing)"))
    lines.append(f"3) Terras (nu: {_nice_mat(a.get('materiaal_terras'))})" + ("" if t > 0 else " (niet van toepassing)"))

    lines.append("")
    lines.append("u kunt meerdere opties tegelijk kiezen, bijv. 1,3")
    lines.append("Of typ 'nee' om terug te gaan.")
    return "\n".join(lines)


def material_choice_menu_text_cheaper(
    ans: dict,
    base_costs: dict,
    part: Any,  # ✅ accepteert str of Tuple[str,...]
) -> Tuple[str, Set[str]]:
    """
    1 is goedkoopst, 4 is duurst.
    We tonen alleen goedkopere opties + besparing per optie.
    """
    a = dict(ans or {})

    def applicable(k: str) -> bool:
        if k == "materiaal_oprit":
            return int(a.get("oprit_pct") or 0) > 0
        if k == "materiaal_paden":
            return int(a.get("paden_pct") or 0) > 0
        if k == "materiaal_terras":
            return int(a.get("terras_pct") or 0) > 0
        return True

    if isinstance(part, (list, tuple)):
        parts = tuple(str(x) for x in part)
    else:
        parts = (str(part),)

    part_to_target = {"1": "materiaal_oprit", "2": "materiaal_paden", "3": "materiaal_terras"}

    targets: List[str] = []
    for p in parts:
        k = part_to_target.get(p)
        if not k:
            continue
        if applicable(k):
            targets.append(k)

    seen = set()
    targets = [k for k in targets if not (k in seen or seen.add(k))]

    current: List[Tuple[str, str]] = []
    for k in targets:
        current.append((k, (a.get(k) or "beton").strip().lower()))

    if not current:
        return ("Geen van de gekozen onderdelen is van toepassing (0% gekozen). Typ 'nee' om terug te gaan.", set())

    max_rank = max(_material_rank(m) for _, m in current)
    cheaper_choices = {c for c, m in _MAT_BY_CHOICE_FIXED.items() if _material_rank(m) < max_rank}

    parts_label = {"materiaal_oprit": "Oprit", "materiaal_paden": "Paden", "materiaal_terras": "Terras"}

    lines = ["Huidige materiaalkeuze:"]
    for k, m in current:
        lines.append(f"- {parts_label.get(k, k)}: {_nice_mat(m)}")
    lines.append("")
    lines.append("Kies een goedkoper materiaal (1 is goedkoopst, 4 is duurst). Ik toon alleen goedkopere opties:")

    allowed: Set[str] = set()

    for choice in ("1", "2", "3", "4"):
        if choice not in cheaper_choices:
            continue

        preview = dict(a)
        new_mat = _MAT_BY_CHOICE_FIXED[choice]
        new_rank = _material_rank(new_mat)

        for k, _m in current:
            cur_m = (preview.get(k) or "beton").strip().lower()
            cur_rank = _material_rank(cur_m)
            if new_rank >= cur_rank:
                continue
            preview[k] = new_mat

        preview_costs = estimate_tuinaanleg_costs(preview)
        s = saving_text_from_delta(base_costs, preview_costs, keys=MATERIAL_LINKED_KEYS)
        if not s:
            continue

        lines.append(f"{choice}) {_nice_mat(new_mat)} {s}")
        allowed.add(choice)

    if not allowed:
        return (
            "Er is geen materiaaloptie die op basis van uw invoer duidelijk goedkoper uitpakt.\n"
            "Typ 'nee' om terug te gaan en kies een andere bespaaroptie.",
            set()
        )

    lines.append("\nReageer met het nummer. (of typ 'nee' om terug te gaan)")
    return "\n".join(lines), allowed


# =====================
# (4) Vlonder goedkoper (renummerd vanaf 1 + 'verwijderen' kan)
# =====================
def vlonder_choice_menu_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})
    if not has_vlonder(a):
        return ("Vlonder is niet gekozen. Typ 'nee' om terug te gaan.", {})

    cur = (a.get("vlonder_type") or "composiet").strip().lower()
    cur_rank = _vlonder_rank(cur)

    candidates: List[Tuple[str, str]] = [
        ("hardhout", "Hardhout"),
        ("zachthout", "Zachthout"),
    ]

    options: List[Tuple[str, str, str]] = []

    for opt, label in candidates:
        if _vlonder_rank(opt) <= cur_rank:
            continue
        preview = dict(a)
        preview["vlonder_type"] = opt
        preview_costs = estimate_tuinaanleg_costs(preview)
        s = saving_text_from_delta(base_costs, preview_costs, keys=VLONDER_KEYS)
        if s:
            options.append((opt, label, s))

    preview = dict(a)
    ov = _overige_clean(preview)
    preview["vlonder_type"] = None
    preview["overige_wensen"] = [x for x in ov if x != "vlonder"]
    preview_costs = estimate_tuinaanleg_costs(preview)
    s_remove = saving_text_from_delta(base_costs, preview_costs, keys=VLONDER_KEYS)
    if s_remove:
        options.append(("remove", "Vlonder verwijderen", s_remove))

    if not options:
        return (
            "Ik zie geen vlonder-optie die op basis van uw invoer duidelijk goedkoper uitpakt.\n"
            "Typ 'nee' om terug te gaan.",
            {}
        )

    mapping: Dict[str, str] = {}
    lines = [
        f"Huidige vlonder: {_nice_vlonder(cur)}",
        "",
        "Kies een goedkopere optie. Ik toon alleen opties die goedkoper uitpakken:",
    ]

    for i, (opt, label, s) in enumerate(options, start=1):
        digit = str(i)
        mapping[digit] = opt
        lines.append(f"{digit}) {label} {s}")

    lines.append("\nReageer met het nummer. (of typ 'nee' om terug te gaan)")
    return "\n".join(lines), mapping


# =====================
# (5) Erfafscheiding aanpassen/verwijderen (multi-select, renummerd)
# =====================
def erf_stats(ans: dict | None) -> dict:
    a = ans or {}
    items = list(a.get("erfafscheiding_items") or [])
    stats = {
        "haag_m": 0.0,
        "betonschutting_m": 0.0,
        "design_schutting_m": 0.0,
        "poortdeur_count": 0,
        "has_any": False,
    }
    for it in items:
        t = (it.get("type") or "").strip().lower()
        m = it.get("meter") or 0
        try:
            m = float(m)
        except Exception:
            m = 0.0

        if t == "haag":
            stats["haag_m"] += m
            stats["has_any"] = True
        elif t == "betonschutting":
            stats["betonschutting_m"] += m
            stats["has_any"] = True
            if it.get("poortdeur") is True:
                stats["poortdeur_count"] += 1
        elif t == "design_schutting":
            stats["design_schutting_m"] += m
            stats["has_any"] = True
            if it.get("poortdeur") is True:
                stats["poortdeur_count"] += 1
    return stats


def erf_remove_select_menu_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})
    items = list(a.get("erfafscheiding_items") or [])
    if not items:
        return ("Ik zie geen ingevulde erfafscheiding-items om te wijzigen. Typ 'nee' om terug te gaan.", {})

    stt = erf_stats(a)

    candidates: List[Tuple[str, str, dict]] = []

    def preview_removed(t_type: str) -> dict:
        p = dict(a)
        p["erfafscheiding_items"] = [it for it in items if (it.get("type") or "").strip().lower() != t_type]
        if not p["erfafscheiding_items"]:
            ov = _overige_clean(p)
            p["overige_wensen"] = [x for x in ov if x != "erfafscheiding"]
        return p

    def preview_remove_poorten() -> dict:
        p = dict(a)
        new_items = []
        for it in items:
            t = (it.get("type") or "").strip().lower()
            it2 = dict(it)
            if t in ("betonschutting", "design_schutting") and it2.get("poortdeur") is True:
                it2["poortdeur"] = False
            new_items.append(it2)
        p["erfafscheiding_items"] = new_items
        return p

    if stt["haag_m"] > 0:
        candidates.append(("rm_haag", f"Haag verwijderen (nu: {stt['haag_m']:.1f} m)", preview_removed("haag")))
    if stt["betonschutting_m"] > 0:
        candidates.append(("rm_beton", f"Betonschutting verwijderen (nu: {stt['betonschutting_m']:.1f} m)", preview_removed("betonschutting")))
    if stt["design_schutting_m"] > 0:
        candidates.append(("rm_design", f"Design schutting verwijderen (nu: {stt['design_schutting_m']:.1f} m)", preview_removed("design_schutting")))
    if stt["poortdeur_count"] > 0:
        candidates.append(("rm_poorten", f"Poortdeur(en) laten vervallen (nu: {stt['poortdeur_count']} st)", preview_remove_poorten()))

    options: List[Tuple[str, str, str]] = []

    for action, label, preview_ans in candidates:
        preview_costs = estimate_tuinaanleg_costs(preview_ans)
        s = saving_text_from_delta(base_costs, preview_costs, keys=ERF_KEYS)
        if s:
            options.append((action, label, s))

    if not options:
        return (
            "Ik zie geen erfafscheiding-aanpassing die op basis van uw invoer duidelijk goedkoper uitpakt.\n"
            "Typ 'nee' om terug te gaan.",
            {}
        )

    mapping: Dict[str, str] = {}
    lines = ["Uw huidige erfafscheiding (op basis van uw invoer):"]
    if stt["haag_m"] > 0:
        lines.append(f"- Haag: {stt['haag_m']:.1f} m")
    if stt["betonschutting_m"] > 0:
        lines.append(f"- Betonschutting: {stt['betonschutting_m']:.1f} m")
    if stt["design_schutting_m"] > 0:
        lines.append(f"- Design schutting: {stt['design_schutting_m']:.1f} m")
    if stt["poortdeur_count"] > 0:
        lines.append(f"- Poortdeur(en): {stt['poortdeur_count']} st")

    lines.append("")
    lines.append("Wat wilt u aanpassen/verwijderen? (u kunt meerdere opties tegelijk kiezen, bijv. 1,3)")
    lines.append("Ik toon alleen opties die goedkoper uitpakken:")

    for i, (action, label, s) in enumerate(options, start=1):
        digit = str(i)
        mapping[digit] = action
        lines.append(f"{digit}) {label} {s}")

    lines.append("")
    lines.append("Reageer met de nummers (bijv. 1,3) of typ 'nee' om terug te gaan.")
    return "\n".join(lines), mapping


# =====================
# Apply changes (✅ consistent “doorgevoerde kostenbesparing”)
# =====================
def apply_set_ratio(answers: dict, ratio_code: str) -> Tuple[dict, str]:
    a = dict(answers or {})
    a["verhouding_bestrating_groen"] = ratio_code
    pretty = {"50_50": "50/50", "30_70": "30/70", "70_30": "70/30"}.get(ratio_code, ratio_code)
    return a, _explain_saving(f"verhouding bestrating/groen aangepast naar {pretty}")


def apply_remove_selected_extras(answers: dict, selected_actions: List[str]) -> Tuple[dict, str]:
    a = dict(answers or {})
    overige = _overige_clean(a)

    chosen: List[str] = []

    if "voegen" in selected_actions:
        a["onkruidwerend_gevoegd"] = False
        chosen.append("voegen verwijderd")

    if "overkapping" in selected_actions:
        a["overkapping"] = False
        chosen.append("overkapping verwijderd")

    if "verlichting" in selected_actions:
        a["verlichting"] = False
        chosen.append("verlichting verwijderd")

    if "beregening" in selected_actions:
        a["beregening_scope"] = None
        overige = [x for x in overige if x != "beregening"]
        chosen.append("beregening verwijderd")

    a["overige_wensen"] = overige

    if not chosen:
        return a, _explain_saving("")
    return a, _explain_saving(", ".join(chosen))


def apply_material_change(answers: dict, part: Any, choice_digit: str) -> Tuple[dict, str]:
    a = dict(answers or {})
    mat = _MAT_BY_CHOICE_FIXED.get(choice_digit)
    if not mat:
        return a, "Onbekende materiaalkeuze."

    if isinstance(part, (list, tuple)):
        parts = tuple(str(x) for x in part)
    else:
        parts = (str(part),)

    part_to_target = {"1": "materiaal_oprit", "2": "materiaal_paden", "3": "materiaal_terras"}
    targets = [part_to_target[p] for p in parts if p in part_to_target]

    seen = set()
    targets = [k for k in targets if not (k in seen or seen.add(k))]

    changed_targets: List[str] = []
    new_rank = _material_rank(mat)

    for k in targets:
        if k == "materiaal_oprit" and int(a.get("oprit_pct") or 0) == 0:
            continue
        if k == "materiaal_paden" and int(a.get("paden_pct") or 0) == 0:
            continue
        if k == "materiaal_terras" and int(a.get("terras_pct") or 0) == 0:
            continue

        cur = (a.get(k) or "beton").strip().lower()
        cur_rank = _material_rank(cur)

        if new_rank >= cur_rank:
            continue

        a[k] = mat
        changed_targets.append(k.replace("materiaal_", ""))

    if not changed_targets:
        return a, "Dit is niet goedkoper dan uw huidige keuze (geen wijziging)."

    return a, _explain_saving(f"materiaal aangepast naar {_nice_mat(mat)} voor: {', '.join(changed_targets)}")


def apply_vlonder_change(answers: dict, action: str) -> Tuple[dict, str]:
    a = dict(answers or {})
    overige = _overige_clean(a)

    if "vlonder" not in overige:
        return a, "Vlonder stond niet in uw keuzes."

    if action == "remove":
        a["vlonder_type"] = None
        a["overige_wensen"] = [x for x in overige if x != "vlonder"]
        return a, _explain_saving("vlonder verwijderd")

    cur = (a.get("vlonder_type") or "composiet").strip().lower()
    if _vlonder_rank(action) <= _vlonder_rank(cur):
        return a, "Dit is niet goedkoper dan uw huidige vlonderkeuze (geen wijziging)."

    a["vlonder_type"] = action
    return a, _explain_saving(f"vlonder aangepast naar {_nice_vlonder(action)} (goedkoper)")


def apply_erf_changes(answers: dict, selected_actions: List[str]) -> Tuple[dict, str]:
    a = dict(answers or {})
    items = list(a.get("erfafscheiding_items") or [])

    if not items:
        ov = _overige_clean(a)
        a["overige_wensen"] = [x for x in ov if x != "erfafscheiding"]
        return a, "Erfafscheiding stond niet (meer) ingesteld."

    remove_types = set()
    remove_poorten = False

    for act in selected_actions:
        if act == "rm_haag":
            remove_types.add("haag")
        elif act == "rm_beton":
            remove_types.add("betonschutting")
        elif act == "rm_design":
            remove_types.add("design_schutting")
        elif act == "rm_poorten":
            remove_poorten = True

    if remove_poorten:
        for it in items:
            t = (it.get("type") or "").strip().lower()
            if t in ("betonschutting", "design_schutting") and it.get("poortdeur") is True:
                it["poortdeur"] = False

    if remove_types:
        items = [it for it in items if (it.get("type") or "").strip().lower() not in remove_types]

    a["erfafscheiding_items"] = items

    if not items:
        ov = _overige_clean(a)
        a["overige_wensen"] = [x for x in ov if x != "erfafscheiding"]

    msgs: List[str] = []
    pretty = {"haag": "haag", "betonschutting": "betonschutting", "design_schutting": "design schutting"}

    if remove_types:
        msgs.append("verwijderd: " + ", ".join(pretty.get(t, t) for t in sorted(remove_types)))
    if remove_poorten:
        msgs.append("poortdeur(en) laten vervallen")

    if not msgs:
        return a, "Geen geldige keuze (geen wijziging)."

    return a, _explain_saving(" • ".join(msgs))
