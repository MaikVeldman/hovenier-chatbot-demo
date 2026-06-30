# leadscore.py
from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple


def bereken_leadscore(
    answers: Optional[Dict[str, Any]],
    costs: Optional[Dict[str, Any]],
    sessie_volledig: bool = False,
    offerte_aangevraagd: bool = False,
    terug_acties: int = 0,
    prijs_gezien_en_doorgegaan: bool = False,
    herberekend: bool = False,
    drop_off: bool = False,
) -> Tuple[int, str, Dict[str, int]]:
    """
    Berekent de leadscore op basis van botantwoorden en sessiegedrag.

    Returns:
        (score, label, breakdown_dict)
        label: "warm" | "potentieel" | "oriënterend"
    """
    breakdown: Dict[str, int] = {}
    answers = answers or {}

    # ──────────────────────────────────────────
    # Signalen uit botantwoorden
    # ──────────────────────────────────────────

    # Antwoorden (max 40 punten)
    fase = answers.get("fase")
    if fase == "klaar_om_te_starten":
        breakdown["fase_klaar_om_te_starten"] = 20
    elif fase == "concrete_plannen":
        breakdown["fase_concrete_plannen"] = 10

    prioriteit = answers.get("prioriteit")
    if prioriteit == "kwaliteit":
        breakdown["prioriteit_kwaliteit"] = 10
    elif prioriteit == "balans":
        breakdown["prioriteit_balans"] = 5

    materiaal_terras = answers.get("materiaal_terras")
    if materiaal_terras == "keramisch":
        breakdown["materiaal_terras_keramiek"] = 5
    elif materiaal_terras == "gebakken":
        breakdown["materiaal_terras_gebakken"] = 3

    extras = answers.get("overige_wensen") or []
    if isinstance(extras, list) and len(extras) > 0:
        breakdown["extras_gekozen"] = min(len(extras), 3) * 2

    tuin_m2 = float(answers.get("tuin_m2") or 0)
    if tuin_m2 > 100:
        breakdown["tuingrootte_groot"] = 5
    elif tuin_m2 > 50:
        breakdown["tuingrootte_middelgroot"] = 3

    # Gedrag (max 60 punten)
    if offerte_aangevraagd:
        breakdown["offerte_aangevraagd"] = 35

    if sessie_volledig:
        breakdown["sessie_volledig"] = 10

    if terug_acties >= 2:
        breakdown["meerdere_terug_acties"] = 5

    if prijs_gezien_en_doorgegaan:
        breakdown["prijs_gezien_doorgegaan"] = 10

    if herberekend:
        breakdown["herberekend_kosten"] = -5

    if drop_off and not sessie_volledig:
        breakdown["sessie_afgebroken"] = -10

    score = sum(breakdown.values())
    score = max(0, min(100, score))

    if score >= 70:
        label = "warm"
    elif score >= 40:
        label = "potentieel"
    else:
        label = "oriënterend"

    return score, label, breakdown


def leadscore_samenvatting(score: int, label: str, breakdown: Dict[str, int]) -> str:
    """Leesbare tekst voor in dashboard/mail."""
    label_tekst = {
        "warm": "Warme lead — snel opbellen",
        "potentieel": "Potentieel — opvolgen",
        "oriënterend": "Oriënterend — lage prioriteit",
    }.get(label, label)

    regels = [f"Score: {score} — {label_tekst}", ""]
    for k, v in breakdown.items():
        teken = "+" if v >= 0 else ""
        regels.append(f"  {teken}{v}  {k.replace('_', ' ')}")
    return "\n".join(regels)
