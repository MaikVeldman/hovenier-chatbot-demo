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

def _migrate_db() -> None:
    """Voeg ontbrekende kolommen toe aan bestaande tabellen."""
    if not _DB:
        return
    try:
        from sqlalchemy import text
        from infrastructure.db.database import engine
        with engine.connect() as conn:
            for sql in [
                "ALTER TABLE tenant_configs ADD COLUMN volume_kortingen JSON",
                "ALTER TABLE tenant_configs ADD COLUMN instellingen JSON",
            ]:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception:
                    pass  # kolom bestaat al
    except Exception as e:
        print(f"[server] DB migratie mislukt: {e}")


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

_origins = [
    "https://veldmanhoveniers.nl", "https://www.veldmanhoveniers.nl",
    "https://indiqa.nl", "https://www.indiqa.nl",
]
if DEMO_MODE:
    _origins += ["https://demo.indiqa.nl"]
CORS(app, origins=_origins)

# DB migraties + laad tenant-prijzen bij opstart
_migrate_db()
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


def _darken_hex(hex_color: str, factor: float = 0.72) -> str:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#{:02x}{:02x}{:02x}".format(int(r * factor), int(g * factor), int(b * factor))


@app.route("/<slug>")
def chatbot_tenant(slug: str):
    import os as _os
    # <slug> shadows Flask's static file handler for single-segment paths; fall back transparently
    static_file = _os.path.join(app.static_folder or "static", slug)
    if _os.path.isfile(static_file):
        return send_from_directory(app.static_folder or "static", slug)

    if not _DB:
        return "Database niet beschikbaar.", 503

    tenant_cfg = TenantRepository().get(slug)
    if not tenant_cfg:
        # Bestaat de slug maar is het account nog niet geactiveerd?
        from infrastructure.db.database import SessionLocal as _SL
        from infrastructure.db.db_models import DbTenant as _DbT
        with _SL() as _db:
            _t = _db.query(_DbT).filter_by(slug=slug).first()
            if _t and not _t.actief:
                return render_template("chatbot/wacht_activatie.html", bedrijfsnaam=_t.naam), 202
        return "Onbekende URL.", 404

    primaire_kleur = tenant_cfg.primaire_kleur or "#5c6b1e"
    return render_template(
        "chatbot/index.html",
        tenant_slug=slug,
        bedrijfsnaam=tenant_cfg.bedrijfsnaam,
        regio=tenant_cfg.regio or "",
        primaire_kleur=primaire_kleur,
        primaire_kleur_dark=_darken_hex(primaire_kleur),
    )


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
        slug = request.headers.get("X-Tenant-Slug", "")
        tenant_id = None
        if slug:
            try:
                from infrastructure.db.database import SessionLocal
                from infrastructure.db.db_models import DbTenant
                with SessionLocal() as db:
                    t = db.query(DbTenant).filter_by(slug=slug, actief=True).first()
                    if t:
                        tenant_id = t.id
            except Exception:
                pass
        log_session_created(sid, user_agent=ua, tenant_id=tenant_id)
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
            flask_session.clear()
            flask_session["admin_logged_in"] = True
            flask_session["tenant_id"]  = tenant_id
            flask_session["user_id"]    = user_id
            flask_session["user_email"] = user_email
            flask_session["is_superadmin"] = (user_id is None)  # ENV-var login = superadmin
            return redirect(url_for("admin_overzicht"))
        error = "Onjuiste inloggegevens."
    return render_template("admin/login.html", error=error)


@app.route("/beheer/logout")
def admin_logout():
    flask_session.clear()
    return redirect(url_for("admin_login"))


# ============================================================
# Registratie nieuwe Indiqa klant
# ============================================================

import re as _re

def _make_slug(name: str) -> str:
    return _re.sub(r'[^a-z0-9]', '', name.lower())[:40] or "bedrijf"

def _unique_slug(base: str) -> str:
    from infrastructure.db.database import SessionLocal
    from infrastructure.db.db_models import DbTenant
    slug, n = base, 2
    with SessionLocal() as db:
        while db.query(DbTenant).filter_by(slug=slug).first():
            slug = f"{base}{n}"
            n += 1
    return slug

@app.route("/wachtwoord-vergeten", methods=["GET", "POST"])
def wachtwoord_vergeten():
    verzonden = False
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if email and "@" in email and _DB:
            try:
                from infrastructure.db.repositories.user_repository import UserRepository
                from infrastructure.services.mailer import send_wachtwoord_reset_email
                token = UserRepository().create_reset_token(email)
                if token:
                    reset_url = f"{BASE_URL}/wachtwoord-reset/{token}"
                    send_wachtwoord_reset_email(email, reset_url)
            except Exception as e:
                print(f"[wachtwoord_vergeten] {e}")
        verzonden = True  # altijd tonen (voorkomt e-mail enumeration)
    return render_template("account/wachtwoord_vergeten.html", verzonden=verzonden)


@app.route("/wachtwoord-reset/<token>", methods=["GET", "POST"])
def wachtwoord_reset(token: str):
    error = None
    success = False
    if request.method == "POST":
        nieuw  = request.form.get("wachtwoord") or ""
        nieuw2 = request.form.get("wachtwoord2") or ""
        if len(nieuw) < 8:
            error = "Wachtwoord moet minimaal 8 tekens bevatten."
        elif nieuw != nieuw2:
            error = "Wachtwoorden komen niet overeen."
        else:
            from infrastructure.db.repositories.user_repository import UserRepository
            ok = UserRepository().use_reset_token(token, nieuw)
            if ok:
                success = True
            else:
                error = "Deze link is verlopen of al gebruikt. Vraag een nieuwe aan."
    return render_template("account/wachtwoord_reset.html", token=token, error=error, success=success)


@app.route("/aanmelden", methods=["GET", "POST"])
def aanmelden():
    if not _DB:
        return "Registratie tijdelijk niet beschikbaar.", 503

    form = {}
    error = None

    if request.method == "POST":
        bedrijfsnaam        = (request.form.get("bedrijfsnaam") or "").strip()
        regio               = (request.form.get("regio") or "").strip()
        email               = (request.form.get("email") or "").strip().lower()
        wachtwoord          = request.form.get("wachtwoord") or ""
        wachtwoord2         = request.form.get("wachtwoord2") or ""
        website_impl        = bool(request.form.get("website_implementatie"))

        form = dict(bedrijfsnaam=bedrijfsnaam, regio=regio, email=email,
                    website_implementatie=website_impl)

        # Validatie
        if not bedrijfsnaam:
            error = "Vul een bedrijfsnaam in."
        elif not email or "@" not in email:
            error = "Vul een geldig e-mailadres in."
        elif len(wachtwoord) < 8:
            error = "Wachtwoord moet minimaal 8 tekens bevatten."
        elif wachtwoord != wachtwoord2:
            error = "Wachtwoorden komen niet overeen."
        else:
            from infrastructure.db.repositories.user_repository import UserRepository
            from infrastructure.db.repositories.tenant_repository import TenantRepository

            # E-mail al in gebruik?
            if UserRepository().find_by_email(email):
                error = "Dit e-mailadres is al geregistreerd."
            else:
                # Tenant + user aanmaken (inactief tot superadmin activeert)
                slug = _unique_slug(_make_slug(bedrijfsnaam))
                tenant_id = TenantRepository().get_or_create_id(
                    slug=slug,
                    bedrijfsnaam=bedrijfsnaam,
                    regio=regio,
                    contact_email=email,
                    actief=False,
                )
                user_id = UserRepository().create(
                    tenant_id=tenant_id,
                    email=email,
                    plain_password=wachtwoord,
                )

                if not user_id:
                    error = "Er ging iets mis bij het aanmaken van je account. Probeer het opnieuw."
                else:
                    # Notificatie aan superadmin + welkomstmail bij activatie
                    try:
                        from infrastructure.services.mailer import send_nieuwe_aanmelding_email
                        send_nieuwe_aanmelding_email(
                            bedrijfsnaam=bedrijfsnaam,
                            email=email,
                            regio=regio,
                            slug=slug,
                            website_implementatie=website_impl,
                        )
                    except Exception as e:
                        print(f"[aanmelden] Notificatiemail mislukt: {e}")

                    # Direct inloggen
                    flask_session.clear()
                    flask_session["admin_logged_in"] = True
                    flask_session["tenant_id"]       = tenant_id
                    flask_session["user_id"]         = user_id
                    flask_session["user_email"]      = email
                    flask_session["is_superadmin"]   = False
                    return redirect(url_for("admin_overzicht"))

    return render_template("account/registreer.html", error=error, form=form)


@app.route("/beheer")
@app.route("/beheer/")
@_admin_required
def admin_overzicht():
    if not _DB:
        return "Database niet beschikbaar.", 503
    from infrastructure.db.database import SessionLocal
    from infrastructure.db.db_models import DbSession, DbContactSubmission
    from sqlalchemy import func, or_

    tenant_id = flask_session.get("tenant_id")
    zeven_dagen_terug = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).replace(tzinfo=None) - __import__("datetime").timedelta(days=7)

    def _tenant_filter(q):
        if tenant_id:
            return q.filter(DbSession.tenant_id == tenant_id)
        return q

    with SessionLocal() as db:
        recente_sessies = (
            _tenant_filter(db.query(DbSession))
            .order_by(DbSession.started_at.desc())
            .limit(50)
            .all()
        )
        stats_7d_sessies  = _tenant_filter(db.query(func.count(DbSession.id))).filter(
            DbSession.started_at >= zeven_dagen_terug).scalar() or 0
        stats_7d_offertes = _tenant_filter(db.query(func.count(DbSession.id))).filter(
            DbSession.started_at >= zeven_dagen_terug,
            DbSession.completed == True).scalar() or 0
        stats_7d_contacten = _tenant_filter(db.query(func.count(DbSession.id))).filter(
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

    tenant_id = flask_session.get("tenant_id")
    with SessionLocal() as db:
        sessie = db.get(DbSession, session_id)
        if not sessie:
            return "Sessie niet gevonden.", 404
        if tenant_id and sessie.tenant_id and sessie.tenant_id != tenant_id:
            return "Geen toegang.", 403
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
    from infrastructure.db.db_models import DbContactSubmission, DbSession
    from sqlalchemy import or_

    tenant_id = flask_session.get("tenant_id")

    with SessionLocal() as db:
        q = db.query(DbContactSubmission).join(DbSession, DbContactSubmission.session_id == DbSession.id)
        if tenant_id:
            q = q.filter(DbSession.tenant_id == tenant_id)
        contacten = q.order_by(DbContactSubmission.timestamp.desc()).limit(100).all()
    return render_template("admin/leads.html", active="leads", contacten=contacten)


_PRIJS_CATEGORIEEN = [
    ("Grondwerk & afvoer", [
        ("grond_afvoer_per_m3",                     "Grond afvoeren",                      "€/m³"),
        ("zand_aanvoer_per_m3",                     "Zand aanvoeren",                      "€/m³"),
        ("puin_aanvoer_per_m3",                     "Puin aanvoeren",                      "€/m³"),
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

# (cat_key, label, eenheid, n_rows, drempel_stap)
_VK_CATEGORIEEN = [
    ("groen",      "Groen",      "m²", 3, 25),
    ("bestrating", "Bestrating", "m²", 3, 25),
    ("grondwerk",  "Grondwerk",  "m³", 3,  5),
    ("vlonder",    "Vlonder",    "m²", 2, 10),
]


@app.route("/beheer/tarieven", methods=["GET", "POST"])
@_admin_required
def admin_tarieven():
    import core.pricing.pricing as _p
    from core.pricing.constants import PRIJZEN as _BASE_PRIJZEN, VOLUME_KORTINGEN as _BASE_VK
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
                    default = _BASE_PRIJZEN.get(key, (0, 0))
                    if (mn, mx) != default:
                        overrides[key] = (mn, mx)
                except (ValueError, TypeError):
                    pass
        repo.save_prijzen(tenant_id, overrides)

        vk_new = {}
        for cat, _, _, n_rows, _ in _VK_CATEGORIEEN:
            rows = []
            for i in range(n_rows):
                try:
                    d = float(request.form.get(f"vk_{cat}_{i}_drempel", 0))
                    f = float(request.form.get(f"vk_{cat}_{i}_factor", 1.0))
                    f = max(0.01, min(1.0, round(f, 2)))
                    rows.append((d, f))
                except (ValueError, TypeError):
                    pass
            if rows:
                vk_new[cat] = sorted(rows, key=lambda x: -x[0])
        repo.save_volume_kortingen(tenant_id, vk_new)

        try:
            zaag_pct = int(request.form.get("zaagwerk_pct", 35))
            zaag_pct = max(1, min(100, zaag_pct))
        except (ValueError, TypeError):
            zaag_pct = 35
        repo.save_instellingen(tenant_id, {"zaagwerk_pct": zaag_pct})

        _refresh_price_table()
        return redirect(url_for("admin_tarieven", opgeslagen=1))

    overrides = repo.get_prijzen_overrides(tenant_id) if repo else {}
    vk_overrides   = repo.get_volume_kortingen(tenant_id) if repo else {}
    instellingen   = repo.get_instellingen(tenant_id) if repo else {}
    zaagwerk_pct   = int(instellingen.get("zaagwerk_pct", 35))
    opgeslagen     = request.args.get("opgeslagen") == "1"

    categorieen = []
    for cat_naam, items in _PRIJS_CATEGORIEEN:
        rijen = []
        for key, label, eenheid in items:
            default = _BASE_PRIJZEN.get(key, (0, 0))
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

    vk_categorieen = []
    for cat, label, eenheid, n_rows, stap in _VK_CATEGORIEEN:
        base_rows  = _BASE_VK.get(cat, [])
        cur_rows   = vk_overrides.get(cat) if cat in vk_overrides else base_rows
        rijen = []
        for i in range(n_rows):
            if i < len(cur_rows):
                d, f = cur_rows[i]
            elif i < len(base_rows):
                d, f = base_rows[i]
            else:
                d, f = 0, 1.0
            rijen.append({"drempel": d, "factor": round(f, 2)})
        vk_categorieen.append({
            "cat": cat, "label": label, "eenheid": eenheid,
            "rijen": rijen, "stap": stap,
            "is_override": cat in vk_overrides,
        })

    return render_template(
        "admin/tarieven.html",
        active="tarieven",
        categorieen=categorieen,
        vk_categorieen=vk_categorieen,
        zaagwerk_pct=zaagwerk_pct,
        opgeslagen=opgeslagen,
        db_actief=bool(repo),
    )


@app.route("/beheer/tarieven/reset", methods=["POST"])
@_admin_required
def admin_tarieven_reset():
    tenant_id = flask_session.get("tenant_id") if _DB else None
    if _DB and tenant_id:
        from infrastructure.db.repositories.tenant_repository import TenantRepository
        repo = TenantRepository()
        repo.save_prijzen(tenant_id, {})
        repo.save_volume_kortingen(tenant_id, {})
        repo.save_instellingen(tenant_id, {})
        _refresh_price_table()
    return redirect(url_for("admin_tarieven", opgeslagen=1))


@app.route("/beheer/klanten")
@_admin_required
def admin_klanten():
    if not flask_session.get("is_superadmin"):
        return redirect(url_for("admin_overzicht"))
    tenants = TenantRepository().list_all()
    return render_template("admin/klanten.html", active="klanten", tenants=tenants)


@app.route("/beheer/klanten/<int:tenant_id>/activeer", methods=["POST"])
@_admin_required
def admin_tenant_activeer(tenant_id: int):
    if not flask_session.get("is_superadmin"):
        return redirect(url_for("admin_overzicht"))
    actief = request.form.get("actief") == "1"
    TenantRepository().set_actief(tenant_id, actief)
    return redirect(url_for("admin_klanten"))


@app.route("/beheer/klanten/<int:tenant_id>/verwijder", methods=["POST"])
@_admin_required
def admin_tenant_verwijder(tenant_id: int):
    if not flask_session.get("is_superadmin"):
        return redirect(url_for("admin_overzicht"))
    if tenant_id == flask_session.get("tenant_id"):
        return redirect(url_for("admin_klanten"))  # eigen account niet verwijderen
    TenantRepository().delete(tenant_id)
    return redirect(url_for("admin_klanten"))


@app.route("/beheer/instellingen", methods=["GET", "POST"])
@_admin_required
def admin_instellingen():
    if not _DB:
        return "Database niet beschikbaar.", 503

    from infrastructure.db.database import SessionLocal
    from infrastructure.db.db_models import DbTenantConfig, DbUser

    tenant_id = flask_session.get("tenant_id")
    user_id   = flask_session.get("user_id")

    success_huisstijl = False
    error_huisstijl   = None
    success_wachtwoord = False
    error_wachtwoord   = None

    if request.method == "POST":
        actie = request.form.get("actie")

        if actie == "huisstijl" and tenant_id:
            bedrijfsnaam  = (request.form.get("bedrijfsnaam") or "").strip()
            regio         = (request.form.get("regio") or "").strip()
            primaire_kleur = (request.form.get("primaire_kleur") or "").strip()

            import re as _re2
            if not bedrijfsnaam:
                error_huisstijl = "Bedrijfsnaam mag niet leeg zijn."
            elif primaire_kleur and not _re2.match(r'^#[0-9a-fA-F]{6}$', primaire_kleur):
                error_huisstijl = "Ongeldige kleurcode. Gebruik formaat #rrggbb."
            else:
                with SessionLocal() as db:
                    cfg = db.query(DbTenantConfig).filter_by(tenant_id=tenant_id).first()
                    if cfg:
                        cfg.bedrijfsnaam  = bedrijfsnaam
                        cfg.regio         = regio
                        if primaire_kleur:
                            cfg.primaire_kleur = primaire_kleur
                        db.commit()
                success_huisstijl = True

        elif actie == "wachtwoord" and user_id:
            oud       = request.form.get("oud_wachtwoord") or ""
            nieuw     = request.form.get("nieuw_wachtwoord") or ""
            nieuw2    = request.form.get("nieuw_wachtwoord2") or ""

            from infrastructure.db.repositories.user_repository import UserRepository
            repo = UserRepository()
            user = repo.find_by_id(user_id) if hasattr(repo, "find_by_id") else None

            if not user:
                error_wachtwoord = "Gebruiker niet gevonden."
            elif not repo.verify_password(user, oud):
                error_wachtwoord = "Huidig wachtwoord is onjuist."
            elif len(nieuw) < 8:
                error_wachtwoord = "Nieuw wachtwoord moet minimaal 8 tekens bevatten."
            elif nieuw != nieuw2:
                error_wachtwoord = "Wachtwoorden komen niet overeen."
            else:
                repo.update_password(user_id, nieuw)
                success_wachtwoord = True

    # Laad huidige config voor formulier
    cfg_obj = None
    if tenant_id:
        with SessionLocal() as db:
            cfg_obj = db.query(DbTenantConfig).filter_by(tenant_id=tenant_id).first()
            if cfg_obj:
                from dataclasses import dataclass
                @dataclass
                class _Cfg:
                    bedrijfsnaam: str
                    regio: str
                    primaire_kleur: str
                cfg_obj = _Cfg(
                    bedrijfsnaam=cfg_obj.bedrijfsnaam or "",
                    regio=cfg_obj.regio or "",
                    primaire_kleur=cfg_obj.primaire_kleur or "#5c6b1e",
                )

    return render_template(
        "admin/instellingen.html",
        active="instellingen",
        cfg=cfg_obj,
        success_huisstijl=success_huisstijl,
        error_huisstijl=error_huisstijl,
        success_wachtwoord=success_wachtwoord,
        error_wachtwoord=error_wachtwoord,
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
