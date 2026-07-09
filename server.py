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

ADMIN_USER     = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")
SECRET_KEY     = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

app = Flask(__name__, static_folder="static", static_url_path="", template_folder="templates")
app.secret_key = SECRET_KEY

_origins = ["https://veldmanhoveniers.nl", "https://www.veldmanhoveniers.nl"]
if DEMO_MODE:
    _origins += ["https://indiqa.nl", "https://www.indiqa.nl", "https://demo.indiqa.nl"]
CORS(app, origins=_origins)

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
        if (request.form.get("username") == ADMIN_USER
                and request.form.get("password") == ADMIN_PASSWORD):
            flask_session["admin_logged_in"] = True
            return redirect(url_for("admin_overzicht"))
        error = "Onjuiste gebruikersnaam of wachtwoord."
    return render_template("admin/login.html", error=error)


@app.route("/beheer/logout")
def admin_logout():
    flask_session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/beheer")
@app.route("/beheer/")
@_admin_required
def admin_overzicht():
    if not _DB:
        return "Database niet beschikbaar.", 503
    from database import SessionLocal
    from models import DbSession, DbContactSubmission
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
    from database import SessionLocal
    from models import DbSession, DbMessage, DbFlowEvent, DbPriceCalculation, DbContactSubmission

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
        sessie=sessie,
        berichten=berichten,
        events=events,
        berekeningen=berekeningen,
        contact=contact,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
