# mailer.py
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from core.pricing.pricing import (
        format_tuinaanleg_choices_for_customer,
        format_losse_onderdelen_choices_for_customer,
        get_prijstoelichting,
    )
    _PRICING_AVAILABLE = True
except Exception:
    _PRICING_AVAILABLE = False
    def get_prijstoelichting(breakdown=None): return ""

BREVO_SMTP_LOGIN = os.getenv("BREVO_SMTP_LOGIN", "")
BREVO_SMTP_KEY   = os.getenv("BREVO_SMTP_KEY", "")
BREVO_FROM       = os.getenv("BREVO_FROM", "Indiqa <noreply@indiqa.nl>")
NOTIFY_TO        = os.getenv("NOTIFY_TO", "info@veldmanhoveniers.nl")

_BREVO_HOST = "smtp-relay.brevo.com"
_BREVO_PORT = 587


def _send_mail(to: str, subject: str, html: str, reply_to: str = None) -> None:
    if not BREVO_SMTP_LOGIN or not BREVO_SMTP_KEY:
        raise RuntimeError("BREVO_SMTP_LOGIN of BREVO_SMTP_KEY niet ingesteld in .env")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = BREVO_FROM
    msg["To"]      = to
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP(_BREVO_HOST, _BREVO_PORT) as server:
        server.starttls()
        server.login(BREVO_SMTP_LOGIN, BREVO_SMTP_KEY)
        server.send_message(msg)

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
    bedrijfsnaam: str = "Uw hoveniersbedrijf",
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
      Via de rekentool van {bedrijfsnaam}
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
    bekijk_token: Optional[str] = None,
    bedrijfsnaam: str = "Uw hoveniersbedrijf",
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

    portaal_blok = ""
    if bekijk_token:
        _base = os.getenv("BASE_URL", "https://www.veldmanhoveniers.nl")
        _url  = f"{_base}/mijn-offerte/{bekijk_token}"
        portaal_blok = (
            f'<div style="margin-top:20px;padding:16px 20px;background:{_BG};'
            f'border-radius:8px;border-left:4px solid {_GREEN};">'
            f'<p style="margin:0 0 8px;font-size:14px;font-weight:700;color:{_TEXT};">Uw prijsindicatie online bekijken?</p>'
            f'<p style="margin:0 0 12px;font-size:13px;color:{_MUTED};">'
            'Via onderstaande link kunt u uw prijsindicatie altijd terugvinden en bewaren.</p>'
            f'<a href="{_url}" style="display:inline-block;background:{_GREEN};color:{_WHITE};'
            'padding:10px 20px;border-radius:7px;text-decoration:none;font-weight:600;font-size:13px;">'
            'Bekijk uw prijsindicatie &rarr;</a></div>'
        )

    content = f"""
    <h2 style="margin:0 0 4px;font-size:20px;color:{_TEXT};">Goed nieuws, {naam}! Uw aanvraag is ontvangen.</h2>
    <p style="margin:0 0 20px;color:{_MUTED};font-size:14px;">
      Bedankt voor uw interesse in {bedrijfsnaam}. We nemen zo snel mogelijk contact met u op.
    </p>

    <p style="margin:0 0 16px;color:{_TEXT};">
      Hieronder vindt u de prijsopgave die u heeft ingevuld.
      Dit is een eerste richtprijs. De definitieve offerte stellen wij op na een persoonlijk gesprek op locatie.
    </p>

    {price_block}
    {portaal_blok}

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
        Bekijk onze website &rarr;
      </a>
    </div>"""

    return _html_wrapper(content, "Uw aanvraag bij Veldman Hoveniers")


# ============================================================
# Mail 3 — welkomstmail nieuwe Indiqa klant
# ============================================================

_INDIQA_GREEN    = "#1E4D2B"
_INDIQA_GREEN_LT = "#EEF4F0"


def send_welkom_email(
    bedrijfsnaam: str,
    email: str,
    slug: str,
    website_implementatie: bool = False,
    trial_eindigt_op: Optional[datetime] = None,
) -> None:
    base = os.getenv("BASE_URL", "https://indiqa.nl")
    tool_url  = f"https://indiqa.nl/{slug}"
    login_url = f"https://indiqa.nl/beheer/login"

    addon_blok = ""
    if website_implementatie:
        addon_blok = f"""
        <div style="margin-top:16px;padding:14px 18px;background:{_INDIQA_GREEN_LT};
                    border-radius:8px;border-left:4px solid {_INDIQA_GREEN};font-size:14px;">
          <strong>Website-implementatie</strong><br>
          <span style="color:#4A6655;">We nemen binnen 2 werkdagen contact met je op om de planning te bespreken.</span>
        </div>"""

    trial_blok = ""
    if trial_eindigt_op:
        trial_blok = f"""
        <div style="margin-bottom:20px;padding:14px 18px;background:{_INDIQA_GREEN_LT};
                    border-radius:8px;border-left:4px solid {_INDIQA_GREEN};font-size:14px;">
          <strong>Gratis proefperiode tot {trial_eindigt_op.strftime('%d-%m-%Y')}</strong><br>
          <span style="color:#4A6655;">Daarna vragen we je om je abonnement te bevestigen — je hoort dat op tijd van ons.</span>
        </div>"""

    content = f"""
    <h2 style="margin:0 0 6px;font-size:22px;color:{_INDIQA_GREEN};font-weight:800;">
      Welkom bij Indiqa, {bedrijfsnaam}!
    </h2>
    <p style="margin:0 0 24px;font-size:14px;color:#4A6655;">
      Je account is aangemaakt. Hieronder vind je alles wat je nodig hebt om te starten.
    </p>

    {trial_blok}

    <div style="margin-bottom:20px;padding:16px 20px;background:{_INDIQA_GREEN_LT};border-radius:8px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                  color:#7A9882;margin-bottom:10px;">Jouw rekentool</div>
      <a href="{tool_url}" style="font-size:16px;font-weight:700;color:{_INDIQA_GREEN};
                                   text-decoration:none;">{tool_url}</a>
      <div style="font-size:13px;color:#4A6655;margin-top:4px;">
        Gebruik deze link aan tafel bij klanten of deel hem met je team.
      </div>
    </div>

    <div style="margin-bottom:20px;padding:16px 20px;background:#F8FAF8;border:1px solid #DDE8DF;border-radius:8px;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
                  color:#7A9882;margin-bottom:10px;">Beheerpaneel</div>
      <div style="font-size:14px;color:#1C2B23;margin-bottom:10px;">
        Stel je eigen tarieven in en bekijk je leads via het beheerpaneel.
      </div>
      <a href="{login_url}"
         style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                padding:10px 20px;border-radius:7px;text-decoration:none;
                font-weight:600;font-size:13px;">
        Naar het beheerpaneel →
      </a>
    </div>

    {addon_blok}

    <div style="margin-top:24px;padding:16px 20px;background:#F8FAF8;
                border-radius:8px;font-size:14px;color:#4A6655;">
      <strong style="color:#1C2B23;">Eerste stap:</strong> log in en stel je eigen tarieven in.
      De tool werkt direct — we hebben standaard tarieven ingeladen als startpunt.
    </div>

    <p style="margin-top:24px;font-size:13px;color:#7A9882;">
      Vragen? Stuur een mail naar <a href="mailto:info@veldmanhoveniers.nl"
      style="color:{_INDIQA_GREEN};">info@veldmanhoveniers.nl</a>
    </p>"""

    html = f"""<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F0F4F1;font-family:'Segoe UI',Arial,sans-serif;font-size:15px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F0F4F1;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background:#fff;border-radius:12px;
                    overflow:hidden;border:1px solid #DDE8DF;">
        <tr>
          <td style="background:{_INDIQA_GREEN};padding:24px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;letter-spacing:-.03em;">indiqa.</div>
            <div style="font-size:12px;color:rgba(255,255,255,.6);margin-top:3px;">
              Rekentool voor hoveniers
            </div>
          </td>
        </tr>
        <tr><td style="padding:32px;">{content}</td></tr>
        <tr>
          <td style="background:#F0F4F1;padding:18px 32px;border-top:1px solid #DDE8DF;">
            <p style="margin:0;font-size:12px;color:#7A9882;">
              Indiqa · indiqa.nl · info@veldmanhoveniers.nl
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    _send_mail(
        to=email,
        subject=f"Welkom bij Indiqa, {bedrijfsnaam}!",
        html=html,
    )


def send_wachtwoord_reset_email(email: str, reset_url: str) -> None:
    html = f"""<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F0F4F1;font-family:'Segoe UI',Arial,sans-serif;font-size:15px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F0F4F1;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background:#fff;border-radius:12px;
                    overflow:hidden;border:1px solid #DDE8DF;">
        <tr>
          <td style="background:{_INDIQA_GREEN};padding:24px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;letter-spacing:-.03em;">indiqa.</div>
            <div style="font-size:12px;color:rgba(255,255,255,.6);margin-top:3px;">Wachtwoord herstellen</div>
          </td>
        </tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;font-size:20px;color:#1C2B23;">Wachtwoord vergeten?</h2>
          <p style="margin:0 0 24px;font-size:14px;color:#4A6655;line-height:1.6;">
            Gebruik de knop hieronder om een nieuw wachtwoord in te stellen.
            Deze link is 2 uur geldig.
          </p>
          <a href="{reset_url}"
             style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                    padding:12px 28px;border-radius:7px;text-decoration:none;
                    font-weight:600;font-size:14px;">
            Nieuw wachtwoord instellen →
          </a>
          <p style="margin:24px 0 0;font-size:12px;color:#7A9882;">
            Heb je dit niet aangevraagd? Dan hoef je niets te doen.
          </p>
        </td></tr>
        <tr>
          <td style="background:#F0F4F1;padding:16px 32px;border-top:1px solid #DDE8DF;">
            <p style="margin:0;font-size:12px;color:#7A9882;">Indiqa · indiqa.nl</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    _send_mail(to=email, subject="Wachtwoord herstellen — Indiqa", html=html)


def send_nieuwe_aanmelding_email(
    bedrijfsnaam: str,
    email: str,
    regio: str,
    slug: str,
    website_implementatie: bool = False,
    trial_eindigt_op: Optional[datetime] = None,
) -> None:
    """Notificatie aan de Indiqa-beheerder bij elke nieuwe aanmelding."""
    klanten_url = f"{os.getenv('BASE_URL', 'https://indiqa.nl')}/beheer/klanten"
    addon_txt = " + website-implementatie" if website_implementatie else ""
    trial_txt = trial_eindigt_op.strftime("%d-%m-%Y") if trial_eindigt_op else "—"
    html = f"""<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F0F4F1;font-family:'Segoe UI',Arial,sans-serif;font-size:15px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F0F4F1;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background:#fff;border-radius:12px;
                    overflow:hidden;border:1px solid #DDE8DF;">
        <tr>
          <td style="background:{_INDIQA_GREEN};padding:24px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;letter-spacing:-.03em;">indiqa.</div>
            <div style="font-size:12px;color:rgba(255,255,255,.6);margin-top:3px;">Nieuwe aanmelding</div>
          </td>
        </tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 20px;font-size:20px;color:#1C2B23;">Nieuwe aanmelding — account is direct actief</h2>
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #DDE8DF;border-radius:8px;overflow:hidden;font-size:14px;">
            <tr style="background:#F0F4F1;">
              <td style="padding:10px 16px;color:#7A9882;font-weight:600;width:40%;">Bedrijfsnaam</td>
              <td style="padding:10px 16px;color:#1C2B23;font-weight:700;">{bedrijfsnaam}</td>
            </tr>
            <tr>
              <td style="padding:10px 16px;color:#7A9882;font-weight:600;border-top:1px solid #DDE8DF;">E-mail</td>
              <td style="padding:10px 16px;color:#1C2B23;border-top:1px solid #DDE8DF;">{email}</td>
            </tr>
            <tr style="background:#F0F4F1;">
              <td style="padding:10px 16px;color:#7A9882;font-weight:600;border-top:1px solid #DDE8DF;">Regio</td>
              <td style="padding:10px 16px;color:#1C2B23;border-top:1px solid #DDE8DF;">{regio or '—'}</td>
            </tr>
            <tr>
              <td style="padding:10px 16px;color:#7A9882;font-weight:600;border-top:1px solid #DDE8DF;">Chatbot-URL</td>
              <td style="padding:10px 16px;border-top:1px solid #DDE8DF;">
                <a href="https://indiqa.nl/{slug}" style="color:#3E7C4F;font-weight:600;text-decoration:none;">indiqa.nl/{slug}</a>
              </td>
            </tr>
            <tr style="background:#F0F4F1;">
              <td style="padding:10px 16px;color:#7A9882;font-weight:600;border-top:1px solid #DDE8DF;">Proefperiode tot</td>
              <td style="padding:10px 16px;color:#1C2B23;border-top:1px solid #DDE8DF;">{trial_txt}{addon_txt}</td>
            </tr>
          </table>
          <div style="margin-top:24px;">
            <a href="{klanten_url}"
               style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                      padding:12px 24px;border-radius:7px;text-decoration:none;
                      font-weight:600;font-size:14px;">
              Bekijk in klantenoverzicht →
            </a>
          </div>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
    _send_mail(to=NOTIFY_TO, subject=f"Nieuwe aanmelding: {bedrijfsnaam}", html=html)


# ============================================================
# Proefperiode
# ============================================================

def _account_mail_wrapper(header_sub: str, body_html: str) -> str:
    """Gedeelde HTML-wrapper voor de trial-mails, zelfde stijl als de rest van deze module."""
    return f"""<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#F0F4F1;font-family:'Segoe UI',Arial,sans-serif;font-size:15px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F0F4F1;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background:#fff;border-radius:12px;
                    overflow:hidden;border:1px solid #DDE8DF;">
        <tr>
          <td style="background:{_INDIQA_GREEN};padding:24px 32px;">
            <div style="font-size:22px;font-weight:700;color:#fff;letter-spacing:-.03em;">indiqa.</div>
            <div style="font-size:12px;color:rgba(255,255,255,.6);margin-top:3px;">{header_sub}</div>
          </td>
        </tr>
        <tr><td style="padding:32px;">{body_html}</td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_trial_herinnering_email(bedrijfsnaam: str, email: str, slug: str,
                                  verloopt_op: datetime, dagen_resterend: int) -> None:
    """Herinnering aan de klant dat de proefperiode bijna afloopt."""
    login_url = f"{os.getenv('BASE_URL', 'https://indiqa.nl')}/beheer/login"
    dag_txt = "dag" if dagen_resterend == 1 else "dagen"
    body = f"""
      <h2 style="margin:0 0 6px;font-size:20px;color:{_INDIQA_GREEN};font-weight:800;">
        Je proefperiode loopt over {dagen_resterend} {dag_txt} af
      </h2>
      <p style="margin:0 0 20px;font-size:14px;color:#4A6655;">
        Hoi {bedrijfsnaam}, je gratis proefperiode van Indiqa eindigt op
        <strong>{verloopt_op.strftime('%d-%m-%Y')}</strong>. Wil je blijven gebruiken? Neem contact met ons op
        om je abonnement te bevestigen, dan zorgen wij dat je zonder onderbreking door kunt.
      </p>
      <a href="{login_url}"
         style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                padding:12px 24px;border-radius:7px;text-decoration:none;
                font-weight:600;font-size:14px;">
        Naar het beheerpaneel →
      </a>
      <p style="margin-top:24px;font-size:13px;color:#7A9882;">
        Vragen? Stuur een mail naar <a href="mailto:info@veldmanhoveniers.nl"
        style="color:{_INDIQA_GREEN};">info@veldmanhoveniers.nl</a>
      </p>"""
    html = _account_mail_wrapper("Proefperiode loopt af", body)
    _send_mail(to=email, subject=f"Je proefperiode loopt over {dagen_resterend} {dag_txt} af — Indiqa", html=html)


def send_trial_herinnering_admin_email(bedrijfsnaam: str, email: str, slug: str,
                                        verloopt_op: datetime) -> None:
    """Notificatie aan de Indiqa-beheerder: trial loopt bijna af, actie nodig voor betaling."""
    klanten_url = f"{os.getenv('BASE_URL', 'https://indiqa.nl')}/beheer/klanten"
    body = f"""
      <h2 style="margin:0 0 20px;font-size:20px;color:#1C2B23;">Trial loopt bijna af</h2>
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #DDE8DF;border-radius:8px;overflow:hidden;font-size:14px;">
        <tr style="background:#F0F4F1;">
          <td style="padding:10px 16px;color:#7A9882;font-weight:600;width:40%;">Bedrijfsnaam</td>
          <td style="padding:10px 16px;color:#1C2B23;font-weight:700;">{bedrijfsnaam}</td>
        </tr>
        <tr>
          <td style="padding:10px 16px;color:#7A9882;font-weight:600;border-top:1px solid #DDE8DF;">E-mail</td>
          <td style="padding:10px 16px;color:#1C2B23;border-top:1px solid #DDE8DF;">{email}</td>
        </tr>
        <tr style="background:#F0F4F1;">
          <td style="padding:10px 16px;color:#7A9882;font-weight:600;border-top:1px solid #DDE8DF;">Proefperiode tot</td>
          <td style="padding:10px 16px;color:#1C2B23;border-top:1px solid #DDE8DF;">{verloopt_op.strftime('%d-%m-%Y')}</td>
        </tr>
      </table>
      <p style="margin-top:20px;font-size:14px;color:#4A6655;">
        Neem contact op voor de betaling, of markeer als betalend in het klantenoverzicht zodra dat geregeld is.
      </p>
      <div style="margin-top:16px;">
        <a href="{klanten_url}"
           style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                  padding:12px 24px;border-radius:7px;text-decoration:none;
                  font-weight:600;font-size:14px;">
          Bekijk in klantenoverzicht →
        </a>
      </div>"""
    html = _account_mail_wrapper("Trial loopt bijna af", body)
    _send_mail(to=NOTIFY_TO, subject=f"Trial loopt bijna af: {bedrijfsnaam}", html=html)


def send_trial_verlopen_email(bedrijfsnaam: str, email: str, slug: str) -> None:
    """Melding aan de klant dat de proefperiode voorbij is en de rekentool gepauzeerd is."""
    login_url = f"{os.getenv('BASE_URL', 'https://indiqa.nl')}/beheer/login"
    body = f"""
      <h2 style="margin:0 0 6px;font-size:20px;color:{_INDIQA_GREEN};font-weight:800;">
        Je proefperiode is afgelopen
      </h2>
      <p style="margin:0 0 20px;font-size:14px;color:#4A6655;">
        Hoi {bedrijfsnaam}, bedankt dat je Indiqa hebt uitgeprobeerd. Je gratis proefperiode van 30 dagen
        is verlopen en de rekentool voor je klanten is tijdelijk gepauzeerd. Neem contact met ons op om
        door te gaan, dan zetten we je account weer aan.
      </p>
      <p style="margin:0 0 20px;font-size:14px;color:#4A6655;">
        Je beheerpaneel blijft gewoon bereikbaar, dus je kunt inloggen om je gegevens en instellingen te bekijken.
      </p>
      <a href="{login_url}"
         style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                padding:12px 24px;border-radius:7px;text-decoration:none;
                font-weight:600;font-size:14px;">
        Naar het beheerpaneel →
      </a>
      <p style="margin-top:24px;font-size:13px;color:#7A9882;">
        Vragen? Stuur een mail naar <a href="mailto:info@veldmanhoveniers.nl"
        style="color:{_INDIQA_GREEN};">info@veldmanhoveniers.nl</a>
      </p>"""
    html = _account_mail_wrapper("Proefperiode afgelopen", body)
    _send_mail(to=email, subject="Je proefperiode is afgelopen — Indiqa", html=html)


def send_trial_verlopen_admin_email(bedrijfsnaam: str, email: str, slug: str) -> None:
    """Notificatie aan de Indiqa-beheerder: trial verlopen, tenant automatisch gedeactiveerd."""
    klanten_url = f"{os.getenv('BASE_URL', 'https://indiqa.nl')}/beheer/klanten"
    body = f"""
      <h2 style="margin:0 0 20px;font-size:20px;color:#1C2B23;">Trial verlopen — account gedeactiveerd</h2>
      <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #DDE8DF;border-radius:8px;overflow:hidden;font-size:14px;">
        <tr style="background:#F0F4F1;">
          <td style="padding:10px 16px;color:#7A9882;font-weight:600;width:40%;">Bedrijfsnaam</td>
          <td style="padding:10px 16px;color:#1C2B23;font-weight:700;">{bedrijfsnaam}</td>
        </tr>
        <tr>
          <td style="padding:10px 16px;color:#7A9882;font-weight:600;border-top:1px solid #DDE8DF;">E-mail</td>
          <td style="padding:10px 16px;color:#1C2B23;border-top:1px solid #DDE8DF;">{email}</td>
        </tr>
      </table>
      <p style="margin-top:20px;font-size:14px;color:#4A6655;">
        De rekentool van deze klant is automatisch gepauzeerd omdat de proefperiode is verlopen zonder
        dat er betaald is. Markeer de klant als betalend in het klantenoverzicht zodra de betaling geregeld is —
        dat heractiveert het account meteen.
      </p>
      <div style="margin-top:16px;">
        <a href="{klanten_url}"
           style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                  padding:12px 24px;border-radius:7px;text-decoration:none;
                  font-weight:600;font-size:14px;">
          Bekijk in klantenoverzicht →
        </a>
      </div>"""
    html = _account_mail_wrapper("Trial verlopen", body)
    _send_mail(to=NOTIFY_TO, subject=f"Trial verlopen (gedeactiveerd): {bedrijfsnaam}", html=html)


def send_betalend_bevestiging_email(bedrijfsnaam: str, email: str, slug: str) -> None:
    """Bevestiging aan de klant dat het abonnement is bevestigd (geen proefperiode meer)."""
    login_url = f"{os.getenv('BASE_URL', 'https://indiqa.nl')}/beheer/login"
    body = f"""
      <h2 style="margin:0 0 6px;font-size:20px;color:{_INDIQA_GREEN};font-weight:800;">
        Je abonnement is bevestigd
      </h2>
      <p style="margin:0 0 20px;font-size:14px;color:#4A6655;">
        Hoi {bedrijfsnaam}, bedankt! Je Indiqa-abonnement is nu actief — geen proefperiode meer,
        je rekentool blijft gewoon beschikbaar voor je klanten.
      </p>
      <a href="{login_url}"
         style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                padding:12px 24px;border-radius:7px;text-decoration:none;
                font-weight:600;font-size:14px;">
        Naar het beheerpaneel →
      </a>
      <p style="margin-top:24px;font-size:13px;color:#7A9882;">
        Vragen? Stuur een mail naar <a href="mailto:info@veldmanhoveniers.nl"
        style="color:{_INDIQA_GREEN};">info@veldmanhoveniers.nl</a>
      </p>"""
    html = _account_mail_wrapper("Abonnement bevestigd", body)
    _send_mail(to=email, subject="Je Indiqa-abonnement is bevestigd", html=html)


def send_gedeactiveerd_email(bedrijfsnaam: str, email: str, slug: str) -> None:
    """Melding aan de klant dat het account handmatig is gepauzeerd door de beheerder."""
    login_url = f"{os.getenv('BASE_URL', 'https://indiqa.nl')}/beheer/login"
    titel = "Je Indiqa-rekentool is gepauzeerd vanwege een achterstallige betaling"
    intro = (
        f"Hoi {bedrijfsnaam}, je account is tijdelijk gepauzeerd. De rekentool is op dit moment "
        "niet bereikbaar. Je beheerpaneel blijft gewoon toegankelijk."
    )

    body = f"""
      <h2 style="margin:0 0 6px;font-size:20px;color:{_INDIQA_GREEN};font-weight:800;">
        {titel}
      </h2>
      <p style="margin:0 0 20px;font-size:14px;color:#4A6655;">
        {intro}
      </p>
      <p style="margin:0 0 20px;font-size:14px;color:#4A6655;">
        Heb je hier vragen over, of wil je dat we dit weer aanzetten? Neem gerust contact met ons op.
      </p>
      <a href="{login_url}"
         style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                padding:12px 24px;border-radius:7px;text-decoration:none;
                font-weight:600;font-size:14px;">
        Naar het beheerpaneel →
      </a>
      <p style="margin-top:24px;font-size:13px;color:#7A9882;">
        Vragen? Stuur een mail naar <a href="mailto:info@veldmanhoveniers.nl"
        style="color:{_INDIQA_GREEN};">info@veldmanhoveniers.nl</a>
      </p>"""
    html = _account_mail_wrapper(titel, body)
    _send_mail(to=email, subject=titel, html=html)


def send_gereactiveerd_email(bedrijfsnaam: str, email: str, slug: str) -> None:
    """Melding aan de klant dat het account weer is geactiveerd na een pauze."""
    login_url = f"{os.getenv('BASE_URL', 'https://indiqa.nl')}/beheer/login"
    titel = "Je Indiqa-rekentool is weer actief"
    body = f"""
      <h2 style="margin:0 0 6px;font-size:20px;color:{_INDIQA_GREEN};font-weight:800;">
        {titel}
      </h2>
      <p style="margin:0 0 20px;font-size:14px;color:#4A6655;">
        Hoi {bedrijfsnaam}, goed nieuws: je account is weer actief. De rekentool is weer
        bereikbaar.
      </p>
      <a href="{login_url}"
         style="display:inline-block;background:{_INDIQA_GREEN};color:#fff;
                padding:12px 24px;border-radius:7px;text-decoration:none;
                font-weight:600;font-size:14px;">
        Naar het beheerpaneel →
      </a>
      <p style="margin-top:24px;font-size:13px;color:#7A9882;">
        Vragen? Stuur een mail naar <a href="mailto:info@veldmanhoveniers.nl"
        style="color:{_INDIQA_GREEN};">info@veldmanhoveniers.nl</a>
      </p>"""
    html = _account_mail_wrapper(titel, body)
    _send_mail(to=email, subject=titel, html=html)


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
    bekijk_token: Optional[str] = None,
    notify_to: Optional[str] = None,
    bedrijfsnaam: Optional[str] = None,
) -> None:
    ontvanger = notify_to or NOTIFY_TO
    naam_bedrijf = bedrijfsnaam or "Uw hoveniersbedrijf"

    # Mail 1 — notificatie aan hovenier
    _send_mail(
        to=ontvanger,
        subject=f"Offerte aanvraag – {naam}",
        html=_build_owner_html(
            naam, telefoon, email, adres, woonplaats, opmerking, costs, flow_type,
            leadscore=leadscore, lead_label=lead_label, score_breakdown=score_breakdown,
            bedrijfsnaam=naam_bedrijf,
        ),
        reply_to=email if email and "@" in email else None,
    )

    # Mail 2 — bevestiging aan klant
    try:
        _send_mail(
            to=email,
            subject=f"Uw aanvraag bij {naam_bedrijf}",
            html=_build_customer_html(naam, costs, flow_type, bekijk_token=bekijk_token,
                                      bedrijfsnaam=naam_bedrijf),
        )
    except Exception as exc:
        print(f"[mailer] Klantbevestiging niet verstuurd: {exc}")
