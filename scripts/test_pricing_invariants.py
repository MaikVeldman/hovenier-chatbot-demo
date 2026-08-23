"""
Regressietest voor prijsberekening + kostenbesparing-logica.

Doel: niet "alle combinaties" doorlopen (combinatorisch onhaalbaar), maar een
representatieve set scenario's voor de "gehele tuin"- en "losse onderdelen"-
flow controleren op invarianten die in de praktijk zijn misgegaan:

  1. Geen crashes in estimate_*_costs of in de bespaar-functies (savings.py).
  2. total_range_eur is intern consistent: min <= max, min >= 0, en komt
     overeen met de som van de breakdown-posten (met het projectminimum van
     EUR 250 als ondergrens).
  3. Voor elke optie die een bespaarmenu toont: de geadverteerde besparing in
     de menutekst komt overeen met het werkelijke verschil nadat de wijziging
     is toegepast en herberekend (dit was precies de bug-klasse die we
     eerder vonden: preview zei "geen besparing" terwijl toepassen wel een
     ander bedrag opleverde, of andersom).
  4. Een bespaaractie ("goedkoper", "verwijderen") verhoogt de prijs nooit.

Scenario's worden gebouwd via de échte flow-klassen (TuinaanlegFlowV2,
LosseOnderdelenFlow) zodat ook de answers->pricing conversie wordt
meegetest, niet alleen handgeschreven dicts.

Los draaien:  python scripts/test_pricing_invariants.py
Exit code 0 = geen afwijkingen gevonden. Exit code 1 = fouten (zie output).
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from core.flows.tuinaanleg import TuinaanlegFlowV2
from core.flows.losse_onderdelen import LosseOnderdelenFlow
from core.pricing.pricing import (
    estimate_tuinaanleg_costs,
    estimate_losse_onderdelen_costs,
    estimate_tuinontwerp_costs,
)
from core.pricing import savings as sv

# ======================================================================
# Boekhouding
# ======================================================================

FAILURES: list[str] = []
N_CHECKS = 0
N_SAVING_OPTIONS_VERIFIED = 0


def fail(ctx: str, msg: str) -> None:
    FAILURES.append(f"[{ctx}] {msg}")


def check(ctx: str, cond: bool, msg: str) -> None:
    global N_CHECKS
    N_CHECKS += 1
    if not cond:
        fail(ctx, msg)


SAVING_RE = re.compile(r"besparing:\s*−€([\d.]+)\s*tot\s*−€([\d.]+)")


def _parse_eur(s: str) -> int:
    return int(s.replace(".", ""))


def _extract_advertised_saving(line: str):
    m = SAVING_RE.search(line)
    if not m:
        return None
    return _parse_eur(m.group(1)), _parse_eur(m.group(2))


TOLERANCE_EUR = 5  # afrondingsmarge (elke regel en het totaal worden apart afgerond)


# ======================================================================
# Generieke prijs-invarianten (elk resultaat van estimate_*_costs)
# ======================================================================

def check_cost_result(ctx: str, costs: dict) -> None:
    tr = costs.get("total_range_eur")
    check(ctx, bool(tr) and len(tr) == 2, "total_range_eur ontbreekt of heeft niet 2 elementen")
    if not tr or len(tr) != 2:
        return
    tmin, tmax = tr
    check(ctx, tmin <= tmax, f"total min ({tmin}) > total max ({tmax})")
    check(ctx, tmin >= 0 and tmax >= 0, f"negatieve prijs: {tr}")
    check(ctx, tmin >= 250 - 1, f"projectminimum niet toegepast: total_min={tmin} < 250")

    if "breakdown" not in costs:
        # bv. estimate_tuinontwerp_costs: vlakke tier-lookup zonder itemized breakdown.
        return

    bd = costs.get("breakdown") or []
    bd_min = bd_max = 0
    for it in bd:
        rng = it.get("range_eur")
        if not rng:
            continue
        lo, hi = rng
        check(ctx, lo <= hi, f"breakdown-post '{it.get('key')}' heeft min ({lo}) > max ({hi})")
        check(ctx, lo >= 0 and hi >= 0, f"breakdown-post '{it.get('key')}' heeft negatieve prijs: {rng}")
        bd_min += lo
        bd_max += hi

    # total hoort de som van de breakdown te zijn, met #250 als vloer.
    expected_min = max(bd_min, 250)
    expected_max = max(bd_max, 250)
    tol = TOLERANCE_EUR + len(bd)  # 1 euro afrondingsmarge per breakdown-regel
    check(
        ctx,
        abs(tmin - expected_min) <= tol,
        f"total_min ({tmin}) wijkt te veel af van som breakdown ({bd_min}, vloer {expected_min}); "
        f"mogelijk een post die niet (of dubbel) meetelt in het totaal",
    )
    check(
        ctx,
        abs(tmax - expected_max) <= tol,
        f"total_max ({tmax}) wijkt te veel af van som breakdown ({bd_max}, vloer {expected_max}); "
        f"mogelijk een post die niet (of dubbel) meetelt in het totaal",
    )


def safe_estimate(ctx: str, fn, answers: dict):
    try:
        return fn(answers)
    except Exception as e:
        fail(ctx, f"crash in {fn.__name__}: {e!r}")
        return None


# ======================================================================
# Generieke bespaar-menu check: geadverteerde besparing == werkelijk verschil
# ======================================================================

def verify_menu_options(
    ctx: str,
    base_answers: dict,
    base_costs: dict,
    menu_text: str,
    mapping: dict,
    apply_fn,
) -> None:
    """
    apply_fn(digit) -> (new_answers, explanation) of None bij onbekende actie.
    Voor elke regel in menu_text met een 'digit)'-nummer: als de tekst een
    besparingsbedrag noemt, moet dat overeenkomen met het werkelijke verschil
    na toepassen + herberekenen. Een bespaaractie mag de prijs nooit verhogen.
    """
    global N_SAVING_OPTIONS_VERIFIED
    base_min, base_max = base_costs["total_range_eur"]
    lines_by_digit = {}
    for line in menu_text.splitlines():
        m = re.match(r"^(\d+)\)\s", line.strip())
        if m:
            lines_by_digit[m.group(1)] = line

    for digit, action in mapping.items():
        if digit == "nee":
            continue
        result = apply_fn(digit, action)
        if result is None:
            continue
        new_answers, explanation = result
        check(ctx, isinstance(explanation, str) and explanation, f"optie {digit} ({action}): lege toelichting na toepassen")

        new_costs = safe_estimate(f"{ctx}/apply({digit}={action})", base_costs["_estimate_fn"], new_answers)
        if new_costs is None:
            continue
        check_cost_result(f"{ctx}/apply({digit}={action})", new_costs)
        new_min, new_max = new_costs["total_range_eur"]

        actual_save_min = base_min - new_min
        actual_save_max = base_max - new_max

        line = lines_by_digit.get(digit, "")
        advertised = _extract_advertised_saving(line)

        if advertised is not None:
            N_SAVING_OPTIONS_VERIFIED += 1
            adv_min, adv_max = advertised
            check(
                ctx,
                abs(actual_save_min - adv_min) <= TOLERANCE_EUR,
                f"optie {digit} ({action}): geadverteerd -EUR{adv_min} maar werkelijk -EUR{actual_save_min} "
                f"(basis {base_min}-{base_max} -> nieuw {new_min}-{new_max})",
            )
            check(
                ctx,
                abs(actual_save_max - adv_max) <= TOLERANCE_EUR,
                f"optie {digit} ({action}): geadverteerd -EUR{adv_max} maar werkelijk -EUR{actual_save_max} "
                f"(basis {base_min}-{base_max} -> nieuw {new_min}-{new_max})",
            )
            # Een geadverteerde besparing moet ook echt >0 zijn (anders had de
            # menu-tekst de optie niet moeten tonen).
            check(ctx, adv_min > 0 or adv_max > 0, f"optie {digit} ({action}): geadverteerde besparing is 0")

        # Universeel: een besparingsactie mag het totaal nooit laten stijgen.
        check(
            ctx,
            new_min <= base_min + TOLERANCE_EUR and new_max <= base_max + TOLERANCE_EUR,
            f"optie {digit} ({action}) verhoogt de prijs: basis {base_min}-{base_max} -> nieuw {new_min}-{new_max}",
        )


def with_estimate_fn(costs: dict, fn) -> dict:
    """Hang de gebruikte pricing-functie aan het costs-dict zodat verify_menu_options
    dezelfde functie kan hergebruiken voor de preview/herberekening."""
    costs = dict(costs)
    costs["_estimate_fn"] = fn
    return costs


# ======================================================================
# Scenario's — Gehele tuin (TuinaanlegFlowV2)
# ======================================================================

def build_tuinaanleg(overrides: dict) -> dict:
    flow = TuinaanlegFlowV2()
    flow.answers.update(overrides)
    return flow.to_answers()


TUINAANLEG_SCENARIOS: dict[str, dict] = {
    "baseline": dict(
        tuin_m2=120.0,
        oprit_m2=25.0, materiaal_oprit="beton",
        terras_m2=20.0, materiaal_terras="keramiek",
        paden_m2=10.0, materiaal_paden="grind",
        gazon_m2=40.0,
        onkruidwerend_gevoegd=True,
    ),
    "alle_materialen_duur_gevoegd": dict(
        tuin_m2=150.0,
        oprit_m2=30.0, materiaal_oprit="keramiek",
        terras_m2=25.0, materiaal_terras="keramiek",
        paden_m2=15.0, materiaal_paden="keramiek",
        gazon_m2=50.0,
        onkruidwerend_gevoegd=True,
    ),
    "alle_materialen_al_grind": dict(
        tuin_m2=100.0,
        oprit_m2=20.0, materiaal_oprit="grind",
        terras_m2=15.0, materiaal_terras="grind",
        paden_m2=10.0, materiaal_paden="grind",
        gazon_m2=40.0,
        onkruidwerend_gevoegd=False,
    ),
    "multi_terras_duur_2e_item": dict(
        tuin_m2=140.0,
        oprit_m2=20.0, materiaal_oprit="beton",
        terras_m2=15.0, materiaal_terras="grind",
        terras_extra_items=[{"m2": 12.0, "materiaal": "keramiek"}],
        paden_m2=10.0, materiaal_paden="beton",
        gazon_m2=40.0,
        onkruidwerend_gevoegd=True,
    ),
    "multi_paden_duur_2e_item": dict(
        tuin_m2=140.0,
        oprit_m2=20.0, materiaal_oprit="grind",
        terras_m2=15.0, materiaal_terras="beton",
        paden_m2=8.0, materiaal_paden="grind",
        paden_extra_items=[{"m2": 9.0, "materiaal": "gebakken"}],
        gazon_m2=40.0,
        onkruidwerend_gevoegd=True,
    ),
    "multi_vlonder_goedkoop_item1_duur_item2": dict(
        tuin_m2=100.0,
        gazon_m2=60.0,
        overige_wensen=["vlonder"],
        vlonder_type="zachthout",
        vlonder_extra_items=[{"m2": 12.0, "type": "composiet"}],
    ),
    "overkapping_klein_geen_downgrade": dict(
        tuin_m2=80.0, gazon_m2=60.0,
        overkapping=True, overkapping_m2=9.0,
    ),
    "overkapping_groot": dict(
        tuin_m2=80.0, gazon_m2=60.0,
        overkapping=True, overkapping_m2=25.0,
    ),
    "verlichting": dict(
        tuin_m2=80.0, gazon_m2=70.0,
        verlichting=True,
    ),
    "beregening_highend_beide": dict(
        tuin_m2=120.0, gazon_m2=90.0,
        overige_wensen=["beregening"],
        beregening_scope=None, beregening_systeem="highend",
    ),
    "beregening_volauto_alleen_gazon": dict(
        tuin_m2=120.0, gazon_m2=90.0,
        overige_wensen=["beregening"],
        beregening_scope="gazon", beregening_systeem="volautomatisch",
    ),
    "beregening_al_basis": dict(
        tuin_m2=120.0, gazon_m2=90.0,
        overige_wensen=["beregening"],
        beregening_scope=None, beregening_systeem="basis",
    ),
    "erf_haag_premium_hoog": dict(
        tuin_m2=100.0, gazon_m2=80.0,
        overige_wensen=["erfafscheiding"],
        erfafscheiding_items=[
            {"type": "haag", "meter": 20.0, "haag_type": "premium_hoog", "poortdeur": None},
        ],
    ),
    "erf_multi_gemengd": dict(
        tuin_m2=120.0, gazon_m2=90.0,
        overige_wensen=["erfafscheiding"],
        erfafscheiding_items=[
            {"type": "haag", "meter": 15.0, "haag_type": "premium_laag", "poortdeur": None},
            {"type": "betonschutting", "meter": 10.0, "poortdeur": True},
            {"type": "design_schutting", "meter": 8.0, "poortdeur": True},
        ],
    ),
    "vlonder_al_goedkoopst": dict(
        tuin_m2=80.0, gazon_m2=70.0,
        overige_wensen=["vlonder"],
        vlonder_type="zachthout",
    ),
    "alles_aan_combinatie": dict(
        tuin_m2=200.0,
        oprit_m2=25.0, materiaal_oprit="gebakken",
        terras_m2=20.0, materiaal_terras="keramiek",
        terras_extra_items=[{"m2": 8.0, "materiaal": "beton"}],
        paden_m2=12.0, materiaal_paden="beton",
        gazon_m2=80.0,
        onkruidwerend_gevoegd=True,
        overkapping=True, overkapping_m2=20.0,
        verlichting=True,
        overige_wensen=["beregening", "vlonder", "erfafscheiding"],
        beregening_scope=None, beregening_systeem="highend",
        vlonder_type="hardhout",
        vlonder_extra_items=[{"m2": 6.0, "type": "composiet"}],
        erfafscheiding_items=[
            {"type": "haag", "meter": 12.0, "haag_type": "premium_hoog", "poortdeur": None},
            {"type": "betonschutting", "meter": 6.0, "poortdeur": True},
        ],
    ),
    "randgeval_niets_ingevuld": dict(
        tuin_m2=50.0, gazon_m2=50.0,
    ),
    "randgeval_grote_tuin": dict(
        tuin_m2=600.0,
        oprit_m2=60.0, materiaal_oprit="keramiek",
        terras_m2=80.0, materiaal_terras="keramiek",
        paden_m2=40.0, materiaal_paden="keramiek",
        gazon_m2=250.0,
        onkruidwerend_gevoegd=True,
    ),
}


def run_tuinaanleg_scenarios() -> None:
    for name, overrides in TUINAANLEG_SCENARIOS.items():
        ctx = f"gehele_tuin/{name}"
        answers = build_tuinaanleg(overrides)
        costs = safe_estimate(ctx, estimate_tuinaanleg_costs, answers)
        if costs is None:
            continue
        check_cost_result(ctx, costs)
        costs = with_estimate_fn(costs, estimate_tuinaanleg_costs)

        menu_text, mapping = sv.lower_costs_menu_text(answers, costs)
        for digit, action in mapping.items():
            sub_ctx = f"{ctx}/{action}"
            _dispatch_gehele_tuin_action(sub_ctx, answers, costs, action)


def _dispatch_gehele_tuin_action(ctx: str, answers: dict, costs: dict, action: str) -> None:
    if action == "more_green":
        menu, mapping = sv.more_green_choice_text(answers, costs)

        def apply(digit, ratio_code):
            a = dict(answers)
            is_items_based = (
                float(a.get("_direct_terras_m2") or 0) > 0
                or float(a.get("_direct_paden_m2") or 0) > 0
                or float(a.get("_direct_oprit_m2") or 0) > 0
                or bool(a.get("terras_extra_items"))
                or bool(a.get("paden_extra_items"))
            )
            if is_items_based:
                return sv.apply_ratio_proportional(a, ratio_code)
            new_a, expl = sv.apply_set_ratio(a, ratio_code)
            new_a.pop("terras_extra_items", None)
            new_a.pop("paden_extra_items", None)
            return new_a, expl

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)

    elif action == "material":
        menu, part_mapping = sv.material_part_menu_text(answers)
        for pdigit, item_spec in part_mapping.items():
            menu2, allowed = sv.material_choice_menu_text_cheaper(answers, costs, item_spec)
            mapping2 = {c: c for c in allowed}

            def apply(digit, choice_digit, _item_spec=item_spec):
                return sv.apply_material_change(dict(answers), _item_spec, choice_digit)

            verify_menu_options(f"{ctx}/{item_spec}", answers, costs, menu2, mapping2, apply)

    elif action == "voegen":
        menu, mapping = sv.voegen_choice_menu_text(answers, costs)

        def apply(digit, _action):
            return sv.apply_voegen_change(dict(answers))

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)

    elif action == "overkapping":
        menu, mapping = sv.overkapping_choice_menu_text(answers, costs)

        def apply(digit, ov_action):
            return sv.apply_overkapping_change(dict(answers), ov_action)

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)

    elif action == "verlichting":
        menu, mapping = sv.verlichting_choice_menu_text(answers, costs)

        def apply(digit, _action):
            return sv.apply_verlichting_change(dict(answers))

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)

    elif action == "beregening":
        menu, mapping = sv.beregening_systeem_choice_text(answers, costs)

        def apply(digit, ber_action):
            if ber_action == "remove":
                return sv.apply_beregening_remove(dict(answers))
            return sv.apply_beregening_systeem_change(dict(answers), ber_action)

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)

    elif action == "vlonder":
        menu, mapping = sv.vlonder_choice_menu_text(answers, costs)

        def apply(digit, vl_action):
            return sv.apply_vlonder_change(dict(answers), vl_action)

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)

    elif action == "erfafscheiding":
        menu, item_mapping = sv.erf_item_select_menu_text(answers, costs)
        items = list(answers.get("erfafscheiding_items") or [])
        for idigit, idx_str in item_mapping.items():
            idx = int(idx_str)
            if idx >= len(items):
                continue
            t = (items[idx].get("type") or "").strip().lower()
            if t == "haag":
                sub_menu, sub_mapping = sv.erf_haag_menu_text(answers, costs, idx)

                def apply(digit, sub_action, _idx=idx):
                    return sv.apply_erf_item_haag_change(dict(answers), _idx, sub_action)
            else:
                sub_menu, sub_mapping = sv.erf_schutting_menu_text(answers, costs, idx)

                def apply(digit, sub_action, _idx=idx):
                    return sv.apply_erf_item_schutting_change(dict(answers), _idx, sub_action)

            verify_menu_options(f"{ctx}/item{idx}", answers, costs, sub_menu, sub_mapping, apply)


# ======================================================================
# Scenario's — Losse onderdelen (LosseOnderdelenFlow)
# ======================================================================

def build_losse(cfg: dict) -> dict:
    flow = LosseOnderdelenFlow()
    flow._configured = cfg
    return flow.to_answers()


LOSSE_SCENARIOS: dict[str, dict] = {
    "baseline_terras_gevoegd": dict(
        terras=[{"m2": 25.0, "materiaal": "keramiek", "gevoegd": True}],
    ),
    "terras_grind_geen_voegen": dict(
        terras=[{"m2": 25.0, "materiaal": "grind", "gevoegd": False}],
    ),
    "multi_terras_verschillend_materiaal": dict(
        terras=[
            {"m2": 25.0, "materiaal": "keramiek", "gevoegd": True},
            {"m2": 15.0, "materiaal": "beton", "gevoegd": True},
        ],
    ),
    "multi_paden_en_oprit": dict(
        oprit=[{"m2": 30.0, "materiaal": "gebakken", "gevoegd": False}],
        paden=[
            {"m2": 8.0, "materiaal": "beton", "gevoegd": True},
            {"m2": 6.0, "materiaal": "keramiek", "gevoegd": True},
        ],
    ),
    "gazon_en_beplanting": dict(
        gazon=[{"m2": 40.0}],
        beplanting=[{"m2": 20.0}],
    ),
    "overkapping": dict(
        overkapping={"m2": 15.0},
    ),
    "verlichting": dict(
        verlichting={},
    ),
    "vlonder": dict(
        vlonder={"m2": 10.0, "type": "composiet"},
    ),
    "beregening_gazon_en_beplanting": dict(
        beregening={"m2": 0, "scope": "", "systeem": "highend", "gazon_m2": 30.0, "beplanting_m2": 15.0},
        gazon=[{"m2": 30.0}],
        beplanting=[{"m2": 15.0}],
    ),
    "beregening_direct_m2": dict(
        beregening={"m2": 25.0, "scope": "", "systeem": "volautomatisch", "gazon_m2": 0, "beplanting_m2": 0},
    ),
    "erf_multi_gemengd": dict(
        erfafscheiding={"items": [
            {"type": "haag", "meter": 15.0, "haag_type": "premium_laag", "poortdeur": None},
            {"type": "design_schutting", "meter": 8.0, "poortdeur": True},
        ]},
    ),
    "alles_aan_combinatie": dict(
        oprit=[{"m2": 25.0, "materiaal": "keramiek", "gevoegd": False}],
        terras=[
            {"m2": 20.0, "materiaal": "keramiek", "gevoegd": True},
            {"m2": 10.0, "materiaal": "beton", "gevoegd": True},
        ],
        paden=[{"m2": 8.0, "materiaal": "gebakken", "gevoegd": True}],
        gazon=[{"m2": 40.0}],
        beplanting=[{"m2": 20.0}],
        overkapping={"m2": 15.0},
        verlichting={},
        vlonder={"m2": 10.0, "type": "hardhout"},
        beregening={"m2": 0, "scope": "", "systeem": "highend", "gazon_m2": 40.0, "beplanting_m2": 20.0},
        erfafscheiding={"items": [
            {"type": "haag", "meter": 12.0, "haag_type": "premium_hoog", "poortdeur": None},
            {"type": "betonschutting", "meter": 6.0, "poortdeur": True},
        ]},
    ),
    "randgeval_alleen_gazon": dict(
        gazon=[{"m2": 60.0}],
    ),
}


def run_losse_scenarios() -> None:
    for name, cfg in LOSSE_SCENARIOS.items():
        ctx = f"losse_onderdelen/{name}"
        answers = build_losse(cfg)
        costs = safe_estimate(ctx, estimate_losse_onderdelen_costs, answers)
        if costs is None:
            continue
        check_cost_result(ctx, costs)
        costs = with_estimate_fn(costs, estimate_losse_onderdelen_costs)

        menu_text, mapping = sv.lower_costs_menu_losse_text(answers, costs)
        for digit, action in mapping.items():
            sub_ctx = f"{ctx}/{action}"
            _dispatch_losse_action(sub_ctx, answers, costs, action)


def _dispatch_losse_action(ctx: str, answers: dict, costs: dict, action: str) -> None:
    if action == "material":
        menu, part_mapping = sv.material_part_menu_text(answers)
        for pdigit, item_spec in part_mapping.items():
            menu2, allowed = sv.material_choice_menu_text_cheaper(answers, costs, item_spec)
            mapping2 = {c: c for c in allowed}

            def apply(digit, choice_digit, _item_spec=item_spec):
                return sv.apply_material_change(dict(answers), _item_spec, choice_digit)

            verify_menu_options(f"{ctx}/{item_spec}", answers, costs, menu2, mapping2, apply)

    elif action == "beregening":
        menu, mapping = sv.beregening_systeem_choice_text(answers, costs)

        def apply(digit, ber_action):
            if ber_action == "remove":
                return sv.apply_beregening_remove(dict(answers))
            return sv.apply_beregening_systeem_change(dict(answers), ber_action)

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)

    elif action in ("oprit_m2", "paden_m2", "terras_m2", "gazon_m2", "beplanting_m2"):
        def apply(digit, comp_key):
            return sv.apply_remove_losse_component(dict(answers), comp_key)

        # losse_component_remove_menu_text geeft dezelfde acties + bespaartekst
        menu, comp_mapping = sv.losse_component_remove_menu_text(answers, costs)
        if action in comp_mapping.values():
            verify_menu_options(ctx, answers, costs, menu, comp_mapping, apply)

    elif re.match(r"^(oprit|paden|terras)_item_\d+$", action):
        m = re.match(r"^(oprit|paden|terras)_item_(\d+)$", action)
        comp_base, index = m.group(1), int(m.group(2))

        def apply(digit, _action, _comp=comp_base, _idx=index):
            return sv.apply_remove_losse_item(dict(answers), _comp, _idx)

        # Herbouw de bijbehorende regel + besparingstekst rechtstreeks
        menu_text, full_mapping = sv.lower_costs_menu_losse_text(answers, costs)
        relevant = {d: a for d, a in full_mapping.items() if a == action}
        verify_menu_options(ctx, answers, costs, menu_text, relevant, apply)

    elif action == "erfafscheiding":
        menu, item_mapping = sv.erf_item_select_menu_text(answers, costs)
        items = list(answers.get("erfafscheiding_items") or [])
        for idigit, idx_str in item_mapping.items():
            idx = int(idx_str)
            if idx >= len(items):
                continue
            t = (items[idx].get("type") or "").strip().lower()
            if t == "haag":
                sub_menu, sub_mapping = sv.erf_haag_menu_text(answers, costs, idx)

                def apply(digit, sub_action, _idx=idx):
                    return sv.apply_erf_item_haag_change(dict(answers), _idx, sub_action)
            else:
                sub_menu, sub_mapping = sv.erf_schutting_menu_text(answers, costs, idx)

                def apply(digit, sub_action, _idx=idx):
                    return sv.apply_erf_item_schutting_change(dict(answers), _idx, sub_action)

            verify_menu_options(f"{ctx}/item{idx}", answers, costs, sub_menu, sub_mapping, apply)

    elif action == "vlonder":
        menu, mapping = sv.vlonder_choice_menu_text(answers, costs)

        def apply(digit, vl_action):
            return sv.apply_vlonder_change(dict(answers), vl_action)

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)

    elif action == "overkapping":
        menu, mapping = sv.overkapping_choice_menu_text(answers, costs)

        def apply(digit, ov_action):
            return sv.apply_overkapping_change(dict(answers), ov_action)

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)

    elif action == "verlichting":
        menu, mapping = sv.verlichting_choice_menu_text(answers, costs)

        def apply(digit, _action):
            return sv.apply_verlichting_change(dict(answers))

        verify_menu_options(ctx, answers, costs, menu, mapping, apply)


# ======================================================================
# Tuinontwerp: alleen basis prijs-invarianten (geen bespaarmenu voor dit type)
# ======================================================================

def run_tuinontwerp_scenarios() -> None:
    for m2 in (30.0, 75.0, 150.0, 400.0):
        ctx = f"tuinontwerp/m2={m2}"
        answers = {"_flow_type": "tuinontwerp", "tuin_m2": m2}
        costs = safe_estimate(ctx, estimate_tuinontwerp_costs, answers)
        if costs is None:
            continue
        check_cost_result(ctx, costs)


# ======================================================================
# Main
# ======================================================================

def main() -> int:
    run_tuinaanleg_scenarios()
    run_losse_scenarios()
    run_tuinontwerp_scenarios()

    print(f"Scenario's gehele tuin: {len(TUINAANLEG_SCENARIOS)}")
    print(f"Scenario's losse onderdelen: {len(LOSSE_SCENARIOS)}")
    print(f"Aantal invariant-checks uitgevoerd: {N_CHECKS}")
    print(f"Aantal bespaaropties met geadverteerd bedrag geverifieerd: {N_SAVING_OPTIONS_VERIFIED}")
    print()

    if FAILURES:
        print(f"FOUTEN GEVONDEN: {len(FAILURES)}")
        print("=" * 70)
        for f in FAILURES:
            print(f"- {f}")
        return 1

    print("Alle checks geslaagd — geen afwijkingen gevonden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
