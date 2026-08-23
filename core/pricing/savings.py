# savings.py
from __future__ import annotations

import re
from typing import Dict, Tuple, List, Optional, Set, Any

from core.pricing.pricing import estimate_tuinaanleg_costs, estimate_losse_onderdelen_costs


def _estimate(ans: dict) -> dict:
    """Kies de juiste prijsfunctie op basis van flow-type."""
    if (ans or {}).get("_flow_type") == "losse_onderdelen":
        return estimate_losse_onderdelen_costs(ans)
    return estimate_tuinaanleg_costs(ans)


# =====================
# Basics
# =====================


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


def has_paving(ans: dict | None) -> bool:
    """True als de gebruiker daadwerkelijk bestrating heeft gekozen."""
    if not ans:
        return False
    a = ans or {}
    for key in ("_direct_oprit_m2", "_direct_terras_m2", "_direct_paden_m2"):
        if float(a.get(key) or 0) > 0:
            return True
    bpct = a.get("bestrating_pct")
    if bpct is not None and int(bpct) > 0:
        return True
    for key in ("oprit_pct", "terras_pct", "paden_pct"):
        if int(a.get(key) or 0) > 0:
            return True
    return False


def has_beregening_downgrade(ans: dict | None) -> bool:
    """True als beregening actief is én het systeem niet al op 'basis' staat."""
    if not ans:
        return False
    overige = _overige_clean(ans)
    if "beregening" not in overige:
        return False
    systeem = (ans.get("beregening_systeem") or "").strip().lower()
    return systeem in ("volautomatisch", "highend")


_HAAG_ORDER = {"voordelig_laag": 1, "voordelig_hoog": 2, "premium_laag": 3, "premium_hoog": 4}

def _haag_items(ans: dict | None) -> List[dict]:
    return [it for it in (ans or {}).get("erfafscheiding_items") or []
            if (it.get("type") or "").strip().lower() == "haag"]

def has_haag_downgrade(ans: dict | None) -> bool:
    """True als er haag is met een type duurder dan 'voordelig_laag'."""
    return any(_HAAG_ORDER.get((it.get("haag_type") or "voordelig_hoog").strip().lower(), 2) > 1
               for it in _haag_items(ans))


def has_overkapping_downgrade(ans: dict | None) -> bool:
    """True als overkapping actief is én er een kleinere presetmaat beschikbaar is."""
    if not ans:
        return False
    if not ans.get("overkapping"):
        return False
    cur_m2 = float(ans.get("overkapping_m2") or 15.0)
    return any(m < cur_m2 - 0.5 for m, _ in _OVERKAPPING_PRESETS)


def has_extras(ans: dict | None) -> bool:
    """True als de gebruiker extra's (overkapping, verlichting, beregening, vlonder, erfafscheiding) heeft gekozen."""
    if not ans:
        return False
    a = ans or {}
    if a.get("overkapping") or a.get("verlichting"):
        return True
    overige = _overige_clean(a)
    return bool(overige)


def has_erfafscheiding(ans: dict | None) -> bool:
    if not ans:
        return False
    if "erfafscheiding" in _overige_clean(ans):
        return True
    items = ans.get("erfafscheiding_items") or []
    return bool(items)


def is_back(text: str) -> bool:
    """Alleen expliciete terugnavigatie: 'terug' of 'back'."""
    t = (text or "").strip().lower()
    return t in {"terug", "back"}


def is_cancel(text: str) -> bool:
    """Annuleren of terug: 'nee', 'n', 'no', 'terug', 'back'."""
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
    if is_cancel(t):
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
    if is_cancel(t):
        return "nee"
    return t if t in allowed else None


# Multi-select voor materiaal-onderdelen (tot 9 items)
def parse_material_parts(user_text: str) -> Optional[Tuple[str, ...]]:
    """
    Multi-select voor materiaalonderdelen.
    Accepteert: "1,3" "13" "1 3" "1-3" etc.
    'nee/terug' => ("nee",)
    """
    parsed = parse_multi_digits(user_text, allowed=("1", "2", "3", "4", "5", "6", "7", "8", "9"))
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
    "beregening_installatie_basis",
    "beregening_installatie_volautomatisch",
    "beregening_installatie_highend",
    "beregening_gazon_basis_per_m2",
    "beregening_gazon_volautomatisch_per_m2",
    "beregening_gazon_highend_per_m2",
    "beregening_beplanting_basis_per_m2",
    "beregening_beplanting_volautomatisch_per_m2",
    "beregening_beplanting_highend_per_m2",
    "keramisch_straatwerk_per_m2",
    "beton_straatwerk_per_m2",
    "gebakken_straatwerk_per_m2",
    "grind_per_m2",
    "graszoden_per_m2",
    "beplanting_border_per_m2",
)

MATERIAL_LINKED_KEYS = (
    "keramisch_straatwerk_per_m2",
    "beton_straatwerk_per_m2",
    "gebakken_straatwerk_per_m2",
    "grind_per_m2",
    "voegen_straatwerk_per_m2",
    "zaagwerk_per_m1",
)

EXTRA_KEYS = {
    "voegen": ("voegen_straatwerk_per_m2",),
    "overkapping": ("overkapping_per_m2",),
    "verlichting": ("verlichting_basis_per_stuk",),
    "beregening": (
        "beregening_installatie_basis",
        "beregening_installatie_volautomatisch",
        "beregening_installatie_highend",
        "beregening_gazon_basis_per_m2",
        "beregening_gazon_volautomatisch_per_m2",
        "beregening_gazon_highend_per_m2",
        "beregening_beplanting_basis_per_m2",
        "beregening_beplanting_volautomatisch_per_m2",
        "beregening_beplanting_highend_per_m2",
    ),
}

VLONDER_KEYS = (
    "vlonder_zachthout_per_m2",
    "vlonder_hardhout_per_m2",
    "vlonder_composiet_per_m2",
)

_OVERKAPPING_PRESETS: List[Tuple[float, str]] = [
    (9.0,  "Knus (ca. 3×3 m, 9 m²)"),
    (15.0, "Standaard (ca. 5×3 m, 15 m²)"),
]

ERF_KEYS = (
    "beplanting_haag_voordelig_laag_per_m1",
    "beplanting_haag_voordelig_hoog_per_m1",
    "beplanting_haag_premium_laag_per_m1",
    "beplanting_haag_premium_hoog_per_m1",
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
# ✅ Consistente "doorgevoerde kostenbesparing" teksten
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
        "**Wat wilt u doen?**\n"
        "1) Vrijblijvende offerte aanvragen – we nemen zo snel mogelijk contact met u op\n"
        "2) Kijken of er keuzes zijn om de kosten te verlagen\n"
        "3) Niets, ik heb genoeg informatie\n\n"
        "Reageer met 1, 2 of 3."
    )


def post_offer_choices_losse_text() -> str:
    return (
        "**Wat wilt u doen?**\n"
        "1) Vrijblijvende offerte aanvragen – we nemen zo snel mogelijk contact met u op\n"
        "2) Nog een onderdeel toevoegen of aanpassen\n"
        "3) Kijken of er keuzes zijn om de kosten te verlagen\n"
        "4) Niets, ik heb genoeg informatie\n\n"
        "Reageer met 1, 2, 3 of 4."
    )


def post_offer_choices_tuinontwerp_text() -> str:
    return (
        "**Wat wilt u doen?**\n"
        "1) Vrijblijvende offerte aanvragen voor het ontwerp\n"
        "2) Ook een aanlegprijs berekenen – gehele tuin\n"
        "3) Ook een aanlegprijs berekenen – losse onderdelen\n"
        "4) Niets, ik heb genoeg informatie\n\n"
        "Reageer met 1, 2, 3 of 4."
    )


def lower_costs_menu_text(ans: dict | None, base_costs: dict | None = None) -> Tuple[str, Dict[str, str]]:
    """Geeft (tekst, mapping digit→actie) terug. Volledig plat — elk item direct zichtbaar."""
    a = ans or {}
    _costs = base_costs or _estimate(a)
    overige = _overige_clean(a)
    mapping: Dict[str, str] = {}
    lines = ["Waar wilt u op besparen?"]
    idx = 1

    if has_paving(a):
        _, mg_map = more_green_choice_text(a, _costs)
        if mg_map:
            mapping[str(idx)] = "more_green"
            lines.append(f"{idx}) Minder bestrating, meer groen")
            idx += 1

    if has_paving(a):
        mapping[str(idx)] = "material"
        lines.append(f"{idx}) Bestratingsmateriaal goedkoper kiezen")
        idx += 1

    if a.get("onkruidwerend_gevoegd"):
        mapping[str(idx)] = "voegen"
        lines.append(f"{idx}) Voegen aanpassen")
        idx += 1

    if a.get("overkapping"):
        mapping[str(idx)] = "overkapping"
        lines.append(f"{idx}) Overkapping aanpassen")
        idx += 1

    if a.get("verlichting"):
        mapping[str(idx)] = "verlichting"
        lines.append(f"{idx}) Tuinverlichting aanpassen")
        idx += 1

    if "beregening" in overige:
        mapping[str(idx)] = "beregening"
        lines.append(f"{idx}) Beregening aanpassen")
        idx += 1

    if has_vlonder(a):
        mapping[str(idx)] = "vlonder"
        lines.append(f"{idx}) Vlonder aanpassen")
        idx += 1

    if has_erfafscheiding(a):
        mapping[str(idx)] = "erfafscheiding"
        lines.append(f"{idx}) Erfafscheiding aanpassen")
        idx += 1

    if not mapping:
        lines.append("Er zijn geen bespaaropties beschikbaar voor uw configuratie.")

    lines.append("")
    lines.append("U kunt hier later terugkomen om eventueel opnieuw een bespaaroptie te kiezen.")
    lines.append("\nReageer met het nummer, of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping




# =====================
# (1) Meer groen / minder bestrating (renummerd vanaf 1)
# =====================

def _current_paving_m2(a: dict) -> float:
    """Huidige totale bestrating m² berekend vanuit items (V2) of percentage-fallback."""
    oprit = float(a.get("_direct_oprit_m2") or 0)
    terras = float(a.get("_direct_terras_m2") or 0) + sum(
        float(it.get("m2") or 0) for it in (a.get("terras_extra_items") or [])
    )
    paden = float(a.get("_direct_paden_m2") or 0) + sum(
        float(it.get("m2") or 0) for it in (a.get("paden_extra_items") or [])
    )
    total_items = oprit + terras + paden
    if total_items > 0.01:
        return total_items
    tuin_m2 = float(a.get("tuin_m2") or 0)
    bpct = a.get("bestrating_pct")
    if bpct is not None:
        return tuin_m2 * float(bpct) / 100.0
    share = {"70_30": 0.70, "50_50": 0.50, "30_70": 0.30}.get(
        a.get("verhouding_bestrating_groen"), 0.50
    )
    return tuin_m2 * share


def more_green_choice_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})
    tuin_m2 = float(a.get("tuin_m2") or 0)

    candidates = [
        ("50_50", 0.50),
        ("30_70", 0.30),
    ]

    def _ratio_label(ratio_code: str, paving_share: float) -> str:
        if tuin_m2 > 0:
            p = round(tuin_m2 * paving_share)
            g = round(tuin_m2 * (1.0 - paving_share))
            return f"ca. {p} m² bestrating + {g} m² groen"
        return {"50_50": "50/50 (gemengd)", "30_70": "30/70 (veel groen)"}.get(ratio_code, ratio_code)

    is_items_based = (
        float(a.get("_direct_terras_m2") or 0) > 0 or
        float(a.get("_direct_paden_m2") or 0) > 0 or
        float(a.get("_direct_oprit_m2") or 0) > 0 or
        bool(a.get("terras_extra_items")) or
        bool(a.get("paden_extra_items"))
    )

    options: List[Tuple[str, str, str]] = []

    for ratio_code, paving_share in candidates:
        if is_items_based:
            # Proportioneel schalen: preview gebruikt apply_ratio_proportional
            preview_a, _ = apply_ratio_proportional(a, ratio_code)
            preview_costs = _estimate(preview_a)
        else:
            # Percentage-modus: simuleer _apply_recalc effect
            preview_a = dict(a)
            for _k in ("_flow_version", "_direct_oprit_m2", "_direct_terras_m2",
                       "_direct_paden_m2", "_direct_gazon_m2", "_direct_beplanting_m2"):
                preview_a.pop(_k, None)
            preview_a["terras_extra_items"] = []
            preview_a["paden_extra_items"] = []
            preview_a["verhouding_bestrating_groen"] = ratio_code
            preview_costs = _estimate(preview_a)

        bt = _total_range(base_costs)
        pt = _total_range(preview_costs)
        if not bt or not pt:
            continue
        save_min = max(0, bt[0] - pt[0])
        save_max = max(0, bt[1] - pt[1])
        if save_max <= 0:
            continue
        s = f"(besparing: −{_eur(save_min)} tot −{_eur(save_max)})"
        options.append((ratio_code, _ratio_label(ratio_code, paving_share), s))

    if not options:
        return (
            "Ik zie op basis van uw invoer geen verhouding die duidelijk goedkoper uitpakt.\n"
            "Kies gerust een andere bespaaroptie.",
            {}
        )

    cur_paving = _current_paving_m2(a)
    cur_green = max(0.0, tuin_m2 - cur_paving)

    mapping: Dict[str, str] = {}
    lines = [
        f"U heeft nu **ca. {int(round(cur_paving))} m² bestrating + {int(round(cur_green))} m² groen**.",
        "Welke verhouding wilt u kiezen? (ik toon alleen opties die goedkoper uitpakken)",
    ]

    for i, (ratio_code, label, s) in enumerate(options, start=1):
        digit = str(i)
        mapping[digit] = ratio_code
        lines.append(f"{digit}) {label} {s}")

    lines.append("\nReageer met het nummer, of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping


# =====================
# Beregening systeem goedkoper
# =====================
def beregening_systeem_choice_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})
    overige = _overige_clean(a)
    if "beregening" not in overige:
        return ("Beregening is niet gekozen. Typ 'nee' om terug te gaan.", {})

    huidig = (a.get("beregening_systeem") or "volautomatisch").strip().lower()
    _LABELS = {"basis": "Basis – deels handmatig", "volautomatisch": "Volautomatisch – tijdschema", "highend": "Smart – via app (wifi/weer-gestuurd)"}
    cheaper = []
    if huidig == "highend":
        cheaper = [("volautomatisch", "Volautomatisch"), ("basis", "Basis (deels handmatig)")]
    elif huidig == "volautomatisch":
        cheaper = [("basis", "Basis (deels handmatig)")]

    mapping: Dict[str, str] = {}
    lines = [
        f"U heeft nu gekozen voor **{_LABELS.get(huidig, huidig)}**.",
        "Kies een goedkopere optie of verwijder de beregening:",
    ]
    idx = 1
    bkeys = tuple(EXTRA_KEYS["beregening"])
    for systeem, label in cheaper:
        preview = dict(a)
        preview["beregening_systeem"] = systeem
        s = saving_text_from_delta(base_costs, _estimate(preview), keys=bkeys)
        mapping[str(idx)] = systeem
        lines.append(f"{idx}) {label}" + (f" {s}" if s else ""))
        idx += 1

    preview_rm = dict(a)
    preview_rm["beregening_scope"] = None
    preview_rm["beregening_systeem"] = None
    preview_rm["overige_wensen"] = [x for x in overige if x != "beregening"]
    s_rm = saving_text_from_delta(base_costs, _estimate(preview_rm), keys=bkeys)
    mapping[str(idx)] = "remove"
    lines.append(f"{idx}) Beregening verwijderen" + (f" {s_rm}" if s_rm else ""))

    lines.append("")
    lines.append("Reageer met het nummer, of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping


def apply_beregening_systeem_change(answers: dict, systeem: str) -> Tuple[dict, str]:
    a = dict(answers)
    _LABELS = {"basis": "Basis – deels handmatig", "volautomatisch": "Volautomatisch – tijdschema", "highend": "Smart – via app (wifi/weer-gestuurd)"}
    a["beregening_systeem"] = systeem
    return a, f"Beregeningssysteem gewijzigd naar {_LABELS.get(systeem, systeem)}."


# =====================
# (2) Extra’s aanpassen (multi-select, renummerd, incl. ‘nee’)
# =====================
def extras_select_menu_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})
    overige = _overige_clean(a)

    candidates: List[Tuple[str, str]] = []

    if a.get("onkruidwerend_gevoegd") is True:
        candidates.append(("voegen", "Voegen"))
    if a.get("overkapping") is True:
        candidates.append(("overkapping", "Overkapping verwijderen"))
    if a.get("overkapping") is True and has_overkapping_downgrade(a):
        candidates.append(("overkapping_downgrade", "Overkapping kleiner kiezen"))
    if a.get("verlichting") is True:
        candidates.append(("verlichting", "Verlichting"))
    if "beregening" in overige:
        candidates.append(("beregening", "Beregening verwijderen"))
    if "beregening" in overige and has_beregening_downgrade(a):
        candidates.append(("beregening_downgrade", "Beregeningssysteem goedkoper kiezen"))

    options: List[Tuple[str, str, str]] = []

    for optcode, label in candidates:
        preview = dict(a)
        ov = _overige_clean(preview)
        keys_for_saving = EXTRA_KEYS.get(optcode)

        if optcode == "voegen":
            preview["onkruidwerend_gevoegd"] = False
        elif optcode == "overkapping":
            preview["overkapping"] = False
            preview["overkapping_m2"] = None
        elif optcode == "overkapping_downgrade":
            cur_m2 = float(a.get("overkapping_m2") or 15.0)
            smallest = min((m for m, _ in _OVERKAPPING_PRESETS if m < cur_m2 - 0.5), default=9.0)
            preview["overkapping_m2"] = smallest
            keys_for_saving = tuple(EXTRA_KEYS["overkapping"])
        elif optcode == "verlichting":
            preview["verlichting"] = False
        elif optcode == "beregening":
            preview["beregening_scope"] = None
            preview["beregening_systeem"] = None
            preview["overige_wensen"] = [x for x in ov if x != "beregening"]
        elif optcode == "beregening_downgrade":
            preview["beregening_systeem"] = "basis"
            keys_for_saving = tuple(EXTRA_KEYS["beregening"])

        if keys_for_saving is None:
            continue
        preview_costs = _estimate(preview)
        s = saving_text_from_delta(base_costs, preview_costs, keys=keys_for_saving)
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
        "(kies één of meerdere nummers, bijv. 1, 3)",
        "Ik toon alleen opties die goedkoper uitpakken:",
    ]

    for i, (optcode, label, s) in enumerate(options, start=1):
        digit = str(i)
        mapping[digit] = optcode
        lines.append(f"{digit}) {label} {s}")

    lines.append("")
    lines.append("Kies één of meerdere nummers (bijv. 1, 3), of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping


# =====================
# (3) Bestratingmateriaal goedkoper (onderdeel -> keuze)
# =====================
def _has_bestrating(a: dict, onderdeel: str) -> bool:
    """Werkt voor zowel gehele-tuin (pct) als losse onderdelen (m2)."""
    pct_key = f"{onderdeel}_pct"
    m2_key = f"{onderdeel}_m2"
    return int(a.get(pct_key) or 0) > 0 or float(a.get(m2_key) or 0) > 0


def _item_spec_label(item_spec: str) -> str:
    """Geeft een leesbaar label voor een item_spec zoals 'terras_0' → 'Terras 1'."""
    if item_spec == "oprit":
        return "Oprit"
    parts = item_spec.split("_")
    if len(parts) == 2:
        comp_label = {"terras": "Terras", "paden": "Paden"}.get(parts[0], parts[0].capitalize())
        try:
            return f"{comp_label} {int(parts[1]) + 1}"
        except ValueError:
            pass
    return item_spec.capitalize()


def _get_item_material(a: dict, item_spec: str) -> str:
    """
    Haal het materiaal op voor een specifiek item_spec.
    Ondersteunt zowel de 'gehele tuin'-opbouw (materiaal_X + X_extra_items)
    als de 'losse onderdelen'-opbouw (X_items lijst, incl. item 0).
    """
    if item_spec == "oprit":
        oprit_items = a.get("oprit_items") or []
        if oprit_items:
            return (oprit_items[0].get("materiaal") or "beton").strip().lower()
        return (a.get("materiaal_oprit") or "beton").strip().lower()
    parts = item_spec.split("_")
    if len(parts) != 2:
        return "beton"
    comp, idx_str = parts
    try:
        idx = int(idx_str)
    except ValueError:
        return "beton"
    lo_items = a.get(f"{comp}_items") or []
    if lo_items:
        if idx < len(lo_items):
            return (lo_items[idx].get("materiaal") or "beton").strip().lower()
        return "beton"
    if idx == 0:
        return (a.get(f"materiaal_{comp}") or "beton").strip().lower()
    items = a.get(f"{comp}_extra_items") or []
    if idx - 1 < len(items):
        return (items[idx - 1].get("materiaal") or "beton").strip().lower()
    return "beton"


def _set_item_material(a: dict, item_spec: str, new_mat: str) -> dict:
    """
    Stel het materiaal in voor een specifiek item_spec (returnt nieuw dict).
    Schrijft ook naar X_items (losse onderdelen) zodat de prijsberekening,
    die X_items boven materiaal_X verkiest, de wijziging daadwerkelijk meeneemt.
    """
    a = dict(a)
    if item_spec == "oprit":
        oprit_items = a.get("oprit_items") or []
        if oprit_items:
            new_items = list(oprit_items)
            new_items[0] = dict(new_items[0], materiaal=new_mat)
            a["oprit_items"] = new_items
        a["materiaal_oprit"] = new_mat
        return a
    parts = item_spec.split("_")
    if len(parts) != 2:
        return a
    comp, idx_str = parts
    try:
        idx = int(idx_str)
    except ValueError:
        return a
    lo_items = a.get(f"{comp}_items") or []
    if lo_items:
        if idx < len(lo_items):
            new_items = list(lo_items)
            new_mat_lower = (new_mat or "").strip().lower()
            item_changes = {"materiaal": new_mat}
            # Voegen wordt alleen gevraagd/toegepast op beton/keramiek (zie intake-flow);
            # bij wisselen naar grind/gebakken vervalt voegen voor dit item.
            if comp in ("paden", "terras") and new_mat_lower not in ("beton", "keramiek"):
                item_changes["gevoegd"] = False
            new_items[idx] = dict(new_items[idx], **item_changes)
            a[f"{comp}_items"] = new_items
            if comp in ("paden", "terras") and "voegen_m2_custom" in a:
                voegen_total = sum(
                    float(it.get("m2", 0))
                    for c in ("paden", "terras")
                    for it in (a.get(c + "_items") or [])
                    if it.get("gevoegd", False)
                )
                a["voegen_m2_custom"] = voegen_total
                a["onkruidwerend_gevoegd"] = voegen_total > 0
        if idx == 0:
            a[f"materiaal_{comp}"] = new_mat
        return a
    if idx == 0:
        a[f"materiaal_{comp}"] = new_mat
    else:
        items = list(a.get(f"{comp}_extra_items") or [])
        extra_idx = idx - 1
        if extra_idx < len(items):
            items[extra_idx] = dict(items[extra_idx], materiaal=new_mat)
            a[f"{comp}_extra_items"] = items
    return a


def material_part_menu_text(ans: dict) -> Tuple[str, Dict[str, str]]:
    """
    Toont per item welk onderdeel goedkoper kan.
    Bij meerdere terrassen/paden worden ze individueel getoond.
    Retourneert (tekst, mapping digit→item_spec).
    """
    a = ans or {}
    lines = ["Welke onderdelen wilt u goedkoper maken?"]
    mapping: Dict[str, str] = {}
    idx = 1

    def _lo_item_lines(comp: str, comp_label: str) -> bool:
        """Toont elk item uit X_items (losse-onderdelen model). True als gebruikt."""
        nonlocal idx
        items = a.get(f"{comp}_items") or []
        if not items:
            return False
        multi = len(items) > 1
        for i, item in enumerate(items):
            m2 = float(item.get("m2") or 0)
            mat = (item.get("materiaal") or "beton")
            if m2 <= 0.01 or _material_rank(mat) <= 1:
                continue
            mapping[str(idx)] = f"{comp}_{i}"
            num = f" {i + 1}" if multi else ""
            lines.append(f"{idx}) {comp_label}{num} – {_nice_mat(mat)} ({int(m2)} m²)")
            idx += 1
        return True

    # Oprit
    if not _lo_item_lines("oprit", "Oprit"):
        if _has_bestrating(a, "oprit") and _material_rank(a.get("materiaal_oprit")) > 1:
            m2 = float(a.get("_direct_oprit_m2") or a.get("oprit_m2") or 0)
            label = f"Oprit – {_nice_mat(a.get('materiaal_oprit'))}" + (f" ({int(m2)} m²)" if m2 > 0 else "")
            mapping[str(idx)] = "oprit"
            lines.append(f"{idx}) {label}")
            idx += 1

    # Paden – per item tonen als meerdere aanwezig
    if not _lo_item_lines("paden", "Paden"):
        paden_extra = a.get("paden_extra_items") or []
        direct_paden = float(a.get("_direct_paden_m2") or 0)
        mat_paden = (a.get("materiaal_paden") or "beton")
        if paden_extra or direct_paden > 0:
            # Pad 1: toon als direct_paden > 0, maar val ook terug op materiaal_paden
            # als _direct_paden_m2 na een savings-operatie op 0 staat
            if _material_rank(mat_paden) > 1 and (direct_paden > 0 or paden_extra):
                m2_label = f" ({int(direct_paden)} m²)" if direct_paden > 0 else ""
                mapping[str(idx)] = "paden_0"
                lines.append(f"{idx}) Paden 1 – {_nice_mat(mat_paden)}{m2_label}")
                idx += 1
            for i, item in enumerate(paden_extra):
                m2 = float(item.get("m2") or 0)
                mat = (item.get("materiaal") or "beton")
                if m2 > 0.01 and _material_rank(mat) > 1:
                    mapping[str(idx)] = f"paden_{i + 1}"
                    lines.append(f"{idx}) Paden {i + 2} – {_nice_mat(mat)} ({int(m2)} m²)")
                    idx += 1
        elif _has_bestrating(a, "paden") and _material_rank(mat_paden) > 1:
            mapping[str(idx)] = "paden_0"
            lines.append(f"{idx}) Paden (nu: {_nice_mat(mat_paden)})")
            idx += 1

    # Terras – per item tonen als meerdere aanwezig
    if not _lo_item_lines("terras", "Terras"):
        terras_extra = a.get("terras_extra_items") or []
        direct_terras = float(a.get("_direct_terras_m2") or 0)
        mat_terras = (a.get("materiaal_terras") or "beton")
        if terras_extra or direct_terras > 0:
            # Terras 1: toon als direct_terras > 0, maar val ook terug op materiaal_terras
            # als _direct_terras_m2 na een savings-operatie op 0 staat
            if _material_rank(mat_terras) > 1 and (direct_terras > 0 or terras_extra):
                m2_label = f" ({int(direct_terras)} m²)" if direct_terras > 0 else ""
                mapping[str(idx)] = "terras_0"
                lines.append(f"{idx}) Terras 1 – {_nice_mat(mat_terras)}{m2_label}")
                idx += 1
            for i, item in enumerate(terras_extra):
                m2 = float(item.get("m2") or 0)
                mat = (item.get("materiaal") or "beton")
                if m2 > 0.01 and _material_rank(mat) > 1:
                    mapping[str(idx)] = f"terras_{i + 1}"
                    lines.append(f"{idx}) Terras {i + 2} – {_nice_mat(mat)} ({int(m2)} m²)")
                    idx += 1
        elif _has_bestrating(a, "terras") and _material_rank(mat_terras) > 1:
            mapping[str(idx)] = "terras_0"
            lines.append(f"{idx}) Terras (nu: {_nice_mat(mat_terras)})")
            idx += 1

    if not mapping:
        return (
            "U heeft al het voordeligste materiaal (grind) gekozen voor al uw bestrating.\n"
            "Er is geen goedkopere materiaaloptie beschikbaar.\n"
            "Typ 'nee' om terug te gaan en kies een andere bespaaroptie.",
            {}
        )

    lines.append("")
    lines.append("Kies één of meerdere nummers (bijv. 1, 3).")
    lines.append("Of typ 'nee' om terug te gaan.")
    return "\n".join(lines), mapping


def material_choice_menu_text_cheaper(
    ans: dict,
    base_costs: dict,
    part: Any,
) -> Tuple[str, Set[str]]:
    """
    Toont goedkopere materiaalopties voor de geselecteerde items.
    Accepteert item_specs ('terras_0', 'paden_1', 'oprit') of legacy digits ('1','2','3').
    """
    a = dict(ans or {})

    if isinstance(part, (list, tuple)):
        parts = tuple(str(x) for x in part)
    else:
        parts = (str(part),)

    # Legacy mapping voor backwards compat (losse onderdelen flow)
    _legacy = {"1": "oprit", "2": "paden_0", "3": "terras_0"}

    # Vertaal naar item_specs
    item_specs: List[str] = []
    seen: set = set()
    for p in parts:
        spec = _legacy.get(p, p)  # legacy digit → item_spec, of al een item_spec
        if spec not in seen:
            item_specs.append(spec)
            seen.add(spec)

    # Haal per spec het huidige materiaal op
    current: List[Tuple[str, str]] = []  # (item_spec, materiaal)
    for spec in item_specs:
        mat = _get_item_material(a, spec)
        current.append((spec, mat))

    if not current:
        return ("Geen van de gekozen onderdelen is van toepassing. Typ 'nee' om terug te gaan.", set())

    max_rank = max(_material_rank(m) for _, m in current)
    cheaper_choices = {c for c, m in _MAT_BY_CHOICE_FIXED.items() if _material_rank(m) < max_rank}

    if len(current) == 1:
        spec, mat = current[0]
        lines = [f"U heeft nu gekozen voor **{_nice_mat(mat)}** voor {_item_spec_label(spec)}."]
    else:
        lines = ["U heeft nu gekozen voor:"]
        for spec, m in current:
            lines.append(f"- **{_nice_mat(m)}** voor {_item_spec_label(spec)}")
    lines.append("Kies een goedkoper materiaal. Ik toon alleen goedkopere opties:")

    allowed: Set[str] = set()

    for choice in ("1", "2", "3", "4"):
        if choice not in cheaper_choices:
            continue

        new_mat = _MAT_BY_CHOICE_FIXED[choice]
        new_rank = _material_rank(new_mat)

        preview = dict(a)
        parts_affected: List[str] = []

        for spec, cur_mat in current:
            if new_rank >= _material_rank(cur_mat):
                continue
            preview = _set_item_material(preview, spec, new_mat)
            parts_affected.append(_item_spec_label(spec))

        if not parts_affected:
            continue

        preview_costs = _estimate(preview)
        s = saving_text_from_delta(base_costs, preview_costs, keys=MATERIAL_LINKED_KEYS)
        if not s:
            continue

        lines.append(f"{choice}) {_nice_mat(new_mat)} {s} (voor: {' + '.join(parts_affected)})")
        allowed.add(choice)

    if not allowed:
        return (
            "Er is geen materiaaloptie die op basis van uw invoer duidelijk goedkoper uitpakt.\n"
            "Typ 'nee' om terug te gaan en kies een andere bespaaroptie.",
            set()
        )

    lines.append("\nReageer met het nummer, of typ **nee** om terug te gaan.")
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
        preview_costs = _estimate(preview)
        s = saving_text_from_delta(base_costs, preview_costs, keys=VLONDER_KEYS)
        if s:
            options.append((opt, label, s))

    preview = dict(a)
    ov = _overige_clean(preview)
    preview["vlonder_type"] = None
    preview["overige_wensen"] = [x for x in ov if x != "vlonder"]
    preview_costs = _estimate(preview)
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
        f"U heeft nu gekozen voor **{_nice_vlonder(cur)}**.",
        "Kies een goedkopere optie of verwijder de vlonder:",
    ]

    for i, (opt, label, s) in enumerate(options, start=1):
        digit = str(i)
        mapping[digit] = opt
        lines.append(f"{digit}) {label} {s}")

    lines.append("\nReageer met het nummer, of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping


# =====================
# (4b) Overkapping kleiner of verwijderen
# =====================
def overkapping_choice_menu_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})
    if not a.get("overkapping"):
        return ("Overkapping is niet gekozen. Typ 'nee' om terug te gaan.", {})

    cur_m2 = float(a.get("overkapping_m2") or 15.0)

    options: List[Tuple[str, str, str]] = []

    for preset_m2, label in _OVERKAPPING_PRESETS:
        if preset_m2 >= cur_m2 - 0.5:
            continue
        preview = dict(a)
        preview["overkapping_m2"] = preset_m2
        preview_costs = _estimate(preview)
        s = saving_text_from_delta(base_costs, preview_costs, keys=EXTRA_KEYS["overkapping"])
        if s:
            options.append((str(int(preset_m2)), label, s))

    preview = dict(a)
    preview["overkapping"] = False
    preview["overkapping_m2"] = None
    preview_costs = _estimate(preview)
    s_remove = saving_text_from_delta(base_costs, preview_costs, keys=EXTRA_KEYS["overkapping"])
    if s_remove:
        options.append(("remove", "Overkapping verwijderen", s_remove))

    if not options:
        return (
            "Ik zie geen kleinere overkapping die duidelijk goedkoper uitpakt.\n"
            "Typ 'nee' om terug te gaan.",
            {}
        )

    mapping: Dict[str, str] = {}
    lines = [
        f"U heeft nu gekozen voor **Overkapping ca. {int(round(cur_m2))} m²**.",
        "Kies een kleinere maat of verwijder de overkapping:",
    ]

    for i, (action, label, s) in enumerate(options, start=1):
        mapping[str(i)] = action
        lines.append(f"{i}) {label} {s}")

    lines.append("\nReageer met het nummer, of typ **nee** om terug te gaan.")
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


    # --- Goedkopere varianten (altijd bovenaan) ---
    if stt["haag_m"] > 0 and has_haag_downgrade(a):
        cur_haag_types = {(it.get("haag_type") or "voordelig_hoog").strip().lower() for it in _haag_items(a)}
        if any(t.startswith("premium") for t in cur_haag_types):
            # premium_* → voordelig_* (zelfde hoogte)
            def preview_haag_to_voordelig() -> dict:
                p = dict(a)
                p["erfafscheiding_items"] = [
                    dict(it, haag_type=(it.get("haag_type") or "voordelig_hoog").replace("premium_", "voordelig_"))
                    if (it.get("type") or "").strip().lower() == "haag" else it
                    for it in items
                ]
                return p
            candidates.append(("haag_to_voordelig", f"Haag goedkoper: naar voordelig type (nu: {stt['haag_m']:.1f} m)", preview_haag_to_voordelig()))
        if any(t.endswith("_hoog") for t in cur_haag_types):
            # *_hoog → *_laag (zelfde type)
            def preview_haag_to_laag() -> dict:
                p = dict(a)
                p["erfafscheiding_items"] = [
                    dict(it, haag_type=(it.get("haag_type") or "voordelig_hoog").replace("_hoog", "_laag"))
                    if (it.get("type") or "").strip().lower() == "haag" else it
                    for it in items
                ]
                return p
            candidates.append(("haag_to_laag", f"Haag goedkoper: naar lagere hoogte (nu: {stt['haag_m']:.1f} m)", preview_haag_to_laag()))
    if stt["design_schutting_m"] > 0:
        def preview_design_to_beton() -> dict:
            p = dict(a)
            p["erfafscheiding_items"] = [
                dict(it, type="betonschutting") if (it.get("type") or "").strip().lower() == "design_schutting" else it
                for it in items
            ]
            return p
        candidates.append(("design_to_beton", f"Design schutting → betonschutting (nu: {stt['design_schutting_m']:.1f} m)", preview_design_to_beton()))

    # --- Verwijderopties ---
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
        preview_costs = _estimate(preview_ans)
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
    lines.append("Wat wilt u aanpassen of verwijderen? Kies één of meerdere nummers (bijv. 1, 3).")
    lines.append("Ik toon alleen opties die goedkoper uitpakken:")

    for i, (action, label, s) in enumerate(options, start=1):
        digit = str(i)
        mapping[digit] = action
        lines.append(f"{digit}) {label} {s}")

    lines.append("")
    lines.append("Kies één of meerdere nummers (bijv. 1, 3), of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping


# =====================
# (5b) Erfafscheiding — twee-laags menu (per item)
# =====================

def _preview_erf_item_modified(a: dict, items: list, item_index: int, changes: dict) -> dict:
    new_items = [dict(it, **changes) if i == item_index else it for i, it in enumerate(items)]
    p = dict(a)
    p["erfafscheiding_items"] = new_items
    return p


def _preview_erf_item_removed(a: dict, items: list, item_index: int) -> dict:
    new_items = [it for i, it in enumerate(items) if i != item_index]
    p = dict(a)
    p["erfafscheiding_items"] = new_items
    if not new_items:
        ov = _overige_clean(p)
        p["overige_wensen"] = [x for x in ov if x != "erfafscheiding"]
    return p


def erf_item_select_menu_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    """Laag 1: elk erfafscheiding-item afzonderlijk, gegroepeerd per type, met suffix bij meerdere."""
    a = dict(ans or {})
    items = list(a.get("erfafscheiding_items") or [])
    if not items:
        return "Ik zie geen erfafscheiding-items om aan te passen. Typ 'nee' om terug te gaan.", {}

    type_counts: Dict[str, int] = {}
    for it in items:
        t = (it.get("type") or "").strip().lower()
        type_counts[t] = type_counts.get(t, 0) + 1

    # Sorteer op type: haag → betonschutting → design_schutting
    _TYPE_ORDER = {"haag": 0, "betonschutting": 1, "design_schutting": 2}
    sorted_indices = sorted(range(len(items)),
                            key=lambda i: _TYPE_ORDER.get((items[i].get("type") or "").strip().lower(), 99))

    type_seen: Dict[str, int] = {}
    mapping: Dict[str, str] = {}
    lines = ["Welk onderdeel van de erfafscheiding wilt u aanpassen?"]

    for i in sorted_indices:
        it = items[i]
        t = (it.get("type") or "").strip().lower()
        m = float(it.get("meter") or 0)
        type_seen[t] = type_seen.get(t, 0) + 1
        suffix = f" {type_seen[t]}" if type_counts[t] > 1 else ""

        if t == "haag":
            haag_type = (it.get("haag_type") or "voordelig_hoog").strip().lower()
            haag_lbl = {
                "voordelig_laag": "voordelig laag", "voordelig_hoog": "voordelig hoog",
                "premium_laag": "premium laag", "premium_hoog": "premium hoog",
            }.get(haag_type, haag_type)
            label = f"Haag{suffix} – {haag_lbl} ({int(m)} m)"
        elif t == "betonschutting":
            poort = ", met poortdeur" if it.get("poortdeur") else ""
            label = f"Betonschutting{suffix} ({int(m)} m{poort})"
        elif t == "design_schutting":
            poort = ", met poortdeur" if it.get("poortdeur") else ""
            label = f"Design schutting{suffix} ({int(m)} m{poort})"
        else:
            continue

        digit = str(len(mapping) + 1)
        mapping[digit] = str(i)
        lines.append(f"{digit}) {label}")

    if not mapping:
        return "Ik zie geen erfafscheiding-items om aan te passen. Typ 'nee' om terug te gaan.", {}

    lines.append("\nReageer met het nummer, of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping


def erf_haag_menu_text(ans: dict, base_costs: dict, item_index: int) -> Tuple[str, Dict[str, str]]:
    """Laag 2: acties voor een specifiek haag-item."""
    a = dict(ans or {})
    items = list(a.get("erfafscheiding_items") or [])
    if item_index >= len(items):
        return "Item niet gevonden. Typ 'nee' om terug te gaan.", {}

    it = items[item_index]
    t = (it.get("type") or "").strip().lower()
    if t != "haag":
        return "Dit is geen haag-item. Typ 'nee' om terug te gaan.", {}

    m = float(it.get("meter") or 0)
    haag_type = (it.get("haag_type") or "voordelig_hoog").strip().lower()
    haag_rank = _HAAG_ORDER.get(haag_type, 2)

    haag_indices = [i for i, item in enumerate(items) if (item.get("type") or "").strip().lower() == "haag"]
    haag_num = haag_indices.index(item_index) + 1
    suffix = f" {haag_num}" if len(haag_indices) > 1 else ""

    _HAAG_LABELS = {
        "voordelig_laag": "voordelig laag (0,5–1m)",
        "voordelig_hoog": "voordelig hoog (1,5–2m)",
        "premium_laag":   "premium laag (0,5–1m)",
        "premium_hoog":   "premium hoog (1,5–2m)",
    }

    # Bouw goedkopere opties op basis van rank
    cheaper_types = [
        ("voordelig_laag", "Naar voordelig laag (0,5–1m)"),
        ("voordelig_hoog", "Naar voordelig hoog (1,5–2m)"),
        ("premium_laag",   "Naar premium laag (0,5–1m)"),
    ]

    candidates: List[Tuple[str, str, dict]] = []
    for new_type, label in cheaper_types:
        if _HAAG_ORDER.get(new_type, 99) < haag_rank:
            candidates.append((f"set_{new_type}", label,
                               _preview_erf_item_modified(a, items, item_index, {"haag_type": new_type})))
    candidates.append(("rm_item", f"Haag{suffix} verwijderen ({int(m)} m)",
                       _preview_erf_item_removed(a, items, item_index)))

    options: List[Tuple[str, str, str]] = []
    for action, label, preview_ans in candidates:
        s = saving_text_from_delta(base_costs, _estimate(preview_ans), keys=ERF_KEYS)
        if s:
            options.append((action, label, s))

    if not options:
        return (f"Ik zie geen aanpassing voor Haag{suffix} die duidelijk goedkoper uitpakt.\n"
                "Typ 'nee' om terug te gaan.", {})

    mapping: Dict[str, str] = {}
    lines = [f"U heeft nu gekozen voor **Haag{suffix} {_HAAG_LABELS.get(haag_type, haag_type)}, {int(m)} m**.", "Kies een goedkopere optie of verwijder:"]
    for i, (action, label, s) in enumerate(options, start=1):
        mapping[str(i)] = action
        lines.append(f"{i}) {label} {s}")
    lines.append("\nReageer met het nummer, of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping


def erf_schutting_menu_text(ans: dict, base_costs: dict, item_index: int) -> Tuple[str, Dict[str, str]]:
    """Laag 2: acties voor een specifiek schutting-item."""
    a = dict(ans or {})
    items = list(a.get("erfafscheiding_items") or [])
    if item_index >= len(items):
        return "Item niet gevonden. Typ 'nee' om terug te gaan.", {}

    it = items[item_index]
    t = (it.get("type") or "").strip().lower()
    if t not in ("betonschutting", "design_schutting"):
        return "Dit is geen schutting-item. Typ 'nee' om terug te gaan.", {}

    m = float(it.get("meter") or 0)
    has_poortdeur = it.get("poortdeur") is True
    type_label = "Betonschutting" if t == "betonschutting" else "Design schutting"

    same_indices = [i for i, item in enumerate(items) if (item.get("type") or "").strip().lower() == t]
    item_num = same_indices.index(item_index) + 1
    suffix = f" {item_num}" if len(same_indices) > 1 else ""

    candidates: List[Tuple[str, str, dict]] = []
    if t == "design_schutting":
        candidates.append(("design_to_beton", f"Design schutting{suffix} → betonschutting ({int(m)} m)",
                           _preview_erf_item_modified(a, items, item_index, {"type": "betonschutting"})))
    if has_poortdeur:
        candidates.append(("rm_poortdeur", "Poortdeur laten vervallen",
                           _preview_erf_item_modified(a, items, item_index, {"poortdeur": False})))
    candidates.append(("rm_item", f"{type_label}{suffix} verwijderen ({int(m)} m)",
                       _preview_erf_item_removed(a, items, item_index)))

    options: List[Tuple[str, str, str]] = []
    for action, label, preview_ans in candidates:
        s = saving_text_from_delta(base_costs, _estimate(preview_ans), keys=ERF_KEYS)
        if s:
            options.append((action, label, s))

    if not options:
        return (f"Ik zie geen aanpassing voor {type_label.lower()}{suffix} die duidelijk goedkoper uitpakt.\n"
                "Typ 'nee' om terug te gaan.", {})

    poort_lbl = " (met poortdeur)" if has_poortdeur else ""
    mapping: Dict[str, str] = {}
    lines = [f"U heeft nu gekozen voor **{type_label}{suffix}, {int(m)} m{poort_lbl}**.", "Kies een goedkopere optie of verwijder:"]
    for i, (action, label, s) in enumerate(options, start=1):
        mapping[str(i)] = action
        lines.append(f"{i}) {label} {s}")
    lines.append("\nReageer met het nummer, of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping


def apply_erf_item_haag_change(answers: dict, item_index: int, action: str) -> Tuple[dict, str]:
    a = dict(answers or {})
    items = list(a.get("erfafscheiding_items") or [])
    if item_index >= len(items):
        return a, "Item niet gevonden (geen wijziging)."

    haag_indices = [i for i, it in enumerate(items) if (it.get("type") or "").strip().lower() == "haag"]
    haag_num = haag_indices.index(item_index) + 1 if item_index in haag_indices else 1
    suffix = f" {haag_num}" if len(haag_indices) > 1 else ""

    # Acties van de vorm "set_voordelig_laag", "set_premium_laag" etc.
    if action.startswith("set_"):
        new_type = action[4:]  # strip "set_"
        _HAAG_LABELS = {
            "voordelig_laag": "voordelig laag (0,5–1m)",
            "voordelig_hoog": "voordelig hoog (1,5–2m)",
            "premium_laag":   "premium laag (0,5–1m)",
            "premium_hoog":   "premium hoog (1,5–2m)",
        }
        if new_type in _HAAG_LABELS:
            a["erfafscheiding_items"] = [dict(it, haag_type=new_type) if i == item_index else it for i, it in enumerate(items)]
            return a, _explain_saving(f"Haag{suffix} aangepast naar {_HAAG_LABELS[new_type]} (goedkoper)")

    if action == "rm_item":
        new_items = [it for i, it in enumerate(items) if i != item_index]
        a["erfafscheiding_items"] = new_items
        if not new_items:
            ov = _overige_clean(a)
            a["overige_wensen"] = [x for x in ov if x != "erfafscheiding"]
        return a, _explain_saving(f"Haag{suffix} verwijderd")

    return a, "Onbekende actie (geen wijziging)."


def apply_erf_item_schutting_change(answers: dict, item_index: int, action: str) -> Tuple[dict, str]:
    a = dict(answers or {})
    items = list(a.get("erfafscheiding_items") or [])
    if item_index >= len(items):
        return a, "Item niet gevonden (geen wijziging)."

    it = items[item_index]
    t = (it.get("type") or "").strip().lower()
    type_label = "Betonschutting" if t == "betonschutting" else "Design schutting"
    same_indices = [i for i, item in enumerate(items) if (item.get("type") or "").strip().lower() == t]
    item_num = same_indices.index(item_index) + 1 if item_index in same_indices else 1
    suffix = f" {item_num}" if len(same_indices) > 1 else ""

    if action == "design_to_beton":
        a["erfafscheiding_items"] = [dict(it, type="betonschutting") if i == item_index else it for i, it in enumerate(items)]
        return a, _explain_saving(f"Design schutting{suffix} aangepast naar betonschutting (goedkoper)")

    if action == "rm_poortdeur":
        a["erfafscheiding_items"] = [dict(it, poortdeur=False) if i == item_index else it for i, it in enumerate(items)]
        return a, _explain_saving(f"Poortdeur bij {type_label.lower()}{suffix} laten vervallen")

    if action == "rm_item":
        new_items = [it for i, it in enumerate(items) if i != item_index]
        a["erfafscheiding_items"] = new_items
        if not new_items:
            ov = _overige_clean(a)
            a["overige_wensen"] = [x for x in ov if x != "erfafscheiding"]
        return a, _explain_saving(f"{type_label}{suffix} verwijderd")

    return a, "Onbekende actie (geen wijziging)."


# =====================
# Apply changes (✅ consistent "doorgevoerde kostenbesparing")
# =====================
def apply_set_ratio(answers: dict, ratio_code: str) -> Tuple[dict, str]:
    a = dict(answers or {})
    a["verhouding_bestrating_groen"] = ratio_code
    tuin_m2 = float(a.get("tuin_m2") or 0)
    share_map = {"70_30": 0.70, "50_50": 0.50, "30_70": 0.30}
    paving_share = share_map.get(ratio_code)
    if paving_share is not None and tuin_m2 > 0:
        p = round(tuin_m2 * paving_share)
        g = round(tuin_m2 * (1.0 - paving_share))
        pretty = f"ca. {p} m² bestrating + {g} m² groen"
    else:
        pretty = {"50_50": "50/50", "30_70": "30/70", "70_30": "70/30"}.get(ratio_code, ratio_code)
    return a, _explain_saving(f"verhouding bestrating/groen aangepast naar {pretty}")


def apply_ratio_proportional(answers: dict, ratio_code: str) -> Tuple[dict, str]:
    """
    Past de paving/groen verhouding toe door alle items proportioneel te schalen.
    Materiaalkeuzes per item blijven behouden.
    Werkt alleen wanneer _direct_*_m2 markers aanwezig zijn (V2 flow).
    """
    a = dict(answers or {})
    tuin_m2 = float(a.get("tuin_m2") or 0)
    if tuin_m2 <= 0:
        return a, "Geen tuinoppervlak ingesteld."

    share_map = {"70_30": 0.70, "50_50": 0.50, "30_70": 0.30}
    paving_share = share_map.get(ratio_code, 0.50)
    target_paving_m2 = tuin_m2 * paving_share
    current_paving_m2 = _current_paving_m2(a)
    if current_paving_m2 <= 0.01:
        return a, "Geen bestrating geconfigureerd."

    factor = target_paving_m2 / current_paving_m2

    # Schaal _direct_*_m2 waarden
    for key in ("_direct_oprit_m2", "_direct_terras_m2", "_direct_paden_m2"):
        v = float(a.get(key) or 0)
        if v > 0:
            a[key] = round(v * factor, 1)

    # Schaal extra items (materiaal blijft behouden)
    if a.get("terras_extra_items"):
        a["terras_extra_items"] = [
            dict(it, m2=round(float(it.get("m2") or 0) * factor, 1))
            for it in a["terras_extra_items"]
        ]
    if a.get("paden_extra_items"):
        a["paden_extra_items"] = [
            dict(it, m2=round(float(it.get("m2") or 0) * factor, 1))
            for it in a["paden_extra_items"]
        ]

    # Update bestrating_pct en verhouding
    a["verhouding_bestrating_groen"] = "custom"
    a["bestrating_pct"] = int(round(paving_share * 100))

    # Herbereken pct-verdeling binnen bestrating
    oprit_new = float(a.get("_direct_oprit_m2") or 0)
    paden_new = float(a.get("_direct_paden_m2") or 0) + sum(
        float(it.get("m2") or 0) for it in (a.get("paden_extra_items") or [])
    )
    terras_new = float(a.get("_direct_terras_m2") or 0) + sum(
        float(it.get("m2") or 0) for it in (a.get("terras_extra_items") or [])
    )
    total_new = oprit_new + paden_new + terras_new
    if total_new > 0:
        a["oprit_pct"] = int(round(oprit_new / total_new * 100))
        a["paden_pct"] = int(round(paden_new / total_new * 100))
        a["terras_pct"] = max(0, 100 - a["oprit_pct"] - a["paden_pct"])

    # Update gazon/beplanting display-markers
    new_green_m2 = tuin_m2 - target_paving_m2
    gazon_pct_raw = a.get("gazon_pct")
    gazon_share = float(gazon_pct_raw) / 100.0 if gazon_pct_raw is not None else 0.5
    a["_direct_gazon_m2"] = round(new_green_m2 * gazon_share, 1)
    a["_direct_beplanting_m2"] = round(new_green_m2 * (1.0 - gazon_share), 1)

    pretty_p = int(round(target_paving_m2))
    pretty_g = int(round(tuin_m2 - target_paving_m2))
    return a, _explain_saving(
        f"verhouding bestrating/groen proportioneel aangepast naar "
        f"ca. {pretty_p} m² bestrating + {pretty_g} m² groen"
    )


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
        a["beregening_systeem"] = None
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

    # Legacy mapping voor backwards compat
    _legacy = {"1": "oprit", "2": "paden_0", "3": "terras_0"}
    item_specs = [_legacy.get(p, p) for p in parts]

    new_rank = _material_rank(mat)
    changed_targets: List[str] = []

    for spec in item_specs:
        cur_mat = _get_item_material(a, spec)
        if new_rank >= _material_rank(cur_mat):
            continue
        a = _set_item_material(a, spec, mat)
        changed_targets.append(_item_spec_label(spec))

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


def voegen_choice_menu_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})
    if not a.get("onkruidwerend_gevoegd"):
        return ("Voegen is niet gekozen. Typ 'nee' om terug te gaan.", {})
    preview = dict(a)
    preview["onkruidwerend_gevoegd"] = False
    s = saving_text_from_delta(base_costs, _estimate(preview), keys=EXTRA_KEYS["voegen"])
    mapping: Dict[str, str] = {"1": "remove"}
    lines = [
        "U heeft nu gekozen voor **Bestrating gevoegd (onkruidwerend)**.",
        "1) Voegen weglaten" + (f" {s}" if s else ""),
        "",
        "Reageer met 1, of typ **nee** om terug te gaan.",
    ]
    return "\n".join(lines), mapping


def verlichting_choice_menu_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    a = dict(ans or {})
    if not a.get("verlichting"):
        return ("Tuinverlichting is niet gekozen. Typ 'nee' om terug te gaan.", {})
    preview = dict(a)
    preview["verlichting"] = False
    s = saving_text_from_delta(base_costs, _estimate(preview), keys=EXTRA_KEYS["verlichting"])
    mapping: Dict[str, str] = {"1": "remove"}
    lines = [
        "U heeft nu gekozen voor **Tuinverlichting (basis)**.",
        "1) Tuinverlichting weglaten" + (f" {s}" if s else ""),
        "",
        "Reageer met 1, of typ **nee** om terug te gaan.",
    ]
    return "\n".join(lines), mapping


def apply_voegen_change(answers: dict) -> Tuple[dict, str]:
    a = dict(answers or {})
    a["onkruidwerend_gevoegd"] = False
    return a, _explain_saving("voegen verwijderd")


def apply_verlichting_change(answers: dict) -> Tuple[dict, str]:
    a = dict(answers or {})
    a["verlichting"] = False
    return a, _explain_saving("tuinverlichting verwijderd")


def apply_beregening_remove(answers: dict) -> Tuple[dict, str]:
    a = dict(answers or {})
    overige = _overige_clean(a)
    a["beregening_scope"] = None
    a["beregening_systeem"] = None
    a["overige_wensen"] = [x for x in overige if x != "beregening"]
    return a, _explain_saving("beregening verwijderd")


def apply_overkapping_change(answers: dict, action: str) -> Tuple[dict, str]:
    a = dict(answers or {})
    if not a.get("overkapping"):
        return a, "Overkapping stond niet in uw keuzes."

    if action == "remove":
        a["overkapping"] = False
        a["overkapping_m2"] = None
        return a, _explain_saving("overkapping verwijderd")

    try:
        new_m2 = float(action)
    except ValueError:
        return a, "Ongeldige keuze (geen wijziging)."

    cur_m2 = float(a.get("overkapping_m2") or 15.0)
    if new_m2 >= cur_m2 - 0.5:
        return a, "Dit is niet kleiner dan uw huidige overkapping (geen wijziging)."

    a["overkapping_m2"] = new_m2
    _size_labels = {9.0: "knus (9 m²)", 15.0: "standaard (15 m²)"}
    label = _size_labels.get(new_m2, f"{int(new_m2)} m²")
    return a, _explain_saving(f"overkapping verkleind naar {label}")


def apply_erf_changes(answers: dict, selected_actions: List[str]) -> Tuple[dict, str]:
    a = dict(answers or {})
    items = list(a.get("erfafscheiding_items") or [])

    if not items:
        ov = _overige_clean(a)
        a["overige_wensen"] = [x for x in ov if x != "erfafscheiding"]
        return a, "Erfafscheiding stond niet (meer) ingesteld."

    remove_types = set()
    remove_poorten = False
    design_to_beton = False

    for act in selected_actions:
        if act == "rm_haag":
            remove_types.add("haag")
        elif act == "rm_beton":
            remove_types.add("betonschutting")
        elif act == "rm_design":
            remove_types.add("design_schutting")
        elif act == "rm_poorten":
            remove_poorten = True
        elif act == "haag_to_voordelig":
            # premium_* → voordelig_* (zelfde hoogte)
            items = [
                dict(it, haag_type=(it.get("haag_type") or "voordelig_hoog").replace("premium_", "voordelig_"))
                if (it.get("type") or "").strip().lower() == "haag" else it
                for it in items
            ]
        elif act == "haag_to_laag":
            # *_hoog → *_laag (zelfde type)
            items = [
                dict(it, haag_type=(it.get("haag_type") or "voordelig_hoog").replace("_hoog", "_laag"))
                if (it.get("type") or "").strip().lower() == "haag" else it
                for it in items
            ]
        elif act == "design_to_beton":
            design_to_beton = True

    if design_to_beton:
        items = [
            dict(it, type="betonschutting") if (it.get("type") or "").strip().lower() == "design_schutting" else it
            for it in items
        ]

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

    if "haag_to_voordelig" in selected_actions:
        msgs.append("haag aangepast naar voordelig type (goedkoper)")
    if "haag_to_laag" in selected_actions:
        msgs.append("haag aangepast naar lagere hoogte (goedkoper)")
    if design_to_beton:
        msgs.append("design schutting aangepast naar betonschutting (goedkoper)")
    if remove_types:
        msgs.append("verwijderd: " + ", ".join(pretty.get(t, t) for t in sorted(remove_types)))
    if remove_poorten:
        msgs.append("poortdeur(en) laten vervallen")

    if not msgs:
        return a, "Geen geldige keuze (geen wijziging)."

    return a, _explain_saving(" • ".join(msgs))


# =====================
# Losse onderdelen: besparingsmenu + component verwijderen
# =====================

def _saving_text_total(base_costs: dict, preview_costs: dict) -> str:
    """Besparing op basis van totaal verschil (voor component-verwijdering)."""
    bt = _total_range(base_costs)
    pt = _total_range(preview_costs)
    if not bt or not pt:
        return ""
    save_min = max(0, bt[0] - pt[0])
    save_max = max(0, bt[1] - pt[1])
    if save_max <= 0:
        return ""
    return f"(besparing: −{_eur(save_min)} tot −{_eur(save_max)})"


def _remove_losse_component(ans: dict, comp_key: str) -> Optional[dict]:
    """Geeft een preview-answers dict terug met het onderdeel verwijderd."""
    a = dict(ans)
    overige = _overige_clean(a)

    if comp_key in ("oprit_m2", "paden_m2", "terras_m2", "gazon_m2", "beplanting_m2"):
        a[comp_key] = 0.0
        comp = comp_key.replace("_m2", "")
        mat_key = "materiaal_" + comp
        if mat_key in a:
            a[mat_key] = None
        items_key = comp + "_items"
        if items_key in a:
            a[items_key] = []
        # Recalculate voegen_m2_custom and onkruidwerend_gevoegd after clearing items
        if "voegen_m2_custom" in a:
            voegen_total = sum(
                float(it.get("m2", 0))
                for c in ("paden", "terras")
                for it in (a.get(c + "_items") or [])
                if it.get("gevoegd", False)
            )
            a["voegen_m2_custom"] = voegen_total
            a["onkruidwerend_gevoegd"] = voegen_total > 0
        return a
    if comp_key == "erfafscheiding":
        a["erfafscheiding_items"] = []
        a["overige_wensen"] = [x for x in overige if x != "erfafscheiding"]
        return a
    if comp_key == "vlonder":
        a["vlonder_type"] = None
        a["overige_wensen"] = [x for x in overige if x != "vlonder"]
        return a
    if comp_key == "beregening":
        a["beregening_scope"] = None
        a["beregening_systeem"] = None
        a["overige_wensen"] = [x for x in overige if x != "beregening"]
        return a
    if comp_key == "overkapping":
        a["overkapping"] = False
        a["overkapping_m2"] = None
        return a
    if comp_key == "verlichting":
        a["verlichting"] = False
        return a
    return None


_COMP_LABELS = {
    "oprit_m2": "Oprit", "paden_m2": "Paden", "terras_m2": "Terras",
    "gazon_m2": "Gazon", "beplanting_m2": "Beplanting",
    "erfafscheiding": "Erfafscheiding", "vlonder": "Vlonder",
    "beregening": "Beregening", "overkapping": "Overkapping", "verlichting": "Verlichting",
}


def losse_component_remove_menu_text(ans: dict, base_costs: dict) -> Tuple[str, Dict[str, str]]:
    """
    Toont welke onderdelen verwijderd kunnen worden met bijbehorende besparing.
    Retourneert (tekst, mapping digit→comp_key).
    """
    a = dict(ans or {})
    overige = _overige_clean(a)

    candidates: List[str] = []
    for k in ("oprit_m2", "paden_m2", "terras_m2", "gazon_m2", "beplanting_m2"):
        if float(a.get(k) or 0) > 0:
            candidates.append(k)
    if "erfafscheiding" in overige and (a.get("erfafscheiding_items") or []):
        candidates.append("erfafscheiding")
    if "vlonder" in overige:
        candidates.append("vlonder")
    if "beregening" in overige:
        candidates.append("beregening")
    if a.get("overkapping"):
        candidates.append("overkapping")
    if a.get("verlichting"):
        candidates.append("verlichting")

    if not candidates:
        return "Ik zie geen onderdelen om te verwijderen. Typ 'nee' om terug te gaan.", {}

    options: List[Tuple[str, str, str]] = []
    for comp_key in candidates:
        preview = _remove_losse_component(a, comp_key)
        if preview is None:
            continue
        preview_costs = _estimate(preview)
        s = _saving_text_total(base_costs, preview_costs)
        if s:
            options.append((comp_key, _COMP_LABELS.get(comp_key, comp_key), s))

    if not options:
        return (
            "Ik zie geen onderdeel dat duidelijk goedkoper uitpakt om te verwijderen.\n"
            "Typ 'nee' om terug te gaan.",
            {},
        )

    mapping: Dict[str, str] = {}
    lines = [
        "Welk onderdeel wilt u verwijderen?",
        "Ik toon de besparing per onderdeel:",
    ]
    for i, (comp_key, label, s) in enumerate(options, start=1):
        digit = str(i)
        mapping[digit] = comp_key
        lines.append(f"{digit}) {label} {s}")
    lines.append("\nReageer met het nummer, of typ **nee** om terug te gaan.")
    return "\n".join(lines), mapping


def apply_remove_losse_component(answers: dict, comp_key: str) -> Tuple[dict, str]:
    a = dict(answers or {})
    result = _remove_losse_component(a, comp_key)
    if result is None:
        return a, "Onbekend onderdeel (geen wijziging)."
    label = _COMP_LABELS.get(comp_key, comp_key).lower()
    return result, _explain_saving(f"{label} verwijderd")


def _remove_losse_item(a: dict, comp_base: str, index: int) -> Optional[dict]:
    """Verwijder één bestrating-item uit de items-lijst op basis van index."""
    result = dict(a)
    items_key = f"{comp_base}_items"
    m2_key = f"{comp_base}_m2"
    mat_key = f"materiaal_{comp_base}"
    items = list(result.get(items_key) or [])
    if index >= len(items):
        return None
    items = [it for i, it in enumerate(items) if i != index]
    result[items_key] = items
    result[m2_key] = sum(float(it.get("m2", 0)) for it in items)
    result[mat_key] = items[0].get("materiaal", "beton") if items else None
    if comp_base in ("paden", "terras") and "voegen_m2_custom" in a:
        voegen_total = sum(
            float(it.get("m2", 0))
            for c in ("paden", "terras")
            for it in (result.get(c + "_items") or [])
            if it.get("gevoegd", False)
        )
        result["voegen_m2_custom"] = voegen_total
        result["onkruidwerend_gevoegd"] = voegen_total > 0
    return result


def apply_remove_losse_item(answers: dict, comp_base: str, index: int) -> Tuple[dict, str]:
    a = dict(answers or {})
    result = _remove_losse_item(a, comp_base, index)
    if result is None:
        return a, "Item niet gevonden (geen wijziging)."
    items_key = f"{comp_base}_items"
    was_multi = len(a.get(items_key) or []) > 1
    label = {"oprit": "oprit", "paden": "paden", "terras": "terras"}.get(comp_base, comp_base)
    num_suffix = f" {index + 1}" if was_multi else ""
    return result, _explain_saving(f"{label}{num_suffix} verwijderd")


def _has_improvable_materials(a: dict) -> bool:
    comp_map = [("oprit", "materiaal_oprit"), ("paden", "materiaal_paden"), ("terras", "materiaal_terras")]
    return any(_has_bestrating(a, comp) and _material_rank(a.get(mat_key)) > 1 for comp, mat_key in comp_map)



def lower_costs_menu_losse_text(ans: dict, base_costs: dict | None = None) -> Tuple[str, Dict[str, str]]:
    """
    Besparingsmenu voor losse-onderdelen flow — volledig plat.
    Retourneert (tekst, mapping digit→actie).
    """
    a = ans or {}
    _costs = base_costs or _estimate(a)
    overige = _overige_clean(a)
    mapping: Dict[str, str] = {}
    lines = ["Waar wilt u op besparen?"]
    idx = 1

    if _has_improvable_materials(a):
        mapping[str(idx)] = "material"
        lines.append(f"{idx}) Bestratingsmateriaal goedkoper kiezen")
        idx += 1

    if "beregening" in overige:
        mapping[str(idx)] = "beregening"
        lines.append(f"{idx}) Beregening aanpassen")
        idx += 1

    _MAT_SHORT = {"grind": "Grind", "beton": "Beton", "gebakken": "Gebakken", "keramiek": "Keramiek"}
    for comp_base, comp_key, label in (
        ("oprit",  "oprit_m2",  "Oprit"),
        ("paden",  "paden_m2",  "Paden"),
        ("terras", "terras_m2", "Terras"),
    ):
        items_list = a.get(f"{comp_base}_items") or []
        if len(items_list) > 1:
            for i, item in enumerate(items_list):
                m2 = float(item.get("m2") or 0)
                if m2 <= 0:
                    continue
                mat_lbl = _MAT_SHORT.get((item.get("materiaal") or "beton").strip().lower(), "Beton")
                preview = _remove_losse_item(a, comp_base, i)
                s = _saving_text_total(_costs, _estimate(preview)) if preview else ""
                mapping[str(idx)] = f"{comp_base}_item_{i}"
                lines.append(f"{idx}) {label} {i + 1} – {mat_lbl} {int(m2)} m² verwijderen" + (f" {s}" if s else ""))
                idx += 1
        elif float(a.get(comp_key) or 0) > 0 or items_list:
            preview = _remove_losse_component(a, comp_key)
            if preview:
                s = _saving_text_total(_costs, _estimate(preview))
                mapping[str(idx)] = comp_key
                lines.append(f"{idx}) {label} verwijderen" + (f" {s}" if s else ""))
                idx += 1

    for comp_key in ("gazon_m2", "beplanting_m2"):
        if float(a.get(comp_key) or 0) > 0:
            preview = _remove_losse_component(a, comp_key)
            if preview:
                s = _saving_text_total(_costs, _estimate(preview))
                label = _COMP_LABELS.get(comp_key, comp_key)
                mapping[str(idx)] = comp_key
                lines.append(f"{idx}) {label} verwijderen" + (f" {s}" if s else ""))
                idx += 1

    if "erfafscheiding" in overige and (a.get("erfafscheiding_items") or []):
        mapping[str(idx)] = "erfafscheiding"
        lines.append(f"{idx}) Erfafscheiding aanpassen")
        idx += 1

    if "vlonder" in overige:
        mapping[str(idx)] = "vlonder"
        lines.append(f"{idx}) Vlonder aanpassen")
        idx += 1

    if a.get("overkapping"):
        mapping[str(idx)] = "overkapping"
        lines.append(f"{idx}) Overkapping aanpassen")
        idx += 1

    if a.get("verlichting"):
        mapping[str(idx)] = "verlichting"
        lines.append(f"{idx}) Tuinverlichting aanpassen")
        idx += 1

    if not mapping:
        return "Er zijn geen verdere besparingsopties beschikbaar. Typ 'nee' om terug te gaan.", {}

    lines += [
        "",
        "U kunt hier later terugkomen om opnieuw een bespaaroptie te kiezen.",
        "\nReageer met het nummer, of typ **nee** om terug te gaan.",
    ]
    return "\n".join(lines), mapping
