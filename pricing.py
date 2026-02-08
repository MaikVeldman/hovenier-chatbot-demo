# pricing.py
from __future__ import annotations

from typing import Dict, Tuple, List, Any


# ✅ Single source of truth: prijzen staan alleen hier
PRIJZEN: Dict[str, Tuple[int, int]] = {
    "onderhoud_aanleg_uurtarief": (65, 75),                             # €/uur
    "voorjaar_najaarsbeurt": (290, 580),                                # € totaal
    "gazon_maaien": (75, 200),                                          # € per keer
    "haag_snoeien": (75, 350),                                          # € per keer

    "bestrating_verwijderen_per_m3": (95, 150),                         # €/m³
    "bestrating_afvoer_per_m3": (95, 150),                              # €/m³
    "bouw_sloop_afval_afvoer_per_m3": (95, 150),                        # €/m³

    "grond_afvoer_per_m3": (95, 150),                                   # €/m³
    "zand_aanvoer_per_m3": (95, 150),                                   # €/m³
    "puin_aanvoer_per_m3": (95, 150),                                   # €/m³

    "keramisch_straatwerk_per_m2": (180, 220),                          # €/m²
    "beton_gebakken_straatwerk_per_m2": (60, 120),                      # €/m²
    "grind_per_m2": (60, 120),                                          # €/m²
    "plaatsen_betonband_per_m1": (14, 28),                              # €/m¹
    "zaagwerk_per_m1": (35, 65),                                        # €/m¹
    "voegen_straatwerk_per_m2": (15, 20),                               # €/m²

    "vlonder_zachthout_per_m2": (200, 250),                             # €/m²
    "vlonder_hardhout_per_m2": (250, 300),                              # €/m²
    "vlonder_composiet_per_m2": (280, 350),                             # €/m²

    "graszoden_per_m2": (15, 25),                                       # €/m²
    "beplanting_border_per_m2": (30, 40),                               # €/m²
    "beplanting_haag_per_m1": (45, 200),                                # €/m¹
    "beplanting_boom_per_stuk": (220, 600),

    "overkapping_basis_per_stuk": (10000, 15000),                       # €/stuk
    "verlichting_basis_per_stuk": (1000, 1500),                         # €/stuk

    "beregening_basis_per_m2": (20, 40),                                # €/m²

    "plaatsen_betonschutting_per_m1": (150, 250),                       # €/m¹
    "plaatsen_poortdeur_per_st": (750, 1000),                           # €/stuk
    "plaatsen_designschutting_per_m1": (300, 400),                      # €/m¹

    "3d_tuinontwerp_<100m2": (500, 750),                                # €/stuk
    "3d_tuinontwerp_100-500m2": (750, 1250),                            # €/stuk
    "3d_tuinontwerp_500-1000m2": (1250, 1750),                          # €/stuk
    "3d_tuinontwerp_>1000m2": (1750, 3000),                             # €/stuk
}

PRICE_KEYS: List[str] = sorted(PRIJZEN.keys())

PRICE_META: Dict[str, Dict[str, str]] = {
    "onderhoud_aanleg_uurtarief": {"unit": "€/uur", "label": "Uurtarief onderhoud/aanleg"},
    "voorjaar_najaarsbeurt": {"unit": "€ totaal", "label": "Voorjaars-/najaarsbeurt"},
    "gazon_maaien": {"unit": "€ per keer", "label": "Gazon maaien"},
    "haag_snoeien": {"unit": "€ per keer", "label": "Haag snoeien"},

    "bestrating_verwijderen_per_m3": {"unit": "€/m³", "label": "Bestrating verwijderen"},
    "bestrating_afvoer_per_m3": {"unit": "€/m³", "label": "Bestrating afvoer"},
    "bouw_sloop_afval_afvoer_per_m3": {"unit": "€/m³", "label": "Bouw-/sloopafval afvoer"},

    "grond_afvoer_per_m3": {"unit": "€/m³", "label": "Grond afvoer"},
    "zand_aanvoer_per_m3": {"unit": "€/m³", "label": "Zand aanvoer"},
    "puin_aanvoer_per_m3": {"unit": "€/m³", "label": "Puin aanvoer"},

    "keramisch_straatwerk_per_m2": {"unit": "€/m²", "label": "Keramisch straatwerk"},
    "beton_gebakken_straatwerk_per_m2": {"unit": "€/m²", "label": "Beton/gebakken straatwerk"},
    "grind_per_m2": {"unit": "€/m²", "label": "Grind"},

    "plaatsen_betonband_per_m1": {"unit": "€/m¹", "label": "Betonband plaatsen"},
    "zaagwerk_per_m1": {"unit": "€/m¹", "label": "Zaagwerk"},
    "voegen_straatwerk_per_m2": {"unit": "€/m²", "label": "Voegen straatwerk"},

    "vlonder_zachthout_per_m2": {"unit": "€/m²", "label": "Vlonder (zachthout)"},
    "vlonder_hardhout_per_m2": {"unit": "€/m²", "label": "Vlonder (hardhout)"},
    "vlonder_composiet_per_m2": {"unit": "€/m²", "label": "Vlonder (composiet)"},

    "graszoden_per_m2": {"unit": "€/m²", "label": "Graszoden"},
    "beplanting_border_per_m2": {"unit": "€/m²", "label": "Beplanting border"},
    "beplanting_haag_per_m1": {"unit": "€/m¹", "label": "Haagbeplanting"},
    "beplanting_boom_per_stuk": {"unit": "€/stuk", "label": "Boom (incl. aanplant)"},

    "overkapping_basis_per_stuk": {"unit": "€/stuk", "label": "Overkapping (basis)"},
    "verlichting_basis_per_stuk": {"unit": "€/stuk", "label": "Verlichting (basis 3 armaturen)"},
    "beregening_basis_per_m2": {"unit": "€/m²", "label": "Beregening (basis)"},

    "plaatsen_betonschutting_per_m1": {"unit": "€/m¹", "label": "Betonschutting plaatsen"},
    "plaatsen_poortdeur_per_st": {"unit": "€/stuk", "label": "Poortdeur plaatsen"},
    "plaatsen_designschutting_per_m1": {"unit": "€/m¹", "label": "Design schutting plaatsen"},

    "3d_tuinontwerp_<100m2": {"unit": "€/stuk", "label": "3D tuinontwerp (<100 m²)"},
    "3d_tuinontwerp_100-500m2": {"unit": "€/stuk", "label": "3D tuinontwerp (100–500 m²)"},
    "3d_tuinontwerp_500-1000m2": {"unit": "€/stuk", "label": "3D tuinontwerp (500–1000 m²)"},
    "3d_tuinontwerp_>1000m2": {"unit": "€/stuk", "label": "3D tuinontwerp (>1000 m²)"},
}


def get_price_range(price_key: str) -> Tuple[int, int]:
    if price_key not in PRIJZEN:
        raise KeyError(f"Onbekende price_key: {price_key}")
    return PRIJZEN[price_key]


def get_price_quote(price_keys: List[str]) -> Dict[str, Dict[str, object]]:
    quote: Dict[str, Dict[str, object]] = {}
    for k in price_keys:
        mn, mx = get_price_range(k)
        meta = PRICE_META.get(k, {"unit": "", "label": k})
        quote[k] = {"min": mn, "max": mx, "unit": meta["unit"], "label": meta["label"]}
    return quote


# ============================================================
# Helpers
# ============================================================
def _range_add(a: Tuple[float, float], b: Tuple[float, float]) -> Tuple[float, float]:
    return (a[0] + b[0], a[1] + b[1])


def _range_mul(a: Tuple[float, float], x: float) -> Tuple[float, float]:
    return (a[0] * x, a[1] * x)


def _eur(x: float) -> int:
    return int(round(x))


def _label(key: str, fallback: str) -> str:
    return PRICE_META.get(key, {}).get("label", fallback)


def _unit(key: str, fallback: str = "") -> str:
    return PRICE_META.get(key, {}).get("unit", fallback)


def _to_float(v) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(str(v).replace(",", ".").strip())
    except Exception:
        return 0.0


# ============================================================
# ✅ NIEUW: Overzicht van gekozen opties (klantvriendelijk)
#    - gebruikt costs["inputs"] (die jij al teruggeeft)
# ============================================================
def format_tuinaanleg_choices_for_customer(costs: Dict[str, Any]) -> str:
    """
    Maakt een compacte opsomming van alle relevante gekozen opties uit costs['inputs'].
    Bedoeld om BOVEN de prijsindicatie te tonen.
    """
    inputs = (costs or {}).get("inputs") or {}
    if not inputs:
        return ""

    def _pct(v: Any) -> str:
        try:
            return f"{int(v)}%"
        except Exception:
            return ""

    def _ratio_label(code: str | None) -> str:
        return {
            "70_30": "70% / 30%",
            "50_50": "50% / 50%",
            "30_70": "30% / 70%",
            "custom": "zelf ingevuld",
        }.get((code or "").strip(), "onbekend")

    def _mat_label(m: str | None) -> str:
        return {
            "grind": "Grind",
            "beton": "Beton",
            "gebakken": "Gebakken klinkers",
            "keramiek": "Keramiek",
            "": "Beton",
            None: "Beton",
        }.get((m or "").strip().lower(), "Beton")

    def _yesno(v: Any) -> str:
        return "Ja" if v is True else "Nee"

    # basis
    tuin_m2 = inputs.get("tuin_m2")
    ratio_bg = inputs.get("verhouding_bestrating_groen")
    ratio_gb = inputs.get("verhouding_gazon_beplanting")

    # custom percentages (als aanwezig)
    b_pct = inputs.get("bestrating_pct")
    g_pct = inputs.get("groen_pct")
    ga_pct = inputs.get("gazon_pct")
    bp_pct = inputs.get("beplanting_pct")

    # verharding verdeling
    oprit_pct = inputs.get("oprit_pct")
    paden_pct = inputs.get("paden_pct")
    terras_pct = inputs.get("terras_pct")

    # materialen
    mat_oprit = inputs.get("materiaal_oprit")
    mat_paden = inputs.get("materiaal_paden")
    mat_terras = inputs.get("materiaal_terras")

    # extra's
    voegen = inputs.get("onkruidwerend_gevoegd") is True
    overkapping = inputs.get("overkapping") is True
    verlichting = inputs.get("verlichting") is True

    overige = inputs.get("overige_wensen") or []
    overige_clean = [str(x).strip().lower() for x in (overige if isinstance(overige, list) else [overige]) if str(x).strip()]

    vlonder_type = (inputs.get("vlonder_type") or "").strip().lower()
    beregening_scope = (inputs.get("beregening_scope") or "").strip().lower()

    erf_count = inputs.get("erfafscheiding_items_count") or 0

    lines: List[str] = []
    lines.append("🧾 **Uw gekozen uitgangspunten**")

    if tuin_m2:
        try:
            lines.append(f"- Tuinoppervlak: ca. {int(round(float(tuin_m2)))} m²")
        except Exception:
            pass

    # bestrating/groen
    if ratio_bg == "custom" and (b_pct is not None or g_pct is not None):
        bp = _pct(b_pct)
        gp = _pct(g_pct)
        if bp and gp:
            lines.append(f"- Verdeling bestrating / groen: {bp} bestrating – {gp} groen")
        else:
            lines.append(f"- Verdeling bestrating / groen: {_ratio_label(ratio_bg)}")
    else:
        # preset (30/70 etc.)
        if ratio_bg:
            # bijv. "30_70" => 30 bestrating / 70 groen
            if ratio_bg in {"70_30", "50_50", "30_70"}:
                a, b = ratio_bg.split("_", 1)
                lines.append(f"- Verdeling bestrating / groen: {a}% bestrating – {b}% groen")
            else:
                lines.append(f"- Verdeling bestrating / groen: {_ratio_label(ratio_bg)}")

    # gazon/beplanting
    if ratio_gb == "custom" and (ga_pct is not None or bp_pct is not None):
        gap = _pct(ga_pct)
        bpp = _pct(bp_pct)
        if gap and bpp:
            lines.append(f"- Groen: {gap} gazon – {bpp} beplanting")
        else:
            lines.append(f"- Groen: {_ratio_label(ratio_gb)} (gazon / beplanting)")
    else:
        if ratio_gb:
            if ratio_gb in {"70_30", "50_50", "30_70"}:
                a, b = ratio_gb.split("_", 1)
                lines.append(f"- Groen: {a}% gazon – {b}% beplanting")
            else:
                lines.append(f"- Groen: {_ratio_label(ratio_gb)} (gazon / beplanting)")

    # bestrating: oprit/paden/terras + materiaal
    parts: List[str] = []
    try:
        o = int(oprit_pct) if oprit_pct is not None else 0
        p = int(paden_pct) if paden_pct is not None else 0
        t = int(terras_pct) if terras_pct is not None else 0
    except Exception:
        o, p, t = 0, 0, 100

    if o > 0:
        parts.append(f"Oprit: {o}% ({_mat_label(mat_oprit)})")
    if p > 0:
        parts.append(f"Paden: {p}% ({_mat_label(mat_paden)})")
    if t > 0:
        parts.append(f"Terras: {t}% ({_mat_label(mat_terras)})")

    if parts:
        lines.append("- Bestrating:")
        for it in parts:
            lines.append(f"  - {it}")

    # extra's (compact)
    extras: List[str] = []
    if voegen:
        extras.append("Bestrating gevoegd (onkruidwerend)")
    if overkapping:
        extras.append("Overkapping")
    if verlichting:
        extras.append("Tuinverlichting (basis)")

    if "beregening" in overige_clean:
        if beregening_scope == "gazon":
            extras.append("Beregening (alleen gazon)")
        elif beregening_scope == "beplanting":
            extras.append("Beregening (alleen beplanting)")
        else:
            extras.append("Beregening (gazon én beplanting)")

    if "vlonder" in overige_clean:
        if vlonder_type:
            extras.append(f"Vlonder ({vlonder_type})")
        else:
            extras.append("Vlonder")

    if erf_count and int(erf_count) > 0:
        extras.append("Erfafscheiding")

    # overige wensen die niet in bovenstaande vallen
    known = {"beregening", "vlonder", "erfafscheiding"}
    overige_over = [x for x in overige_clean if x not in known]
    if overige_over:
        # laat ze als losse wens zien
        extras.extend([f"Overige wens: {x}" for x in overige_over])

    if extras:
        lines.append("- Extra’s:")
        for ex in extras:
            lines.append(f"  - {ex}")

    return "\n".join(lines)


# ============================================================
# ✅ Globaal kostenoverzicht tuinaanleg op basis van flow
# ============================================================
def estimate_tuinaanleg_costs(answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rekent met:
    - tuin_m2
    - verhouding_bestrating_groen
    - verhouding_gazon_beplanting
    - oprit/paden/terras percentages: oprit_pct, paden_pct, terras_pct
    - materialen: materiaal_oprit, materiaal_paden, materiaal_terras
    - onkruidwerend_gevoegd (voegen alleen op straatwerk, niet op grind)
    - ✅ grondwerk (altijd): afvoer/aanvoer in m³ o.b.v. dieptes per onderdeel
    - zaagwerk
    - overige_wensen + vlonder_type
    - ✅ erfafscheiding (MEERDERE): erfafscheiding_items[] met type/meter/poortdeur
    - ✅ beregening: scope -> m² berekening
    """

    m2 = float(answers.get("tuin_m2") or 0)
    if m2 <= 0:
        return {"error": "tuin_m2 ontbreekt of is ongeldig"}

    ratio_bg = answers.get("verhouding_bestrating_groen")
    ratio_gb = answers.get("verhouding_gazon_beplanting")

    voegen = answers.get("onkruidwerend_gevoegd") is True
    overkapping = answers.get("overkapping") is True
    verlichting = answers.get("verlichting") is True

    overige = answers.get("overige_wensen") or []
    vlonder_type = (answers.get("vlonder_type") or "").strip().lower()
    beregening_scope = (answers.get("beregening_scope") or "").strip().lower()

    oprit_pct = answers.get("oprit_pct")
    paden_pct = answers.get("paden_pct")
    terras_pct = answers.get("terras_pct")
    mat_oprit = (answers.get("materiaal_oprit") or "").strip().lower()
    mat_paden = (answers.get("materiaal_paden") or "").strip().lower()
    mat_terras = (answers.get("materiaal_terras") or "").strip().lower()

    overige_clean = [str(x).strip().lower() for x in overige if str(x).strip()]

    breakdown: List[Dict[str, Any]] = []
    total: Tuple[float, float] = (0.0, 0.0)

    # 1) Verhouding bestrating/groen -> schatting bestratingsm²
    share_map_bg = {"70_30": 0.70, "50_50": 0.50, "30_70": 0.30}
    paving_share = share_map_bg.get(ratio_bg, 0.50)
    paving_m2 = m2 * paving_share

    # Groenoppervlak
    green_m2 = max(0.0, m2 - paving_m2)

    # 2) Groen verdeling gazon/beplanting
    share_map_gb = {"70_30": 0.70, "50_50": 0.50, "30_70": 0.30}  # aandeel gazon
    gazon_share = share_map_gb.get(ratio_gb, 0.50)
    beplanting_share = 1.0 - gazon_share

    gazon_m2 = green_m2 * gazon_share
    border_m2 = green_m2 * beplanting_share

    # ------------------------------------------------------------
    # 3) Verharding per onderdeel (oprit / paden / terras) + materiaalkeuze
    # ------------------------------------------------------------
    def _safe_int(x, default: int) -> int:
        try:
            return int(x)
        except Exception:
            return default

    if oprit_pct is None or paden_pct is None or terras_pct is None:
        oprit_pct_i, paden_pct_i, terras_pct_i = 0, 0, 100
    else:
        oprit_pct_i = _safe_int(oprit_pct, 0)
        paden_pct_i = _safe_int(paden_pct, 0)
        terras_pct_i = _safe_int(terras_pct, 100)

    s_pct = oprit_pct_i + paden_pct_i + terras_pct_i
    if s_pct <= 0:
        oprit_pct_i, paden_pct_i, terras_pct_i = 0, 0, 100
        s_pct = 100

    oprit_m2 = paving_m2 * (oprit_pct_i / s_pct)
    paden_m2 = paving_m2 * (paden_pct_i / s_pct)
    terras_m2 = paving_m2 * (terras_pct_i / s_pct)

    if not mat_oprit:
        mat_oprit = "beton"
    if not mat_paden:
        mat_paden = "beton"
    if not mat_terras:
        mat_terras = "beton"

    def material_to_key(material: str) -> str:
        material = (material or "").strip().lower()
        if material == "keramiek":
            return "keramisch_straatwerk_per_m2"
        if material == "grind":
            return "grind_per_m2"
        return "beton_gebakken_straatwerk_per_m2"

    def material_pretty(material: str) -> str:
        material = (material or "").strip().lower()
        if material == "keramiek":
            return "Keramiek"
        if material == "grind":
            return "Grind"
        if material == "gebakken":
            return "Gebakken klinkers"
        return "Beton"

    def add_surface_cost(part_label: str, m2_part: float, material: str) -> None:
        nonlocal total
        if m2_part <= 0.01:
            return

        key = material_to_key(material)
        unit_range = PRIJZEN.get(key, (60, 120))
        rng = _range_mul((float(unit_range[0]), float(unit_range[1])), m2_part)
        total = _range_add(total, rng)

        breakdown.append({
            "key": key,
            "label": f"{part_label} – {material_pretty(material)}",
            "unit": _unit(key, "€/m²"),
            "qty": int(round(m2_part)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": "Indicatief; onderbouw/fundering, snijwerk en complexiteit beïnvloeden de prijs."
        })

    add_surface_cost("Oprit", oprit_m2, mat_oprit)
    add_surface_cost("Paden", paden_m2, mat_paden)
    add_surface_cost("Terras", terras_m2, mat_terras)

    straatwerk_m2 = 0.0
    for m2_part, mat in ((oprit_m2, mat_oprit), (paden_m2, mat_paden), (terras_m2, mat_terras)):
        if (mat or "").strip().lower() != "grind":
            straatwerk_m2 += float(m2_part)

    # ------------------------------------------------------------
    # ✅ 3a) Grondwerk (altijd): m² -> m³ en koppelen aan pricing keys
    # ------------------------------------------------------------
    def add_volume_cost(label: str, key: str, m3: float, notes: str) -> None:
        nonlocal total
        if m3 <= 0.0001:
            return
        unit_range = PRIJZEN.get(key)
        if not unit_range:
            return

        rng = _range_mul((float(unit_range[0]), float(unit_range[1])), m3)
        total = _range_add(total, rng)

        breakdown.append({
            "key": key,
            "label": label,
            "unit": _unit(key, "€/m³"),
            "qty": round(m3, 2),  # m³ (2 decimalen)
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": notes
        })

    grond_afvoer_key = "grond_afvoer_per_m3"
    zand_key = "zand_aanvoer_per_m3"
    puin_key = "puin_aanvoer_per_m3"

    # Paden + Terras: 20 cm afvoer, 15 cm zand
    paden_terras_m2 = float(paden_m2) + float(terras_m2)

    grond_afvoer_paden_terras_m3 = paden_terras_m2 * 0.20
    add_volume_cost(
        label="Grond afvoer – paden/terras (20 cm)",
        key=grond_afvoer_key,
        m3=grond_afvoer_paden_terras_m3,
        notes="Aannames: 0,20 m ontgraven per m² voor paden/terras."
    )

    zand_paden_terras_m3 = paden_terras_m2 * 0.15
    add_volume_cost(
        label="Zand aanvoer – paden/terras (15 cm)",
        key=zand_key,
        m3=zand_paden_terras_m3,
        notes="Aannames: 0,15 m zand per m² voor paden/terras."
    )

    # Oprit: 35 cm afvoer, 25 cm puin, 5 cm zand
    oprit_m2_f = float(oprit_m2)

    grond_afvoer_oprit_m3 = oprit_m2_f * 0.35
    add_volume_cost(
        label="Grond afvoer – oprit (35 cm)",
        key=grond_afvoer_key,
        m3=grond_afvoer_oprit_m3,
        notes="Aannames: 0,35 m ontgraven per m² voor oprit."
    )

    puin_oprit_m3 = oprit_m2_f * 0.25
    add_volume_cost(
        label="Puin aanvoer – oprit (25 cm)",
        key=puin_key,
        m3=puin_oprit_m3,
        notes="Aannames: 0,25 m puin per m² voor oprit."
    )

    zand_oprit_m3 = oprit_m2_f * 0.05
    add_volume_cost(
        label="Zand aanvoer – oprit (5 cm)",
        key=zand_key,
        m3=zand_oprit_m3,
        notes="Aannames: 0,05 m zand per m² voor oprit."
    )

    # ------------------------------------------------------------
    # 3b) Zaagwerk
    # ------------------------------------------------------------
    zaag_m1_min = 0.0
    zaag_m1_max = 0.0
    if straatwerk_m2 > 0.01:
        zaag_key = "zaagwerk_per_m1"
        zaag_unit_range = PRIJZEN.get(zaag_key, (35, 65))

        zaag_m1_min = straatwerk_m2 * 0.3
        zaag_m1_max = straatwerk_m2 * 0.5

        zaag_range = (
            float(zaag_unit_range[0]) * zaag_m1_min,
            float(zaag_unit_range[1]) * zaag_m1_max,
        )
        total = _range_add(total, zaag_range)

        zaag_qty_mid = int(round((zaag_m1_min + zaag_m1_max) / 2))
        breakdown.append({
            "key": zaag_key,
            "label": _label(zaag_key, "Zaagwerk"),
            "unit": _unit(zaag_key, "€/m¹"),
            "qty": zaag_qty_mid,
            "range_eur": [_eur(zaag_range[0]), _eur(zaag_range[1])],
            "notes": (
                f"Schatting {int(round(zaag_m1_min))}–{int(round(zaag_m1_max))} m¹ zaagwerk "
                f"(afhankelijk van randen/hoeken/obstakels)."
            )
        })

    # ------------------------------------------------------------
    # 4) Gazon (graszoden)
    # ------------------------------------------------------------
    if gazon_m2 > 0:
        gazon_key = "graszoden_per_m2"
        gazon_unit_range = PRIJZEN.get(gazon_key, (15, 25))
        gazon_range = _range_mul((float(gazon_unit_range[0]), float(gazon_unit_range[1])), gazon_m2)
        total = _range_add(total, gazon_range)

        breakdown.append({
            "key": gazon_key,
            "label": _label(gazon_key, "Graszoden"),
            "unit": _unit(gazon_key, "€/m²"),
            "qty": int(round(gazon_m2)),
            "range_eur": [_eur(gazon_range[0]), _eur(gazon_range[1])],
            "notes": "Indicatief; afhankelijk van ondergrond, egaliseren en bereikbaarheid."
        })

    # ------------------------------------------------------------
    # 5) Beplanting (borders)
    # ------------------------------------------------------------
    if border_m2 > 0:
        border_key = "beplanting_border_per_m2"
        border_unit_range = PRIJZEN.get(border_key, (30, 40))
        border_range = _range_mul((float(border_unit_range[0]), float(border_unit_range[1])), border_m2)
        total = _range_add(total, border_range)

        breakdown.append({
            "key": border_key,
            "label": _label(border_key, "Beplanting border"),
            "unit": _unit(border_key, "€/m²"),
            "qty": int(round(border_m2)),
            "range_eur": [_eur(border_range[0]), _eur(border_range[1])],
            "notes": "Indicatief; soort, ondergrond, beplanting en plantdichtheid beïnvloeden de prijs."
        })

    # ------------------------------------------------------------
    # ✅ 5b) Erfafscheiding (MEERDERE items) + ✅ poortdeuren samenvoegen
    # ------------------------------------------------------------
    erf_gevraagd = any(str(x).strip().lower() == "erfafscheiding" for x in (overige or []))
    items = answers.get("erfafscheiding_items") or []

    # backward compat: oude single-velden (als iemand nog oude flow gebruikt)
    old_type = (answers.get("erfafscheiding_type") or "").strip().lower()
    old_meter = _to_float(answers.get("erfafscheiding_meter"))
    old_poort = answers.get("poortdeur")
    if (not items) and old_type and old_meter > 0:
        items = [{"type": old_type, "meter": old_meter, "poortdeur": (old_poort is True) if old_poort is not None else None}]

    poortdeur_count = 0

    if erf_gevraagd and items:
        for it in items:
            t = (it.get("type") or "").strip().lower()
            meters = _to_float(it.get("meter"))
            pd = it.get("poortdeur") is True

            if meters <= 0:
                continue

            if t == "haag":
                key = "beplanting_haag_per_m1"
                unit_fallback = "€/m¹"
            elif t == "betonschutting":
                key = "plaatsen_betonschutting_per_m1"
                unit_fallback = "€/m¹"
            elif t == "design_schutting":
                key = "plaatsen_designschutting_per_m1"
                unit_fallback = "€/m¹"
            else:
                key = None
                unit_fallback = "€/m¹"

            if key and key in PRIJZEN:
                unit_range = PRIJZEN[key]
                rng = _range_mul((float(unit_range[0]), float(unit_range[1])), meters)
                total = _range_add(total, rng)
                breakdown.append({
                    "key": key,
                    "label": _label(key, "Erfafscheiding"),
                    "unit": _unit(key, unit_fallback),
                    "qty": int(round(meters)),
                    "range_eur": [_eur(rng[0]), _eur(rng[1])],
                    "notes": "Indicatief; afhankelijk van soort, formaat, ondergrond en bereikbaarheid."
                })

                if pd and t in ("betonschutting", "design_schutting"):
                    poortdeur_count += 1

        if poortdeur_count > 0 and "plaatsen_poortdeur_per_st" in PRIJZEN:
            pk = "plaatsen_poortdeur_per_st"
            pr = PRIJZEN[pk]
            rng = (float(pr[0]) * poortdeur_count, float(pr[1]) * poortdeur_count)
            total = _range_add(total, rng)
            breakdown.append({
                "key": pk,
                "label": _label(pk, "Poortdeur plaatsen"),
                "unit": _unit(pk, "€/stuk"),
                "qty": poortdeur_count,
                "range_eur": [_eur(rng[0]), _eur(rng[1])],
                "notes": "Indicatief; afhankelijk van maatvoering, beslag en fundering."
            })

        overige_clean = [x for x in overige_clean if x != "erfafscheiding"]

    # ------------------------------------------------------------
    # ✅ 5c) Beregening (per m²) op basis van scope: gazon / beplanting / allebei
    # ------------------------------------------------------------
    if "beregening" in overige_clean:
        key = "beregening_basis_per_m2"
        unit_range = PRIJZEN.get(key, (20, 40))

        if beregening_scope == "gazon":
            b_m2 = gazon_m2
            scope_txt = "alleen gazon"
        elif beregening_scope == "beplanting":
            b_m2 = border_m2
            scope_txt = "alleen beplanting"
        else:
            b_m2 = gazon_m2 + border_m2
            scope_txt = "gazon én beplanting"

        if b_m2 > 0.01:
            rng = _range_mul((float(unit_range[0]), float(unit_range[1])), b_m2)
            total = _range_add(total, rng)

            breakdown.append({
                "key": key,
                "label": _label(key, "Beregening (basis)"),
                "unit": _unit(key, "€/m²"),
                "qty": int(round(b_m2)),
                "range_eur": [_eur(rng[0]), _eur(rng[1])],
                "notes": f"Indicatief; berekend over {scope_txt}. Afhankelijk van pomp, zones, waterpunt en besturing."
            })

        overige_clean = [x for x in overige_clean if x != "beregening"]

    # ------------------------------------------------------------
    # 6) Voegen (per m²) — alleen op straatwerk, niet op grind
    # ------------------------------------------------------------
    if voegen and straatwerk_m2 > 0.01:
        voeg_key = "voegen_straatwerk_per_m2"
        voeg_unit_range = PRIJZEN.get(voeg_key, (15, 20))

        voeg_range = _range_mul((float(voeg_unit_range[0]), float(voeg_unit_range[1])), straatwerk_m2)
        total = _range_add(total, voeg_range)

        breakdown.append({
            "key": voeg_key,
            "label": _label(voeg_key, "Voegen straatwerk"),
            "unit": _unit(voeg_key, "€/m²"),
            "qty": int(round(straatwerk_m2)),
            "range_eur": [_eur(voeg_range[0]), _eur(voeg_range[1])],
            "notes": "Indicatief; voegwerk berekend per m² straatwerk (excl. grind)."
        })

    # ------------------------------------------------------------
    # 7) Overkapping (stuk)
    # ------------------------------------------------------------
    if overkapping:
        ov_key = "overkapping_basis_per_stuk"
        ov = PRIJZEN.get(ov_key, (10000, 15000))
        ov_range = (float(ov[0]), float(ov[1]))
        total = _range_add(total, ov_range)

        breakdown.append({
            "key": ov_key,
            "label": _label(ov_key, "Overkapping (basis)"),
            "unit": _unit(ov_key, "€/stuk"),
            "qty": 1,
            "range_eur": [_eur(ov_range[0]), _eur(ov_range[1])],
            "notes": "Basis; luxe opties/maatwerk/fundering en afwerking kunnen extra zijn."
        })

    # ------------------------------------------------------------
    # 8) Verlichting (stuk)
    # ------------------------------------------------------------
    if verlichting:
        vl_key = "verlichting_basis_per_stuk"
        vl = PRIJZEN.get(vl_key, (1000, 1500))
        vl_range = (float(vl[0]), float(vl[1]))
        total = _range_add(total, vl_range)

        breakdown.append({
            "key": vl_key,
            "label": _label(vl_key, "Verlichting (basis)"),
            "unit": _unit(vl_key, "€/stuk"),
            "qty": 1,
            "range_eur": [_eur(vl_range[0]), _eur(vl_range[1])],
            "notes": "Afhankelijk van aantal spots, trafo, bekabeling en montage."
        })

    # ------------------------------------------------------------
    # 9) Overige wensen (incl. vlonder)
    # ------------------------------------------------------------
    if "vlonder" in overige_clean:
        vlonder_m2 = min(12.0, max(6.0, 0.12 * m2))  # default: 12% van tuin, min 6 m², max 12 m²

        if vlonder_type == "zachthout":
            vlonder_key = "vlonder_zachthout_per_m2"
        elif vlonder_type == "hardhout":
            vlonder_key = "vlonder_hardhout_per_m2"
        else:
            vlonder_key = "vlonder_composiet_per_m2"

        unit_range = PRIJZEN.get(vlonder_key, (280, 350))
        rng = _range_mul((float(unit_range[0]), float(unit_range[1])), vlonder_m2)
        total = _range_add(total, rng)

        breakdown.append({
            "key": vlonder_key,
            "label": _label(vlonder_key, "Vlonder"),
            "unit": _unit(vlonder_key, "€/m²"),
            "qty": int(round(vlonder_m2)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": "Schatting o.b.v. standaard vlonder-oppervlak; materiaal, fundering en afwerking kunnen variëren."
        })

        overige_clean = [x for x in overige_clean if x != "vlonder"]

    if overige_clean:
        breakdown.append({
            "key": None,
            "label": "Overige wensen",
            "unit": "",
            "qty": None,
            "range_eur": None,
            "notes": "Opgenomen als wens: " + ", ".join(overige_clean)
        })

    # ------------------------------------------------------------
    # ✅ Combineer grondwerk regels: 1 regel per key (grond/zand/puin)
    # ------------------------------------------------------------
    aggregate_keys = {
        "grond_afvoer_per_m3": "Grond afvoer",
        "zand_aanvoer_per_m3": "Zand aanvoer",
        "puin_aanvoer_per_m3": "Puin aanvoer",
    }

    agg: Dict[str, Dict[str, Any]] = {}
    new_breakdown: List[Dict[str, Any]] = []

    for item in breakdown:
        k = item.get("key")
        if k in aggregate_keys and item.get("range_eur") is not None:
            if k not in agg:
                agg[k] = {
                    "key": k,
                    "label": aggregate_keys[k],
                    "unit": _unit(k, "€/m³"),
                    "qty": 0.0,
                    "min_sum": 0.0,
                    "max_sum": 0.0,
                }

            qty = float(item.get("qty") or 0.0)
            r0, r1 = item.get("range_eur") or (0, 0)

            agg[k]["qty"] += qty
            agg[k]["min_sum"] += float(r0)
            agg[k]["max_sum"] += float(r1)
            continue

        new_breakdown.append(item)

    for k in ("grond_afvoer_per_m3", "zand_aanvoer_per_m3", "puin_aanvoer_per_m3"):
        if k in agg:
            a = agg[k]
            new_breakdown.append({
                "key": a["key"],
                "label": a["label"],
                "unit": a["unit"],
                "qty": round(a["qty"], 2),
                "range_eur": [_eur(a["min_sum"]), _eur(a["max_sum"])],
                "notes": "Indicatief; grondwerk kan afwijken als de bestaande ondergrond al geschikt is."
            })

    breakdown = new_breakdown

    # ------------------------------------------------------------
    # ✅ Sorteer breakdown: grondwerk eerst (mooie volgorde)
    # ------------------------------------------------------------
    order = {
        "grond_afvoer_per_m3": 0,
        "zand_aanvoer_per_m3": 1,
        "puin_aanvoer_per_m3": 2,
    }

    def _prio(item: Dict[str, Any]) -> Tuple[int, int]:
        k = item.get("key")
        if k in order:
            return (0, order[k])
        return (1, 0)

    breakdown.sort(key=_prio)

    return {
        "total_range_eur": [_eur(total[0]), _eur(total[1])],
        "breakdown": breakdown,
        "inputs": {
            "tuin_m2": m2,
            "verhouding_bestrating_groen": ratio_bg,
            "verhouding_gazon_beplanting": ratio_gb,
            "paving_share": paving_share,
            "paving_m2_estimate": int(round(paving_m2)),
            "oprit_pct": oprit_pct_i,
            "paden_pct": paden_pct_i,
            "terras_pct": terras_pct_i,
            "oprit_m2_estimate": int(round(oprit_m2)),
            "paden_m2_estimate": int(round(paden_m2)),
            "terras_m2_estimate": int(round(terras_m2)),
            "straatwerk_m2_estimate": int(round(straatwerk_m2)),
            "grond_afvoer_paden_terras_m3_estimate": round(grond_afvoer_paden_terras_m3, 2),
            "zand_paden_terras_m3_estimate": round(zand_paden_terras_m3, 2),
            "grond_afvoer_oprit_m3_estimate": round(grond_afvoer_oprit_m3, 2),
            "puin_oprit_m3_estimate": round(puin_oprit_m3, 2),
            "zand_oprit_m3_estimate": round(zand_oprit_m3, 2),
            "zaag_m1_estimate_min": int(round(zaag_m1_min)),
            "zaag_m1_estimate_max": int(round(zaag_m1_max)),
            "green_m2_estimate": int(round(green_m2)),
            "gazon_m2_estimate": int(round(gazon_m2)),
            "beplanting_m2_estimate": int(round(border_m2)),
            "onkruidwerend_gevoegd": voegen,
            "overkapping": overkapping,
            "verlichting": verlichting,
            "overige_wensen": overige,
            "vlonder_type": vlonder_type,
            "materiaal_oprit": mat_oprit,
            "materiaal_paden": mat_paden,
            "materiaal_terras": mat_terras,
            "beregening_scope": beregening_scope,
            "erfafscheiding_items_count": len(items) if erf_gevraagd else 0,
        }
    }


# ============================================================
# ✅ Formatter -> klantvriendelijke tekst voor chat/UI
# ============================================================
def format_tuinaanleg_costs_for_customer(costs: Dict[str, Any]) -> str:
    if not costs or not costs.get("total_range_eur"):
        return (
            "Op basis van de ingevulde gegevens kan ik nu nog geen "
            "betrouwbare indicatie geven. We helpen u graag verder met een offerte op maat."
        )

    total_min, total_max = costs["total_range_eur"]

    def eur(v: int) -> str:
        return f"€{v:,}".replace(",", ".")

    lines: List[str] = []

    # ✅ NIEUW: eerst keuze-overzicht
    choices = format_tuinaanleg_choices_for_customer(costs)
    if choices:
        lines.append(choices)
        lines.append("")

    # ✅ 1) “prijs” herpositioneren
    lines.append("✅ **Globale inschatting**")
    lines.append(
        "Bedankt voor het invullen, op basis van uw ingevulde keuzes geef ik u hieronder een globale indicatie."
    )
    lines.append("")

    # ✅ 2) geruststelling vóór bedragen
    lines.append(
        "_Iedere tuin is uniek. Deze indicatie is bedoeld als richting, "
        "niet als definitieve offerte._"
    )
    lines.append("")

    lines.append(f"**Totale indicatie:** {eur(int(total_min))} – {eur(int(total_max))}")
    lines.append("")

    for item in costs.get("breakdown", []):
        label = item.get("label", "Onderdeel")
        rng = item.get("range_eur")
        qty = item.get("qty")
        unit = item.get("unit", "")
        notes = item.get("notes")

        if rng is None:
            lines.append(f"- {label}: wordt meegenomen in de offerte")
            continue

        qty_txt = str(qty) if qty is not None else ""
        unit_txt = unit.replace("€/", "").replace("€ ", "").strip()

        line = f"- {label}"
        if qty_txt and unit_txt:
            line += f" ({qty_txt} {unit_txt})"
        line += f": {eur(int(rng[0]))} – {eur(int(rng[1]))}"
        lines.append(line)

        if notes:
            lines.append(f"  _{notes}_")

    lines.append("")
    lines.append(
        "_Deze globale prijsindicatie is gebaseerd op aannames en is inclusief arbeid en standaard materialen._"
    )
    lines.append("")

    # ✅ 3) menselijk contact als plus/volgende stap
    lines.append(
        "Wilt u dat we dit samen verfijnen en kijken wat er mogelijk is binnen uw wensen? "
        "Dan komen we graag langs voor een vrijblijvende offerte."
    )

    return "\n".join(lines)
