# core/pricing/constants.py
from __future__ import annotations

from typing import Dict, List, Tuple

PRIJZEN: Dict[str, Tuple[int, int]] = {
    # Onderhoud (−10%)
    "onderhoud_aanleg_uurtarief": (58, 68),
    "voorjaar_najaarsbeurt": (260, 520),
    "gazon_maaien": (68, 180),
    "haag_snoeien": (68, 315),

    # Grondwerk & afvoer (−10% → vaste marktprijzen)
    "bestrating_verwijderen_per_m3": (85, 135),
    "bestrating_afvoer_per_m3": (85, 135),
    "bouw_sloop_afval_afvoer_per_m3": (85, 135),

    "grond_afvoer_per_m3": (85, 135),
    "zand_aanvoer_per_m3": (85, 135),
    "puin_aanvoer_per_m3": (85, 135),

    # Bestrating (−20%)
    "keramisch_straatwerk_per_m2": (145, 175),
    "beton_straatwerk_per_m2": (50, 70),
    "gebakken_straatwerk_per_m2": (65, 105),
    "grind_per_m2": (30, 50),
    "plaatsen_betonband_per_m1": (11, 22),
    "zaagwerk_per_m1": (16, 28),
    "voegen_straatwerk_per_m2": (12, 16),

    # Vlonders (−20%)
    "vlonder_zachthout_per_m2": (160, 200),
    "vlonder_hardhout_per_m2": (225, 335),
    "vlonder_composiet_per_m2": (280, 415),

    # Groen (−20%)
    "graszoden_per_m2": (10, 18),
    "beplanting_border_per_m2": (20, 32),
    "beplanting_haag_voordelig_laag_per_m1": (16, 32),
    "beplanting_haag_voordelig_hoog_per_m1": (36, 60),
    "beplanting_haag_premium_laag_per_m1": (60, 95),
    "beplanting_haag_premium_hoog_per_m1": (95, 145),
    "beplanting_boom_per_stuk": (175, 480),

    # Overkapping & verlichting (−20%)
    "overkapping_per_m2": (520, 800),
    "verlichting_basis_per_stuk": (800, 1200),

    # Beregening (−20%)
    "beregening_installatie_basis":               (480, 720),
    "beregening_installatie_volautomatisch":      (800, 1200),
    "beregening_installatie_highend":             (1440, 2000),
    "beregening_gazon_basis_per_m2":              (4, 7),
    "beregening_gazon_volautomatisch_per_m2":     (6, 10),
    "beregening_gazon_highend_per_m2":            (10, 14),
    "beregening_beplanting_basis_per_m2":         (6, 10),
    "beregening_beplanting_volautomatisch_per_m2":(10, 14),
    "beregening_beplanting_highend_per_m2":       (14, 22),

    # Erfafscheiding (−20%)
    "plaatsen_betonschutting_per_m1": (160, 240),
    "plaatsen_poortdeur_per_st": (600, 1200),
    "plaatsen_designschutting_per_m1": (240, 320),

    # 3D Tuinontwerp (ongewijzigd — breed en bedrijfsspecifiek)
    "3d_tuinontwerp_<100m2":    (500, 1000),
    "3d_tuinontwerp_100-500m2": (1000, 1500),
    "3d_tuinontwerp_500-1000m2":(1500, 2000),
    "3d_tuinontwerp_>1000m2":   (2000, 3000),
}

PRICE_KEYS: List[str] = sorted(PRIJZEN.keys())

VOLUME_KORTINGEN: Dict[str, List[Tuple[float, float]]] = {
    "groen":    [(300, 0.82), (150, 0.87), (75, 0.93)],
    "bestrating":[(200, 0.86),(100, 0.91), (50, 0.96)],
    "grondwerk": [(60, 0.83), (25, 0.88), (10, 0.94)],
    "vlonder":  [(50, 0.88),  (20, 0.94)],
}

GRONDWERK_DIEPTES: Dict[str, float] = {
    "paden_terras_afvoer":          0.20,
    "paden_terras_zand":            0.15,
    "paden_terras_afvoer_keramiek": 0.15,
    "paden_terras_zand_keramiek":   0.10,
    "oprit_afvoer":                 0.35,
    "oprit_puin":                   0.25,
    "oprit_zand":                   0.05,
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
    "3d_tuinontwerp_<100m2":    {"unit": "€/stuk", "label": "3D tuinontwerp (<100 m²)"},
    "3d_tuinontwerp_100-500m2": {"unit": "€/stuk", "label": "3D tuinontwerp (100–500 m²)"},
    "3d_tuinontwerp_500-1000m2":{"unit": "€/stuk", "label": "3D tuinontwerp (500–1000 m²)"},
    "3d_tuinontwerp_>1000m2":   {"unit": "€/stuk", "label": "3D tuinontwerp (>1000 m²)"},
}
