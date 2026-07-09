"""
Preview van de klant-bevestigingsmail. Voer uit en open preview_klant.html in je browser.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from mailer import _build_customer_html

sample_costs = {
    "total_range_eur": [3529, 5306],
    "breakdown": [
        {"key": "grond_afvoer_per_m3",        "label": "Grond afvoer",          "unit": "€/m³", "qty": 6.5,  "range_eur": [617, 975]},
        {"key": "zand_aanvoer_per_m3",         "label": "Zand aanvoer",          "unit": "€/m³", "qty": 2.75, "range_eur": [262, 413]},
        {"key": "puin_aanvoer_per_m3",         "label": "Puin aanvoer",          "unit": "€/m³", "qty": 2.5,  "range_eur": [238, 375]},
        {"key": "beton_straatwerk_per_m2",     "label": "Oprit – Beton",         "unit": "€/m²", "qty": 10,   "range_eur": [600, 900]},
        {"key": "beton_straatwerk_per_m2",     "label": "Paden – Beton",         "unit": "€/m²", "qty": 8,    "range_eur": [450, 675]},
        {"key": "beton_straatwerk_per_m2",     "label": "Terras – Beton",        "unit": "€/m²", "qty": 8,    "range_eur": [450, 675]},
        {"key": "zaagwerk_per_m1",             "label": "Zaagwerk",              "unit": "€/m¹", "qty": 9,    "range_eur": [350, 481]},
        {"key": "graszoden_per_m2",            "label": "Graszoden",             "unit": "€/m²", "qty": 12,   "range_eur": [188, 312]},
        {"key": "beplanting_border_per_m2",    "label": "Beplanting border",     "unit": "€/m²", "qty": 12,   "range_eur": [375, 500]},
    ],
    "inputs": {
        "tuin_m2": 50,
        "verhouding_bestrating_groen": "70_30",
        "verhouding_gazon_beplanting": "70_30",
        "oprit_pct": 50, "paden_pct": 30, "terras_pct": 20,
        "materiaal_oprit": "beton", "materiaal_paden": "beton", "materiaal_terras": "beton",
        "onkruidwerend_gevoegd": False,
        "overkapping": False, "verlichting": False,
        "overige_wensen": [], "vlonder_type": "", "beregening_scope": "",
        "erfafscheiding_items_count": 0,
    },
}

html = _build_customer_html("Maik", sample_costs, "gehele_tuin")

out = os.path.join(os.path.dirname(__file__), "preview_klant.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Preview opgeslagen: {out}")
print("Open dit bestand in je browser.")
