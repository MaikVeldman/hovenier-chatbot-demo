from __future__ import annotations

import re
from typing import List, Tuple

from core.models.chat_state import ChatState

try:
    from db_logger import (
        log_event,
        log_contact_submission,
        update_session_ended,
        save_leadscore,
    )
    from mailer import send_contact_email
    from leadscore import bereken_leadscore
    _DB = True
except Exception:
    _DB = False

_NAAM_INVALID = frozenset({"nee", "n", "geen", "x", "?", "-", "nvt", "n.v.t.", "onbekend", "anoniem"})
_NAAM_LETTER_RE = re.compile(r"[a-zA-ZÀ-ÖØ-öø-ÿ]")


class ContactController:
    def __init__(self, state: ChatState):
        self.state = state

    @staticmethod
    def _is_terug(t: str) -> bool:
        return t.strip().lower() in {"terug", "back"}

    def _bereken_en_sla_leadscore(
        self,
        sessie_volledig: bool,
        offerte_aangevraagd: bool,
        drop_off: bool = False,
    ) -> tuple:
        if not (_DB and self.state.session_id):
            return 0, "", {}
        try:
            from models import DbSession
            from database import SessionLocal
            with SessionLocal() as db:
                sess = db.get(DbSession, self.state.session_id)
                terug_acties = (sess.terug_acties or 0) if sess else 0
        except Exception:
            terug_acties = 0

        score, label, breakdown = bereken_leadscore(
            answers=self.state.last_answers,
            costs=self.state.last_costs,
            sessie_volledig=sessie_volledig,
            offerte_aangevraagd=offerte_aangevraagd,
            terug_acties=terug_acties,
            prijs_gezien_en_doorgegaan=self.state.prijs_gezien_en_doorgegaan,
            herberekend=self.state.heeft_herberekend,
            drop_off=drop_off,
        )
        save_leadscore(self.state.session_id, score, label, breakdown)
        return score, label, breakdown

    def _submit(self) -> None:
        score, label, breakdown = self._bereken_en_sla_leadscore(
            sessie_volledig=True, offerte_aangevraagd=True
        )

        email_sent_at = None
        if _DB:
            try:
                send_contact_email(
                    naam=self.state.contact_naam or "",
                    telefoon=self.state.contact_telefoon or "",
                    email=self.state.contact_email or "",
                    adres=self.state.contact_adres or "",
                    woonplaats=self.state.contact_woonplaats or "",
                    opmerking=self.state.contact_opmerking,
                    costs=self.state.last_costs,
                    flow_type=self.state.flow_type,
                    leadscore=score,
                    lead_label=label,
                    score_breakdown=breakdown,
                )
                from datetime import datetime as _dt, timezone as _tz
                email_sent_at = _dt.now(_tz.utc)
            except Exception as exc:
                print(f"[mailer] Kon e-mail niet versturen: {exc}")

            log_contact_submission(
                session_id=self.state.session_id or "",
                naam=self.state.contact_naam or "",
                telefoon=self.state.contact_telefoon or "",
                email=self.state.contact_email or "",
                adres=self.state.contact_adres or "",
                woonplaats=self.state.contact_woonplaats or "",
                notitie=self.state.contact_opmerking,
                price_calculation_id=self.state.last_calc_id,
                email_sent_at=email_sent_at,
            )
            log_event(self.state.session_id or "", "contact_submitted", {
                "naam": self.state.contact_naam,
                "email": self.state.contact_email,
                "email_sent": email_sent_at is not None,
            })
            update_session_ended(self.state.session_id or "")

    def handle_naam(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        from savings import post_offer_choices_text, post_offer_choices_losse_text, post_offer_choices_tuinontwerp_text
        if self._is_terug(t_raw):
            self.state.post_offer_stage = "menu"
            ft = (self.state.last_answers or {}).get("_flow_type")
            if ft == "tuinontwerp":
                menu = post_offer_choices_tuinontwerp_text()
            elif ft == "losse_onderdelen":
                menu = post_offer_choices_losse_text()
            else:
                menu = post_offer_choices_text()
            return self.state, [menu]
        naam = t_raw.strip()
        if len(naam) < 2 or naam.lower() in _NAAM_INVALID or not _NAAM_LETTER_RE.search(naam):
            return self.state, ["Vul alstublieft uw naam in (bijv. Jan de Vries)."]
        self.state.contact_naam = naam
        self.state.post_offer_stage = "contact_telefoon"
        return self.state, [
            f"Bedankt, {self.state.contact_naam}! Wat is uw telefoonnummer?\n"
            "_(typ 'nee' als u dit liever niet deelt)_"
        ]

    def handle_telefoon(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        if self._is_terug(t_raw):
            self.state.post_offer_stage = "contact_naam"
            return self.state, ["Wat is uw naam?"]
        tel = t_raw.strip()
        if tel.lower() in ("overslaan", "skip", "-", "nvt", "n.v.t.", "nee"):
            self.state.contact_telefoon = None
        else:
            digits = re.sub(r"[\s\-\+\(\).]", "", tel)
            if len(digits) < 9 or not digits.lstrip("+").isdigit():
                return self.state, [
                    "Vul alstublieft een geldig telefoonnummer in (bijv. 06-12345678), of typ 'nee'."
                ]
            self.state.contact_telefoon = tel
        self.state.post_offer_stage = "contact_email"
        return self.state, ["En wat is uw e-mailadres?"]

    def handle_email(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        if self._is_terug(t_raw):
            self.state.post_offer_stage = "contact_telefoon"
            return self.state, ["Wat is uw telefoonnummer?\n_(typ 'nee' als u dit liever niet deelt)_"]
        email = t_raw.strip()
        if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]{2,}$", email):
            return self.state, [
                "Dat lijkt geen geldig e-mailadres. Kunt u een geldig adres invoeren? (bijv. naam@voorbeeld.nl)"
            ]
        self.state.contact_email = email
        self.state.post_offer_stage = "contact_adres"
        return self.state, [
            "Wat is het adres van de tuin (straat + huisnummer)?\n_(typ 'nee' als u dit liever niet deelt)_"
        ]

    def handle_adres(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        if self._is_terug(t_raw):
            self.state.post_offer_stage = "contact_email"
            return self.state, ["En wat is uw e-mailadres?"]
        val = t_raw.strip()
        if val.lower() in ("overslaan", "skip", "-", "nvt", "n.v.t.", "nee"):
            self.state.contact_adres = None
        elif len(val) < 3:
            return self.state, [
                "Vul alstublieft een adres in (bijv. Dorpsstraat 12), of typ 'nee'."
            ]
        else:
            self.state.contact_adres = val
        self.state.post_offer_stage = "contact_woonplaats"
        return self.state, ["In welke woonplaats woont u?"]

    def handle_woonplaats(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        if self._is_terug(t_raw):
            self.state.post_offer_stage = "contact_adres"
            return self.state, [
                "Wat is het adres van de tuin (straat + huisnummer)?\n_(typ 'nee' als u dit liever niet deelt)_"
            ]
        woonplaats = t_raw.strip()
        if len(woonplaats) < 2:
            return self.state, ["Vul alstublieft uw woonplaats in (bijv. Balkbrug)."]
        self.state.contact_woonplaats = woonplaats
        self.state.post_offer_stage = "contact_opmerking"
        return self.state, ["Heeft u nog opmerkingen of wensen? (optioneel, typ 'nee' om over te slaan)"]

    def handle_opmerking(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        if self._is_terug(t_raw):
            self.state.post_offer_stage = "contact_woonplaats"
            return self.state, ["In welke woonplaats woont u?"]
        val = t_raw.strip()
        self.state.contact_opmerking = None if val.lower() == "nee" else val
        self._submit()
        self.state.post_offer_mode = False
        self.state.post_offer_stage = "end"
        self.state.ended = True
        self.state.end_reason = "contact_submitted"
        return self.state, [
            "✅ Aanvraag ontvangen! We nemen zo snel mogelijk contact met u op.\n\n"
            "Bedankt voor uw interesse in Veldman Hoveniers!"
        ]
