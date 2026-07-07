# pricing_demo.py — Voorbeeldprijzen voor de publieke demo
#
# Dit zijn generieke markttarieven ter illustratie.
# Elke Indiqa-installatie wordt geconfigureerd met de eigen tarieven van
# het betreffende hoveniersbedrijf.
#
# ⚠️  Verander deze waarden NIET naar jouw echte tarieven.
#     Gebruik daarvoor pricing.py (niet in de publieke repo).
from __future__ import annotations
from typing import Dict, Tuple, List

PRIJZEN_DEMO: Dict[str, Tuple[int, int]] = {
    "onderhoud_aanleg_uurtarief":               (62,  78),
    "voorjaar_najaarsbeurt":                    (285, 565),
    "gazon_maaien":                             (72,  195),
    "haag_snoeien":                             (78,  340),

    "bestrating_verwijderen_per_m3":            (92,  148),
    "bestrating_afvoer_per_m3":                 (92,  148),
    "bouw_sloop_afval_afvoer_per_m3":           (92,  148),

    "grond_afvoer_per_m3":                      (88,  145),
    "zand_aanvoer_per_m3":                      (98,  158),
    "puin_aanvoer_per_m3":                      (90,  148),

    "keramisch_straatwerk_per_m2":              (188, 228),
    "beton_straatwerk_per_m2":                  (62,  94),
    "gebakken_straatwerk_per_m2":               (82,  126),
    "grind_per_m2":                             (33,  58),
    "plaatsen_betonband_per_m1":                (13,  26),
    "zaagwerk_per_m1":                          (19,  34),
    "voegen_straatwerk_per_m2":                 (14,  21),

    "vlonder_zachthout_per_m2":                 (195, 245),
    "vlonder_hardhout_per_m2":                  (272, 408),
    "vlonder_composiet_per_m2":                 (342, 508),

    "graszoden_per_m2":                         (11,  21),
    "beplanting_border_per_m2":                 (26,  42),
    "beplanting_haag_voordelig_laag_per_m1":    (19,  39),
    "beplanting_haag_voordelig_hoog_per_m1":    (44,  72),
    "beplanting_haag_premium_laag_per_m1":      (72,  116),
    "beplanting_haag_premium_hoog_per_m1":      (116, 175),
    "beplanting_boom_per_stuk":                 (215, 585),

    "overkapping_per_m2":                       (630, 975),
    "verlichting_basis_per_stuk":               (975, 1475),

    "beregening_installatie_basis":             (575, 875),
    "beregening_installatie_volautomatisch":    (1050, 1575),
    "beregening_installatie_highend":           (1750, 2450),
    "beregening_gazon_basis_per_m2":            (5,   9),
    "beregening_gazon_volautomatisch_per_m2":   (8,   13),
    "beregening_gazon_highend_per_m2":          (11,  17),
    "beregening_beplanting_basis_per_m2":       (7,   12),
    "beregening_beplanting_volautomatisch_per_m2": (11, 18),
    "beregening_beplanting_highend_per_m2":     (17,  27),

    "plaatsen_betonschutting_per_m1":           (195, 292),
    "plaatsen_poortdeur_per_st":                (725, 1450),
    "plaatsen_designschutting_per_m1":          (292, 388),

    "3d_tuinontwerp_<100m2":                    (488, 975),
    "3d_tuinontwerp_100-500m2":                 (975, 1462),
    "3d_tuinontwerp_500-1000m2":                (1462, 1950),
    "3d_tuinontwerp_>1000m2":                   (1950, 2925),
}

# Volume-kortingen: drempelwaardes iets anders dan productie
VOLUME_KORTINGEN_DEMO: Dict[str, List[Tuple[float, float]]] = {
    "groen":      [(320, 0.83), (160, 0.88), (80, 0.94)],
    "bestrating": [(220, 0.87), (110, 0.92), (55, 0.97)],
    "grondwerk":  [(65,  0.84), (28,  0.89), (12, 0.95)],
    "vlonder":    [(55,  0.89), (22,  0.95)],
}

# Grondwerk dieptes: licht afwijkend van productie
GRONDWERK_DIEPTES_DEMO: Dict[str, float] = {
    "paden_terras_afvoer":         0.20,
    "paden_terras_zand":           0.14,
    "paden_terras_afvoer_keramiek":0.15,
    "paden_terras_zand_keramiek":  0.10,
    "oprit_afvoer":                0.36,
    "oprit_puin":                  0.24,
    "oprit_zand":                  0.05,
}
