# demo.py  —  Hovenier Chatbot Sales Demo Configurator
"""
Gebruik: streamlit run demo.py

Vul links de klantgegevens en tarieven in.
Klik 'Toepassen & chat resetten' om de wijzigingen te activeren.
De chatbot rechts rekent direct met de ingestelde tarieven.
"""
from __future__ import annotations

import contextlib
import html as _html
import os
import re
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pricing as _pm
from pricing import PRIJZEN, GRONDWERK_DIEPTES, VOLUME_KORTINGEN
from bot_logic import handle_message, make_initial_state

# DB tabellen aanmaken als ze nog niet bestaan (veilig om meerdere keren aan te roepen)
try:
    from database import engine, Base
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Demo Configurator – Hovenier Chatbot",
    page_icon="🌿",
    layout="wide",
)

# ─── Module-level constanten ─────────────────────────────────────────────────

_DEPTH_ITEMS: list[tuple] = [
    ("gw_oprit_afvoer",                 "Oprit – ontgraven diepte",           0.35),
    ("gw_oprit_puin",                   "Oprit – puinfundering diepte",       0.25),
    ("gw_oprit_zand",                   "Oprit – zand aanvoer diepte",        0.05),
    ("gw_paden_terras_afvoer",          "Paden/terras – ontgraven (standaard)",0.20),
    ("gw_paden_terras_zand",            "Paden/terras – zand (standaard)",     0.15),
    ("gw_paden_terras_afvoer_keramiek", "Paden/terras – ontgraven (keramiek)", 0.15),
    ("gw_paden_terras_zand_keramiek",   "Paden/terras – zand (keramiek)",      0.10),
]

_VK_LABELS: dict[str, str] = {
    "groen":      "Groen (m²)",
    "bestrating": "Bestrating (m²)",
    "grondwerk":  "Grondwerk (m³)",
    "vlonder":    "Vlonder (m²)",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _greeting(naam: str) -> str:
    return (
        f"Welkom bij **{naam}**! 👋\n\n"
        "Bereken in 2 minuten wat uw tuin kost 👇\n\n"
        "1) De gehele tuin aanleggen – ik stel een paar vragen en reken alles door\n"
        "2) Losse onderdelen – kies zelf wat u wilt laten aanleggen\n"
        "3) Tuinontwerp – professioneel ontwerp met 3D visualisatie\n\n"
        "Reageer met **1**, **2** of **3**."
    )


@contextlib.contextmanager
def _patched(config: dict):
    """
    Tijdelijke override van de globale pricing-variabelen voor de duur van het
    with-blok. Demo-only: werkt alleen single-threaded (localhost).
    """
    orig_p  = dict(_pm.PRIJZEN)
    orig_gw = dict(_pm.GRONDWERK_DIEPTES)
    orig_vk = {k: list(v) for k, v in _pm.VOLUME_KORTINGEN.items()}
    try:
        _pm.PRIJZEN.update(config.get("prijzen", {}))
        _pm.GRONDWERK_DIEPTES.update(config.get("grondwerk_dieptes", {}))
        for cat, tiers in config.get("volume_kortingen", {}).items():
            _pm.VOLUME_KORTINGEN[cat] = [tuple(t) for t in tiers]
        yield
    finally:
        _pm.PRIJZEN.clear()
        _pm.PRIJZEN.update(orig_p)
        _pm.GRONDWERK_DIEPTES.clear()
        _pm.GRONDWERK_DIEPTES.update(orig_gw)
        _pm.VOLUME_KORTINGEN.clear()
        _pm.VOLUME_KORTINGEN.update(orig_vk)


def _handle(state, text: str, config: dict):
    with _patched(config):
        return handle_message(state, text)


def _render_markdown(text: str) -> str:
    """Convert bot markdown to HTML matching the chatbot's JS renderMarkdown."""
    s = _html.escape(text)
    lines = s.split('\n')
    out: list[str] = []
    in_list = False
    list_type = ''
    for line in lines:
        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        line = re.sub(r'(?<![a-zA-Z0-9])_([^_\n]+?)_(?![a-zA-Z0-9])', r'<em>\1</em>', line)
        line = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',
                      r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', line)
        is_bullet = bool(re.match(r'^[-*]\s', line))
        is_num    = bool(re.match(r'^\d+[).]\s', line))
        cur_type  = 'ul' if is_bullet else ('ol' if is_num else '')
        if cur_type:
            if in_list and list_type != cur_type:
                out.append(f'</{list_type}>')
                in_list = False
            if not in_list:
                out.append(f'<{cur_type} class="md-list">')
                in_list = True
                list_type = cur_type
            content = line[2:] if is_bullet else line
            out.append(f'<li>{content}</li>')
        elif line.strip() == '':
            if in_list:
                out.append(f'</{list_type}>')
                in_list = False
                list_type = ''
            out.append('<br>')
        else:
            if in_list:
                out.append(f'</{list_type}>')
                in_list = False
                list_type = ''
            out.append(line + '<br>')
    if in_list:
        out.append(f'</{list_type}>')
    result = ''.join(out)
    result = re.sub(r'(<br>){3,}', '<br><br>', result)
    result = re.sub(r'<br>$', '', result)
    return result


def _chat_css(primary: str) -> str:
    return f"""<style>
:root {{
  --dp: {primary};
  --da: #b84d1a;
  --dbg: #f4f1ec;
  --dbb: #f5f2ed;
  --dbt: #1a1a14;
  --dub: #b84d1a;
  --dut: #ffffff;
  --dsub: #6b6b50;
  --dbrd: #d4cfc0;
}}
.demo-msgs {{ display:flex; flex-direction:column; gap:14px; padding:8px 0;
              font-family:'Segoe UI',system-ui,sans-serif; font-size:15px; line-height:1.6; }}
.demo-row  {{ display:flex; gap:10px; align-items:flex-start; }}
.demo-row.user {{ flex-direction:row-reverse; }}
.demo-av {{ width:38px; height:38px; border-radius:50%; flex-shrink:0;
            display:flex; align-items:center; justify-content:center;
            font-size:1.2em; background:#e8e4d8; box-shadow:0 1px 4px rgba(0,0,0,.12); }}
.demo-row.user .demo-av {{ background:#d4cfc0; }}
.demo-bbl {{ max-width:80%; padding:10px 14px; word-break:break-word;
             border-radius:4px 14px 14px 14px;
             background:var(--dbb); color:var(--dbt);
             box-shadow:0 1px 4px rgba(0,0,0,.07); font-size:14px; line-height:1.6; }}
.demo-row.user .demo-bbl {{ background:var(--dub); color:var(--dut);
                            border-radius:14px 4px 14px 14px; }}
.demo-bbl.wide {{ max-width:96%; }}
.demo-bbl strong {{ font-weight:700; }}
.demo-bbl em     {{ font-style:italic; color:#555; }}
.demo-bbl ol.md-list {{ list-style:none; margin:6px 0 4px 4px; padding:0; }}
.demo-bbl ul.md-list {{ list-style:disc;  margin:6px 0 4px 20px; padding:0; }}
.demo-bbl .md-list li {{ margin:3px 0; }}
.demo-bbl a {{ color:var(--dp); text-decoration:underline; }}
/* Prijskaart */
.cp {{ font-size:14px; line-height:1.5; }}
.cp-choices {{ background:var(--dbg); border-radius:8px; padding:12px 14px; margin-bottom:14px; }}
.cp-chd {{ font-weight:700; font-size:13px; color:var(--dbt); margin-bottom:6px; }}
.cp-ci  {{ font-size:13px; color:var(--dbt); padding:2px 0; }}
.cp-ci-sub {{ padding-left:14px; color:var(--dsub); }}
.cp-est-hd   {{ font-size:16px; font-weight:700; color:var(--dbt); margin-bottom:4px; }}
.cp-est-sub  {{ font-size:13px; color:var(--dbt); margin-bottom:4px; }}
.cp-est-note {{ font-size:12px; font-style:italic; color:var(--dsub); margin-bottom:12px; }}
.cp-total     {{ background:var(--dbg); border-radius:8px; padding:14px 16px; margin-bottom:12px; }}
.cp-total-lbl {{ font-size:12px; color:var(--dsub); margin-bottom:2px; }}
.cp-btw       {{ font-size:11px; font-style:italic; }}
.cp-total-val {{ font-size:22px; font-weight:700; color:var(--dp); }}
.cp-min       {{ font-size:12px; color:var(--dsub); font-style:italic; margin-bottom:10px; }}
.cp-toel {{ background:var(--dbg); border-radius:8px; padding:12px 14px;
            border-left:3px solid var(--dp); font-size:13px; color:var(--dsub);
            font-style:italic; line-height:1.6; margin-bottom:16px; }}
.cp-section  {{ margin-bottom:16px; }}
.cp-sec-hd   {{ font-size:14px; font-weight:700; color:var(--dbt); margin-bottom:4px; }}
.cp-sec-note {{ font-size:12px; font-style:italic; color:var(--dsub); margin-bottom:6px; }}
.cp-row      {{ display:flex; justify-content:space-between; align-items:baseline;
                padding:5px 0; border-bottom:1px solid var(--dbrd); gap:8px; }}
.cp-row-lbl  {{ font-size:13px; color:var(--dbt); flex:1; }}
.cp-qty      {{ font-size:12px; color:var(--dsub); }}
.cp-row-val  {{ font-size:13px; font-weight:600; color:var(--dp); white-space:nowrap; }}
.cp-row-offerte {{ color:var(--dsub); font-weight:normal; }}
.cp-sloop    {{ background:var(--dbg); border-radius:8px; padding:12px 14px;
                border-left:3px solid var(--dbrd); margin:16px 0 12px; }}
.cp-sloop-hd   {{ font-size:13px; font-weight:700; color:var(--dbt); margin-bottom:4px; }}
.cp-sloop-note {{ font-size:12px; color:var(--dsub); font-style:italic; }}
.cp-footer   {{ font-size:12px; color:var(--dsub); font-style:italic; margin-top:8px; }}
.bot-header  {{ background:{primary}; color:#fff; padding:14px 18px;
                font-size:1.05em; font-weight:700; border-radius:8px 8px 0 0; margin-bottom:8px; }}
</style>"""


def _default_config() -> dict:
    return {
        "bedrijf": {
            "naam":     "Uw Hoveniersbedrijf",
            "regio":    "regio Zwolle",
            "email":    "info@uwbedrijf.nl",
            "telefoon": "06-00000000",
            "kleur":    "#5c6b1e",
        },
        "prijzen":           {k: list(v) for k, v in PRIJZEN.items()},
        "grondwerk_dieptes": dict(GRONDWERK_DIEPTES),
        "volume_kortingen":  {k: [list(t) for t in v] for k, v in VOLUME_KORTINGEN.items()},
    }


def _build_config_from_form() -> dict:
    cfg = _default_config()

    # Bedrijfsgegevens
    for field, ss_key in [
        ("naam", "f_naam"), ("regio", "f_regio"),
        ("email", "f_email"), ("telefoon", "f_tel"), ("kleur", "f_kleur"),
    ]:
        if ss_key in st.session_state:
            cfg["bedrijf"][field] = st.session_state[ss_key]

    # Prijzen
    for key in PRIJZEN:
        mn = st.session_state.get(f"p_{key}_min")
        mx = st.session_state.get(f"p_{key}_max")
        if mn is not None:
            cfg["prijzen"][key] = [int(mn), int(mx if mx is not None else mn)]

    # Grondwerk dieptes
    for sk, _, _ in _DEPTH_ITEMS:
        v = st.session_state.get(sk)
        if v is not None:
            cfg["grondwerk_dieptes"][sk[3:]] = float(v)  # sk[3:] strips 'gw_' prefix

    # Volume kortingen
    for cat, tiers in VOLUME_KORTINGEN.items():
        new_tiers = []
        for i, (drempel, factor) in enumerate(tiers):
            d = float(st.session_state.get(f"vk_{cat}_{i}_d", drempel))
            f = float(st.session_state.get(f"vk_{cat}_{i}_f", factor))
            new_tiers.append([d, f])
        cfg["volume_kortingen"][cat] = new_tiers

    return cfg


def _reset_chat(config: dict):
    st.session_state.active_config = config
    st.session_state.chat_state    = make_initial_state()
    st.session_state.messages      = [
        {"role": "assistant", "content": _greeting(config["bedrijf"]["naam"])}
    ]


# ─── Session state init ──────────────────────────────────────────────────────
if "active_config" not in st.session_state:
    _reset_chat(_default_config())

_ac = st.session_state.active_config

# ─── CSS ─────────────────────────────────────────────────────────────────────
_kleur = _ac["bedrijf"].get("kleur", "#5c6b1e")
st.markdown(f"""
<style>
.bot-header {{
    background: {_kleur};
    color: white;
    padding: 10px 18px;
    border-radius: 8px;
    margin-bottom: 10px;
    font-weight: 600;
    font-size: 1.05rem;
    letter-spacing: 0.01em;
}}
</style>
""", unsafe_allow_html=True)

# ─── UI helpers (moeten na page-config staan) ────────────────────────────────

def _pheader() -> None:
    """Min / Max kolomkoppen boven een prijsblok."""
    _, b, c, _ = st.columns([3, 1.4, 1.4, 1.1])
    b.markdown("<span style='font-size:.78rem;font-weight:600;color:#555'>Min</span>",
               unsafe_allow_html=True)
    c.markdown("<span style='font-size:.78rem;font-weight:600;color:#555'>Max</span>",
               unsafe_allow_html=True)


def _prow(label: str, key: str, unit: str, step: int = 1) -> None:
    """Één prijs-rij: label | min-input | max-input | eenheid."""
    d = PRIJZEN.get(key, (0, 0))
    a, b, c, e = st.columns([3, 1.4, 1.4, 1.1])
    a.markdown(f"<span style='font-size:.85rem'>{label}</span>", unsafe_allow_html=True)
    b.number_input("min", value=int(d[0]), step=step,
                   key=f"p_{key}_min", label_visibility="collapsed")
    c.number_input("max", value=int(d[1]), step=step,
                   key=f"p_{key}_max", label_visibility="collapsed")
    e.markdown(f"<span style='font-size:.77rem;color:#777'>{unit}</span>",
               unsafe_allow_html=True)


# ─── Intro ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:#f8fdf0;border-left:4px solid {_kleur};padding:14px 20px;
            border-radius:6px;margin-bottom:1.2rem;font-size:.95rem;">
    <strong>🌿 Hovenier Chatbot – Live Demo</strong>&nbsp;&nbsp;
    <span style="color:#555;">Stel links uw tarieven en bedrijfsgegevens in en zie rechts direct
    hoe de bot eruitziet voor uw klanten.</span>
</div>
""", unsafe_allow_html=True)

_c1, _c2, _c3 = st.columns(3)
with _c1:
    st.markdown("**🤖 Wat doet de bot?**")
    st.markdown(
        "- Begeleidt klanten stap voor stap\n"
        "- Rekent automatisch een prijsschatting op maat\n"
        "- Stuurt offerte-aanvraag direct naar uw e-mail\n"
        "- Legt naam, telefoon en wensen vast"
    )
with _c2:
    st.markdown("**⚙️ Wat is aanpasbaar?**")
    st.markdown(
        "- Alle tarieven per m² / m³ / stuk\n"
        "- Grondwerk dieptes en zaagwerk\n"
        "- Volume kortingen per categorie\n"
        "- Bedrijfsnaam, regio en huisstijlkleur"
    )
with _c3:
    st.markdown("**📈 Wat levert het op?**")
    st.markdown(
        "- 24/7 offertes voor uw klanten\n"
        "- Professionele uitstraling bij uw klanten\n"
        "- Uw eigen tarieven, uw eigen identiteit\n"
        "- Direct een prijsindicatie bij de klant aan tafel"
    )

st.divider()

# ─── Twee-kolom layout ───────────────────────────────────────────────────────
col_cfg, col_chat = st.columns([1, 1.1], gap="large")


# ════════════════════════════════════════
# LINKER KOLOM — Configuratie
# ════════════════════════════════════════
with col_cfg:
    st.subheader("⚙️ Configuratie")

    # ── Bedrijfsgegevens ──────────────────────────────────────────────────────
    with st.expander("🏢 Bedrijfsgegevens", expanded=True):
        st.text_input("Bedrijfsnaam",    value=_ac["bedrijf"]["naam"],     key="f_naam")
        st.text_input("Regio",           value=_ac["bedrijf"]["regio"],    key="f_regio")
        st.text_input("E-mailadres",     value=_ac["bedrijf"]["email"],    key="f_email")
        st.text_input("Telefoon",        value=_ac["bedrijf"]["telefoon"], key="f_tel")
        st.color_picker("Huisstijlkleur", value=_ac["bedrijf"]["kleur"],  key="f_kleur")

    # ── Bestrating ────────────────────────────────────────────────────────────
    with st.expander("🧱 Bestrating"):
        _pheader()
        _prow("Keramisch straatwerk",  "keramisch_straatwerk_per_m2",  "€/m²")
        _prow("Beton straatwerk",      "beton_straatwerk_per_m2",      "€/m²")
        _prow("Gebakken klinkers",     "gebakken_straatwerk_per_m2",   "€/m²")
        _prow("Grind",                 "grind_per_m2",                 "€/m²")
        _prow("Betonband plaatsen",    "plaatsen_betonband_per_m1",    "€/m¹")
        _prow("Zaagwerk",              "zaagwerk_per_m1",              "€/m¹")
        _prow("Voegen straatwerk",     "voegen_straatwerk_per_m2",     "€/m²")

    # ── Groen ─────────────────────────────────────────────────────────────────
    with st.expander("🌿 Groen"):
        _pheader()
        _prow("Graszoden",                    "graszoden_per_m2",                      "€/m²")
        _prow("Beplanting border",            "beplanting_border_per_m2",              "€/m²")
        _prow("Haag voordelig laag (0,5–1m)", "beplanting_haag_voordelig_laag_per_m1", "€/m¹")
        _prow("Haag voordelig hoog (1,5–2m)", "beplanting_haag_voordelig_hoog_per_m1", "€/m¹")
        _prow("Haag premium laag (0,5–1m)",   "beplanting_haag_premium_laag_per_m1",   "€/m¹")
        _prow("Haag premium hoog (1,5–2m)",   "beplanting_haag_premium_hoog_per_m1",   "€/m¹")
        _prow("Boom (incl. aanplant)",        "beplanting_boom_per_stuk",              "€/stuk", step=10)

    # ── Vlonder ───────────────────────────────────────────────────────────────
    with st.expander("🪵 Vlonder"):
        _pheader()
        _prow("Zachthout",  "vlonder_zachthout_per_m2",  "€/m²", step=5)
        _prow("Hardhout",   "vlonder_hardhout_per_m2",   "€/m²", step=5)
        _prow("Composiet",  "vlonder_composiet_per_m2",  "€/m²", step=5)

    # ── Grondwerk ─────────────────────────────────────────────────────────────
    with st.expander("⛏️ Grondwerk"):
        st.markdown("**Tarieven per m³**")
        _pheader()
        _prow("Grond afvoer", "grond_afvoer_per_m3", "€/m³")
        _prow("Zand aanvoer", "zand_aanvoer_per_m3", "€/m³")
        _prow("Puin aanvoer", "puin_aanvoer_per_m3", "€/m³")

        st.markdown("**Aannamedieptes**")
        st.caption(
            "De bot rekent m² bestrating automatisch om naar m³ grondwerk. "
            "Deze dieptes bepalen die berekening."
        )
        for sk, label, default_val in _DEPTH_ITEMS:
            gw_key = sk[3:]  # strip 'gw_'
            a, b, c = st.columns([3.5, 1.5, 0.8])
            a.markdown(f"<span style='font-size:.85rem'>{label}</span>",
                       unsafe_allow_html=True)
            b.number_input(
                "diepte",
                value=float(GRONDWERK_DIEPTES.get(gw_key, default_val)),
                step=0.01,
                format="%.2f",
                key=sk,
                label_visibility="collapsed",
            )
            c.markdown("<span style='font-size:.77rem;color:#777'>m</span>",
                       unsafe_allow_html=True)

    # ── Volume kortingen ──────────────────────────────────────────────────────
    with st.expander("📊 Volume kortingen"):
        st.caption(
            "Factor < 1 geeft korting. De eerste rij met drempel die gehaald wordt, "
            "geldt. Stel drempel op 0 en factor op 1.00 om een rij uit te schakelen."
        )
        for cat, tiers in VOLUME_KORTINGEN.items():
            st.markdown(f"**{_VK_LABELS.get(cat, cat)}**")
            h1, h2, h3, h4, h5 = st.columns([0.9, 1.4, 1.0, 1.4, 1.8])
            h2.markdown("<span style='font-size:.77rem;font-weight:600;color:#555'>Drempel</span>",
                        unsafe_allow_html=True)
            h4.markdown("<span style='font-size:.77rem;font-weight:600;color:#555'>Factor</span>",
                        unsafe_allow_html=True)
            for i, (drempel, factor) in enumerate(tiers):
                a, b, c, d, e = st.columns([0.9, 1.4, 1.0, 1.4, 1.8])
                a.markdown("<span style='font-size:.83rem'>≥</span>",
                           unsafe_allow_html=True)
                b.number_input(
                    "drempel", value=int(drempel), step=5,
                    key=f"vk_{cat}_{i}_d", label_visibility="collapsed",
                )
                c.markdown("<span style='font-size:.83rem'>→</span>",
                           unsafe_allow_html=True)
                f_live = d.number_input(
                    "factor", value=float(factor),
                    min_value=0.50, max_value=1.00,
                    step=0.01, format="%.2f",
                    key=f"vk_{cat}_{i}_f", label_visibility="collapsed",
                )
                korting = round((1.0 - f_live) * 100)
                e.markdown(
                    f"<span style='font-size:.8rem;color:#666'>−{korting}% korting</span>",
                    unsafe_allow_html=True,
                )

    # ── Extras ────────────────────────────────────────────────────────────────
    with st.expander("✨ Extras"):
        _pheader()
        _prow("Overkapping",                "overkapping_per_m2",                    "€/m²",   step=10)
        _prow("Verlichting (basis 3 arm.)", "verlichting_basis_per_stuk",            "€/stuk", step=50)

        st.markdown("*Beregening – vaste installatie*")
        _prow("Basis",         "beregening_installatie_basis",          "€ vast", step=50)
        _prow("Volautomatisch","beregening_installatie_volautomatisch", "€ vast", step=50)
        _prow("High-end",      "beregening_installatie_highend",        "€ vast", step=100)

        st.markdown("*Beregening gazon (per m²)*")
        _prow("Basis",         "beregening_gazon_basis_per_m2",             "€/m²")
        _prow("Volautomatisch","beregening_gazon_volautomatisch_per_m2",    "€/m²")
        _prow("High-end",      "beregening_gazon_highend_per_m2",           "€/m²")

        st.markdown("*Beregening beplanting (per m²)*")
        _prow("Basis",         "beregening_beplanting_basis_per_m2",            "€/m²")
        _prow("Volautomatisch","beregening_beplanting_volautomatisch_per_m2",   "€/m²")
        _prow("High-end",      "beregening_beplanting_highend_per_m2",          "€/m²")

        st.markdown("*Erfafscheiding*")
        _prow("Betonschutting",  "plaatsen_betonschutting_per_m1",   "€/m¹",  step=10)
        _prow("Design schutting","plaatsen_designschutting_per_m1",  "€/m¹",  step=10)
        _prow("Poortdeur",       "plaatsen_poortdeur_per_st",        "€/stuk", step=25)

    # ── Tuinontwerp ───────────────────────────────────────────────────────────
    with st.expander("📐 Tuinontwerp (3D)"):
        _pheader()
        _prow("Ontwerp < 100 m²",    "3d_tuinontwerp_<100m2",     "€", step=50)
        _prow("Ontwerp 100–500 m²",  "3d_tuinontwerp_100-500m2",  "€", step=50)
        _prow("Ontwerp 500–1000 m²", "3d_tuinontwerp_500-1000m2", "€", step=50)
        _prow("Ontwerp > 1000 m²",   "3d_tuinontwerp_>1000m2",    "€", step=50)

    # ── Toepassen ─────────────────────────────────────────────────────────────
    st.divider()
    if st.button("✅ Toepassen & chat resetten", use_container_width=True, type="primary"):
        _reset_chat(_build_config_from_form())
        st.rerun()
    st.caption("Wijzigingen zijn pas actief na klikken op 'Toepassen'.")


# ════════════════════════════════════════
# RECHTER KOLOM — Live chatbot
# ════════════════════════════════════════
with col_chat:
    naam    = _ac["bedrijf"]["naam"]
    regio   = _ac["bedrijf"]["regio"]
    primary = _ac["bedrijf"].get("kleur", "#5c6b1e")

    # CSS injecteren
    st.markdown(_chat_css(primary), unsafe_allow_html=True)

    # Header
    st.markdown(
        f'<div class="bot-header">🌿 {_html.escape(naam)}'
        + (f" &nbsp;·&nbsp; {_html.escape(regio)}" if regio else "")
        + "</div>",
        unsafe_allow_html=True,
    )

    # Chat berichten als gestyled HTML (identiek aan de echte chatbot)
    rows = []
    for msg in st.session_state.messages:
        content = msg["content"] or ""
        if msg["role"] == "assistant":
            if content.startswith("CHATHTML:"):
                inner = content[len("CHATHTML:"):]
                cls   = "demo-bbl wide"
            else:
                inner = _render_markdown(content)
                cls   = "demo-bbl"
            rows.append(
                f'<div class="demo-row bot">'
                f'<div class="demo-av">🌿</div>'
                f'<div class="{cls}">{inner}</div>'
                f'</div>'
            )
        else:
            rows.append(
                f'<div class="demo-row user">'
                f'<div class="demo-bbl">{_html.escape(content)}</div>'
                f'<div class="demo-av">👤</div>'
                f'</div>'
            )
    st.markdown(
        '<div class="demo-msgs">' + ''.join(rows) + '</div>',
        unsafe_allow_html=True,
    )

    # Invoer (form zodat enter werkt en het binnen de kolom blijft)
    with st.form("chat_form", clear_on_submit=True):
        c_inp, c_btn = st.columns([5, 1])
        user_text = c_inp.text_input(
            "invoer",
            placeholder="Typ hier uw antwoord…",
            label_visibility="collapsed",
        )
        send = c_btn.form_submit_button("→", use_container_width=True)

    if send and user_text.strip():
        t = user_text.strip()
        st.session_state.messages.append({"role": "user", "content": t})
        state = st.session_state.chat_state
        state, replies = _handle(state, t, _ac)
        st.session_state.chat_state = state
        for reply in replies:
            st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()
