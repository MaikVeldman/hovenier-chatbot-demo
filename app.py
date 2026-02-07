# app.py
import re
import streamlit as st

from flow_tuinaanleg import TuinaanlegFlow
from pricing import PRIJZEN, estimate_tuinaanleg_costs, format_tuinaanleg_costs_for_customer
from bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON


# =====================
# Config
# =====================
st.set_page_config(page_title=f"{BEDRIJFSNAAM} – Tuinaanleg demo", page_icon="🌿")

st.title("🌿 Tuinaanleg prijsindicatie (demo)")
st.caption(f"{BEDRIJFSNAAM} • {REGIO}")


# =====================
# Constants / Session defaults
# =====================
MAX_RECALC = 5  # gelijk aan main.py


def _init_state():
    if "flow" not in st.session_state:
        st.session_state.flow = TuinaanlegFlow(prijzen=PRIJZEN)

    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": (
                "Hoi! Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.\n\n"
                "Hoe groot is uw tuin in m²? (geef een getal)"
            )
        }]

    if "done" not in st.session_state:
        st.session_state.done = False

    if "post_offer_mode" not in st.session_state:
        st.session_state.post_offer_mode = False

    if "post_offer_stage" not in st.session_state:
        st.session_state.post_offer_stage = None  # "menu" | ... (zie hieronder)

    if "last_answers" not in st.session_state:
        st.session_state.last_answers = None

    if "last_costs" not in st.session_state:
        st.session_state.last_costs = None

    if "recalc_count" not in st.session_state:
        st.session_state.recalc_count = 0

    if "_pending_material_part" not in st.session_state:
        st.session_state._pending_material_part = None  # "1"/"2"/"3"/"4"


_init_state()


# =====================
# Helpers (alignment met main.py)
# =====================
def remaining_recalcs() -> int:
    return max(0, MAX_RECALC - int(st.session_state.recalc_count or 0))


def soft_limit_message() -> str:
    return (
        "We kunnen samen een paar varianten bekijken. Daarna kijken we liever persoonlijk mee, "
        "zodat het echt goed aansluit bij uw situatie."
    )


def post_offer_choices_text() -> str:
    return (
        "Hoe wilt u verder?\n"
        "- **1)** Kijken of er keuzes zijn om de kosten te verlagen\n"
        "- **2)** Contact voor offerte op maat (vrijblijvend)\n"
        "- **3)** Het hierbij laten\n\n"
        "Reageer met **1**, **2** of **3**."
    )


def limit_followup_text() -> str:
    return (
        "Hoe wilt u verder?\n"
        "- **1)** Contact voor offerte op maat (vrijblijvend)\n"
        "- **2)** Het hierbij laten\n\n"
        "Reageer met **1** of **2**."
    )


def _eur(v: int) -> str:
    return f"€{int(v):,}".replace(",", ".")


def _total_range(costs: dict):
    tr = (costs or {}).get("total_range_eur")
    if not tr or len(tr) != 2:
        return None
    return int(tr[0]), int(tr[1])


def _overige_clean(ans: dict | None) -> list[str]:
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


def parse_multi_digits(user_text: str, *, allowed: tuple[str, ...]) -> tuple[str, ...] | None:
    """
    Dummy-proof multi-select:
    - accepteert: "1,3" "1 3" "13" "31" "1/3" "1-3" etc.
    - verwijdert duplicates, behoudt volgorde
    """
    t = (user_text or "").strip().lower()
    if not t:
        return None
    if t in ("nee", "n", "no"):
        return ("nee",)

    digits = re.findall(r"\d", t)
    if not digits:
        return None

    out = []
    seen = set()
    for d in digits:
        if d in allowed and d not in seen:
            out.append(d)
            seen.add(d)

    return tuple(out) if out else None


# ============================================================
# ✅ Besparing: consistent + gekoppelde posten mee (zoals main.py)
# ============================================================
def _sum_breakdown_range_allow_zero(costs: dict | None, *, keys: tuple[str, ...]) -> tuple[int, int]:
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


def _saving_text_from_delta(base_costs: dict, preview_costs: dict, *, keys: tuple[str, ...]) -> str:
    """
    Besparing op basis van delta binnen een set gekoppelde posten.
    Toon alleen goedkoper.
    """
    bmin, bmax = _sum_breakdown_range_allow_zero(base_costs, keys=keys)
    pmin, pmax = _sum_breakdown_range_allow_zero(preview_costs, keys=keys)

    save_min = bmin - pmin
    save_max = bmax - pmax

    if save_max <= 0:
        return ""

    save_min = max(0, save_min)
    save_max = max(0, save_max)

    # altijd oplopend tonen
    lo = min(save_min, save_max)
    hi = max(save_min, save_max)
    return f"(besparing: −{_eur(lo)} tot −{_eur(hi)})"


# ---------------------
# Material ranking (1 duurst -> 4 goedkoopst)
# ---------------------
_MAT_BY_CHOICE = {"1": "keramiek", "2": "gebakken", "3": "beton", "4": "grind"}
_MAT_ORDER = {"keramiek": 1, "gebakken": 2, "beton": 3, "grind": 4}


def _material_rank(mat: str | None) -> int:
    m = (mat or "").strip().lower()
    return _MAT_ORDER.get(m, 3)


def _nice_mat(mat: str | None) -> str:
    m = (mat or "").strip().lower()
    return {"keramiek": "Keramiek", "gebakken": "Gebakken", "beton": "Beton", "grind": "Grind"}.get(m, "Beton")


# ---------------------
# Vlonder ranking (composiet duurst -> zachthout goedkoopst)
# ---------------------
_VLONDER_BY_CHOICE = {"1": "composiet", "2": "hardhout", "3": "zachthout"}
_VLONDER_ORDER = {"composiet": 1, "hardhout": 2, "zachthout": 3}


def _vlonder_rank(v: str | None) -> int:
    vv = (v or "").strip().lower()
    return _VLONDER_ORDER.get(vv, 2)


def _nice_vlonder(v: str | None) -> str:
    vv = (v or "").strip().lower()
    return {"composiet": "Composiet", "hardhout": "Hardhout", "zachthout": "Zachthout"}.get(vv, "Hardhout")


# ---------------------
# Keysets per bespaaroptie (gekoppelde posten)
# ---------------------
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
    "1": ("voegen_straatwerk_per_m2",),
    "2": ("overkapping_basis_per_stuk",),
    "3": ("verlichting_basis_per_stuk",),
    "4": ("beregening_basis_per_m2",),
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
# Menu texts (prijsbesparing) — altijd Markdown-lijsten
# =====================
def lower_costs_menu_text(ans: dict | None) -> str:
    lines = [
        "Waar wilt u eventueel op besparen?",
        "- **1)** Minder bestrating, meer groen (kies een voordeligere verhouding)",
        "- **2)** Extra’s aanpassen (kies welke extra’s u wilt weglaten)",
        "- **3)** Bestratingmateriaal goedkoper kiezen (toon besparing per optie)",
    ]
    if has_vlonder(ans):
        lines.append("- **4)** Vlonder goedkoper maken (toon besparing per optie)")
    if has_erfafscheiding(ans):
        lines.append("- **5)** Erfafscheiding aanpassen/verwijderen (incl. poortdeuren, toon besparing per optie)")
    lines.append("\nReageer met het nummer.")
    return "\n".join(lines)


def more_green_choice_text(ans: dict | None, base_costs: dict | None) -> tuple[str, dict[str, str]]:
    a = dict(ans or {})
    base_costs = base_costs or estimate_tuinaanleg_costs(a)

    candidates = [
        ("1", "50_50", "50/50 (gemengd)"),
        ("2", "30_70", "30/70 (veel groen)"),
    ]

    out = [
        "Welke verhouding wilt u kiezen?",
        "_Ik toon alleen opties die goedkoper uitpakken:_",
    ]
    mapping: dict[str, str] = {}

    for digit, ratio_code, label in candidates:
        preview = dict(a)
        preview["verhouding_bestrating_groen"] = ratio_code
        preview_costs = estimate_tuinaanleg_costs(preview)

        s = _saving_text_from_delta(base_costs, preview_costs, keys=GREEN_LINKED_KEYS)
        if not s:
            continue

        out.append(f"- **{digit}) {label}** {s}")
        mapping[digit] = ratio_code

    if not mapping:
        return (
            "Ik zie op basis van uw invoer geen verhouding die duidelijk goedkoper uitpakt.\n"
            "Kies gerust een andere bespaaroptie.",
            {}
        )

    out.append("\nReageer met het nummer.")
    return "\n".join(out), mapping


def extras_select_menu_text(ans: dict | None, base_costs: dict | None) -> tuple[str, tuple[str, ...]]:
    a = dict(ans or {})
    base_costs = base_costs or estimate_tuinaanleg_costs(a)
    overige = _overige_clean(a)

    labels = {"1": "Voegen", "2": "Overkapping", "3": "Verlichting", "4": "Beregening"}

    lines = [
        "Welke extra’s wilt u weglaten?",
        "_U kunt meerdere opties tegelijk kiezen, bijv. 1,3 (ook 13 werkt)_",
        "_Ik toon alleen opties die goedkoper uitpakken:_",
    ]

    allowed: list[str] = []

    def add_option(opt: str, preview_ans: dict):
        nonlocal allowed, lines
        preview_costs = estimate_tuinaanleg_costs(preview_ans)
        s = _saving_text_from_delta(base_costs, preview_costs, keys=EXTRA_KEYS[opt])
        if not s:
            return
        lines.append(f"- **{opt}) {labels[opt]}** {s}")
        allowed.append(opt)

    # voegen
    if a.get("onkruidwerend_gevoegd") is True:
        p = dict(a)
        p["onkruidwerend_gevoegd"] = False
        add_option("1", p)

    # overkapping
    if a.get("overkapping") is True:
        p = dict(a)
        p["overkapping"] = False
        add_option("2", p)

    # verlichting
    if a.get("verlichting") is True:
        p = dict(a)
        p["verlichting"] = False
        add_option("3", p)

    # beregening
    if "beregening" in overige:
        p = dict(a)
        p["beregening_scope"] = None
        p["overige_wensen"] = [x for x in overige if x != "beregening"]
        add_option("4", p)

    if not allowed:
        return (
            "Ik zie geen extra’s die u nu kunt weglaten met een duidelijke besparing (op basis van uw invoer).\n"
            "Kies gerust een andere bespaaroptie.",
            tuple()
        )

    lines.append("\nTyp **'nee'** als u niets wilt weglaten.")
    return "\n".join(lines), tuple(allowed)


def material_part_menu_text(ans: dict | None) -> str:
    a = ans or {}
    o = int(a.get("oprit_pct") or 0)
    p = int(a.get("paden_pct") or 0)
    t = int(a.get("terras_pct") or 0)

    lines = [
        "Welk onderdeel wilt u goedkoper maken?",
        f"- **1)** Oprit (nu: {_nice_mat(a.get('materiaal_oprit'))})" + ("" if o > 0 else " _(niet van toepassing)_"),
        f"- **2)** Paden (nu: {_nice_mat(a.get('materiaal_paden'))})" + ("" if p > 0 else " _(niet van toepassing)_"),
        f"- **3)** Terras (nu: {_nice_mat(a.get('materiaal_terras'))})" + ("" if t > 0 else " _(niet van toepassing)_"),
        "- **4)** Alle onderdelen",
        "\nReageer met **1**, **2**, **3** of **4**."
    ]
    return "\n".join(lines)


def material_choice_menu_text_cheaper(ans: dict | None, base_costs: dict | None, part: str) -> tuple[str, set[str]]:
    a = dict(ans or {})
    base_costs = base_costs or estimate_tuinaanleg_costs(a)

    def applicable(k: str) -> bool:
        if k == "materiaal_oprit":
            return int(a.get("oprit_pct") or 0) > 0
        if k == "materiaal_paden":
            return int(a.get("paden_pct") or 0) > 0
        if k == "materiaal_terras":
            return int(a.get("terras_pct") or 0) > 0
        return True

    if part == "1":
        targets = ["materiaal_oprit"]
    elif part == "2":
        targets = ["materiaal_paden"]
    elif part == "3":
        targets = ["materiaal_terras"]
    else:
        targets = ["materiaal_oprit", "materiaal_paden", "materiaal_terras"]

    current = []
    for k in targets:
        if applicable(k):
            current.append((k, (a.get(k) or "beton").strip().lower()))

    if not current:
        return ("Dit onderdeel is niet van toepassing (0% gekozen). Kies een ander onderdeel.", set())

    max_rank = max(_material_rank(m) for _, m in current)
    cheaper_choices = {c for c, m in _MAT_BY_CHOICE.items() if _material_rank(m) > max_rank}

    parts_label = {"materiaal_oprit": "Oprit", "materiaal_paden": "Paden", "materiaal_terras": "Terras"}

    lines = ["**Huidige materiaalkeuze:**"]
    for k, m in current:
        lines.append(f"- {parts_label.get(k, k)}: {_nice_mat(m)}")
    lines.append("")
    lines.append("Kies een goedkoper materiaal (1 is duurst, 4 is goedkoopst).")
    lines.append("_Ik toon alleen opties die goedkoper uitpakken:_")

    allowed: set[str] = set()

    for choice in ("1", "2", "3", "4"):
        if choice not in cheaper_choices:
            continue

        preview = dict(a)
        for k, _m in current:
            if _material_rank(_MAT_BY_CHOICE[choice]) <= _material_rank(preview.get(k) or "beton"):
                continue
            preview[k] = _MAT_BY_CHOICE[choice]

        preview_costs = estimate_tuinaanleg_costs(preview)
        savings = _saving_text_from_delta(base_costs, preview_costs, keys=MATERIAL_LINKED_KEYS)
        if not savings:
            continue

        lines.append(f"- **{choice}) {_nice_mat(_MAT_BY_CHOICE[choice])}** {savings}")
        allowed.add(choice)

    if not allowed:
        return (
            "Er is geen materiaaloptie die op basis van uw invoer duidelijk goedkoper uitpakt.\n"
            "Kies gerust een andere bespaaroptie.",
            set()
        )

    lines.append("\nReageer met het nummer.")
    return "\n".join(lines), allowed


def vlonder_choice_menu_text(ans: dict | None, base_costs: dict | None) -> tuple[str, set[str]]:
    a = dict(ans or {})
    if not has_vlonder(a):
        return ("Vlonder is niet gekozen. Kies een andere bespaaroptie.", set())

    base_costs = base_costs or estimate_tuinaanleg_costs(a)

    cur = (a.get("vlonder_type") or "composiet").strip().lower()
    cur_rank = _vlonder_rank(cur)

    lines = [
        f"**Huidige vlonder:** {_nice_vlonder(cur)}",
        "",
        "Kies een goedkopere optie.",
        "_Ik toon alleen opties die goedkoper uitpakken:_",
    ]

    allowed: set[str] = set()

    for choice in ("1", "2", "3"):
        mat = _VLONDER_BY_CHOICE[choice]
        if _vlonder_rank(mat) <= cur_rank:
            continue

        preview = dict(a)
        preview["vlonder_type"] = mat
        preview_costs = estimate_tuinaanleg_costs(preview)

        savings = _saving_text_from_delta(base_costs, preview_costs, keys=VLONDER_KEYS)
        if not savings:
            continue

        lines.append(f"- **{choice}) {_nice_vlonder(mat)}** {savings}")
        allowed.add(choice)

    # verwijderen
    preview = dict(a)
    overige = _overige_clean(preview)
    preview["vlonder_type"] = None
    preview["overige_wensen"] = [x for x in overige if x != "vlonder"]
    preview_costs = estimate_tuinaanleg_costs(preview)
    savings = _saving_text_from_delta(base_costs, preview_costs, keys=VLONDER_KEYS)
    if savings:
        lines.append(f"- **9) Vlonder verwijderen** {savings}")
        allowed.add("9")

    if not allowed:
        return (
            "Ik zie geen vlonder-optie die op basis van uw invoer duidelijk goedkoper uitpakt.\n"
            "Kies gerust een andere bespaaroptie.",
            set()
        )

    lines.append("\nReageer met het nummer.")
    return "\n".join(lines), allowed


def erf_stats(ans: dict | None) -> dict:
    a = ans or {}
    items = list(a.get("erfafscheiding_items") or [])
    stats = {
        "haag_m": 0.0,
        "betonschutting_m": 0.0,
        "design_schutting_m": 0.0,
        "poortdeur_count": 0,
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
        elif t == "betonschutting":
            stats["betonschutting_m"] += m
            if it.get("poortdeur") is True:
                stats["poortdeur_count"] += 1
        elif t == "design_schutting":
            stats["design_schutting_m"] += m
            if it.get("poortdeur") is True:
                stats["poortdeur_count"] += 1
    return stats


def erf_remove_select_menu_text(ans: dict | None, base_costs: dict | None) -> tuple[str, tuple[str, ...]]:
    a = dict(ans or {})
    items = list(a.get("erfafscheiding_items") or [])
    if not items:
        return ("Ik zie geen ingevulde erfafscheiding-items om te verwijderen.", tuple())

    base_costs = base_costs or estimate_tuinaanleg_costs(a)
    stt = erf_stats(a)

    lines = ["**Uw huidige erfafscheiding (op basis van uw invoer):**"]
    if stt["haag_m"] > 0:
        lines.append(f"- Haag: {stt['haag_m']:.1f} m")
    if stt["betonschutting_m"] > 0:
        lines.append(f"- Betonschutting: {stt['betonschutting_m']:.1f} m")
    if stt["design_schutting_m"] > 0:
        lines.append(f"- Design schutting: {stt['design_schutting_m']:.1f} m")
    if stt["poortdeur_count"] > 0:
        lines.append(f"- Poortdeur(en): {stt['poortdeur_count']} st")

    lines += [
        "",
        "Wat wilt u verwijderen?",
        "_U kunt meerdere opties tegelijk kiezen, bijv. 1,3 (ook 13 werkt)_",
        "_Ik toon alleen opties die goedkoper uitpakken:_",
    ]

    allowed: list[str] = []

    def add_option(opt_digit: str, label: str, preview_ans: dict):
        nonlocal allowed, lines
        preview_costs = estimate_tuinaanleg_costs(preview_ans)
        savings = _saving_text_from_delta(base_costs, preview_costs, keys=ERF_KEYS)
        if not savings:
            return
        lines.append(f"- **{opt_digit}) {label}** {savings}")
        allowed.append(opt_digit)

    # 1 haag weg
    if stt["haag_m"] > 0:
        p = dict(a)
        p["erfafscheiding_items"] = [it for it in items if (it.get("type") or "").strip().lower() != "haag"]
        add_option("1", "Haag verwijderen", p)

    # 2 betonschutting weg
    if stt["betonschutting_m"] > 0:
        p = dict(a)
        p["erfafscheiding_items"] = [it for it in items if (it.get("type") or "").strip().lower() != "betonschutting"]
        add_option("2", "Betonschutting verwijderen", p)

    # 3 design schutting weg
    if stt["design_schutting_m"] > 0:
        p = dict(a)
        p["erfafscheiding_items"] = [it for it in items if (it.get("type") or "").strip().lower() != "design_schutting"]
        add_option("3", "Design schutting verwijderen", p)

    # 4 poortdeuren vervallen
    if stt["poortdeur_count"] > 0:
        p = dict(a)
        new_items = []
        for it in items:
            t = (it.get("type") or "").strip().lower()
            it2 = dict(it)
            if t in ("betonschutting", "design_schutting") and it2.get("poortdeur") is True:
                it2["poortdeur"] = False
            new_items.append(it2)
        p["erfafscheiding_items"] = new_items
        add_option("4", "Poortdeur(en) laten vervallen", p)

    if not allowed:
        return (
            "Ik zie geen erfafscheiding-aanpassing die op basis van uw invoer duidelijk goedkoper uitpakt.\n"
            "Kies gerust een andere bespaaroptie.",
            tuple()
        )

    lines.append("\nTyp **'nee'** als u niets wilt verwijderen.")
    return "\n".join(lines), tuple(allowed)


# =====================
# Apply changes (zelfde als main.py)
# =====================
def apply_set_ratio(answers: dict, ratio_code: str) -> tuple[dict, str]:
    a = dict(answers or {})
    a["verhouding_bestrating_groen"] = ratio_code
    pretty = {"50_50": "50/50", "30_70": "30/70", "70_30": "70/30"}.get(ratio_code, ratio_code)
    return a, f"Ik heb de verhouding bestrating/groen aangepast naar **{pretty}**."


def apply_remove_selected_extras(answers: dict, selected: tuple[str, ...]) -> tuple[dict, str]:
    a = dict(answers or {})
    overige = _overige_clean(a)
    chosen_labels = []

    if "1" in selected:
        a["onkruidwerend_gevoegd"] = False
        chosen_labels.append("Voegen")

    if "2" in selected:
        a["overkapping"] = False
        chosen_labels.append("Overkapping")

    if "3" in selected:
        a["verlichting"] = False
        chosen_labels.append("Verlichting")

    if "4" in selected:
        a["beregening_scope"] = None
        overige = [x for x in overige if x != "beregening"]
        chosen_labels.append("Beregening")

    a["overige_wensen"] = overige

    if not chosen_labels:
        return a, "Er is geen extra aangepast."
    return a, "Ik heb aangepast: **" + ", ".join(chosen_labels) + "**."


def apply_material_change(answers: dict, part: str, choice_digit: str) -> tuple[dict, str]:
    a = dict(answers or {})
    mat = _MAT_BY_CHOICE.get(choice_digit)
    if not mat:
        return a, "Onbekende materiaalkeuze."

    if part == "1":
        targets = ["materiaal_oprit"]
    elif part == "2":
        targets = ["materiaal_paden"]
    elif part == "3":
        targets = ["materiaal_terras"]
    else:
        targets = ["materiaal_oprit", "materiaal_paden", "materiaal_terras"]

    changed_targets = []
    for k in targets:
        if k == "materiaal_oprit" and int(a.get("oprit_pct") or 0) == 0:
            continue
        if k == "materiaal_paden" and int(a.get("paden_pct") or 0) == 0:
            continue
        if k == "materiaal_terras" and int(a.get("terras_pct") or 0) == 0:
            continue

        cur = (a.get(k) or "beton").strip().lower()
        if _material_rank(mat) <= _material_rank(cur):
            continue

        a[k] = mat
        changed_targets.append(k.replace("materiaal_", ""))

    if not changed_targets:
        return a, "Dit is niet goedkoper dan uw huidige keuze (geen wijziging)."

    return a, f"Ik heb het materiaal aangepast naar **{_nice_mat(mat)}** voor: **{', '.join(changed_targets)}**."


def apply_vlonder_change(answers: dict, choice: str) -> tuple[dict, str]:
    a = dict(answers or {})
    overige = _overige_clean(a)

    if "vlonder" not in overige:
        return a, "Vlonder stond niet in uw keuzes."

    if choice == "remove":
        a["vlonder_type"] = None
        a["overige_wensen"] = [x for x in overige if x != "vlonder"]
        return a, "Ik heb de vlonder verwijderd uit de keuzes."

    cur = (a.get("vlonder_type") or "composiet").strip().lower()
    if _vlonder_rank(choice) <= _vlonder_rank(cur):
        return a, "Dit is niet goedkoper dan uw huidige vlonderkeuze (geen wijziging)."

    a["vlonder_type"] = choice
    return a, f"Ik heb de vlonder aangepast naar **{_nice_vlonder(choice)}** (goedkoper)."


def apply_erf_changes(answers: dict, selected: tuple[str, ...]) -> tuple[dict, str]:
    a = dict(answers or {})
    items = list(a.get("erfafscheiding_items") or [])
    if not items:
        ov = _overige_clean(a)
        a["overige_wensen"] = [x for x in ov if x != "erfafscheiding"]
        return a, "Erfafscheiding stond niet (meer) ingesteld."

    mapping = {"1": "haag", "2": "betonschutting", "3": "design_schutting"}
    remove_types = {mapping[d] for d in selected if d in mapping}
    remove_poort = "4" in selected

    if remove_poort:
        for it in items:
            t = (it.get("type") or "").strip().lower()
            if t in ("betonschutting", "design_schutting") and it.get("poortdeur") is True:
                it["poortdeur"] = False

    if remove_types:
        items = [it for it in items if (it.get("type") or "").strip().lower() not in remove_types]

    a["erfafscheiding_items"] = items
    msgs = []
    pretty = {"haag": "haag", "betonschutting": "betonschutting", "design_schutting": "design schutting"}
    if remove_types:
        msgs.append("verwijderd: " + ", ".join(pretty.get(t, t) for t in remove_types))
    if remove_poort:
        msgs.append("poortdeur(en) laten vervallen")

    if not msgs:
        return a, "Geen geldige keuze (geen wijziging)."

    return a, "Ik heb aangepast: **" + " • ".join(msgs) + "**."


# =====================
# Sidebar
# =====================
with st.sidebar:
    st.subheader("Demo controls")

    if st.button("🔄 Reset gesprek", use_container_width=True):
        st.session_state.flow = TuinaanlegFlow(prijzen=PRIJZEN)
        st.session_state.messages = [{
            "role": "assistant",
            "content": (
                "Hoi! Ik stel u een paar korte vragen over uw tuin, zodat ik u een gerichte indicatie kan geven.\n\n"
                "Hoe groot is uw tuin in m²? (geef een getal)"
            )
        }]
        st.session_state.done = False
        st.session_state.post_offer_mode = False
        st.session_state.post_offer_stage = None
        st.session_state.last_answers = None
        st.session_state.last_costs = None
        st.session_state.recalc_count = 0
        st.session_state._pending_material_part = None
        st.rerun()

    st.divider()
    st.write("**Contact (voor demo):**")
    st.write(f"- Email: {CONTACT_EMAIL}")
    st.write(f"- Telefoon: {CONTACT_TELEFOON}")


# =====================
# Render chat history (normalize line breaks)
# =====================
for msg in st.session_state.messages:
    content = (msg.get("content") or "").replace("\r\n", "\n").replace("\r", "\n")
    with st.chat_message(msg["role"]):
        st.markdown(content)


# =====================
# Chat input
# =====================
user_text = st.chat_input("Typ je antwoord…")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})

    # -----------------------------------------
    # Post-offer menu logic (zoals main.py)
    # -----------------------------------------
    if st.session_state.post_offer_mode:
        t_raw = user_text.strip()
        t_low = t_raw.lower()

        # contact/offerte shortcut
        if t_low in {"contact", "offerte", "advies"}:
            st.session_state.post_offer_stage = "contact_details"
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?"
            })
            st.rerun()

        # limit follow-up
        if st.session_state.post_offer_stage == "limit_followup":
            if t_raw == "1":
                st.session_state.post_offer_stage = "contact_details"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?"
                })
                st.rerun()
            elif t_raw == "2":
                st.session_state.messages.append({"role": "assistant", "content": "Helemaal goed. Fijn dat u even heeft gekeken. 👋"})
                st.session_state.post_offer_mode = False
                st.session_state.post_offer_stage = "end"
                st.rerun()
            else:
                st.session_state.messages.append({"role": "assistant", "content": limit_followup_text()})
                st.rerun()

        # hoofdmenu
        if st.session_state.post_offer_stage == "menu":
            if t_raw == "1":
                if remaining_recalcs() <= 0:
                    st.session_state.messages.append({"role": "assistant", "content": soft_limit_message()})
                    st.session_state.post_offer_stage = "limit_followup"
                    st.session_state.messages.append({"role": "assistant", "content": limit_followup_text()})
                    st.rerun()

                st.session_state.post_offer_stage = "lower_costs_menu"
                st.session_state.messages.append({"role": "assistant", "content": lower_costs_menu_text(st.session_state.last_answers)})
                st.rerun()

            elif t_raw == "2":
                st.session_state.post_offer_stage = "contact_details"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Top. Wilt u uw naam + postcode + telefoon/e-mail + een korte omschrijving sturen?"
                })
                st.rerun()

            elif t_raw == "3":
                st.session_state.messages.append({"role": "assistant", "content": "Helemaal goed. Fijn dat u even heeft gekeken. 👋"})
                st.session_state.post_offer_mode = False
                st.session_state.post_offer_stage = "end"
                st.rerun()

            else:
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

        # kostenbesparing: categorie
        if st.session_state.post_offer_stage == "lower_costs_menu":
            allowed = {"1", "2", "3"}
            if has_vlonder(st.session_state.last_answers):
                allowed.add("4")
            if has_erfafscheiding(st.session_state.last_answers):
                allowed.add("5")

            if t_raw not in allowed:
                st.session_state.messages.append({"role": "assistant", "content": lower_costs_menu_text(st.session_state.last_answers)})
                st.rerun()

            if t_raw == "1":
                menu, mapping = more_green_choice_text(st.session_state.last_answers, st.session_state.last_costs)
                if not mapping:
                    st.session_state.messages.append({"role": "assistant", "content": menu})
                    st.session_state.post_offer_stage = "menu"
                    st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                    st.rerun()

                st.session_state.post_offer_stage = "lc_more_green_choice"
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.rerun()

            if t_raw == "2":
                menu, allowed_extras = extras_select_menu_text(st.session_state.last_answers, st.session_state.last_costs)
                if not allowed_extras:
                    st.session_state.messages.append({"role": "assistant", "content": menu})
                    st.session_state.post_offer_stage = "menu"
                    st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                    st.rerun()

                st.session_state.post_offer_stage = "lc_extras_select"
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.rerun()

            if t_raw == "3":
                st.session_state.post_offer_stage = "lc_material_part"
                st.session_state.messages.append({"role": "assistant", "content": material_part_menu_text(st.session_state.last_answers)})
                st.rerun()

            if t_raw == "4" and has_vlonder(st.session_state.last_answers):
                menu, allowed_v = vlonder_choice_menu_text(st.session_state.last_answers, st.session_state.last_costs)
                if not allowed_v:
                    st.session_state.messages.append({"role": "assistant", "content": menu})
                    st.session_state.post_offer_stage = "menu"
                    st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                    st.rerun()

                st.session_state.post_offer_stage = "lc_vlonder_choice"
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.rerun()

            if t_raw == "5" and has_erfafscheiding(st.session_state.last_answers):
                menu, allowed_e = erf_remove_select_menu_text(st.session_state.last_answers, st.session_state.last_costs)
                if not allowed_e:
                    st.session_state.messages.append({"role": "assistant", "content": menu})
                    st.session_state.post_offer_stage = "menu"
                    st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                    st.rerun()

                st.session_state.post_offer_stage = "lc_erf_remove_select"
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.rerun()

        # verhouding groen/bestrating
        if st.session_state.post_offer_stage == "lc_more_green_choice":
            menu, mapping = more_green_choice_text(st.session_state.last_answers, st.session_state.last_costs)
            if not mapping:
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.session_state.post_offer_stage = "menu"
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

            if t_raw not in mapping:
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.rerun()

            if remaining_recalcs() <= 0:
                st.session_state.messages.append({"role": "assistant", "content": soft_limit_message()})
                st.session_state.post_offer_stage = "limit_followup"
                st.session_state.messages.append({"role": "assistant", "content": limit_followup_text()})
                st.rerun()

            before_a = dict(st.session_state.last_answers or {})
            before_c = dict(st.session_state.last_costs or {})
            new_a, expl = apply_set_ratio(before_a, mapping[t_raw])

            st.session_state.recalc_count += 1
            new_c = estimate_tuinaanleg_costs(new_a)

            st.session_state.messages.append({"role": "assistant", "content": expl})
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    f"**Oude indicatie:** {_eur((_total_range(before_c) or (0,0))[0])} – {_eur((_total_range(before_c) or (0,0))[1])}\n\n"
                    f"**Nieuwe indicatie:** {_eur((_total_range(new_c) or (0,0))[0])} – {_eur((_total_range(new_c) or (0,0))[1])}"
                )
            })
            st.session_state.messages.append({"role": "assistant", "content": format_tuinaanleg_costs_for_customer(new_c)})

            st.session_state.last_answers = dict(new_a)
            st.session_state.last_costs = dict(new_c)

            st.session_state.post_offer_stage = "menu"
            st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
            st.rerun()

        # extra’s select
        if st.session_state.post_offer_stage == "lc_extras_select":
            menu, allowed_extras = extras_select_menu_text(st.session_state.last_answers, st.session_state.last_costs)
            if not allowed_extras:
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.session_state.post_offer_stage = "menu"
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

            if t_low in ("nee", "n", "no"):
                st.session_state.messages.append({"role": "assistant", "content": "Helemaal goed — we laten de extra’s zoals ze zijn."})
                st.session_state.post_offer_stage = "menu"
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

            parsed = parse_multi_digits(t_raw, allowed=allowed_extras)
            if parsed is None or parsed == ("nee",):
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.rerun()

            if remaining_recalcs() <= 0:
                st.session_state.messages.append({"role": "assistant", "content": soft_limit_message()})
                st.session_state.post_offer_stage = "limit_followup"
                st.session_state.messages.append({"role": "assistant", "content": limit_followup_text()})
                st.rerun()

            before_a = dict(st.session_state.last_answers or {})
            before_c = dict(st.session_state.last_costs or {})
            new_a, expl = apply_remove_selected_extras(before_a, parsed)

            st.session_state.recalc_count += 1
            new_c = estimate_tuinaanleg_costs(new_a)

            st.session_state.messages.append({"role": "assistant", "content": expl})
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    f"**Oude indicatie:** {_eur((_total_range(before_c) or (0,0))[0])} – {_eur((_total_range(before_c) or (0,0))[1])}\n\n"
                    f"**Nieuwe indicatie:** {_eur((_total_range(new_c) or (0,0))[0])} – {_eur((_total_range(new_c) or (0,0))[1])}"
                )
            })
            st.session_state.messages.append({"role": "assistant", "content": format_tuinaanleg_costs_for_customer(new_c)})

            st.session_state.last_answers = dict(new_a)
            st.session_state.last_costs = dict(new_c)

            st.session_state.post_offer_stage = "menu"
            st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
            st.rerun()

        # materiaal: onderdeel
        if st.session_state.post_offer_stage == "lc_material_part":
            if t_raw not in {"1", "2", "3", "4"}:
                st.session_state.messages.append({"role": "assistant", "content": material_part_menu_text(st.session_state.last_answers)})
                st.rerun()

            st.session_state._pending_material_part = t_raw
            menu, allowed_choices = material_choice_menu_text_cheaper(
                st.session_state.last_answers,
                st.session_state.last_costs,
                st.session_state._pending_material_part
            )

            if not allowed_choices:
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.session_state.post_offer_stage = "menu"
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

            st.session_state.post_offer_stage = "lc_material_choice"
            st.session_state.messages.append({"role": "assistant", "content": menu})
            st.rerun()

        # materiaal: keuze
        if st.session_state.post_offer_stage == "lc_material_choice":
            menu, allowed_choices = material_choice_menu_text_cheaper(
                st.session_state.last_answers,
                st.session_state.last_costs,
                st.session_state._pending_material_part or "4"
            )
            if not allowed_choices:
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.session_state.post_offer_stage = "menu"
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

            if t_raw not in allowed_choices:
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.rerun()

            if remaining_recalcs() <= 0:
                st.session_state.messages.append({"role": "assistant", "content": soft_limit_message()})
                st.session_state.post_offer_stage = "limit_followup"
                st.session_state.messages.append({"role": "assistant", "content": limit_followup_text()})
                st.rerun()

            before_a = dict(st.session_state.last_answers or {})
            before_c = dict(st.session_state.last_costs or {})
            new_a, expl = apply_material_change(before_a, st.session_state._pending_material_part or "4", t_raw)

            st.session_state.recalc_count += 1
            new_c = estimate_tuinaanleg_costs(new_a)

            st.session_state.messages.append({"role": "assistant", "content": expl})
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    f"**Oude indicatie:** {_eur((_total_range(before_c) or (0,0))[0])} – {_eur((_total_range(before_c) or (0,0))[1])}\n\n"
                    f"**Nieuwe indicatie:** {_eur((_total_range(new_c) or (0,0))[0])} – {_eur((_total_range(new_c) or (0,0))[1])}"
                )
            })
            st.session_state.messages.append({"role": "assistant", "content": format_tuinaanleg_costs_for_customer(new_c)})

            st.session_state.last_answers = dict(new_a)
            st.session_state.last_costs = dict(new_c)
            st.session_state._pending_material_part = None

            st.session_state.post_offer_stage = "menu"
            st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
            st.rerun()

        # vlonder
        if st.session_state.post_offer_stage == "lc_vlonder_choice":
            menu, allowed_v = vlonder_choice_menu_text(st.session_state.last_answers, st.session_state.last_costs)
            if not allowed_v:
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.session_state.post_offer_stage = "menu"
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

            if t_raw not in allowed_v:
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.rerun()

            if remaining_recalcs() <= 0:
                st.session_state.messages.append({"role": "assistant", "content": soft_limit_message()})
                st.session_state.post_offer_stage = "limit_followup"
                st.session_state.messages.append({"role": "assistant", "content": limit_followup_text()})
                st.rerun()

            before_a = dict(st.session_state.last_answers or {})
            before_c = dict(st.session_state.last_costs or {})

            if t_raw == "9":
                new_a, expl = apply_vlonder_change(before_a, "remove")
            else:
                new_a, expl = apply_vlonder_change(before_a, _VLONDER_BY_CHOICE[t_raw])

            st.session_state.recalc_count += 1
            new_c = estimate_tuinaanleg_costs(new_a)

            st.session_state.messages.append({"role": "assistant", "content": expl})
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    f"**Oude indicatie:** {_eur((_total_range(before_c) or (0,0))[0])} – {_eur((_total_range(before_c) or (0,0))[1])}\n\n"
                    f"**Nieuwe indicatie:** {_eur((_total_range(new_c) or (0,0))[0])} – {_eur((_total_range(new_c) or (0,0))[1])}"
                )
            })
            st.session_state.messages.append({"role": "assistant", "content": format_tuinaanleg_costs_for_customer(new_c)})

            st.session_state.last_answers = dict(new_a)
            st.session_state.last_costs = dict(new_c)

            st.session_state.post_offer_stage = "menu"
            st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
            st.rerun()

        # erfafscheiding
        if st.session_state.post_offer_stage == "lc_erf_remove_select":
            menu, allowed_e = erf_remove_select_menu_text(st.session_state.last_answers, st.session_state.last_costs)
            if not allowed_e:
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.session_state.post_offer_stage = "menu"
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

            if t_low in ("nee", "n", "no"):
                st.session_state.messages.append({"role": "assistant", "content": "Helemaal goed — we laten de erfafscheiding zoals hij is."})
                st.session_state.post_offer_stage = "menu"
                st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
                st.rerun()

            parsed = parse_multi_digits(t_raw, allowed=allowed_e)
            if parsed is None or parsed == ("nee",):
                st.session_state.messages.append({"role": "assistant", "content": menu})
                st.rerun()

            if remaining_recalcs() <= 0:
                st.session_state.messages.append({"role": "assistant", "content": soft_limit_message()})
                st.session_state.post_offer_stage = "limit_followup"
                st.session_state.messages.append({"role": "assistant", "content": limit_followup_text()})
                st.rerun()

            before_a = dict(st.session_state.last_answers or {})
            before_c = dict(st.session_state.last_costs or {})
            new_a, expl = apply_erf_changes(before_a, parsed)

            st.session_state.recalc_count += 1
            new_c = estimate_tuinaanleg_costs(new_a)

            st.session_state.messages.append({"role": "assistant", "content": expl})
            st.session_state.messages.append({
                "role": "assistant",
                "content": (
                    f"**Oude indicatie:** {_eur((_total_range(before_c) or (0,0))[0])} – {_eur((_total_range(before_c) or (0,0))[1])}\n\n"
                    f"**Nieuwe indicatie:** {_eur((_total_range(new_c) or (0,0))[0])} – {_eur((_total_range(new_c) or (0,0))[1])}"
                )
            })
            st.session_state.messages.append({"role": "assistant", "content": format_tuinaanleg_costs_for_customer(new_c)})

            st.session_state.last_answers = dict(new_a)
            st.session_state.last_costs = dict(new_c)

            st.session_state.post_offer_stage = "menu"
            st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})
            st.rerun()

        # contact details
        if st.session_state.post_offer_stage == "contact_details":
            st.session_state.messages.append({"role": "assistant", "content": "Dank u wel! We nemen zo snel mogelijk contact met u op!"})
            st.session_state.post_offer_mode = False
            st.session_state.post_offer_stage = "end"
            st.rerun()

    # -----------------------------------------
    # Flow logic
    # -----------------------------------------
    if not st.session_state.done and not st.session_state.post_offer_mode:
        reply, done = st.session_state.flow.handle(user_text)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.session_state.done = done

        if done:
            ans = st.session_state.flow.answers
            costs = estimate_tuinaanleg_costs(ans)
            klanttekst = format_tuinaanleg_costs_for_customer(costs)

            st.session_state.messages.append({
                "role": "assistant",
                "content": "Iedere tuin is uniek. Deze indicatie is bedoeld als richting, niet als definitieve offerte."
            })
            st.session_state.messages.append({"role": "assistant", "content": klanttekst})

            st.session_state.last_answers = dict(ans)
            st.session_state.last_costs = dict(costs)

            st.session_state.post_offer_mode = True
            st.session_state.post_offer_stage = "menu"
            st.session_state.messages.append({"role": "assistant", "content": post_offer_choices_text()})

        st.rerun()
