# server.py
from __future__ import annotations

import os
import uuid
import functools
from datetime import datetime, timezone
from typing import Dict

from dotenv import load_dotenv
load_dotenv()

from flask import (
    Flask, jsonify, request, send_from_directory,
    render_template, redirect, url_for, session as flask_session,
)
from flask_cors import CORS

from infrastructure.config.bedrijf import BEDRIJFSNAAM, REGIO
from core.controllers.chat_controller import ChatController, INITIAL_GREETING
from core.models.chat_state import make_initial_state
from core.models.tenant_context import TenantContext
from core.pricing.price_table import PriceTable
from infrastructure.db.repositories.tenant_repository import TenantRepository

# ============================================================
# Demo modus: DEMO_MODE=1 laadt voorbeeldprijzen in plaats van
# de echte bedrijfsprijzen. Stel in via environment variable.
# ============================================================
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"
if DEMO_MODE:
    import core.pricing.pricing as _p
    from pricing_demo import PRIJZEN_DEMO, VOLUME_KORTINGEN_DEMO, GRONDWERK_DIEPTES_DEMO
    _p.PRIJZEN.clear()
    _p.PRIJZEN.update(PRIJZEN_DEMO)
    _p.VOLUME_KORTINGEN.clear()
    _p.VOLUME_KORTINGEN.update({k: [tuple(t) for t in v] for k, v in VOLUME_KORTINGEN_DEMO.items()})
    _p.GRONDWERK_DIEPTES.clear()
    _p.GRONDWERK_DIEPTES.update(GRONDWERK_DIEPTES_DEMO)

try:
    from infrastructure.db.db_logger import log_session_created, log_message
    _DB = True
except Exception:
    _DB = False

def _refresh_price_table() -> None:
    if not _DB:
        return
    try:
        import core.pricing.pricing as _p
        import core.pricing.price_table as _pt
        from core.pricing.constants import PRIJZEN as _BASE

        tenant_config = TenantRepository().get_or_default(TENANT_SLUG)
        overrides = tenant_config.prijzen or {}

        # In-place update zodat alle PRIJZEN.get() aanroepen in pricing.py de juiste waarden zien
        _p.PRIJZEN.clear()
        _p.PRIJZEN.update(_BASE)
        _p.PRIJZEN.update(overrides)

        # Ook DEFAULT_PRICE_TABLE verversen voor PriceTable-bewuste aanroepen
        _pt.DEFAULT_PRICE_TABLE = PriceTable(tenant_config)
    except Exception as e:
        print(f"[server] Prijstabel verversen mislukt: {e}")

ADMIN_USER     = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
SECRET_KEY     = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
TENANT_SLUG    = os.getenv("TENANT_SLUG", "veldmanhoveniers")
BASE_URL       = os.getenv("BASE_URL", "http://localhost:5000")

app = Flask(__name__, static_folder="static", static_url_path="", template_folder="templates")
app.secret_key = SECRET_KEY

_origins = ["https://veldmanhoveniers.nl", "https://www.veldmanhoveniers.nl"]
if DEMO_MODE:
    _origins += ["https://indiqa.nl", "https://www.indiqa.nl", "https://demo.indiqa.nl"]
CORS(app, origins=_origins)

# Laad tenant-prijzen bij opstart
_refresh_price_table()

# ============================================================
# Template globals
# ============================================================

@app.context_processor
def _inject_session():
    return {"session": flask_session}

# ============================================================
# Admin auth helper
# ============================================================

def _admin_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not flask_session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

# In-memory session store — prima voor demo/productie op één server
_sessions: Dict[str, object] = {}


def _get_or_create(session_id: str | None):
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]
    sid = str(uuid.uuid4())
    state = make_initial_state(session_id=sid)
    _sessions[sid] = state
    if _DB:
        ua = request.headers.get("User-Agent", "")
        log_session_created(sid, user_agent=ua)
    return sid, _sessions[sid]


@app.route("/")
def index():
    response = send_from_directory("static", "index.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/api/info")
def info():
    return jsonify({
        "bedrijfsnaam": BEDRIJFSNAAM,
        "regio": REGIO,
        "demo": DEMO_MODE,
    })


@app.route("/api/reset", methods=["POST"])
def reset():
    data = request.get_json(silent=True) or {}
    old_sid = data.get("session_id")
    if old_sid and old_sid in _sessions:
        del _sessions[old_sid]
    sid = str(uuid.uuid4())
    state = make_initial_state(session_id=sid)
    _sessions[sid] = state
    if _DB:
        ua = request.headers.get("User-Agent", "")
        log_session_created(sid, user_agent=ua)
    return jsonify({
        "session_id": sid,
        "messages": [{"role": "bot", "text": INITIAL_GREETING}],
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "empty message"}), 400

    slug = request.headers.get("X-Tenant-Slug", "veldman-hoveniers")
    tenant_cfg = TenantRepository().get_or_default(slug)
    tenant_ctx = TenantContext(config=tenant_cfg, price_table=PriceTable(tenant_cfg))

    sid, state = _get_or_create(session_id)
    ctrl = ChatController(state, tenant_ctx)
    state, new_messages = ctrl.handle(message)
    _sessions[sid] = state

    if _DB:
        log_message(sid, "user", message)
        for m in new_messages:
            log_message(sid, "bot", m)

    return jsonify({
        "session_id": sid,
        "messages": [{"role": "bot", "text": m} for m in new_messages],
    })


# ============================================================
# Admin routes
# ============================================================

@app.route("/beheer/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        login_input = (request.form.get("username") or "").strip()
        password    = request.form.get("password") or ""
        authenticated = False
        tenant_id = None
        user_id   = None
        user_email = login_input

        # ── Probeer DB-authenticatie ──────────────────────────
        if _DB:
            try:
                from infrastructure.db.repositories.user_repository import UserRepository
                _user_repo = UserRepository()
                _user = _user_repo.find_by_email(login_input)
                if _user and _user_repo.verify_password(_user, password):
                    authenticated = True
                    tenant_id  = _user.tenant_id
                    user_id    = _user.id
                    user_email = _user.email
            except Exception as _e:
                print(f"[admin_login] DB-auth fout: {_e}")

        # ── Fallback: ENV-var authenticatie ───────────────────
        if not authenticated and login_input == ADMIN_USER and password == ADMIN_PASSWORD:
            authenticated = True
            user_email = ADMIN_USER
            if _DB:
                try:
                    from infrastructure.db.repositories.tenant_repository import TenantRepository
                    from infrastructure.config.bedrijf import BEDRIJFSNAAM, REGIO, CONTACT_EMAIL, CONTACT_TELEFOON
                    tenant_id = TenantRepository().get_or_create_id(
                        slug=TENANT_SLUG,
                        bedrijfsnaam=BEDRIJFSNAAM,
                        regio=REGIO,
                        contact_email=CONTACT_EMAIL,
                        contact_telefoon=CONTACT_TELEFOON,
                    )
                except Exception as _e:
                    print(f"[admin_login] tenant init fout: {_e}")

        if authenticated:
            flask_session["admin_logged_in"] = True
            flask_session["tenant_id"]  = tenant_id
            flask_session["user_id"]    = user_id
            flask_session["user_email"] = user_email
            return redirect(url_for("admin_overzicht"))
        error = "Onjuiste inloggegevens."
    return render_template("admin/login.html", error=error)


@app.route("/beheer/logout")
def admin_logout():
    flask_session.clear()
    return redirect(url_for("admin_login"))


@app.route("/beheer")
@app.route("/beheer/")
@_admin_required
def admin_overzicht():
    if not _DB:
        return "Database niet beschikbaar.", 503
    from infrastructure.db.database import SessionLocal
    from infrastructure.db.db_models import DbSession, DbContactSubmission
    from sqlalchemy import func

    zeven_dagen_terug = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).replace(tzinfo=None) - __import__("datetime").timedelta(days=7)

    with SessionLocal() as db:
        recente_sessies = (
            db.query(DbSession)
            .order_by(DbSession.started_at.desc())
            .limit(50)
            .all()
        )
        stats_7d_sessies  = db.query(func.count(DbSession.id)).filter(
            DbSession.started_at >= zeven_dagen_terug).scalar() or 0
        stats_7d_offertes = db.query(func.count(DbSession.id)).filter(
            DbSession.started_at >= zeven_dagen_terug,
            DbSession.completed == True).scalar() or 0
        stats_7d_contacten = db.query(func.count(DbSession.id)).filter(
            DbSession.started_at >= zeven_dagen_terug,
            DbSession.contact_submitted == True).scalar() or 0

    return render_template(
        "admin/overzicht.html",
        active="overzicht",
        sessies=recente_sessies,
        stats={
            "sessies":   stats_7d_sessies,
            "offertes":  stats_7d_offertes,
            "contacten": stats_7d_contacten,
        },
    )


@app.route("/beheer/sessies/<session_id>")
@_admin_required
def admin_sessie_detail(session_id: str):
    if not _DB:
        return "Database niet beschikbaar.", 503
    from infrastructure.db.database import SessionLocal
    from infrastructure.db.db_models import DbSession, DbMessage, DbFlowEvent, DbPriceCalculation, DbContactSubmission

    with SessionLocal() as db:
        sessie = db.get(DbSession, session_id)
        if not sessie:
            return "Sessie niet gevonden.", 404
        berichten  = db.query(DbMessage).filter_by(session_id=session_id).order_by(DbMessage.timestamp).all()
        events     = db.query(DbFlowEvent).filter_by(session_id=session_id).order_by(DbFlowEvent.timestamp).all()
        berekeningen = db.query(DbPriceCalculation).filter_by(session_id=session_id).order_by(DbPriceCalculation.timestamp).all()
        contact    = db.query(DbContactSubmission).filter_by(session_id=session_id).order_by(DbContactSubmission.timestamp.desc()).first()

    return render_template(
        "admin/sessie_detail.html",
        active="overzicht",
        sessie=sessie,
        berichten=berichten,
        events=events,
        berekeningen=berekeningen,
        contact=contact,
    )


@app.route("/beheer/leads")
@_admin_required
def admin_leads():
    if not _DB:
        return "Database niet beschikbaar.", 503
    from infrastructure.db.database import SessionLocal
    from infrastructure.db.db_models import DbContactSubmission

    with SessionLocal() as db:
        contacten = (
            db.query(DbContactSubmission)
            .order_by(DbContactSubmission.timestamp.desc())
            .limit(100)
            .all()
        )
    return render_template("admin/leads.html", active="leads", contacten=contacten)


_PRIJS_CATEGORIEEN = [
    ("Onderhoud", [
        ("onderhoud_aanleg_uurtarief",              "Uurtarief aanleg/onderhoud",          "€/uur"),
        ("voorjaar_najaarsbeurt",                   "Voorjaars-/najaarsbeurt",             "€ totaal"),
        ("gazon_maaien",                            "Gazon maaien",                        "€/keer"),
        ("haag_snoeien",                            "Haag snoeien",                        "€/keer"),
    ]),
    ("Grondwerk & afvoer", [
        ("grond_afvoer_per_m3",                     "Grond afvoeren",                      "€/m³"),
        ("zand_aanvoer_per_m3",                     "Zand aanvoeren",                      "€/m³"),
        ("puin_aanvoer_per_m3",                     "Puin aanvoeren",                      "€/m³"),
        ("bestrating_verwijderen_per_m3",           "Bestrating verwijderen",              "€/m³"),
        ("bestrating_afvoer_per_m3",                "Bestrating afvoeren",                 "€/m³"),
        ("bouw_sloop_afval_afvoer_per_m3",          "Bouw-/sloopafval afvoeren",           "€/m³"),
    ]),
    ("Bestrating", [
        ("beton_straatwerk_per_m2",                 "Betonstraatstenen",                   "€/m²"),
        ("keramisch_straatwerk_per_m2",             "Keramische tegels",                   "€/m²"),
        ("gebakken_straatwerk_per_m2",              "Gebakken klinkers",                   "€/m²"),
        ("grind_per_m2",                            "Grind",                               "€/m²"),
        ("plaatsen_betonband_per_m1",               "Betonband plaatsen",                  "€/m¹"),
        ("zaagwerk_per_m1",                         "Zaagwerk",                            "€/m¹"),
        ("voegen_straatwerk_per_m2",                "Voegen (onkruidwerend)",              "€/m²"),
    ]),
    ("Vlonders", [
        ("vlonder_zachthout_per_m2",                "Zachthout (grenen/lariks)",           "€/m²"),
        ("vlonder_hardhout_per_m2",                 "Hardhout (bangkirai)",                "€/m²"),
        ("vlonder_composiet_per_m2",                "Composiet",                           "€/m²"),
    ]),
    ("Groen", [
        ("graszoden_per_m2",                        "Graszoden",                           "€/m²"),
        ("beplanting_border_per_m2",                "Beplanting border",                   "€/m²"),
        ("beplanting_haag_voordelig_laag_per_m1",   "Haag voordelig laag (0,5–1m)",        "€/m¹"),
        ("beplanting_haag_voordelig_hoog_per_m1",   "Haag voordelig hoog (1,5–2m)",        "€/m¹"),
        ("beplanting_haag_premium_laag_per_m1",     "Haag premium laag (0,5–1m)",          "€/m¹"),
        ("beplanting_haag_premium_hoog_per_m1",     "Haag premium hoog (1,5–2m)",          "€/m¹"),
        ("beplanting_boom_per_stuk",                "Boom plaatsen",                       "€/stuk"),
    ]),
    ("Beregening", [
        ("beregening_installatie_basis",            "Installatie basis (handmatig)",       "€ vast"),
        ("beregening_installatie_volautomatisch",   "Installatie volautomatisch",          "€ vast"),
        ("beregening_installatie_highend",          "Installatie highend",                 "€ vast"),
        ("beregening_gazon_basis_per_m2",           "Gazon basis",                         "€/m²"),
        ("beregening_gazon_volautomatisch_per_m2",  "Gazon volautomatisch",                "€/m²"),
        ("beregening_gazon_highend_per_m2",         "Gazon highend",                       "€/m²"),
        ("beregening_beplanting_basis_per_m2",      "Beplanting basis",                    "€/m²"),
        ("beregening_beplanting_volautomatisch_per_m2", "Beplanting volautomatisch",       "€/m²"),
        ("beregening_beplanting_highend_per_m2",    "Beplanting highend",                  "€/m²"),
    ]),
    ("Overkapping & verlichting", [
        ("overkapping_per_m2",                      "Overkapping",                         "€/m²"),
        ("verlichting_basis_per_stuk",              "Verlichting (spot/paal)",             "€/stuk"),
    ]),
    ("Erfafscheiding", [
        ("plaatsen_betonschutting_per_m1",          "Betonschutting",                      "€/m¹"),
        ("plaatsen_designschutting_per_m1",         "Designschutting",                     "€/m¹"),
        ("plaatsen_poortdeur_per_st",               "Poort/deur",                          "€/stuk"),
    ]),
    ("3D Tuinontwerp", [
        ("3d_tuinontwerp_<100m2",                   "Tuinontwerp <100m²",                  "€ vast"),
        ("3d_tuinontwerp_100-500m2",                "Tuinontwerp 100–500m²",               "€ vast"),
        ("3d_tuinontwerp_500-1000m2",               "Tuinontwerp 500–1000m²",              "€ vast"),
        ("3d_tuinontwerp_>1000m2",                  "Tuinontwerp >1000m²",                 "€ vast"),
    ]),
]


@app.route("/beheer/tarieven", methods=["GET", "POST"])
@_admin_required
def admin_tarieven():
    import core.pricing.pricing as _p
    tenant_id = flask_session.get("tenant_id") if _DB else None
    repo = None
    if _DB and tenant_id:
        from infrastructure.db.repositories.tenant_repository import TenantRepository
        repo = TenantRepository()

    if request.method == "POST" and repo:
        overrides = {}
        for _, items in _PRIJS_CATEGORIEEN:
            for key, _, _ in items:
                try:
                    mn = int(request.form.get(f"min_{key}", 0))
                    mx = int(request.form.get(f"max_{key}", 0))
                    default = _p.PRIJZEN.get(key, (0, 0))
                    if (mn, mx) != default:
                        overrides[key] = (mn, mx)
                except (ValueError, TypeError):
                    pass
        repo.save_prijzen(tenant_id, overrides)
        _refresh_price_table()
        return redirect(url_for("admin_tarieven", opgeslagen=1))

    overrides = repo.get_prijzen_overrides(tenant_id) if repo else {}
    opgeslagen = request.args.get("opgeslagen") == "1"

    categorieen = []
    for cat_naam, items in _PRIJS_CATEGORIEEN:
        rijen = []
        for key, label, eenheid in items:
            default = _p.PRIJZEN.get(key, (0, 0))
            current = overrides.get(key, default)
            rijen.append({
                "key":     key,
                "label":   label,
                "eenheid": eenheid,
                "min":     current[0],
                "max":     current[1],
                "is_override": key in overrides,
            })
        categorieen.append({"naam": cat_naam, "rijen": rijen})

    return render_template(
        "admin/tarieven.html",
        active="tarieven",
        categorieen=categorieen,
        opgeslagen=opgeslagen,
        db_actief=bool(repo),
    )


@app.route("/mijn-offerte/<token>")
def klantportaal(token: str):
    if not _DB:
        return "Portaal tijdelijk niet beschikbaar.", 503
    from infrastructure.db.database import SessionLocal
    from infrastructure.db.db_models import DbContactSubmission, DbPriceCalculation, DbSession

    with SessionLocal() as db:
        contact = db.query(DbContactSubmission).filter_by(bekijk_token=token).first()
        if not contact:
            return render_template("klantportaal/niet_gevonden.html"), 404

        berekening = None
        if contact.price_calculation_id:
            berekening = db.get(DbPriceCalculation, contact.price_calculation_id)
        if not berekening:
            berekening = (
                db.query(DbPriceCalculation)
                .filter_by(session_id=contact.session_id)
                .order_by(DbPriceCalculation.timestamp.desc())
                .first()
            )

        sessie = db.get(DbSession, contact.session_id)

    return render_template(
        "klantportaal/offerte.html",
        contact=contact,
        berekening=berekening,
        sessie=sessie,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
