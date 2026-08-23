# pricing_demo.py — Voorbeeldprijzen voor de publieke demo
#
# Bewust afwijkend van echte tarieven — uitsluitend ter illustratie.
# Elke Indiqa-installatie wordt geconfigureerd met de eigen tarieven
# van het betreffende hoveniersbedrijf.
from __future__ import annotations
from typing import Dict, Tuple, List

PRIJZEN_DEMO: Dict[str, Tuple[int, int]] = {
    "onderhoud_aanleg_uurtarief":               (55,  70),
    "voorjaar_najaarsbeurt":                    (250, 500),
    "gazon_maaien":                             (65,  175),
    "haag_snoeien":                             (65,  300),

    "bestrating_verwijderen_per_m3":            (75,  125),
    "bestrating_afvoer_per_m3":                 (75,  125),
    "bouw_sloop_afval_afvoer_per_m3":           (75,  125),

    "grond_afvoer_per_m3":                      (70,  115),
    "zand_aanvoer_per_m3":                      (70,  115),
    "puin_aanvoer_per_m3":                      (70,  115),

    "keramisch_straatwerk_per_m2":              (145, 195),
    "beton_straatwerk_per_m2":                  (50,  80),
    "gebakken_straatwerk_per_m2":               (65,  105),
    "grind_per_m2":                             (25,  50),
    "plaatsen_betonband_per_m1":                (10,  22),
    "zaagwerk_per_m1":                          (15,  30),
    "voegen_straatwerk_per_m2":                 (12,  18),

    "vlonder_zachthout_per_m2":                 (160, 210),
    "vlonder_hardhout_per_m2":                  (225, 350),
    "vlonder_composiet_per_m2":                 (280, 430),

    "graszoden_per_m2":                         (10,  18),
    "beplanting_border_per_m2":                 (20,  35),
    "beplanting_haag_voordelig_laag_per_m1":    (15,  35),
    "beplanting_haag_voordelig_hoog_per_m1":    (35,  60),
    "beplanting_haag_premium_laag_per_m1":      (60,  100),
    "beplanting_haag_premium_hoog_per_m1":      (95,  150),
    "beplanting_boom_per_stuk":                 (175, 500),

    "overkapping_per_m2":                       (500, 850),
    "verlichting_basis_per_stuk":               (800, 1250),

    "beregening_installatie_basis":             (450, 750),
    "beregening_installatie_volautomatisch":    (800, 1250),
    "beregening_installatie_highend":           (1400, 2000),
    "beregening_gazon_basis_per_m2":            (4,   8),
    "beregening_gazon_volautomatisch_per_m2":   (6,   11),
    "beregening_gazon_highend_per_m2":          (9,   15),
    "beregening_beplanting_basis_per_m2":       (5,   10),
    "beregening_beplanting_volautomatisch_per_m2": (9, 15),
    "beregening_beplanting_highend_per_m2":     (14,  22),

    "plaatsen_betonschutting_per_m1":           (160, 250),
    "plaatsen_poortdeur_per_st":                (600, 1250),
    "plaatsen_designschutting_per_m1":          (240, 325),

    "3d_tuinontwerp_<100m2":                    (400, 850),
    "3d_tuinontwerp_100-500m2":                 (850, 1250),
    "3d_tuinontwerp_500-1000m2":                (1250, 1750),
    "3d_tuinontwerp_>1000m2":                   (1750, 2500),
}

VOLUME_KORTINGEN_DEMO: Dict[str, List[Tuple[float, float]]] = {
    "groen":      [(300, 0.83), (150, 0.88), (75, 0.94)],
    "bestrating": [(200, 0.87), (100, 0.92), (50, 0.97)],
    "grondwerk":  [(60,  0.84), (25,  0.89), (10, 0.95)],
    "vlonder":    [(50,  0.89), (20,  0.95)],
}

GRONDWERK_DIEPTES_DEMO: Dict[str, float] = {
    "paden_terras_afvoer":          0.20,
    "paden_terras_zand":            0.15,
    "paden_terras_afvoer_keramiek": 0.15,
    "paden_terras_zand_keramiek":   0.10,
    "oprit_afvoer":                 0.35,
    "oprit_puin":                   0.25,
    "oprit_zand":                   0.05,
}
