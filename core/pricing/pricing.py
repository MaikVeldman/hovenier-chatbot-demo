# pricing.py
from __future__ import annotations

import math
from typing import Dict, Tuple, List, Any


def _round_to_half(x: float) -> float:
    """Rond altijd naar boven af op 0,5 (bijv. 11,25 → 11,5 en 2,75 → 3,0)."""
    return round(math.ceil(x * 2) / 2, 1)


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
    "beton_straatwerk_per_m2": (60, 90),                                # €/m²
    "gebakken_straatwerk_per_m2": (80, 130),                            # €/m²
    "grind_per_m2": (35, 60),                                           # €/m²
    "plaatsen_betonband_per_m1": (14, 28),                              # €/m¹
    "zaagwerk_per_m1": (20, 35),                                        # €/m¹
    "voegen_straatwerk_per_m2": (15, 20),                               # €/m²

    "vlonder_zachthout_per_m2": (200, 250),                             # €/m²
    "vlonder_hardhout_per_m2": (280, 420),                              # €/m²
    "vlonder_composiet_per_m2": (350, 520),                             # €/m²

    "graszoden_per_m2": (12, 22),                                       # €/m²
    "beplanting_border_per_m2": (25, 40),                               # €/m²
    "beplanting_haag_voordelig_laag_per_m1": (20, 40),                   # €/m¹  ca. 0,5–1m
    "beplanting_haag_voordelig_hoog_per_m1": (45, 75),                  # €/m¹  ca. 1,5–2m
    "beplanting_haag_premium_laag_per_m1": (75, 120),                   # €/m¹  ca. 0,5–1m
    "beplanting_haag_premium_hoog_per_m1": (120, 180),                  # €/m¹  ca. 1,5–2m
    "beplanting_boom_per_stuk": (220, 600),

    "overkapping_per_m2": (650, 1000),                                  # €/m²
    "verlichting_basis_per_stuk": (1000, 1500),                         # €/stuk

    "beregening_installatie_basis":               (600, 900),           # € vast
    "beregening_installatie_volautomatisch":      (1000, 1500),         # € vast
    "beregening_installatie_highend":             (1800, 2500),         # € vast
    "beregening_gazon_basis_per_m2":              (5, 9),               # €/m²
    "beregening_gazon_volautomatisch_per_m2":     (8, 13),              # €/m²
    "beregening_gazon_highend_per_m2":            (12, 18),             # €/m²
    "beregening_beplanting_basis_per_m2":         (7, 12),              # €/m²
    "beregening_beplanting_volautomatisch_per_m2":(12, 18),             # €/m²
    "beregening_beplanting_highend_per_m2":       (18, 28),             # €/m²

    "plaatsen_betonschutting_per_m1": (200, 300),                       # €/m¹
    "plaatsen_poortdeur_per_st": (750, 1500),                           # €/stuk
    "plaatsen_designschutting_per_m1": (300, 400),                      # €/m¹

    "3d_tuinontwerp_<100m2": (500, 1000),                                # €/stuk
    "3d_tuinontwerp_100-500m2": (1000, 1500),                            # €/stuk
    "3d_tuinontwerp_500-1000m2": (1500, 2000),                          # €/stuk
    "3d_tuinontwerp_>1000m2": (2000, 3000),                             # €/stuk
}

PRICE_KEYS: List[str] = sorted(PRIJZEN.keys())

# ============================================================
# Volume-kortingen — SaaS-klaar: pas alleen deze tabel aan per klant
# Formaat per categorie: [(drempel, factor), ...]  hoogste drempel eerst
# De laagste factor is de vloer: daarboven bevriest de korting
# ============================================================
VOLUME_KORTINGEN: Dict[str, List[Tuple[float, float]]] = {
    #            drempel    factor   korting   wanneer
    "groen":    [(300,      0.82),  # -18%    ≥300 m²  — bulk pallet + grote machine
                 (150,      0.87),  # -13%    ≥150 m²  — crew van 2, bulk plantaankoop
                 (75,       0.93)], #  -7%    ≥75 m²   — machine loont
    "bestrating":[(200,     0.86),  # -14%    ≥200 m²  — meerdere pallets, bulk transport
                  (100,     0.91),  #  -9%    ≥100 m²  — volledige pallet, minder % snijwerk
                  (50,      0.96)], #  -4%    ≥50 m²   — werkset staat de hele dag
    "grondwerk": [(60,      0.83),  # -17%    ≥60 m³   — zware hydraulische kraan, bulktransport
                  (25,      0.88),  # -12%    ≥25 m³   — grote graafmachine + bulk
                  (10,      0.94)], #  -6%    ≥10 m³   — middelgrote bagger, efficiënte rit
    "vlonder":  [(50,       0.88),  # -12%    ≥50 m²   — volledige vrachtwagen hout
                 (20,       0.94)], #  -6%    ≥20 m²   — bulk planken, minder relatief zaagwerk
}

PRIJSTOELICHTING: str = (
    "Deze prijs is all-in: materialen, arbeid en grondwerk. "
    "Grondwerk ziet u niet terug in uw tuin, maar bepaalt of uw bestrating gedurende lange tijd recht blijft liggen."
    "In sommige gevallen volstaat de bestaande ondergrond, wat de kosten aanzienlijk kan verlagen. "
    "Let bij het vergelijken van offertes altijd op of er op een correcte manier grondwerk wordt toegepast. "
    "De prijs is daarnaast sterk afhankelijk van uw materiaalkeuze, een upgrade of downgrade heeft direct invloed op het totaal. "
    "Wilt u het budget spreiden? We werken ook in fasen."
)

_PRIJSTOELICHTING_ZONDER_GRONDWERK: str = (
    "Deze prijs is all-in: materialen en arbeid. "
    "De prijs is sterk afhankelijk van uw materiaalkeuze, een upgrade of downgrade heeft direct invloed op het totaal. "
    "Wilt u het budget spreiden? We werken ook in fasen."
)


def get_prijstoelichting(breakdown: List[Dict[str, Any]]) -> str:
    has_grondwerk = any(item.get("key") in _GRONDWERK_KEYS for item in (breakdown or []))
    return PRIJSTOELICHTING if has_grondwerk else _PRIJSTOELICHTING_ZONDER_GRONDWERK

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
    "beton_straatwerk_per_m2": {"unit": "€/m²", "label": "Beton straatwerk"},
    "gebakken_straatwerk_per_m2": {"unit": "€/m²", "label": "Gebakken klinkers"},
    "grind_per_m2": {"unit": "€/m²", "label": "Grind"},

    "plaatsen_betonband_per_m1": {"unit": "€/m¹", "label": "Betonband plaatsen"},
    "zaagwerk_per_m1": {"unit": "€/m¹", "label": "Zaagwerk"},
    "voegen_straatwerk_per_m2": {"unit": "€/m²", "label": "Voegen straatwerk"},

    "vlonder_zachthout_per_m2": {"unit": "€/m²", "label": "Vlonder (zachthout)"},
    "vlonder_hardhout_per_m2": {"unit": "€/m²", "label": "Vlonder (hardhout)"},
    "vlonder_composiet_per_m2": {"unit": "€/m²", "label": "Vlonder (composiet)"},

    "graszoden_per_m2": {"unit": "€/m²", "label": "Graszoden"},
    "beplanting_border_per_m2": {"unit": "€/m²", "label": "Beplanting border"},
    "beplanting_haag_voordelig_laag_per_m1": {"unit": "€/m¹", "label": "Haag voordelig laag (0,5–1m)"},
    "beplanting_haag_voordelig_hoog_per_m1": {"unit": "€/m¹", "label": "Haag voordelig hoog (1,5–2m)"},
    "beplanting_haag_premium_laag_per_m1":   {"unit": "€/m¹", "label": "Haag premium laag (0,5–1m)"},
    "beplanting_haag_premium_hoog_per_m1":   {"unit": "€/m¹", "label": "Haag premium hoog (1,5–2m)"},
    "beplanting_boom_per_stuk": {"unit": "€/stuk", "label": "Boom (incl. aanplant)"},

    "overkapping_per_m2": {"unit": "€/m²", "label": "Overkapping"},
    "verlichting_basis_per_stuk": {"unit": "€/stuk", "label": "Verlichting (basis 3 armaturen)"},
    "beregening_installatie_basis":               {"unit": "€ vast", "label": "Technische installatie & opstartkosten (basis)"},
    "beregening_installatie_volautomatisch":      {"unit": "€ vast", "label": "Technische installatie & opstartkosten (volautomatisch)"},
    "beregening_installatie_highend":             {"unit": "€ vast", "label": "Technische installatie & opstartkosten (high-end)"},
    "beregening_gazon_basis_per_m2":              {"unit": "€/m²", "label": "Beregening gazon (basis)"},
    "beregening_gazon_volautomatisch_per_m2":     {"unit": "€/m²", "label": "Beregening gazon (volautomatisch)"},
    "beregening_gazon_highend_per_m2":            {"unit": "€/m²", "label": "Beregening gazon (high-end)"},
    "beregening_beplanting_basis_per_m2":         {"unit": "€/m²", "label": "Beregening beplanting (basis)"},
    "beregening_beplanting_volautomatisch_per_m2":{"unit": "€/m²", "label": "Beregening beplanting (volautomatisch)"},
    "beregening_beplanting_highend_per_m2":       {"unit": "€/m²", "label": "Beregening beplanting (high-end)"},

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


def _schaal_factor(volume: float, soort: str) -> float:
    """Volume-kortingsfactor (≤ 1.0) op basis van VOLUME_KORTINGEN.
    Drempels staan gesorteerd van hoog naar laag — de eerste match wint.
    Boven de laatste drempel bevriest de factor (maximale korting).
    """
    for drempel, factor in VOLUME_KORTINGEN.get(soort, []):
        if volume >= drempel:
            return factor
    return 1.0


# ============================================================
# Grondwerk dieptes (aannames per onderdeel)
# Hier centraal beheerd zodat ze op één plek aangepast kunnen worden.
# ============================================================
GRONDWERK_DIEPTES: Dict[str, float] = {
    "paden_terras_afvoer": 0.20,          # m ontgraven voor paden/terras (standaard)
    "paden_terras_zand":   0.15,          # m zand aanvoer voor paden/terras (standaard)
    "paden_terras_afvoer_keramiek": 0.15, # m ontgraven voor keramiek (drainage mortel)
    "paden_terras_zand_keramiek":   0.10, # m zand aanvoer voor keramiek
    "oprit_afvoer":        0.35,          # m ontgraven voor oprit
    "oprit_puin":          0.25,          # m puin aanvoer voor oprit
    "oprit_zand":          0.05,          # m zand aanvoer voor oprit
}


# ============================================================
# Gedeelde breakdown-helpers (gebruikt door beide estimators)
# ============================================================

def _aggregate_grondwerk(breakdown: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Combineer meerdere grondwerk-regels per prijssleutel tot één samengevatte regel."""
    _AGG_KEYS: Dict[str, str] = {
        "grond_afvoer_per_m3": "Grond afvoer",
        "zand_aanvoer_per_m3": "Zand aanvoer",
        "puin_aanvoer_per_m3": "Puin aanvoer",
    }
    agg: Dict[str, Dict[str, Any]] = {}
    new_breakdown: List[Dict[str, Any]] = []

    for item in breakdown:
        k = item.get("key")
        if k in _AGG_KEYS and item.get("range_eur") is not None:
            if k not in agg:
                agg[k] = {
                    "key": k,
                    "label": _AGG_KEYS[k],
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
                "qty": _round_to_half(a["qty"]),
                "range_eur": [_eur(a["min_sum"]), _eur(a["max_sum"])],
                "notes": "Indicatief; grondwerk kan afwijken als de bestaande ondergrond al geschikt is.",
            })
    return new_breakdown


def _sort_breakdown_grondwerk_first(breakdown: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sorteer breakdown zodat grondwerk altijd bovenaan staat."""
    _ORDER = {"grond_afvoer_per_m3": 0, "zand_aanvoer_per_m3": 1, "puin_aanvoer_per_m3": 2}
    return sorted(
        breakdown,
        key=lambda x: (0, _ORDER[x["key"]]) if x.get("key") in _ORDER else (1, 0),
    )


# ============================================================
# Gegroepeerde breakdown formatter (gedeeld door beide flows)
# ============================================================

_BESTRATING_KEYS = {
    "beton_straatwerk_per_m2", "gebakken_straatwerk_per_m2",
    "keramisch_straatwerk_per_m2", "grind_per_m2",
    "zaagwerk_per_m1", "voegen_straatwerk_per_m2",
}
_GRONDWERK_KEYS = {
    "grond_afvoer_per_m3", "zand_aanvoer_per_m3", "puin_aanvoer_per_m3",
}
_GROEN_KEYS = {
    "graszoden_per_m2", "beplanting_border_per_m2",
}
_EXTRA_KEY_GROUP: Dict[str, str] = {
    "beplanting_haag_voordelig_laag_per_m1": "Erfafscheiding",
    "beplanting_haag_voordelig_hoog_per_m1": "Erfafscheiding",
    "beplanting_haag_premium_laag_per_m1":   "Erfafscheiding",
    "beplanting_haag_premium_hoog_per_m1":   "Erfafscheiding",
    "plaatsen_betonschutting_per_m1":   "Erfafscheiding",
    "plaatsen_designschutting_per_m1":  "Erfafscheiding",
    "plaatsen_poortdeur_per_st":        "Erfafscheiding",
    "beregening_installatie_basis":               "Beregening",
    "beregening_installatie_volautomatisch":      "Beregening",
    "beregening_installatie_highend":             "Beregening",
    "beregening_gazon_basis_per_m2":              "Beregening",
    "beregening_gazon_volautomatisch_per_m2":     "Beregening",
    "beregening_gazon_highend_per_m2":            "Beregening",
    "beregening_beplanting_basis_per_m2":         "Beregening",
    "beregening_beplanting_volautomatisch_per_m2":"Beregening",
    "beregening_beplanting_highend_per_m2":       "Beregening",
    "overkapping_per_m2":               "Overkapping",
    "verlichting_basis_per_stuk":       "Verlichting",
    "vlonder_zachthout_per_m2":         "Vlonder",
    "vlonder_hardhout_per_m2":          "Vlonder",
    "vlonder_composiet_per_m2":         "Vlonder",
}
_EXTRA_DISCLAIMERS: Dict[str, str] = {
    "Erfafscheiding": "Varieert door: soort, hoogte, ondergrond en bereikbaarheid.",
    "Beregening":     "Afhankelijk van aantal zones, pomp, waterpunt en besturing.",
    "Overkapping":    "Sterk afhankelijk van houtsoort, maatwerk en benodigde fundering.",
    "Verlichting":    "Basis installatie: 3 armaturen incl. trafo en bekabeling. Uitbreiding mogelijk op offerte.",
    "Vlonder":        "Varieert door: hoogteverschillen, fundering en afwerkingsdetails.",
}


_SYSTEEM_MAP = {"basis": "basis", "volautomatisch": "volautomatisch", "highend": "highend"}

def _beregening_key(gebied: str, systeem: str) -> str:
    """Geeft de juiste prijssleutel terug op basis van gebied (gazon/beplanting) en systeem."""
    g = "gazon" if gebied == "gazon" else "beplanting"
    s = _SYSTEEM_MAP.get((systeem or "").strip().lower(), "volautomatisch")
    return f"beregening_{g}_{s}_per_m2"

def _beregening_installatie_key(systeem: str) -> str:
    s = _SYSTEEM_MAP.get((systeem or "").strip().lower(), "volautomatisch")
    return f"beregening_installatie_{s}"


def _fmt_item(item: Dict[str, Any]) -> str:
    label = item.get("label", "Onderdeel")
    rng   = item.get("range_eur")
    qty   = item.get("qty")
    unit  = item.get("unit", "")
    if rng is None:
        return f"- {label}: wordt meegenomen in de offerte"
    unit_lbl = unit.replace("€/", "").replace("€ ", "").strip() if unit else ""
    qty_txt  = f" ({qty} {unit_lbl})" if qty is not None and unit_lbl else ""
    return f"- {label}{qty_txt}: €{int(rng[0]):,} – €{int(rng[1]):,}".replace(",", ".")


def format_breakdown_grouped(breakdown: List[Dict[str, Any]]) -> str:
    bestrating: List[Dict] = []
    grondwerk:  List[Dict] = []
    groen:      List[Dict] = []
    extras:     Dict[str, List[Dict]] = {}

    for item in breakdown:
        key = item.get("key")
        if key in _BESTRATING_KEYS:
            bestrating.append(item)
        elif key in _GRONDWERK_KEYS:
            grondwerk.append(item)
        elif key in _GROEN_KEYS:
            groen.append(item)
        elif key in _EXTRA_KEY_GROUP:
            extras.setdefault(_EXTRA_KEY_GROUP[key], []).append(item)
        else:
            extras.setdefault(item.get("label", "Overig"), []).append(item)

    lines: List[str] = []

    if grondwerk:
        lines.append("**Grondwerk & fundering t.b.v. bestrating:**")
        lines.append("_Varieert door: bereikbaarheid, grondsoort en afvoermogelijkheden._")
        lines.append("")
        for item in grondwerk:
            lines.append(_fmt_item(item))

    if bestrating:
        lines.append("")
        lines.append("**Bestrating:**")
        lines.append("_Prijs varieert o.a. door: tegelsoort, hoeken/randen, bereikbaarheid en afwatering._")
        lines.append("")
        for item in bestrating:
            lines.append(_fmt_item(item))

    if groen:
        lines.append("")
        lines.append("**Groen:**")
        lines.append("_Varieert door: soort, staat van de bodem en egaliseerwerk._")
        lines.append("")
        for item in groen:
            lines.append(_fmt_item(item))

    for group_name, items in extras.items():
        lines.append("")
        lines.append(f"**{group_name}:**")
        disclaimer = _EXTRA_DISCLAIMERS.get(group_name)
        if disclaimer:
            lines.append(f"_{disclaimer}_")
        lines.append("")
        for item in items:
            lines.append(_fmt_item(item))

    while lines and lines[-1] == "":
        lines.pop()

    lines.append("")
    lines.append("**Sloopwerk & verwijdering bestaande tuin:**")
    lines.append("_Nader te bepalen na een inspectiebezoek. Sterk afhankelijk van de bestaande situatie (bestrating, beplanting, gazon, schuttingen, etc.)._")
    lines.append("_Overweegt u zelf de tuin leeg te halen? Dit kan de sloopkosten aanzienlijk verlagen — vraag ernaar bij het gesprek._")

    return "\n".join(lines)


# ============================================================
# ✅ NIEUW: Overzicht van gekozen opties (klantvriendelijk)
#    - gebruikt costs["inputs"] (die jij al teruggeeft)
# ============================================================
def _format_v2_choices(inputs: Dict[str, Any]) -> str:
    """Klantvriendelijke samenvatting voor V2-flow (directe m²-invoer)."""
    lines: List[str] = ["🧾 **Uw gekozen uitgangspunten**"]

    def _m2(v: Any) -> str:
        try:
            return f"ca. {int(round(float(v)))} m²"
        except Exception:
            return "?"

    def _mat(m: Any) -> str:
        return {
            "grind": "Grind", "beton": "Beton klinkers",
            "gebakken": "Gebakken klinkers", "keramiek": "Keramische tegels",
        }.get((m or "").strip().lower(), "Beton klinkers")

    tuin_m2 = inputs.get("tuin_m2")

    if tuin_m2:
        lines.append(f"- Tuinoppervlak: {_m2(tuin_m2)}")

    oprit_v = float(inputs.get("_direct_oprit_m2") or 0)
    if oprit_v > 0.01:
        lines.append(f"- Oprit: {_m2(oprit_v)} ({_mat(inputs.get('materiaal_oprit'))})")

    terras_v = float(inputs.get("_direct_terras_m2") or 0)
    terras_extras = [(float(it.get("m2") or 0), it.get("materiaal"))
                     for it in (inputs.get("terras_extra_items") or [])
                     if float(it.get("m2") or 0) > 0.01]
    if terras_v > 0.01 and terras_extras:
        lines.append(f"- Terras 1: {_m2(terras_v)} ({_mat(inputs.get('materiaal_terras'))})")
        for i, (m, mat) in enumerate(terras_extras, 2):
            lines.append(f"- Terras {i}: {_m2(m)} ({_mat(mat)})")
    elif terras_v > 0.01:
        lines.append(f"- Terras: {_m2(terras_v)} ({_mat(inputs.get('materiaal_terras'))})")

    paden_v = float(inputs.get("_direct_paden_m2") or 0)
    paden_extras = [(float(it.get("m2") or 0), it.get("materiaal"))
                    for it in (inputs.get("paden_extra_items") or [])
                    if float(it.get("m2") or 0) > 0.01]
    if paden_v > 0.01 and paden_extras:
        lines.append(f"- Paden 1: {_m2(paden_v)} ({_mat(inputs.get('materiaal_paden'))})")
        for i, (m, mat) in enumerate(paden_extras, 2):
            lines.append(f"- Paden {i}: {_m2(m)} ({_mat(mat)})")
    elif paden_v > 0.01:
        lines.append(f"- Paden: {_m2(paden_v)} ({_mat(inputs.get('materiaal_paden'))})")

    for key, label in (("_direct_gazon_m2", "Gazon"), ("_direct_beplanting_m2", "Beplanting")):
        v = float(inputs.get(key) or 0)
        if v > 0.01:
            lines.append(f"- {label}: {_m2(v)}")

    extras: List[str] = []
    if inputs.get("onkruidwerend_gevoegd") is True:
        extras.append("Bestrating gevoegd (onkruidwerend)")
    if inputs.get("overkapping") is True:
        ov = inputs.get("overkapping_m2")
        extras.append(f"Overkapping (ca. {int(round(float(ov or 15)))} m²)")
    if inputs.get("verlichting") is True:
        extras.append("Tuinverlichting (basis)")
    overige = inputs.get("overige_wensen") or []
    overige_clean = [str(x).strip().lower() for x in overige if str(x).strip()]
    scope = (inputs.get("beregening_scope") or "").lower()
    if "beregening" in overige_clean:
        scope_txt = {"gazon": "alleen gazon", "beplanting": "alleen beplanting"}.get(scope, "gazon én beplanting")
        extras.append(f"Beregening ({scope_txt})")
    vt = (inputs.get("vlonder_type") or "").lower()
    if "vlonder" in overige_clean:
        extras.append(f"Vlonder ({vt})" if vt else "Vlonder")
    erf_items_v2 = inputs.get("erfafscheiding_items") or []
    for it in erf_items_v2:
        t = (it.get("type") or "").strip().lower()
        m = int(it.get("meter") or 0)
        if t == "haag":
            haag_type = (it.get("haag_type") or "voordelig_hoog").strip().lower()
            haag_lbl = {
                "voordelig_laag": "voordelig laag (0,5–1m)",
                "voordelig_hoog": "voordelig hoog (1,5–2m)",
                "premium_laag":   "premium laag (0,5–1m)",
                "premium_hoog":   "premium hoog (1,5–2m)",
            }.get(haag_type, haag_type)
            lines.append(f"- Haag {haag_lbl}: {m} m")
        elif t == "betonschutting":
            lines.append(f"- Betonschutting: {m} m")
        elif t == "design_schutting":
            lines.append(f"- Design schutting: {m} m")

    if extras:
        lines.append("- Extra's:")
        for ex in extras:
            lines.append(f"  - {ex}")

    return "\n".join(lines)


def format_tuinaanleg_choices_for_customer(costs: Dict[str, Any]) -> str:
    """
    Maakt een compacte opsomming van alle relevante gekozen opties uit costs['inputs'].
    Bedoeld om BOVEN de prijsindicatie te tonen.
    """
    inputs = (costs or {}).get("inputs") or {}
    if not inputs:
        return ""

    if inputs.get("_flow_version") == "v2":
        return _format_v2_choices(inputs)

    def _pct(v: Any) -> str:
        try:
            return f"{int(v)}%"
        except Exception:
            return ""

    def _mat_label(m: str | None) -> str:
        return {
            "grind": "Grind",
            "beton": "Beton",
            "gebakken": "Gebakken klinkers",
            "keramiek": "Keramiek",
            "": "Beton",
            None: "Beton",
        }.get((m or "").strip().lower(), "Beton")

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

    # Pre-bereken m² op basis van tuin_m2 en ratios
    _t = float(tuin_m2 or 0)
    _share_bg_map = {"70_30": 0.70, "50_50": 0.50, "30_70": 0.30}
    _paving_sh = float(b_pct or 50) / 100.0 if ratio_bg == "custom" else _share_bg_map.get(ratio_bg or "", 0.50)
    _paving_m2 = _t * _paving_sh if _t > 0 else 0.0
    _green_m2  = _t - _paving_m2 if _t > 0 else 0.0

    _share_gb_map = {"70_30": 0.70, "50_50": 0.50, "30_70": 0.30}
    _gazon_sh = (float(ga_pct) / 100.0 if ga_pct is not None else 0.5) if ratio_gb == "custom" else _share_gb_map.get(ratio_gb or "", 0.50)
    _gazon_m2      = _green_m2 * _gazon_sh      if _green_m2 > 0 else 0.0
    _beplanting_m2 = _green_m2 - _gazon_m2      if _green_m2 > 0 else 0.0

    # bestrating/groen
    if ratio_bg:
        if _t > 0:
            lines.append(f"- Verdeling bestrating / groen: ca. {int(round(_paving_m2))} m² bestrating – {int(round(_green_m2))} m² groen")
        elif ratio_bg == "custom" and b_pct is not None and g_pct is not None:
            lines.append(f"- Verdeling bestrating / groen: {_pct(b_pct)} bestrating – {_pct(g_pct)} groen")
        elif ratio_bg in {"70_30", "50_50", "30_70"}:
            a, b = ratio_bg.split("_", 1)
            lines.append(f"- Verdeling bestrating / groen: {a}% bestrating – {b}% groen")

    # gazon/beplanting
    if ratio_gb:
        if _green_m2 > 0:
            lines.append(f"- Groen: ca. {int(round(_gazon_m2))} m² gazon – {int(round(_beplanting_m2))} m² beplanting")
        elif ratio_gb == "custom" and ga_pct is not None and bp_pct is not None:
            lines.append(f"- Groen: {_pct(ga_pct)} gazon – {_pct(bp_pct)} beplanting")
        elif ratio_gb in {"70_30", "50_50", "30_70"}:
            a, b = ratio_gb.split("_", 1)
            lines.append(f"- Groen: {a}% gazon – {b}% beplanting")

    # bestrating: oprit/paden/terras + materiaal
    parts: List[str] = []
    try:
        o = int(oprit_pct) if oprit_pct is not None else 0
        p = int(paden_pct) if paden_pct is not None else 0
        t = int(terras_pct) if terras_pct is not None else 0
    except Exception:
        o, p, t = 0, 0, 100

    def _m2_label(pct: int, mat: str | None) -> str:
        if _paving_m2 > 0:
            return f"ca. {int(round(_paving_m2 * pct / 100))} m² ({_mat_label(mat)})"
        return f"{pct}% ({_mat_label(mat)})"

    if o > 0:
        parts.append(f"Oprit: {_m2_label(o, mat_oprit)}")
    if p > 0:
        parts.append(f"Paden: {_m2_label(p, mat_paden)}")
    if t > 0:
        parts.append(f"Terras: {_m2_label(t, mat_terras)}")

    if parts:
        lines.append("- Bestrating:")
        for it in parts:
            lines.append(f"  - {it}")

    # extra's (compact)
    extras: List[str] = []
    if voegen:
        extras.append("Bestrating gevoegd (onkruidwerend)")
    if overkapping:
        ov_m2 = inputs.get("overkapping_m2")
        if ov_m2:
            try:
                extras.append(f"Overkapping (ca. {int(round(float(ov_m2)))} m²)")
            except Exception:
                extras.append("Overkapping")
        else:
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
            extras.append(f"Vlonder 1 ({vlonder_type})")
        else:
            extras.append("Vlonder")
        for i, ex in enumerate(inputs.get("vlonder_extra_items") or [], 2):
            ex_type = ex.get("type") or ""
            extras.append(f"Vlonder {i} ({ex_type})" if ex_type else f"Vlonder {i}")

    erf_items_v1 = inputs.get("erfafscheiding_items") or []
    for it in erf_items_v1:
        t = (it.get("type") or "").strip().lower()
        m = int(it.get("meter") or 0)
        if t == "haag":
            haag_type = (it.get("haag_type") or "voordelig_hoog").strip().lower()
            haag_lbl = {
                "voordelig_laag": "voordelig laag (0,5–1m)",
                "voordelig_hoog": "voordelig hoog (1,5–2m)",
                "premium_laag":   "premium laag (0,5–1m)",
                "premium_hoog":   "premium hoog (1,5–2m)",
            }.get(haag_type, haag_type)
            extras.append(f"Haag {haag_lbl}: {m} m")
        elif t == "betonschutting":
            extras.append(f"Betonschutting: {m} m")
        elif t == "design_schutting":
            extras.append(f"Design schutting: {m} m")
    if erf_count and int(erf_count) > 0 and not erf_items_v1:
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
def estimate_tuinaanleg_costs(answers: Dict[str, Any], price_table=None) -> Dict[str, Any]:
    from core.pricing.price_table import DEFAULT_PRICE_TABLE
    p = price_table or DEFAULT_PRICE_TABLE
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
    terras_extra_items = [
        (float(it.get("m2") or 0), (it.get("materiaal") or "beton").strip().lower())
        for it in (answers.get("terras_extra_items") or [])
        if float(it.get("m2") or 0) > 0.01
    ]
    paden_extra_items = [
        (float(it.get("m2") or 0), (it.get("materiaal") or "beton").strip().lower())
        for it in (answers.get("paden_extra_items") or [])
        if float(it.get("m2") or 0) > 0.01
    ]

    overige_clean = [str(x).strip().lower() for x in overige if str(x).strip()]

    breakdown: List[Dict[str, Any]] = []
    total: Tuple[float, float] = (0.0, 0.0)

    # 1) Verhouding bestrating/groen -> schatting bestratingsm²
    share_map_bg = {"70_30": 0.70, "50_50": 0.50, "30_70": 0.30}
    if ratio_bg == "custom":
        bpct = answers.get("bestrating_pct")
        paving_share = float(bpct if bpct is not None else 50) / 100.0
    else:
        paving_share = share_map_bg.get(ratio_bg, 0.50)
    paving_m2 = m2 * paving_share
    bestrating_factor = p.schaal_factor(paving_m2, "bestrating")

    # Groenoppervlak
    green_m2 = max(0.0, m2 - paving_m2)

    # 2) Groen verdeling gazon/beplanting
    share_map_gb = {"70_30": 0.70, "50_50": 0.50, "30_70": 0.30}  # aandeel gazon
    if ratio_gb == "custom":
        gazon_pct_raw = answers.get("gazon_pct")
        gazon_share = (float(gazon_pct_raw) / 100.0) if gazon_pct_raw is not None else 0.5
    else:
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
        if material == "gebakken":
            return "gebakken_straatwerk_per_m2"
        return "beton_straatwerk_per_m2"

    def material_pretty(material: str) -> str:
        material = (material or "").strip().lower()
        if material == "keramiek":
            return "Keramiek"
        if material == "grind":
            return "Grind"
        if material == "gebakken":
            return "Gebakken klinkers"
        return "Beton"

    def add_surface_cost(part_label: str, m2_part: float, material: str, factor: float = 1.0) -> None:
        nonlocal total
        if m2_part <= 0.01:
            return

        key = material_to_key(material)
        unit_range = PRIJZEN.get(key, (60, 120))
        rng = _range_mul((float(unit_range[0]), float(unit_range[1])), m2_part)
        if factor < 1.0:
            rng = (rng[0] * factor, rng[1] * factor)
        total = _range_add(total, rng)

        notes = "Indicatief; materiaalprijs, onderbouw/fundering, snijwerk en complexiteit beïnvloeden de prijs."
        breakdown.append({
            "key": key,
            "label": f"{part_label} – {material_pretty(material)}",
            "unit": _unit(key, "€/m²"),
            "qty": int(round(m2_part)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": notes,
        })

    add_surface_cost("Oprit", oprit_m2, mat_oprit, bestrating_factor)

    if paden_extra_items:
        direct_p1 = float(answers.get("_direct_paden_m2") or 0)
        pad1_m2 = direct_p1 if direct_p1 > 0.01 else paden_m2
        add_surface_cost("Paden 1", pad1_m2, mat_paden, bestrating_factor)
        for i, (m, mat) in enumerate(paden_extra_items, 2):
            add_surface_cost(f"Paden {i}", m, mat, bestrating_factor)
    else:
        add_surface_cost("Paden", paden_m2, mat_paden, bestrating_factor)

    if terras_extra_items:
        direct_t1 = float(answers.get("_direct_terras_m2") or 0)
        terras1_m2 = direct_t1 if direct_t1 > 0.01 else terras_m2
        add_surface_cost("Terras 1", terras1_m2, mat_terras, bestrating_factor)
        for i, (m, mat) in enumerate(terras_extra_items, 2):
            add_surface_cost(f"Terras {i}", m, mat, bestrating_factor)
    else:
        add_surface_cost("Terras", terras_m2, mat_terras, bestrating_factor)

    # Straatwerk m² voor zaagwerk — per onderdeel en materiaal
    straatwerk_m2 = 0.0
    if mat_oprit != "grind":
        straatwerk_m2 += float(oprit_m2)
    _pad1_m2 = float(answers.get("_direct_paden_m2") or 0) if paden_extra_items else float(paden_m2)
    if mat_paden != "grind":
        straatwerk_m2 += _pad1_m2
    for m, mat in paden_extra_items:
        if mat != "grind":
            straatwerk_m2 += m
    _terras1_m2 = float(answers.get("_direct_terras_m2") or 0) if terras_extra_items else float(terras_m2)
    if mat_terras != "grind":
        straatwerk_m2 += _terras1_m2
    for m, mat in terras_extra_items:
        if mat != "grind":
            straatwerk_m2 += m

    # ------------------------------------------------------------
    # ✅ 3a) Grondwerk (altijd): m² -> m³ en koppelen aan pricing keys
    # ------------------------------------------------------------
    def add_volume_cost(label: str, key: str, m3: float, notes: str, factor: float = 1.0) -> None:
        nonlocal total
        if m3 <= 0.0001:
            return
        unit_range = PRIJZEN.get(key)
        if not unit_range:
            return

        m3 = _round_to_half(m3)
        rng = _range_mul((float(unit_range[0]), float(unit_range[1])), m3)
        if factor < 1.0:
            rng = (rng[0] * factor, rng[1] * factor)
        total = _range_add(total, rng)

        breakdown.append({
            "key": key,
            "label": label,
            "unit": _unit(key, "€/m³"),
            "qty": m3,
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": notes,
        })

    grond_afvoer_key = "grond_afvoer_per_m3"
    zand_key = "zand_aanvoer_per_m3"
    puin_key = "puin_aanvoer_per_m3"

    # Paden + Terras: afvoer + zand (dieptes uit GRONDWERK_DIEPTES)
    # Keramiek gebruikt een dunner grondpakket (drainage mortel in m²-prijs)
    _gd = p.grondwerk_dieptes
    oprit_m2_f = float(oprit_m2)

    def _ker_split(base_m2: float, base_mat: str, extra_items: list) -> tuple:
        """Geeft (keramiek_m2, standaard_m2) terug."""
        k = base_m2 if base_mat == "keramiek" else 0.0
        s = base_m2 if base_mat != "keramiek" else 0.0
        for m, mat in extra_items:
            if mat == "keramiek":
                k += m
            else:
                s += m
        return k, s

    _paden_ker, _paden_std = _ker_split(float(paden_m2), mat_paden, paden_extra_items)
    _terras_ker, _terras_std = _ker_split(float(terras_m2), mat_terras, terras_extra_items)
    _ker_m2 = _paden_ker + _terras_ker
    _std_m2 = _paden_std + _terras_std

    grond_afvoer_paden_terras_m3 = (
        _std_m2 * _gd["paden_terras_afvoer"]
        + _ker_m2 * _gd["paden_terras_afvoer_keramiek"]
    )
    zand_paden_terras_m3 = (
        _std_m2 * _gd["paden_terras_zand"]
        + _ker_m2 * _gd["paden_terras_zand_keramiek"]
    )

    # Totaal grondwerkvolume bepaalt de machinekeuze → schaalfactor
    _total_grw_m3 = _round_to_half(
        grond_afvoer_paden_terras_m3 + zand_paden_terras_m3
        + oprit_m2_f * (_gd["oprit_afvoer"] + _gd["oprit_puin"] + _gd["oprit_zand"])
    )
    grondwerk_factor = p.schaal_factor(_total_grw_m3, "grondwerk")

    add_volume_cost(
        label="Grond afvoer – paden/terras",
        key=grond_afvoer_key,
        m3=grond_afvoer_paden_terras_m3,
        notes="Aanname: 15 cm (keramiek met drainage mortel) of 20 cm (overige materialen).",
        factor=grondwerk_factor,
    )

    add_volume_cost(
        label="Zand aanvoer – paden/terras",
        key=zand_key,
        m3=zand_paden_terras_m3,
        notes="Aanname: 10 cm (keramiek) of 15 cm (overige materialen).",
        factor=grondwerk_factor,
    )

    # Oprit: afvoer, puin, zand (dieptes uit GRONDWERK_DIEPTES)
    grond_afvoer_oprit_m3 = oprit_m2_f * _gd["oprit_afvoer"]
    add_volume_cost(
        label="Grond afvoer – oprit (35 cm)",
        key=grond_afvoer_key,
        m3=grond_afvoer_oprit_m3,
        notes="Aannames: 0,35 m ontgraven per m² voor oprit.",
        factor=grondwerk_factor,
    )

    puin_oprit_m3 = oprit_m2_f * _gd["oprit_puin"]
    add_volume_cost(
        label="Puin aanvoer – oprit (25 cm)",
        key=puin_key,
        m3=puin_oprit_m3,
        notes="Aannames: 0,25 m puin per m² voor oprit.",
        factor=grondwerk_factor,
    )

    zand_oprit_m3 = oprit_m2_f * _gd["oprit_zand"]
    add_volume_cost(
        label="Zand aanvoer – oprit (5 cm)",
        key=zand_key,
        m3=zand_oprit_m3,
        notes="Aannames: 0,05 m zand per m² voor oprit.",
        factor=grondwerk_factor,
    )

    # ------------------------------------------------------------
    # 3b) Zaagwerk
    # ------------------------------------------------------------
    zaag_m1_min = 0.0
    zaag_m1_max = 0.0
    if straatwerk_m2 > 0.01:
        zaag_key = "zaagwerk_per_m1"
        zaag_unit_range = PRIJZEN.get(zaag_key, (35, 65))

        zaag_m1 = straatwerk_m2 * 0.35

        zaag_range = (
            float(zaag_unit_range[0]) * zaag_m1,
            float(zaag_unit_range[1]) * zaag_m1,
        )
        total = _range_add(total, zaag_range)

        breakdown.append({
            "key": zaag_key,
            "label": _label(zaag_key, "Zaagwerk"),
            "unit": _unit(zaag_key, "€/m¹"),
            "qty": int(round(zaag_m1)),
            "range_eur": [_eur(zaag_range[0]), _eur(zaag_range[1])],
            "notes": "Schatting op basis van 35% van straatwerk (randen, hoeken en obstakels)."
        })

    # ------------------------------------------------------------
    # 4) Gazon (graszoden)
    # ------------------------------------------------------------
    if gazon_m2 > 0:
        gazon_key = "graszoden_per_m2"
        gazon_unit_range = p.get(gazon_key, (15, 25))
        gazon_factor = p.schaal_factor(gazon_m2, "groen")
        gazon_range = _range_mul((float(gazon_unit_range[0]), float(gazon_unit_range[1])), gazon_m2)
        if gazon_factor < 1.0:
            gazon_range = (gazon_range[0] * gazon_factor, gazon_range[1] * gazon_factor)
        total = _range_add(total, gazon_range)

        gazon_notes = "Indicatief; afhankelijk van ondergrond, egaliseren en bereikbaarheid."
        breakdown.append({
            "key": gazon_key,
            "label": _label(gazon_key, "Graszoden"),
            "unit": _unit(gazon_key, "€/m²"),
            "qty": int(round(gazon_m2)),
            "range_eur": [_eur(gazon_range[0]), _eur(gazon_range[1])],
            "notes": gazon_notes,
        })

    # ------------------------------------------------------------
    # 5) Beplanting (borders)
    # ------------------------------------------------------------
    if border_m2 > 0:
        border_key = "beplanting_border_per_m2"
        border_unit_range = PRIJZEN.get(border_key, (30, 40))
        border_factor = _schaal_factor(border_m2, "groen")
        border_range = _range_mul((float(border_unit_range[0]), float(border_unit_range[1])), border_m2)
        if border_factor < 1.0:
            border_range = (border_range[0] * border_factor, border_range[1] * border_factor)
        total = _range_add(total, border_range)

        border_notes = "Indicatief; soort, ondergrond, beplanting en plantdichtheid beïnvloeden de prijs."
        breakdown.append({
            "key": border_key,
            "label": _label(border_key, "Beplanting border"),
            "unit": _unit(border_key, "€/m²"),
            "qty": int(round(border_m2)),
            "range_eur": [_eur(border_range[0]), _eur(border_range[1])],
            "notes": border_notes,
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
                haag_type = (it.get("haag_type") or "voordelig_hoog").strip().lower()
                key = {
                    "voordelig_laag": "beplanting_haag_voordelig_laag_per_m1",
                    "voordelig_hoog": "beplanting_haag_voordelig_hoog_per_m1",
                    "premium_laag":   "beplanting_haag_premium_laag_per_m1",
                    "premium_hoog":   "beplanting_haag_premium_hoog_per_m1",
                }.get(haag_type, "beplanting_haag_voordelig_hoog_per_m1")
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

            if key and p.get(key) != (0, 0):
                unit_range = p[key]
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

        if poortdeur_count > 0 and p.get("plaatsen_poortdeur_per_st") != (0, 0):
            pk = "plaatsen_poortdeur_per_st"
            pr = p[pk]
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
    # ✅ 5c) Beregening (per m²) op basis van scope + systeem
    # ------------------------------------------------------------
    if "beregening" in overige_clean:
        beregening_systeem = (answers.get("beregening_systeem") or "volautomatisch").strip().lower()

        inst_key = _beregening_installatie_key(beregening_systeem)
        inst_ur = PRIJZEN.get(inst_key, (800, 1200))
        total = _range_add(total, (float(inst_ur[0]), float(inst_ur[1])))
        breakdown.append({
            "key": inst_key,
            "label": _label(inst_key, "Technische installatie & opstartkosten"),
            "unit": "€ vast",
            "qty": 1,
            "range_eur": [_eur(inst_ur[0]), _eur(inst_ur[1])],
            "notes": "Pomp, besturingscomputer, aansluiting waterpunt en ingebruikstelling. Vaste post ongeacht het aantal m².",
        })

        ber_gebieden = []
        if beregening_scope == "gazon":
            ber_gebieden = [("gazon", gazon_m2, "alleen gazon")]
        elif beregening_scope == "beplanting":
            ber_gebieden = [("beplanting", border_m2, "alleen beplanting")]
        else:
            ber_gebieden = [("gazon", gazon_m2, "gazon"), ("beplanting", border_m2, "beplanting")]

        for gebied, ber_m2, scope_txt in ber_gebieden:
            if ber_m2 <= 0.01:
                continue
            key = _beregening_key(gebied, beregening_systeem)
            ur = PRIJZEN.get(key, (8, 13))
            rng = _range_mul((float(ur[0]), float(ur[1])), ber_m2)
            total = _range_add(total, rng)
            breakdown.append({
                "key": key,
                "label": _label(key, "Beregening"),
                "unit": _unit(key, "€/m²"),
                "qty": int(round(ber_m2)),
                "range_eur": [_eur(rng[0]), _eur(rng[1])],
                "notes": f"Indicatief; berekend over {scope_txt}. Afhankelijk van zones en leidingwerk.",
            })

        overige_clean = [x for x in overige_clean if x != "beregening"]

    # ------------------------------------------------------------
    # 6) Voegen (per m²) — alleen paden/terras met beton of keramiek
    # ------------------------------------------------------------
    voegen_m2 = 0.0
    if mat_paden in ("beton", "keramiek"):
        voegen_m2 += _pad1_m2
    for m, mat in paden_extra_items:
        if mat in ("beton", "keramiek"):
            voegen_m2 += m
    if mat_terras in ("beton", "keramiek"):
        voegen_m2 += _terras1_m2
    for m, mat in terras_extra_items:
        if mat in ("beton", "keramiek"):
            voegen_m2 += m
    if voegen and voegen_m2 > 0.01:
        voeg_key = "voegen_straatwerk_per_m2"
        voeg_unit_range = PRIJZEN.get(voeg_key, (15, 20))

        voeg_range = _range_mul((float(voeg_unit_range[0]), float(voeg_unit_range[1])), voegen_m2)
        total = _range_add(total, voeg_range)

        breakdown.append({
            "key": voeg_key,
            "label": _label(voeg_key, "Voegen straatwerk"),
            "unit": _unit(voeg_key, "€/m²"),
            "qty": int(round(voegen_m2)),
            "range_eur": [_eur(voeg_range[0]), _eur(voeg_range[1])],
            "notes": "Indicatief; voegwerk berekend over paden/terras met beton of keramiek."
        })

    # ------------------------------------------------------------
    # 7) Overkapping (per m²)
    # ------------------------------------------------------------
    if overkapping:
        ov_key = "overkapping_per_m2"
        ov_m2 = float(answers.get("overkapping_m2") or 15.0)
        ov_unit = PRIJZEN.get(ov_key, (650, 1000))
        ov_range = _range_mul((float(ov_unit[0]), float(ov_unit[1])), ov_m2)
        total = _range_add(total, ov_range)

        breakdown.append({
            "key": ov_key,
            "label": "Overkapping",
            "unit": "€/m²",
            "qty": int(round(ov_m2)),
            "range_eur": [_eur(ov_range[0]), _eur(ov_range[1])],
            "notes": "Fundering, maatwerk en afwerkingsgraad beïnvloeden de prijs."
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
        _vlonder_m2_raw = float(answers.get("vlonder_m2") or 0)
        if _vlonder_m2_raw > 0:
            vlonder_m2 = _vlonder_m2_raw
            _vlonder_notes = "Schatting o.b.v. opgegeven oppervlak; fundering en afwerking kunnen variëren."
        else:
            vlonder_m2 = min(12.0, max(6.0, 0.12 * m2))
            _vlonder_notes = (
                f"Geen oppervlakte opgegeven. Indicatief berekend op ca. {int(round(vlonder_m2))} m². "
                "Geef uw eigen m² op voor een nauwkeurigere indicatie."
            )

        if vlonder_type == "zachthout":
            vlonder_key = "vlonder_zachthout_per_m2"
        elif vlonder_type == "hardhout":
            vlonder_key = "vlonder_hardhout_per_m2"
        else:
            vlonder_key = "vlonder_composiet_per_m2"

        vlonder_factor = p.schaal_factor(vlonder_m2, "vlonder")
        unit_range = PRIJZEN.get(vlonder_key, (280, 350))
        rng = _range_mul((float(unit_range[0]), float(unit_range[1])), vlonder_m2)
        if vlonder_factor < 1.0:
            rng = (rng[0] * vlonder_factor, rng[1] * vlonder_factor)
        total = _range_add(total, rng)

        breakdown.append({
            "key": vlonder_key,
            "label": _label(vlonder_key, "Vlonder"),
            "unit": _unit(vlonder_key, "€/m²"),
            "qty": int(round(vlonder_m2)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": _vlonder_notes,
        })

        # Extra vlonders
        for i, ex in enumerate(answers.get("vlonder_extra_items") or [], 2):
            ex_m2 = float(ex.get("m2") or 0)
            if ex_m2 <= 0:
                continue
            ex_type = (ex.get("type") or "composiet").strip().lower()
            if ex_type == "zachthout":
                ex_key = "vlonder_zachthout_per_m2"
            elif ex_type == "hardhout":
                ex_key = "vlonder_hardhout_per_m2"
            else:
                ex_key = "vlonder_composiet_per_m2"
            ex_ur = PRIJZEN.get(ex_key, (280, 350))
            ex_rng = _range_mul((float(ex_ur[0]), float(ex_ur[1])), ex_m2)
            total = _range_add(total, ex_rng)
            breakdown.append({
                "key": ex_key,
                "label": f"Vlonder {i} ({ex_type})",
                "unit": "€/m²",
                "qty": int(round(ex_m2)),
                "range_eur": [_eur(ex_rng[0]), _eur(ex_rng[1])],
                "notes": "Schatting o.b.v. opgegeven oppervlak; fundering en afwerking kunnen variëren.",
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
    # Combineer grondwerk regels + sorteer (gedeelde helpers)
    # ------------------------------------------------------------
    breakdown = _aggregate_grondwerk(breakdown)
    breakdown = _sort_breakdown_grondwerk_first(breakdown)

    # Minimumprijs: elk project kost minimaal €250
    _MIN_PROJECT = 250
    _minimum_applied = total[0] < _MIN_PROJECT
    total = (max(total[0], _MIN_PROJECT), max(total[1], _MIN_PROJECT))

    return {
        "total_range_eur": [_eur(total[0]), _eur(total[1])],
        "minimum_applied": _minimum_applied,
        "breakdown": breakdown,
        "inputs": {
            "tuin_m2": m2,
            "verhouding_bestrating_groen": ratio_bg,
            "verhouding_gazon_beplanting": ratio_gb,
            "bestrating_pct": int(float(answers.get("bestrating_pct") or 0)) if ratio_bg == "custom" else None,
            "groen_pct": int(float(answers.get("groen_pct") or 0)) if ratio_bg == "custom" else None,
            "gazon_pct": int(float(answers.get("gazon_pct") or 0)) if ratio_gb == "custom" else None,
            "beplanting_pct": int(float(answers.get("beplanting_pct") or 0)) if ratio_gb == "custom" else None,
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
            "overkapping_m2": float(answers.get("overkapping_m2") or 15.0) if overkapping else None,
            "verlichting": verlichting,
            "overige_wensen": overige,
            "vlonder_type": vlonder_type,
            "materiaal_oprit": mat_oprit,
            "materiaal_paden": mat_paden,
            "materiaal_terras": mat_terras,
            "beregening_scope": beregening_scope,
            "erfafscheiding_items_count": len(items) if erf_gevraagd else 0,
            "erfafscheiding_items": list(items) if erf_gevraagd else [],
            # V2 passthrough (present only when called from TuinaanlegFlowV2.to_answers)
            "_flow_version": answers.get("_flow_version"),
            "_direct_oprit_m2": answers.get("_direct_oprit_m2"),
            "_direct_terras_m2": answers.get("_direct_terras_m2"),
            "_direct_paden_m2": answers.get("_direct_paden_m2"),
            "_direct_gazon_m2": answers.get("_direct_gazon_m2"),
            "_direct_beplanting_m2": answers.get("_direct_beplanting_m2"),
            "style_tuin": answers.get("style_tuin"),
            "stijl_voorkeur": answers.get("stijl_voorkeur"),
            "fase": answers.get("fase"),
            "prioriteit": answers.get("prioriteit"),
            "terras_extra_items": answers.get("terras_extra_items") or [],
            "paden_extra_items": answers.get("paden_extra_items") or [],
            "vlonder_extra_items": answers.get("vlonder_extra_items") or [],
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
    lines.append("✅ **Eerste schatting**")
    lines.append(
        "Bedankt voor uw antwoorden. Op basis van uw keuzes volgt hier een eerste indicatie."
    )
    lines.append("")

    # ✅ 2) geruststelling vóór bedragen
    lines.append(
        "_Iedere tuin is uniek. Deze schatting is een richtprijs, "
        "geen definitieve offerte._"
    )
    lines.append("")

    lines.append(f"**Totale indicatie:** {eur(int(total_min))} – {eur(int(total_max))} _(incl. BTW)_")
    if costs.get("minimum_applied"):
        lines.append(
            "_ℹ️ Op dit project is een minimumprijs van €250 van toepassing, "
            "omdat de berekende kosten hieronder uitkwamen._"
        )
    lines.append("")
    lines.append(f"_{PRIJSTOELICHTING}_")
    lines.append("")
    lines.append("")

    lines.append(format_breakdown_grouped(costs.get("breakdown", [])))
    lines.append("")
    lines.append(
        "_Deze schatting is gebaseerd op aannames en is inclusief arbeid en standaard materialen._"
    )
    lines.append("")
    return "\n".join(lines)


# ============================================================
# Chat HTML formatter — identiek aan mail-layout
# ============================================================

def _cp_choices_html(costs: Dict[str, Any], flow_type: str) -> str:
    try:
        if flow_type == "gehele_tuin":
            md = format_tuinaanleg_choices_for_customer(costs)
        else:
            md = format_losse_onderdelen_choices_for_customer(costs)
    except Exception:
        return ""
    if not md:
        return ""

    items: List[str] = []
    for line in md.split("\n"):
        if not line.strip() or line.startswith("🧾"):
            continue
        if line.startswith("  - "):
            item = line[4:].strip().replace("**", "")
            items.append(f'<div class="cp-ci cp-ci-sub">– {item}</div>')
        elif line.startswith("- "):
            item = line[2:].strip().rstrip(":").replace("**", "")
            items.append(f'<div class="cp-ci">• {item}</div>')

    if not items:
        return ""
    return (
        '<div class="cp-choices">'
        '<div class="cp-chd">Uw gekozen uitgangspunten</div>'
        + "".join(items)
        + "</div>"
    )


def _cp_breakdown_html(breakdown: List[Dict[str, Any]]) -> str:
    bestrating: List[Dict] = []
    grondwerk:  List[Dict] = []
    groen:      List[Dict] = []
    extras:     Dict[str, List[Dict]] = {}

    for item in breakdown:
        key = item.get("key")
        if key in _BESTRATING_KEYS:
            bestrating.append(item)
        elif key in _GRONDWERK_KEYS:
            grondwerk.append(item)
        elif key in _GROEN_KEYS:
            groen.append(item)
        elif key in _EXTRA_KEY_GROUP:
            extras.setdefault(_EXTRA_KEY_GROUP[key], []).append(item)
        else:
            extras.setdefault(item.get("label", "Overig"), []).append(item)

    def _eur(v: int) -> str:
        return f"€{v:,}".replace(",", ".")

    def _section(title: str, note: str, items: List[Dict]) -> str:
        rows = ""
        for it in items:
            label = it.get("label", "")
            rng   = it.get("range_eur")
            qty   = it.get("qty")
            unit  = (it.get("unit") or "").replace("€/", "").replace("€ ", "").strip()
            qty_html = f' <span class="cp-qty">({qty} {unit})</span>' if qty is not None and unit else ""
            if rng:
                price_html = f'<span class="cp-row-val">{_eur(int(rng[0]))} – {_eur(int(rng[1]))}</span>'
            else:
                price_html = '<span class="cp-row-val cp-row-offerte">op offerte</span>'
            rows += (
                f'<div class="cp-row">'
                f'<span class="cp-row-lbl">{label}{qty_html}</span>'
                f'{price_html}'
                f'</div>'
            )
        note_html = f'<div class="cp-sec-note">{note}</div>' if note else ""
        return (
            f'<div class="cp-section">'
            f'<div class="cp-sec-hd">{title}</div>'
            f'{note_html}{rows}'
            f'</div>'
        )

    html = ""
    if grondwerk:
        html += _section(
            "Grondwerk &amp; fundering t.b.v. bestrating:",
            "Varieert door: bereikbaarheid, grondsoort en afvoermogelijkheden.",
            grondwerk,
        )
    if bestrating:
        html += _section(
            "Bestrating:",
            "Prijs varieert o.a. door: tegelsoort, hoeken/randen, bereikbaarheid en afwatering.",
            bestrating,
        )
    if groen:
        html += _section(
            "Groen:",
            "Varieert door: soort, staat van de bodem en egaliseerwerk.",
            groen,
        )
    for group_name, items in extras.items():
        html += _section(f"{group_name}:", _EXTRA_DISCLAIMERS.get(group_name, ""), items)

    html += (
        '<div class="cp-sloop">'
        '<div class="cp-sloop-hd">Sloopwerk &amp; verwijdering bestaande tuin</div>'
        '<div class="cp-sloop-note">Nader te bepalen na een inspectiebezoek. Sterk afhankelijk van de bestaande situatie (bestrating, beplanting, gazon, schuttingen, etc.).</div>'
        '<div class="cp-sloop-note">Overweegt u zelf de tuin leeg te halen? Dit kan de sloopkosten aanzienlijk verlagen — vraag ernaar bij het gesprek.</div>'
        '</div>'
    )
    return html


def format_costs_as_chat_html(costs: Dict[str, Any], flow_type: str = "gehele_tuin") -> str:
    """Genereert een HTML-prijskaart voor de chatbot bubble, identiek aan de mail-layout."""
    if not costs or not costs.get("total_range_eur"):
        return ""

    tr = costs["total_range_eur"]
    total_min, total_max = int(tr[0]), int(tr[1])

    def eur(v: int) -> str:
        return f"€{v:,}".replace(",", ".")

    min_note = ""
    if costs.get("minimum_applied"):
        min_note = (
            '<div class="cp-min">ℹ️ Op dit project is een minimumprijs van €250 van toepassing, '
            'omdat de berekende kosten hieronder uitkwamen.</div>'
        )

    choices_html = _cp_choices_html(costs, flow_type)

    return (
        'CHATHTML:<div class="cp">'
        + (choices_html or "")
        + '<div class="cp-est-hd">✅ Eerste schatting</div>'
        + '<div class="cp-est-sub">Bedankt voor uw antwoorden. Op basis van uw keuzes volgt hier een eerste indicatie.</div>'
        + '<div class="cp-est-note">Iedere tuin is uniek. Deze schatting is een richtprijs, geen definitieve offerte.</div>'
        + '<div class="cp-total">'
        + '<div class="cp-total-lbl">Totale indicatie <span class="cp-btw">incl. BTW</span></div>'
        + f'<div class="cp-total-val">{eur(total_min)} – {eur(total_max)}</div>'
        + '</div>'
        + min_note
        + f'<div class="cp-toel">{get_prijstoelichting(costs.get("breakdown") or [])}</div>'
        + _cp_breakdown_html(costs.get("breakdown") or [])
        + '<div class="cp-footer">Deze schatting is gebaseerd op aannames en is inclusief arbeid en standaard materialen.</div>'
        + '</div>'
    )


# ============================================================
# Losse onderdelen: directe m² invoer (gedeelde PRIJZEN)
# ============================================================
def estimate_losse_onderdelen_costs(answers: Dict[str, Any], price_table=None) -> Dict[str, Any]:
    from core.pricing.price_table import DEFAULT_PRICE_TABLE
    p = price_table or DEFAULT_PRICE_TABLE
    """
    Rekent op basis van directe m² per onderdeel (geen percentages).
    Gebruikt dezelfde PRIJZEN als estimate_tuinaanleg_costs.

    Verwachte keys in answers:
      oprit_m2, paden_m2, terras_m2, gazon_m2, beplanting_m2  (float|None)
      materiaal_oprit, materiaal_paden, materiaal_terras       (str|None)
      onkruidwerend_gevoegd                                    (bool)
      overkapping, overkapping_m2                              (bool, float)
      verlichting                                              (bool)
      overige_wensen                                           (list)
      beregening_scope                                         (str)
      vlonder_type                                             (str)
      erfafscheiding_items                                     (list)
    """

    def _f(key: str) -> float:
        return max(0.0, _to_float(answers.get(key)))

    oprit_m2     = _f("oprit_m2")
    paden_m2     = _f("paden_m2")
    terras_m2    = _f("terras_m2")
    gazon_m2     = _f("gazon_m2")
    beplanting_m2 = _f("beplanting_m2")

    mat_oprit  = (answers.get("materiaal_oprit")  or "beton").strip().lower()
    mat_paden  = (answers.get("materiaal_paden")  or "beton").strip().lower()
    mat_terras = (answers.get("materiaal_terras") or "beton").strip().lower()

    voegen          = answers.get("onkruidwerend_gevoegd") is True
    overkapping     = answers.get("overkapping") is True
    verlichting     = answers.get("verlichting") is True
    overige         = answers.get("overige_wensen") or []
    vlonder_type    = (answers.get("vlonder_type") or "").strip().lower()
    beregening_scope = (answers.get("beregening_scope") or "").strip().lower()

    overige_clean = [str(x).strip().lower() for x in overige if str(x).strip()]

    breakdown: List[Dict[str, Any]] = []
    total: Tuple[float, float] = (0.0, 0.0)

    def _mat_key(mat: str) -> str:
        if mat == "keramiek":
            return "keramisch_straatwerk_per_m2"
        if mat == "grind":
            return "grind_per_m2"
        if mat == "gebakken":
            return "gebakken_straatwerk_per_m2"
        return "beton_straatwerk_per_m2"

    def _mat_pretty(mat: str) -> str:
        return {"keramiek": "Keramiek", "grind": "Grind", "gebakken": "Gebakken klinkers"}.get(mat, "Beton")

    def add_surface(part_label: str, m2_part: float, mat: str, factor: float = 1.0) -> None:
        nonlocal total
        if m2_part <= 0.01:
            return
        key = _mat_key(mat)
        ur = PRIJZEN.get(key, (60, 120))
        rng = _range_mul((float(ur[0]), float(ur[1])), m2_part)
        if factor < 1.0:
            rng = (rng[0] * factor, rng[1] * factor)
        total = _range_add(total, rng)
        notes = "Indicatief; materiaalprijs, onderbouw/fundering, snijwerk en complexiteit beïnvloeden de prijs."
        breakdown.append({
            "key": key,
            "label": f"{part_label} – {_mat_pretty(mat)}",
            "unit": _unit(key, "€/m²"),
            "qty": int(round(m2_part)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": notes,
        })

    # Multi-item bestrating (losse flow) of single-item (gehele flow)
    _oprit_items  = answers.get("oprit_items")  or []
    _paden_items  = answers.get("paden_items")  or []
    _terras_items = answers.get("terras_items") or []

    _paving_total_lo = (
        (sum(it.get("m2", 0) for it in _oprit_items) if _oprit_items else oprit_m2) +
        (sum(it.get("m2", 0) for it in _paden_items) if _paden_items else paden_m2) +
        (sum(it.get("m2", 0) for it in _terras_items) if _terras_items else terras_m2)
    )
    bestrating_factor_lo = p.schaal_factor(_paving_total_lo, "bestrating")

    if _oprit_items:
        for it in _oprit_items:
            add_surface("Oprit",  it.get("m2", 0), it.get("materiaal", "beton"), bestrating_factor_lo)
    else:
        add_surface("Oprit", oprit_m2, mat_oprit, bestrating_factor_lo)

    if _paden_items:
        for it in _paden_items:
            add_surface("Paden",  it.get("m2", 0), it.get("materiaal", "beton"), bestrating_factor_lo)
    else:
        add_surface("Paden", paden_m2, mat_paden, bestrating_factor_lo)

    if _terras_items:
        for it in _terras_items:
            add_surface("Terras", it.get("m2", 0), it.get("materiaal", "beton"), bestrating_factor_lo)
    else:
        add_surface("Terras", terras_m2, mat_terras, bestrating_factor_lo)

    # Grondwerk per onderdeel
    def add_vol(label: str, key: str, m3: float, notes: str, factor: float = 1.0) -> None:
        nonlocal total
        if m3 <= 0.0001:
            return
        ur = PRIJZEN.get(key)
        if not ur:
            return
        m3 = _round_to_half(m3)
        rng = _range_mul((float(ur[0]), float(ur[1])), m3)
        if factor < 1.0:
            rng = (rng[0] * factor, rng[1] * factor)
        total = _range_add(total, rng)
        breakdown.append({
            "key": key,
            "label": label,
            "unit": _unit(key, "€/m³"),
            "qty": m3,
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": notes,
        })

    _gd = p.grondwerk_dieptes

    # Split keramiek vs standaard per item voor correcte grondwerkdiepte
    def _ker_m2_from_items(items: list, fallback_m2: float, fallback_mat: str):
        if items:
            k = sum(it.get("m2", 0) for it in items if (it.get("materiaal") or "beton") == "keramiek")
            s = sum(it.get("m2", 0) for it in items if (it.get("materiaal") or "beton") != "keramiek")
            return k, s
        return (fallback_m2, 0.0) if fallback_mat == "keramiek" else (0.0, fallback_m2)

    _paden_ker, _paden_std = _ker_m2_from_items(_paden_items, paden_m2, mat_paden)
    _terras_ker, _terras_std = _ker_m2_from_items(_terras_items, terras_m2, mat_terras)
    _ker_m2_lo = _paden_ker + _terras_ker
    _std_m2_lo = _paden_std + _terras_std

    _grond_afvoer_pt_m3 = (
        _std_m2_lo * _gd["paden_terras_afvoer"]
        + _ker_m2_lo * _gd["paden_terras_afvoer_keramiek"]
    )
    _zand_pt_m3 = (
        _std_m2_lo * _gd["paden_terras_zand"]
        + _ker_m2_lo * _gd["paden_terras_zand_keramiek"]
    )

    _total_grw_m3_lo = _round_to_half(
        _grond_afvoer_pt_m3 + _zand_pt_m3
        + oprit_m2 * (_gd["oprit_afvoer"] + _gd["oprit_puin"] + _gd["oprit_zand"])
    )
    grondwerk_factor_lo = p.schaal_factor(_total_grw_m3_lo, "grondwerk")

    add_vol("Grond afvoer – paden/terras", "grond_afvoer_per_m3",
            _grond_afvoer_pt_m3, "Aanname: 15 cm (keramiek) of 20 cm (overige materialen).",
            grondwerk_factor_lo)
    add_vol("Zand aanvoer – paden/terras", "zand_aanvoer_per_m3",
            _zand_pt_m3, "Aanname: 10 cm (keramiek) of 15 cm (overige materialen).",
            grondwerk_factor_lo)
    add_vol("Grond afvoer – oprit (35 cm)", "grond_afvoer_per_m3",
            oprit_m2 * _gd["oprit_afvoer"], "Aanname: 0,35 m ontgraven per m² voor oprit.",
            grondwerk_factor_lo)
    add_vol("Puin aanvoer – oprit (25 cm)", "puin_aanvoer_per_m3",
            oprit_m2 * _gd["oprit_puin"], "Aanname: 0,25 m puin per m² voor oprit.",
            grondwerk_factor_lo)
    add_vol("Zand aanvoer – oprit (5 cm)", "zand_aanvoer_per_m3",
            oprit_m2 * _gd["oprit_zand"], "Aanname: 0,05 m zand per m² voor oprit.",
            grondwerk_factor_lo)

    # Zaagwerk (alle niet-grind vlakken); voegen alleen paden/terras niet-grind
    if _oprit_items or _paden_items or _terras_items:
        straatwerk_m2 = sum(it.get("m2", 0) for it in _oprit_items if it.get("materiaal") != "grind")
        straatwerk_m2 += sum(it.get("m2", 0) for it in _paden_items if it.get("materiaal") != "grind")
        straatwerk_m2 += sum(it.get("m2", 0) for it in _terras_items if it.get("materiaal") != "grind")
        voegen_m2_losse = sum(it.get("m2", 0) for it in _paden_items if it.get("materiaal") not in ("grind",))
        voegen_m2_losse += sum(it.get("m2", 0) for it in _terras_items if it.get("materiaal") not in ("grind",))
    else:
        straatwerk_m2 = sum(
            m for m, mat in ((oprit_m2, mat_oprit), (paden_m2, mat_paden), (terras_m2, mat_terras))
            if mat != "grind"
        )
        # Voegen alleen voor paden/terras, niet voor oprit
        voegen_m2_losse = (paden_m2 if mat_paden != "grind" else 0.0) + \
                          (terras_m2 if mat_terras != "grind" else 0.0)
    if straatwerk_m2 > 0.01:
        zaag_key = "zaagwerk_per_m1"
        zur = PRIJZEN.get(zaag_key, (35, 65))
        z_m1 = straatwerk_m2 * 0.35
        zaag_rng = (float(zur[0]) * z_m1, float(zur[1]) * z_m1)
        total = _range_add(total, zaag_rng)
        breakdown.append({
            "key": zaag_key,
            "label": _label(zaag_key, "Zaagwerk"),
            "unit": _unit(zaag_key, "€/m¹"),
            "qty": int(round(z_m1)),
            "range_eur": [_eur(zaag_rng[0]), _eur(zaag_rng[1])],
            "notes": "Schatting op basis van 35% van straatwerk (randen, hoeken en obstakels).",
        })

    # Gazon
    if gazon_m2 > 0:
        key = "graszoden_per_m2"
        ur = p.get(key, (15, 25))
        gazon_factor_lo = p.schaal_factor(gazon_m2, "groen")
        rng = _range_mul((float(ur[0]), float(ur[1])), gazon_m2)
        if gazon_factor_lo < 1.0:
            rng = (rng[0] * gazon_factor_lo, rng[1] * gazon_factor_lo)
        total = _range_add(total, rng)
        gazon_notes_lo = "Indicatief; afhankelijk van ondergrond, egaliseren en bereikbaarheid."
        breakdown.append({
            "key": key,
            "label": _label(key, "Graszoden"),
            "unit": _unit(key, "€/m²"),
            "qty": int(round(gazon_m2)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": gazon_notes_lo,
        })

    # Beplanting
    if beplanting_m2 > 0:
        key = "beplanting_border_per_m2"
        ur = p.get(key, (30, 40))
        beplanting_factor_lo = p.schaal_factor(beplanting_m2, "groen")
        rng = _range_mul((float(ur[0]), float(ur[1])), beplanting_m2)
        if beplanting_factor_lo < 1.0:
            rng = (rng[0] * beplanting_factor_lo, rng[1] * beplanting_factor_lo)
        total = _range_add(total, rng)
        beplanting_notes_lo = "Indicatief; soort, ondergrond en plantdichtheid beïnvloeden de prijs."
        breakdown.append({
            "key": key,
            "label": _label(key, "Beplanting border"),
            "unit": _unit(key, "€/m²"),
            "qty": int(round(beplanting_m2)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": beplanting_notes_lo,
        })

    # Erfafscheiding — items-lijst is de bron van waarheid, onafhankelijk van overige_wensen
    items = answers.get("erfafscheiding_items") or []
    if items:
        poortdeur_count = 0
        for it in items:
            t = (it.get("type") or "").strip().lower()
            meters = _to_float(it.get("meter"))
            pd = it.get("poortdeur") is True
            if meters <= 0:
                continue
            haag_type = (it.get("haag_type") or "voordelig_hoog").strip().lower()
            haag_key = {
                "voordelig_laag": "beplanting_haag_voordelig_laag_per_m1",
                "voordelig_hoog": "beplanting_haag_voordelig_hoog_per_m1",
                "premium_laag":   "beplanting_haag_premium_laag_per_m1",
                "premium_hoog":   "beplanting_haag_premium_hoog_per_m1",
            }.get(haag_type, "beplanting_haag_voordelig_hoog_per_m1")
            key_map = {
                "haag": haag_key,
                "betonschutting": "plaatsen_betonschutting_per_m1",
                "design_schutting": "plaatsen_designschutting_per_m1",
            }
            key = key_map.get(t)
            if key and p.get(key) != (0, 0):
                ur = p[key]
                rng = _range_mul((float(ur[0]), float(ur[1])), meters)
                total = _range_add(total, rng)
                breakdown.append({
                    "key": key,
                    "label": _label(key, "Erfafscheiding"),
                    "unit": _unit(key, "€/m¹"),
                    "qty": int(round(meters)),
                    "range_eur": [_eur(rng[0]), _eur(rng[1])],
                    "notes": "Indicatief; afhankelijk van soort, formaat en ondergrond.",
                })
            if pd and t in ("betonschutting", "design_schutting"):
                poortdeur_count += 1
        if poortdeur_count > 0:
            pk = "plaatsen_poortdeur_per_st"
            pr = p[pk]
            rng = (float(pr[0]) * poortdeur_count, float(pr[1]) * poortdeur_count)
            total = _range_add(total, rng)
            breakdown.append({
                "key": pk,
                "label": _label(pk, "Poortdeur plaatsen"),
                "unit": _unit(pk, "€/stuk"),
                "qty": poortdeur_count,
                "range_eur": [_eur(rng[0]), _eur(rng[1])],
                "notes": "Indicatief; afhankelijk van maatvoering, beslag en fundering.",
            })
        overige_clean = [x for x in overige_clean if x != "erfafscheiding"]

    # Beregening – losse onderdelen: directe m² invoer; scope + systeem bepalen prijs
    if "beregening" in overige_clean:
        b_systeem = (answers.get("beregening_systeem") or "volautomatisch").strip().lower()
        b_scope   = beregening_scope
        b_m2_direct = _f("beregening_m2")

        inst_key_l = _beregening_installatie_key(b_systeem)
        inst_ur_l = PRIJZEN.get(inst_key_l, (800, 1200))
        total = _range_add(total, (float(inst_ur_l[0]), float(inst_ur_l[1])))
        breakdown.append({
            "key": inst_key_l,
            "label": _label(inst_key_l, "Technische installatie & opstartkosten"),
            "unit": "€ vast",
            "qty": 1,
            "range_eur": [_eur(inst_ur_l[0]), _eur(inst_ur_l[1])],
            "notes": "Pomp, besturingscomputer, aansluiting waterpunt en ingebruikstelling. Vaste post ongeacht het aantal m².",
        })

        if b_m2_direct > 0.01:
            ber_gebieden_l = []
            if b_scope == "gazon":
                ber_gebieden_l = [("gazon", b_m2_direct, "gazon")]
            elif b_scope == "beplanting":
                ber_gebieden_l = [("beplanting", b_m2_direct, "beplanting")]
            else:
                b_gazon_m2 = float(answers.get("beregening_gazon_m2") or 0)
                b_beplanting_m2 = float(answers.get("beregening_beplanting_m2") or 0)
                if b_gazon_m2 > 0.01 or b_beplanting_m2 > 0.01:
                    if b_gazon_m2 > 0.01:
                        ber_gebieden_l.append(("gazon", b_gazon_m2, "gazon"))
                    if b_beplanting_m2 > 0.01:
                        ber_gebieden_l.append(("beplanting", b_beplanting_m2, "beplanting"))
                else:
                    ber_gebieden_l = [("gazon", b_m2_direct, "gazon én beplanting")]
        else:
            if b_scope == "gazon":
                ber_gebieden_l = [("gazon", gazon_m2, "alleen gazon")]
            elif b_scope == "beplanting":
                ber_gebieden_l = [("beplanting", beplanting_m2, "alleen beplanting")]
            else:
                ber_gebieden_l = [("gazon", gazon_m2, "gazon"), ("beplanting", beplanting_m2, "beplanting")]

        for gebied, ber_m2, scope_txt in ber_gebieden_l:
            if ber_m2 <= 0.01:
                continue
            key = _beregening_key(gebied, b_systeem)
            ur = PRIJZEN.get(key, (8, 13))
            rng = _range_mul((float(ur[0]), float(ur[1])), ber_m2)
            total = _range_add(total, rng)
            breakdown.append({
                "key": key,
                "label": _label(key, "Beregening"),
                "unit": _unit(key, "€/m²"),
                "qty": int(round(ber_m2)),
                "range_eur": [_eur(rng[0]), _eur(rng[1])],
                "notes": f"Indicatief; berekend over {scope_txt}. Afhankelijk van zones en leidingwerk.",
            })
        overige_clean = [x for x in overige_clean if x != "beregening"]

    # Voegen: altijd alleen paden/terras (niet oprit); voegen_m2_losse sluit oprit al uit
    if "voegen_m2_custom" in answers:
        _voegen_m2 = float(answers["voegen_m2_custom"])
    else:
        _voegen_m2 = voegen_m2_losse
    if voegen and _voegen_m2 > 0.01:
        key = "voegen_straatwerk_per_m2"
        ur = PRIJZEN.get(key, (15, 20))
        rng = _range_mul((float(ur[0]), float(ur[1])), _voegen_m2)
        total = _range_add(total, rng)
        breakdown.append({
            "key": key,
            "label": _label(key, "Voegen straatwerk"),
            "unit": _unit(key, "€/m²"),
            "qty": int(round(_voegen_m2)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": "Voegwerk berekend per m² straatwerk (excl. grind).",
        })

    # Overkapping
    if overkapping:
        key = "overkapping_per_m2"
        ov_m2 = float(answers.get("overkapping_m2") or 15.0)
        ur = PRIJZEN.get(key, (650, 1000))
        rng = _range_mul((float(ur[0]), float(ur[1])), ov_m2)
        total = _range_add(total, rng)
        breakdown.append({
            "key": key,
            "label": "Overkapping",
            "unit": "€/m²",
            "qty": int(round(ov_m2)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": "Fundering, maatwerk en afwerkingsgraad beïnvloeden de prijs.",
        })

    # Verlichting
    if verlichting:
        key = "verlichting_basis_per_stuk"
        vl = PRIJZEN.get(key, (1000, 1500))
        rng = (float(vl[0]), float(vl[1]))
        total = _range_add(total, rng)
        breakdown.append({
            "key": key,
            "label": _label(key, "Verlichting (basis)"),
            "unit": _unit(key, "€/stuk"),
            "qty": 1,
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": "Afhankelijk van aantal spots, trafo, bekabeling en montage.",
        })

    # Vlonder
    if "vlonder" in overige_clean:
        vlonder_m2_direct = _f("vlonder_m2")
        total_m2_all = oprit_m2 + paden_m2 + terras_m2 + gazon_m2 + beplanting_m2
        if vlonder_m2_direct > 0:
            vlonder_m2 = vlonder_m2_direct
            _vlonder_notes_losse = "Schatting o.b.v. ingevoerd oppervlak; fundering en afwerking kunnen variëren."
        else:
            vlonder_m2 = min(12.0, max(6.0, 0.12 * total_m2_all)) if total_m2_all > 0 else 9.0
            _vlonder_notes_losse = (
                f"Geen oppervlakte opgegeven. Indicatief berekend op ca. {int(round(vlonder_m2))} m². "
                "Geef uw eigen m² op voor een nauwkeurigere indicatie."
            )
        key = {
            "zachthout": "vlonder_zachthout_per_m2",
            "hardhout": "vlonder_hardhout_per_m2",
        }.get(vlonder_type, "vlonder_composiet_per_m2")
        ur = PRIJZEN.get(key, (280, 350))
        rng = _range_mul((float(ur[0]), float(ur[1])), vlonder_m2)
        total = _range_add(total, rng)
        breakdown.append({
            "key": key,
            "label": _label(key, "Vlonder"),
            "unit": _unit(key, "€/m²"),
            "qty": int(round(vlonder_m2)),
            "range_eur": [_eur(rng[0]), _eur(rng[1])],
            "notes": _vlonder_notes_losse,
        })
        overige_clean = [x for x in overige_clean if x != "vlonder"]

    # Combineer grondwerk regels + sorteer (gedeelde helpers)
    breakdown = _aggregate_grondwerk(breakdown)
    breakdown = _sort_breakdown_grondwerk_first(breakdown)

    # Minimumprijs: elk project kost minimaal €250
    _MIN_PROJECT = 250
    _minimum_applied = total[0] < _MIN_PROJECT
    total = (max(total[0], _MIN_PROJECT), max(total[1], _MIN_PROJECT))

    return {
        "total_range_eur": [_eur(total[0]), _eur(total[1])],
        "minimum_applied": _minimum_applied,
        "breakdown": breakdown,
        "inputs": {
            "oprit_m2": oprit_m2,
            "paden_m2": paden_m2,
            "terras_m2": terras_m2,
            "gazon_m2": gazon_m2,
            "beplanting_m2": beplanting_m2,
            "materiaal_oprit": mat_oprit,
            "materiaal_paden": mat_paden,
            "materiaal_terras": mat_terras,
            "onkruidwerend_gevoegd": voegen,
            "overkapping": overkapping,
            "overkapping_m2": float(answers.get("overkapping_m2") or 15.0) if overkapping else None,
            "verlichting": verlichting,
            "overige_wensen": overige,
            "vlonder_type": vlonder_type,
            "beregening_scope": beregening_scope,
            "beregening_m2": float(answers.get("beregening_m2") or 0),
            "oprit_items":   answers.get("oprit_items")  or [],
            "paden_items":   answers.get("paden_items")  or [],
            "terras_items":  answers.get("terras_items") or [],
            "erfafscheiding_items_count": len(items),
            "erfafscheiding_items": list(items),
            "flow_type": "losse_onderdelen",
        },
    }


def format_losse_onderdelen_choices_for_customer(costs: Dict[str, Any]) -> str:
    """Klantvriendelijk overzicht van gekozen onderdelen voor de losse-onderdelen flow."""
    inputs = (costs or {}).get("inputs") or {}
    if not inputs:
        return ""

    def eur_m2(v: float) -> str:
        return f"ca. {int(round(v))} m²"

    def mat(m: str) -> str:
        return {"grind": "Grind", "beton": "Beton", "gebakken": "Gebakken klinkers",
                "keramiek": "Keramiek"}.get((m or "").strip().lower(), "Beton")

    lines = ["🧾 **Uw gekozen onderdelen**"]

    # Bestrating: gebruik items-lijsten (multi-item support), nummerering bij meerdere
    for items_key, label in (("oprit_items", "Oprit"), ("paden_items", "Paden"), ("terras_items", "Terras")):
        items_list = inputs.get(items_key) or []
        for i, item in enumerate(items_list):
            v = float(item.get("m2") or 0)
            if v <= 0:
                continue
            num = f" {i + 1}" if len(items_list) > 1 else ""
            gevoegd_txt = ", gevoegd" if item.get("gevoegd", False) else ""
            lines.append(f"- {label}{num}: {eur_m2(v)} ({mat(item.get('materiaal', 'beton'))}{gevoegd_txt})")

    # Groen: multi-item support
    for items_key, fallback_key, label in (
        ("gazon_items", "gazon_m2", "Gazon"),
        ("beplanting_items", "beplanting_m2", "Beplanting"),
    ):
        items_list = inputs.get(items_key) or []
        if items_list:
            for i, item in enumerate(items_list):
                v = float(item.get("m2") or 0)
                if v <= 0:
                    continue
                num = f" {i + 1}" if len(items_list) > 1 else ""
                lines.append(f"- {label}{num}: {eur_m2(v)}")
        else:
            v = float(inputs.get(fallback_key) or 0)
            if v > 0:
                lines.append(f"- {label}: {eur_m2(v)}")

    # Erfafscheiding: per type weergeven zonder wrapper
    erf_items = inputs.get("erfafscheiding_items") or []
    for it in erf_items:
        t = (it.get("type") or "").strip().lower()
        m = int(it.get("meter") or 0)
        if t == "haag":
            haag_type = (it.get("haag_type") or "voordelig_hoog").strip().lower()
            haag_lbl = {
                "voordelig_laag": "voordelig laag (0,5–1m)",
                "voordelig_hoog": "voordelig hoog (1,5–2m)",
                "premium_laag":   "premium laag (0,5–1m)",
                "premium_hoog":   "premium hoog (1,5–2m)",
            }.get(haag_type, haag_type)
            lines.append(f"- Haag {haag_lbl}: {m} m")
        elif t == "betonschutting":
            lines.append(f"- Betonschutting: {m} m")
        elif t == "design_schutting":
            lines.append(f"- Design schutting: {m} m")

    extras: List[str] = []
    if inputs.get("overkapping"):
        ov = inputs.get("overkapping_m2")
        extras.append(f"Overkapping (ca. {int(round(float(ov or 15)))} m²)")
    if inputs.get("verlichting"):
        extras.append("Tuinverlichting (basis)")
    overige = inputs.get("overige_wensen") or []
    overige_clean = [str(x).strip().lower() for x in overige if str(x).strip()]
    scope = (inputs.get("beregening_scope") or "").strip().lower()
    if "beregening" in overige_clean:
        b_m2 = float(inputs.get("beregening_m2") or 0)
        if b_m2 > 0:
            extras.append(f"Beregening ({int(round(b_m2))} m²)")
        else:
            scope_txt = {"gazon": "alleen gazon", "beplanting": "alleen beplanting"}.get(scope, "gazon én beplanting")
            extras.append(f"Beregening ({scope_txt})")
    if "vlonder" in overige_clean:
        vt = (inputs.get("vlonder_type") or "").strip().lower()
        extras.append(f"Vlonder ({vt})" if vt else "Vlonder")

    if extras:
        lines.append("- Extra's:")
        for ex in extras:
            lines.append(f"  - {ex}")

    return "\n".join(lines)


# ============================================================
# Tuinontwerp: prijsindicatie op basis van m²-tier
# ============================================================

def estimate_tuinontwerp_costs(answers: Dict[str, Any], price_table=None) -> Dict[str, Any]:
    from core.pricing.price_table import DEFAULT_PRICE_TABLE
    p = price_table or DEFAULT_PRICE_TABLE
    m2 = float((answers or {}).get("tuin_m2") or 0)

    if m2 < 100:
        key = "3d_tuinontwerp_<100m2"
    elif m2 <= 500:
        key = "3d_tuinontwerp_100-500m2"
    elif m2 <= 1000:
        key = "3d_tuinontwerp_500-1000m2"
    else:
        key = "3d_tuinontwerp_>1000m2"

    lo, hi = p[key]
    return {
        "total_range_eur": (lo, hi),
        "tuin_m2": m2,
        "price_key": key,
        "_flow_type": "tuinontwerp",
    }


def format_tuinontwerp_costs_as_chat_html(costs: Dict[str, Any]) -> str:
    if not costs or not costs.get("total_range_eur"):
        return ""

    lo, hi = costs["total_range_eur"]
    m2 = int(costs.get("tuin_m2") or 0)

    def eur(v: int) -> str:
        return f"€{v:,}".replace(",", ".")

    return (
        'CHATHTML:<div class="cp">'
        '<div class="cp-est-hd">✅ Eerste schatting tuinontwerp</div>'
        '<div class="cp-est-sub">Op basis van de tuingrootte volgt hier een eerste indicatie voor een professioneel tuinontwerp.</div>'
        '<div class="cp-est-note">De uiteindelijke prijs is afhankelijk van de complexiteit en het gewenste detailniveau.</div>'
        '<div class="cp-total">'
        '<div class="cp-total-lbl">Indicatieprijs tuinontwerp '
        f'({m2} m²) <span class="cp-btw">incl. BTW</span></div>'
        f'<div class="cp-total-val">{eur(lo)} – {eur(hi)}</div>'
        '</div>'
        '<div class="cp-toel">Inbegrepen: intakegesprek, ontwerptekening en presentatie. '
        'Na goedkeuring van het ontwerp kunnen wij ook de aanleg voor u verzorgen.<br><br>'
        '<strong>De prijs varieert o.a. door:</strong> de grootte van de tuin, de detaillering rondom de woning, '
        'de complexiteit van eventuele bouwkundige elementen en het gewenste detailniveau van het ontwerp.</div>'
        '<div class="cp-footer">Deze schatting is een richtprijs. Na een vrijblijvend gesprek ontvangt u een exacte offerte.</div>'
        '</div>'
    )
