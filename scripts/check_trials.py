"""
scripts/check_trials.py — dagelijkse cronjob.

Doet twee dingen:
  1. Stuurt een herinnering (klant + superadmin) als een trial binnen
     TRIAL_REMINDER_DAGEN_VOOR dagen afloopt en dat nog niet is gemeld.
  2. Deactiveert tenants waarvan de trial al verlopen is (en niet betalend zijn),
     en stuurt daarover een melding naar klant + superadmin.

Los draaien (vanaf de projectroot, met venv actief):
  python scripts/check_trials.py

Cron (voorbeeldregel, paden aanpassen naar de eigen serverinrichting):
  0 7 * * * cd /pad/naar/chatbot-hovenier && venv/bin/python scripts/check_trials.py >> /var/log/indiqa-check-trials.log 2>&1
"""
from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from infrastructure.db.repositories.tenant_repository import TenantRepository
from infrastructure.services.mailer import (
    send_trial_herinnering_email, send_trial_herinnering_admin_email,
    send_trial_verlopen_email, send_trial_verlopen_admin_email,
)

TRIAL_REMINDER_DAGEN_VOOR = 5  # aantal dagen vóór trial_eindigt_op dat de herinnering verstuurd wordt


def _try(beschrijving: str, fn, *args) -> bool:
    """Voert fn(*args) uit; logt en geeft False bij een fout i.p.v. de hele run te onderbreken."""
    try:
        fn(*args)
        return True
    except Exception as e:
        print(f"Fout bij {beschrijving}: {e}")
        return False


def run() -> None:
    repo = TenantRepository()
    nu = datetime.now(timezone.utc).replace(tzinfo=None)

    # ── 1) Herinneringen ───────────────────────────────────────
    # Klant- en adminmail apart proberen: als de ene faalt (bv. ongeldig
    # klant-e-mailadres) moet de andere (met name de admin-melding) alsnog verstuurd worden.
    for t in repo.list_trials_binnenkort_verlopen(dagen=TRIAL_REMINDER_DAGEN_VOOR):
        dagen_resterend = max((t["trial_eindigt_op"] - nu).days, 0)
        ok_klant = _try(f"herinnering (klant) {t['slug']}", send_trial_herinnering_email,
                         t["naam"], t["email"], t["slug"], t["trial_eindigt_op"], dagen_resterend)
        ok_admin = _try(f"herinnering (admin) {t['slug']}", send_trial_herinnering_admin_email,
                         t["naam"], t["email"], t["slug"], t["trial_eindigt_op"])
        repo.mark_herinnering_verzonden(t["id"])
        if ok_klant and ok_admin:
            print(f"Herinnering verstuurd: {t['naam']} ({t['slug']}), nog {dagen_resterend} dagen")

    # ── 2) Verlopen trials deactiveren ─────────────────────────
    # Deactiveren gebeurt altijd, ongeacht of de mails lukken.
    for t in repo.list_trials_verlopen():
        repo.set_actief(t["id"], False)
        ok_klant = _try(f"verval-melding (klant) {t['slug']}", send_trial_verlopen_email,
                         t["naam"], t["email"], t["slug"])
        ok_admin = _try(f"verval-melding (admin) {t['slug']}", send_trial_verlopen_admin_email,
                         t["naam"], t["email"], t["slug"])
        print(f"Trial verlopen, gedeactiveerd: {t['naam']} ({t['slug']})"
              + ("" if (ok_klant and ok_admin) else " (let op: niet alle mails zijn gelukt, zie foutregels hierboven)"))


if __name__ == "__main__":
    run()
