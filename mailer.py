# mailer.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import resend

try:
    from pricing import (
        format_tuinaanleg_choices_for_customer,
        format_losse_onderdelen_choices_for_customer,
        get_prijstoelichting,
    )
    _PRICING_AVAILABLE = True
except Exception:
    _PRICING_AVAILABLE = False
    def get_prijstoelichting(breakdown=None): return ""

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM    = os.getenv("RESEND_FROM", "Veldman Hoveniers <onboarding@resend.dev>")
NOTIFY_TO      = os.getenv("NOTIFY_TO", "info@veldmanhoveniers.nl")

# Huisstijlkleuren
_GREEN     = "#5c6b1e"
_GREEN_DK  = "#46520f"
_TERRA     = "#b84d1a"
_BG        = "#f4f1ec"
_WHITE     = "#ffffff"
_TEXT      = "#1a1a14"
_MUTED     = "#6b6b50"
_BORDER    = "#d4cfc0"


def _eur(v: int) -> str:
    return f"€{v:,}".replace(",", ".")


def _flow_label(flow_type: Optional[str]) -> str:
    return {
        "gehele_tuin":     "Gehele tuin",
        "losse_onderdelen": "Losse onderdelen",
        "tuinontwerp":     "Tuinontwerp",
    }.get(flow_type or "", "Losse onderdelen")


# ============================================================
# HTML bouwblokken
# ============================================================

def _html_wrapper(content: str, title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:{_BG};font-family:'Segoe UI',Arial,sans-serif;font-size:15px;color:{_TEXT};">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:{_WHITE};border-radius:12px;overflow:hidden;border:1px solid {_BORDER};">

        <!-- Header -->
        <tr>
          <td style="background:{_GREEN};padding:28px 32px;">
            <div style="font-size:22px;font-weight:700;color:{_WHITE};letter-spacing:0.5px;">
              VELDMAN<span style="font-weight:400;">HOVENIERS</span>
            </div>
            <div style="font-size:12px;color:rgba(255,255,255,0.7);margin-top:4px;">
              Ontwerp · Aanleg · Onderhoud
            </div>
          </td>
        </tr>

        <!-- Inhoud -->
        <tr><td style="padding:32px;">
          {content}
        </td></tr>

        <!-- Footer -->
        <tr>
          <td style="background:{_BG};padding:20px 32px;border-top:1px solid {_BORDER};">
            <p style="margin:0;font-size:12px;color:{_MUTED};">
              Veldman Hoveniers &nbsp;·&nbsp; info@veldmanhoveniers.nl &nbsp;·&nbsp; 06-18906921<br>
              <a href="https://www.veldmanhoveniers.nl/privacybeleid/" style="color:{_MUTED};">Privacyverklaring</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ============================================================
# Gegroepeerde breakdown (spiegelt de chatbot-weergave)
# ============================================================

_BESTRATING_KEYS_M = {
    "beton_straatwerk_per_m2", "gebakken_straatwerk_per_m2",
    "keramisch_straatwerk_per_m2", "grind_per_m2",
    "zaagwerk_per_m1", "voegen_straatwerk_per_m2",
}
_GRONDWERK_KEYS_M = {
    "grond_afvoer_per_m3", "zand_aanvoer_per_m3", "puin_aanvoer_per_m3",
}
_GROEN_KEYS_M = {"graszoden_per_m2", "beplanting_border_per_m2"}
_EXTRA_KEY_GROUP_M: Dict[str, str] = {
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
_EXTRA_DISCLAIMERS_M: Dict[str, str] = {
    "Erfafscheiding": "Varieert door: soort, hoogte, ondergrond en bereikbaarheid.",
    "Beregening":     "Afhankelijk van aantal zones, pomp, waterpunt en besturing.",
    "Overkapping":    "Sterk afhankelijk van houtsoort, maatwerk en benodigde fundering.",
    "Verlichting":    "Basis installatie: 3 armaturen incl. trafo en bekabeling. Uitbreiding mogelijk op offerte.",
    "Vlonder":        "Varieert door: hoogteverschillen, fundering en afwerkingsdetails.",
}


def _group_section_html(title: str, disclaimer: str, items: List[Dict]) -> str:
    rows = ""
    for item in items:
        label = item.get("label", "")
        rng   = item.get("range_eur")
        qty   = item.get("qty")
        unit  = (item.get("unit") or "").replace("€/", "").replace("€ ", "").strip()
        qty_txt = (
            f"<span style='color:{_MUTED};font-size:12px;'> ({qty} {unit})</span>"
            if qty is not None and unit else ""
        )
        price = (
            f"{_eur(int(rng[0]))} – {_eur(int(rng[1]))}"
            if rng else f"<span style='color:{_MUTED};'>op offerte</span>"
        )
        rows += f"""
        <tr>
          <td style="padding:5px 0;border-bottom:1px solid {_BORDER};font-size:14px;color:{_TEXT};">
            {label}{qty_txt}
          </td>
          <td style="padding:5px 0;border-bottom:1px solid {_BORDER};text-align:right;font-size:14px;font-weight:600;color:{_GREEN};white-space:nowrap;">
            {price}
          </td>
        </tr>"""

    disc_html = (
        f'<p style="margin:0 0 8px;font-size:12px;color:{_MUTED};font-style:italic;">{disclaimer}</p>'
        if disclaimer else ""
    )
    return f"""
    <div style="margin-bottom:20px;">
      <div style="font-weight:700;font-size:14px;color:{_TEXT};margin-bottom:4px;">{title}</div>
      {disc_html}
      <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
    </div>"""


def _grouped_breakdown_html(costs: Dict[str, Any]) -> str:
    breakdown: List[Dict] = costs.get("breakdown") or []
    if not breakdown:
        return ""

    bestrating: List[Dict] = []
    grondwerk:  List[Dict] = []
    groen:      List[Dict] = []
    extras:     Dict[str, List[Dict]] = {}

    for item in breakdown:
        key = item.get("key")
        if key in _BESTRATING_KEYS_M:
            bestrating.append(item)
        elif key in _GRONDWERK_KEYS_M:
            grondwerk.append(item)
        elif key in _GROEN_KEYS_M:
            groen.append(item)
        elif key in _EXTRA_KEY_GROUP_M:
            extras.setdefault(_EXTRA_KEY_GROUP_M[key], []).append(item)
        else:
            extras.setdefault(item.get("label", "Overig"), []).append(item)

    html = ""
    if grondwerk:
        html += _group_section_html(
            "Grondwerk &amp; fundering t.b.v. bestrating:",
            "Varieert door: bereikbaarheid, grondsoort en afvoermogelijkheden.",
            grondwerk,
        )
    if bestrating:
        html += _group_section_html(
            "Bestrating:",
            "Prijs varieert o.a. door: tegelsoort, hoeken/randen, bereikbaarheid en afwatering.",
            bestrating,
        )
    if groen:
        html += _group_section_html(
            "Groen:",
            "Varieert door: soort, staat van de bodem en egaliseerwerk.",
            groen,
        )
    for group_name, items in extras.items():
        html += _group_section_html(
            f"{group_name}:",
            _EXTRA_DISCLAIMERS_M.get(group_name, ""),
            items,
        )

    html += f"""
    <div style="margin-top:16px;padding:12px 16px;background:{_BG};border-radius:8px;border-left:3px solid {_BORDER};">
      <div style="font-weight:700;font-size:13px;color:{_TEXT};margin-bottom:4px;">
        Sloopwerk &amp; verwijdering bestaande tuin
      </div>
      <div style="font-size:12px;color:{_MUTED};font-style:italic;">
        Nader te bepalen na een inspectiebezoek. Sterk afhankelijk van de bestaande situatie
        (bestrating, beplanting, gazon, schuttingen, etc.).
      </div>
      <div style="font-size:12px;color:{_MUTED};font-style:italic;margin-top:4px;">
        Overweegt u zelf de tuin leeg te halen? Dit kan de sloopkosten aanzienlijk verlagen — vraag ernaar bij het gesprek.
      </div>
    </div>"""

    return html


_STYLE_TUIN_LABELS = {
    "verharding": "Veel verharding – praktisch, weinig onderhoud",
    "gemengd":    "Gemengd – combinatie van verharding én groen",
    "groen":      "Veel groen – gazon en beplanting staan centraal",
}
_STIJL_VOORKEUR_LABELS = {
    "modern":         "Modern & strak",
    "natuurlijk":     "Natuurlijk & landelijk",
    "klassiek":       "Klassiek & sfeervol",
    "geen_voorkeur":  "Nog geen voorkeur",
}
_FASE_LABELS = {
    "oriënterend":          "Oriënterend – kijkt wat er mogelijk is",
    "concrete_plannen":     "Concrete plannen – overweegt binnenkort te beginnen",
    "klaar_om_te_starten":  "Klaar om te starten – wil snel een afspraak",
}
_PRIORITEIT_LABELS = {
    "prijsbewust": "Scherpe prijs",
    "balans":      "Balans kwaliteit / prijs",
    "kwaliteit":   "Kwaliteit & duurzaamheid",
}


def _profiling_html(costs: Optional[Dict[str, Any]], flow_type: Optional[str]) -> str:
    """Klantprofiel-blok voor de eigenaar-mail (alleen bij gehele tuin)."""
    if flow_type != "gehele_tuin" or not costs:
        return ""
    inputs = costs.get("inputs") or {}
    style      = _STYLE_TUIN_LABELS.get(inputs.get("style_tuin") or "", "")
    stijl      = _STIJL_VOORKEUR_LABELS.get(inputs.get("stijl_voorkeur") or "", "")
    fase       = _FASE_LABELS.get(inputs.get("fase") or "", "")
    prioriteit = _PRIORITEIT_LABELS.get(inputs.get("prioriteit") or "", "")
    if not any([style, stijl, fase, prioriteit]):
        return ""

    def _row(label: str, value: str) -> str:
        if not value:
            return ""
        return f"""
      <tr>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};color:{_MUTED};white-space:nowrap;">{label}</td>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};text-align:right;font-weight:600;">{value}</td>
      </tr>"""

    rows = (
        _row("Stijl voorkeur", stijl)
        + _row("Verdeling tuin", style)
        + _row("Fase klant", fase)
        + _row("Prioriteit klant", prioriteit)
    )
    table = f'<table width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
    return _section("Klantprofiel", table)


def _choices_html(costs: Dict[str, Any], flow_type: Optional[str]) -> str:
    """Zet de keuze-samenvatting (markdown-achtig) om naar HTML voor de mail."""
    if not _PRICING_AVAILABLE or not costs:
        return ""
    try:
        if flow_type == "gehele_tuin":
            md = format_tuinaanleg_choices_for_customer(costs)
        elif flow_type == "losse_onderdelen":
            md = format_losse_onderdelen_choices_for_customer(costs)
        else:
            return ""
    except Exception:
        return ""
    if not md:
        return ""

    lines = md.split("\n")
    rows = ""
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("🧾"):
            # verwijder markdown bold en emoji, toon als sectietitel
            clean = line.replace("🧾", "").replace("**", "").strip()
            rows += f'<div style="font-weight:700;font-size:14px;color:{_TEXT};margin-bottom:8px;">{clean}</div>'
        elif line.startswith("  - "):
            item = line[4:].strip()
            rows += f'<div style="padding:2px 0 2px 16px;font-size:13px;color:{_TEXT};">– {item}</div>'
        elif line.startswith("- "):
            item = line[2:].strip().rstrip(":")
            rows += f'<div style="padding:3px 0;font-size:14px;color:{_TEXT};">• {item}</div>'

    return f"""
    <div style="background:{_BG};border-radius:8px;padding:14px 16px;margin-bottom:20px;">
      {rows}
    </div>"""


def _breakdown_html(costs: Dict[str, Any]) -> str:
    breakdown: List[Dict] = costs.get("breakdown") or []
    if not breakdown:
        return ""

    rows = ""
    for item in breakdown:
        label = item.get("label", "")
        rng   = item.get("range_eur")
        qty   = item.get("qty")
        unit  = (item.get("unit") or "").replace("€/", "").replace("€ ", "").strip()
        if rng:
            qty_txt = f"<span style='color:{_MUTED};font-size:13px;'> ({qty} {unit})</span>" if qty is not None and unit else ""
            price   = f"{_eur(int(rng[0]))} – {_eur(int(rng[1]))}"
        else:
            qty_txt = ""
            price   = "<span style='color:{_MUTED};'>op offerte</span>"

        rows += f"""
        <tr>
          <td style="padding:7px 0;border-bottom:1px solid {_BORDER};color:{_TEXT};">
            {label}{qty_txt}
          </td>
          <td style="padding:7px 0;border-bottom:1px solid {_BORDER};text-align:right;font-weight:600;color:{_GREEN_DK};white-space:nowrap;">
            {price}
          </td>
        </tr>"""

    tr = costs.get("total_range_eur") or [0, 0]
    total_row = f"""
        <tr>
          <td style="padding:12px 0 0;font-weight:700;font-size:15px;color:{_TEXT};">Totale indicatie</td>
          <td style="padding:12px 0 0;text-align:right;font-weight:700;font-size:16px;color:{_GREEN};">
            {_eur(int(tr[0]))} – {_eur(int(tr[1]))}
          </td>
        </tr>"""

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px;">
      {rows}
      {total_row}
    </table>"""


def _prijstoelichting_html(breakdown=None) -> str:
    tekst = get_prijstoelichting(breakdown or [])
    if not tekst:
        return ""
    return f"""
    <div style="margin:16px 0;padding:12px 16px;background:{_BG};border-radius:8px;border-left:3px solid {_GREEN};font-size:13px;color:{_MUTED};font-style:italic;line-height:1.6;">
      {tekst}
    </div>"""


def _tuinontwerp_toelichting_html() -> str:
    return f"""
    <div style="margin:16px 0;padding:12px 16px;background:{_BG};border-radius:8px;border-left:3px solid {_GREEN};font-size:13px;color:{_MUTED};font-style:italic;line-height:1.6;">
      <strong>Inbegrepen:</strong> intakegesprek, ontwerptekening en presentatie.
      Na goedkeuring van het ontwerp kunnen wij ook de aanleg voor u verzorgen.<br><br>
      <strong>De prijs varieert o.a. door:</strong> de grootte van de tuin, de detaillering rondom de woning,
      de complexiteit van eventuele bouwkundige elementen en het gewenste detailniveau van het ontwerp.
    </div>"""


def _section(title: str, body: str) -> str:
    return f"""
    <div style="margin-bottom:24px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:{_MUTED};margin-bottom:10px;">
        {title}
      </div>
      {body}
    </div>"""


def _kv(label: str, value: str) -> str:
    return f"""
    <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid {_BORDER};">
      <span style="color:{_MUTED};">{label}</span>
      <span style="font-weight:600;">{value}</span>
    </div>"""


# ============================================================
# Mail 1 — notificatie aan hovenier
# ============================================================

def _leadscore_html(score: int, label: str, breakdown: Optional[Dict[str, int]]) -> str:
    if not score and not label:
        return ""
    label_kleur = {"warm": "#c0392b", "potentieel": "#d68910", "oriënterend": _MUTED}.get(label, _MUTED)
    label_tekst = {"warm": "Warme lead — snel opbellen", "potentieel": "Potentieel — opvolgen",
                   "oriënterend": "Oriënterend — lage prioriteit"}.get(label, label)
    rows = ""
    for k, v in (breakdown or {}).items():
        teken = "+" if v >= 0 else ""
        rows += f"""
        <tr>
          <td style="padding:3px 0;font-size:12px;color:{_MUTED};">{k.replace("_", " ")}</td>
          <td style="padding:3px 0;text-align:right;font-size:12px;font-weight:600;
                     color:{'#27ae60' if v >= 0 else '#c0392b'};">{teken}{v}</td>
        </tr>"""
    table = f'<table width="100%" cellpadding="0" cellspacing="0">{rows}</table>' if rows else ""
    body = f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
      <span style="font-size:28px;font-weight:700;color:{label_kleur};">{score}</span>
      <span style="font-size:14px;font-weight:600;color:{label_kleur};">{label_tekst}</span>
    </div>
    {table}"""
    return _section("Leadscore", body)


def _build_owner_html(
    naam: str, telefoon: str, email: str,
    adres: str, woonplaats: str,
    opmerking: Optional[str],
    costs: Optional[Dict[str, Any]], flow_type: Optional[str],
    leadscore: int = 0, lead_label: str = "", score_breakdown: Optional[Dict[str, int]] = None,
) -> str:
    adres_row = f"""
      <tr>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};color:{_MUTED};">Adres</td>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};text-align:right;font-weight:600;">{adres}</td>
      </tr>""" if adres else ""

    woonplaats_row = f"""
      <tr>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};color:{_MUTED};">Woonplaats</td>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};text-align:right;font-weight:600;">{woonplaats}</td>
      </tr>""" if woonplaats else ""

    opmerking_block = f"""
    <div style="margin-bottom:24px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:{_MUTED};margin-bottom:10px;">
        Opmerkingen
      </div>
      <div style="background:{_BG};border-radius:8px;padding:12px 16px;color:{_TEXT};font-size:14px;">
        {opmerking}
      </div>
    </div>""" if opmerking else ""

    contact_block = f"""
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};color:{_MUTED};">Naam</td>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};text-align:right;font-weight:600;">{naam}</td>
      </tr>
      <tr>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};color:{_MUTED};">Telefoon</td>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};text-align:right;font-weight:600;">
          <a href="tel:{telefoon}" style="color:{_GREEN};text-decoration:none;">{telefoon}</a>
        </td>
      </tr>
      <tr>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};color:{_MUTED};">E-mail</td>
        <td style="padding:7px 0;border-bottom:1px solid {_BORDER};text-align:right;font-weight:600;">
          <a href="mailto:{email}" style="color:{_GREEN};text-decoration:none;">{email}</a>
        </td>
      </tr>
      {adres_row}
      {woonplaats_row}
    </table>"""

    price_block = ""
    if costs:
        tr = costs.get("total_range_eur") or [0, 0]
        price_block = f"""
        <div style="background:{_BG};border-radius:8px;padding:16px 20px;margin-bottom:16px;">
          <div style="font-size:12px;color:{_MUTED};margin-bottom:4px;">
            {_flow_label(flow_type)} &nbsp;·&nbsp; {datetime.now().strftime('%d-%m-%Y %H:%M')}
          </div>
          <div style="font-size:22px;font-weight:700;color:{_GREEN};">
            {_eur(int(tr[0]))} – {_eur(int(tr[1]))}
          </div>
        </div>
        {_tuinontwerp_toelichting_html() if flow_type == "tuinontwerp" else _prijstoelichting_html(costs.get("breakdown") or [])}
        {_grouped_breakdown_html(costs)}"""

    content = f"""
    <h2 style="margin:0 0 4px;font-size:20px;color:{_TEXT};">Nieuwe offerte aanvraag</h2>
    <p style="margin:0 0 24px;color:{_MUTED};font-size:14px;">
      Via de chatbot op veldmanhoveniers.nl
    </p>

    {_section("Contactgegevens", contact_block)}
    {opmerking_block}
    {_section("Prijsindicatie", price_block) if price_block else ""}

    <div style="margin-top:28px;">
      <a href="mailto:{email}"
         style="display:inline-block;background:{_TERRA};color:{_WHITE};padding:12px 24px;
                border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
        Reageer op {naam} →
      </a>
    </div>"""

    return _html_wrapper(content, f"Offerte aanvraag – {naam}")


# ============================================================
# Mail 2 — bevestiging aan klant
# ============================================================

def _build_customer_html(
    naam: str,
    costs: Optional[Dict[str, Any]],
    flow_type: Optional[str],
) -> str:
    price_block = ""
    if costs:
        tr = costs.get("total_range_eur") or [0, 0]
        price_block = f"""
        {_choices_html(costs, flow_type)}

        <div style="margin:16px 0;">
          <div style="font-size:12px;color:{_MUTED};margin-bottom:4px;">
            ✅ Globale inschatting · {_flow_label(flow_type)}
          </div>
          <div style="font-size:11px;color:{_MUTED};font-style:italic;margin-bottom:8px;">
            Iedere tuin is uniek. Deze indicatie is bedoeld als richting, niet als definitieve offerte.
          </div>
          <div style="font-size:22px;font-weight:700;color:{_GREEN};">
            {_eur(int(tr[0]))} – {_eur(int(tr[1]))}
          </div>
        </div>

        {_tuinontwerp_toelichting_html() if flow_type == "tuinontwerp" else _prijstoelichting_html(costs.get("breakdown") or [])}

        <div style="margin-top:20px;">
          {_grouped_breakdown_html(costs)}
        </div>

"""

    content = f"""
    <h2 style="margin:0 0 4px;font-size:20px;color:{_TEXT};">Goed nieuws, {naam}! Uw aanvraag is ontvangen.</h2>
    <p style="margin:0 0 20px;color:{_MUTED};font-size:14px;">
      Bedankt voor uw interesse in Veldman Hoveniers. We nemen zo snel mogelijk contact met u op.
    </p>

    <p style="margin:0 0 16px;color:{_TEXT};">
      Hieronder vindt u de prijsopgave die u heeft ingevuld.
      Dit is een eerste richtprijs. De definitieve offerte stellen wij op na een persoonlijk gesprek op locatie.
    </p>

    {price_block}

    <div style="margin-top:24px;padding:16px 20px;background:{_BG};border-radius:8px;border-left:4px solid {_GREEN};">
      <p style="margin:0 0 6px;font-size:14px;color:{_TEXT};font-weight:700;">Wat kunt u verwachten?</p>
      <p style="margin:0;font-size:14px;color:{_TEXT};">
        Wij nemen telefonisch of per e-mail contact met u op voor een vrijblijvend gesprek op locatie.
        Tijdens dit gesprek kijken wij samen naar uw wensen en stellen wij een persoonlijke offerte op.
      </p>
    </div>

    <div style="margin-top:24px;">
      <a href="https://www.veldmanhoveniers.nl"
         style="display:inline-block;background:{_GREEN};color:{_WHITE};padding:12px 24px;
                border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;">
        Bekijk onze website →
      </a>
    </div>"""

    return _html_wrapper(content, "Uw aanvraag bij Veldman Hoveniers")


# ============================================================
# Publieke functie
# ============================================================

def send_contact_email(
    naam: str,
    telefoon: str,
    email: str,
    adres: str = "",
    woonplaats: str = "",
    opmerking: Optional[str] = None,
    costs: Optional[Dict[str, Any]] = None,
    flow_type: Optional[str] = None,
    leadscore: int = 0,
    lead_label: str = "",
    score_breakdown: Optional[Dict[str, int]] = None,
) -> None:
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY niet ingesteld in .env")

    resend.api_key = RESEND_API_KEY

    # Mail 1 — notificatie aan hovenier
    owner_mail = {
        "from":    RESEND_FROM,
        "to":      [NOTIFY_TO],
        "subject": f"Offerte aanvraag – {naam}",
        "html":    _build_owner_html(
            naam, telefoon, email, adres, woonplaats, opmerking, costs, flow_type,
            leadscore=leadscore, lead_label=lead_label, score_breakdown=score_breakdown,
        ),
    }
    if email and "@" in email:
        owner_mail["reply_to"] = email
    resend.Emails.send(owner_mail)

    # Mail 2 — bevestiging aan klant (best-effort: faalt stil totdat domein geverifieerd is)
    try:
        resend.Emails.send({
            "from":    RESEND_FROM,
            "to":      [email],
            "subject": "Uw aanvraag bij Veldman Hoveniers",
            "html":    _build_customer_html(naam, costs, flow_type),
        })
    except Exception as exc:
        print(f"[mailer] Klantbevestiging niet verstuurd (domein nog niet geverifieerd?): {exc}")
