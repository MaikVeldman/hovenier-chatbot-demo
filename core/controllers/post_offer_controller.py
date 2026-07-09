from __future__ import annotations

import re
from typing import List, Tuple

from core.models.chat_state import ChatState

try:
    from db_logger import (
        log_event,
        log_price_calculation,
        update_session_ended,
        save_leadscore,
        log_drop_off,
        log_offerte_aangevraagd,
    )
    from leadscore import bereken_leadscore
    _DB = True
except Exception:
    _DB = False

from pricing import (
    estimate_tuinaanleg_costs,
    estimate_losse_onderdelen_costs,
    estimate_tuinontwerp_costs,
    format_costs_as_chat_html,
    format_tuinontwerp_costs_as_chat_html,
)
from savings import (
    post_offer_choices_text,
    post_offer_choices_losse_text,
    post_offer_choices_tuinontwerp_text,
    lower_costs_menu_text,
    lower_costs_menu_losse_text,
    more_green_choice_text,
    extras_select_menu_text,
    material_part_menu_text,
    material_choice_menu_text_cheaper,
    vlonder_choice_menu_text,
    overkapping_choice_menu_text,
    voegen_choice_menu_text,
    verlichting_choice_menu_text,
    erf_remove_select_menu_text,
    erf_item_select_menu_text,
    erf_haag_menu_text,
    erf_schutting_menu_text,
    apply_erf_item_haag_change,
    apply_erf_item_schutting_change,
    losse_component_remove_menu_text,
    apply_set_ratio,
    apply_ratio_proportional,
    apply_remove_selected_extras,
    apply_material_change,
    apply_vlonder_change,
    apply_overkapping_change,
    apply_voegen_change,
    apply_verlichting_change,
    apply_beregening_remove,
    apply_erf_changes,
    apply_remove_losse_component,
    apply_remove_losse_item,
    beregening_systeem_choice_text,
    apply_beregening_systeem_change,
    parse_multi_digits,
    parse_single_digit,
    parse_material_parts,
    is_cancel,
)

_EXIT_MSG = (
    "Helemaal goed. Fijn dat u even heeft gekeken. 👋\n\n"
    "Heeft u later nog vragen of wilt u alsnog een offerte? U kunt altijd een nieuwe berekening starten "
    "of ons direct bereiken via [veldmanhoveniers.nl](https://www.veldmanhoveniers.nl)."
)


class PostOfferController:
    def __init__(self, state: ChatState):
        self.state = state

    # ----------------------------------------------------------
    # Shared helpers
    # ----------------------------------------------------------

    def _is_losse(self) -> bool:
        return (self.state.last_answers or {}).get("_flow_type") == "losse_onderdelen"

    def _is_tuinontwerp(self) -> bool:
        return (self.state.last_answers or {}).get("_flow_type") == "tuinontwerp"

    def _main_menu_text(self) -> str:
        if self._is_tuinontwerp():
            return post_offer_choices_tuinontwerp_text()
        return post_offer_choices_losse_text() if self._is_losse() else post_offer_choices_text()

    def _estimate_costs(self, answers: dict) -> dict:
        ft = (answers or {}).get("_flow_type")
        if ft == "losse_onderdelen":
            return estimate_losse_onderdelen_costs(answers)
        if ft == "tuinontwerp":
            return estimate_tuinontwerp_costs(answers)
        return estimate_tuinaanleg_costs(answers)

    def _format_costs(self, answers: dict, costs: dict) -> str:
        ft = (answers or {}).get("_flow_type")
        if ft == "tuinontwerp":
            return format_tuinontwerp_costs_as_chat_html(costs)
        flow_type = "losse_onderdelen" if ft == "losse_onderdelen" else "gehele_tuin"
        return format_costs_as_chat_html(costs, flow_type)

    def _lower_costs_menu(self) -> str:
        if self._is_losse():
            text, _ = lower_costs_menu_losse_text(self.state.last_answers)
            return text
        text, _ = lower_costs_menu_text(self.state.last_answers, self.state.last_costs)
        return text

    @staticmethod
    def _ensure_prefix(explanation: str) -> str:
        t = (explanation or "").strip()
        if not t:
            return "✅ Doorgevoerde kostenbesparing."
        low = t.lower()
        if "doorgevoerde kostenbesparing" in low:
            return t
        if low.startswith("ik heb aangepast:"):
            rest = t.split(":", 1)[1].strip() if ":" in t else t
            return f"✅ Doorgevoerde kostenbesparing: {rest}"
        if low.startswith("ik heb de ") or low.startswith("ik heb het "):
            return f"✅ Doorgevoerde kostenbesparing: {t[0].lower() + t[1:]}" if len(t) > 1 else "✅ Doorgevoerde kostenbesparing."
        return f"✅ Doorgevoerde kostenbesparing: {t}"

    @staticmethod
    def _eur(v) -> str:
        return f"€{int(v):,}".replace(",", ".")

    def _recalc_messages(self, before_costs: dict, after_costs: dict, explanation: str) -> List[str]:
        old_tr = before_costs.get("total_range_eur") or (0, 0)
        new_tr = after_costs.get("total_range_eur") or (0, 0)
        return [
            self._ensure_prefix(explanation),
            f"Oude indicatie: {self._eur(old_tr[0])} – {self._eur(old_tr[1])}",
            f"Nieuwe indicatie: {self._eur(new_tr[0])} – {self._eur(new_tr[1])}",
            self._format_costs(self.state.last_answers, after_costs),
        ]

    def _bereken_en_sla_leadscore(
        self,
        sessie_volledig: bool,
        offerte_aangevraagd: bool,
        drop_off: bool = False,
    ) -> tuple:
        if not (_DB and self.state.session_id):
            return 0, "", {}
        try:
            from infrastructure.db.db_models import DbSession
            from infrastructure.db.database import SessionLocal
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

    # ----------------------------------------------------------
    # Main dispatcher
    # ----------------------------------------------------------

    def handle(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        t_low = t_raw.lower()

        if t_low in {"contact", "offerte", "advies"}:
            self.state.post_offer_stage = "contact_naam"
            return self.state, [
                "Uitstekend. Ik noteer graag uw gegevens om de offerte op te stellen.\n\nWat is uw naam?"
            ]

        stage = self.state.post_offer_stage

        if stage == "menu":
            return self._handle_main_menu(t_raw)
        if stage == "lower_costs_menu":
            return self._handle_lower_costs_menu(t_raw)

        if stage == "lc_more_green_choice":
            return self._handle_more_green_choice(t_raw)
        if stage == "lc_extras_select":
            return self._handle_extras_select(t_raw)
        if stage == "lc_vlonder_choice":
            return self._handle_vlonder_choice(t_raw)
        if stage == "lc_overkapping_choice":
            return self._handle_overkapping_choice(t_raw)
        if stage == "lc_voegen_choice":
            return self._handle_voegen_choice(t_raw)
        if stage == "lc_verlichting_choice":
            return self._handle_verlichting_choice(t_raw)
        if stage == "lc_erf_remove_select":
            return self._handle_erf_remove_select(t_raw)
        if stage == "lc_erf_component":
            return self._handle_erf_component(t_raw)
        if stage == "lc_erf_sub":
            return self._handle_erf_sub(t_raw)
        if stage == "lc_beregening_systeem_choice":
            return self._handle_beregening_systeem_choice(t_raw)
        if stage == "lc_material_part":
            return self._handle_material_part(t_raw)
        if stage == "lc_material_choice":
            return self._handle_material_choice(t_raw)
        if stage == "lc_losse_remove":
            return self._handle_losse_component_remove(t_raw)

        # Contact stages — delegate to ContactController
        if stage in ("contact_naam", "contact_telefoon", "contact_email",
                     "contact_adres", "contact_woonplaats", "contact_opmerking"):
            return self._handle_contact_stage(stage, t_raw)

        return self.state, [self._main_menu_text()]

    def _handle_contact_stage(self, stage: str, t_raw: str) -> Tuple[ChatState, List[str]]:
        from core.controllers.contact_controller import ContactController
        ctrl = ContactController(self.state)
        dispatch = {
            "contact_naam": ctrl.handle_naam,
            "contact_telefoon": ctrl.handle_telefoon,
            "contact_email": ctrl.handle_email,
            "contact_adres": ctrl.handle_adres,
            "contact_woonplaats": ctrl.handle_woonplaats,
            "contact_opmerking": ctrl.handle_opmerking,
        }
        return dispatch[stage](t_raw)

    # ----------------------------------------------------------
    # Main menu
    # ----------------------------------------------------------

    def _handle_main_menu(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        from flow_tuinaanleg import TuinaanlegFlowV2
        from flow_losse_onderdelen import LosseOnderdelenFlow

        if t_raw == "1":
            self.state.post_offer_stage = "contact_naam"
            self.state.prijs_gezien_en_doorgegaan = True
            if _DB and self.state.session_id:
                log_offerte_aangevraagd(self.state.session_id)
            return self.state, ["Uitstekend. We helpen u graag verder. Wat is uw naam?"]

        if self._is_tuinontwerp():
            if t_raw == "2":
                self.state.post_offer_mode = False
                self.state.post_offer_stage = None
                self.state.flow = TuinaanlegFlowV2()
                self.state.flow_type = "gehele_tuin"
                self.state.last_answers = None
                self.state.last_costs = None
                if _DB and self.state.session_id:
                    from db_logger import update_session_flow
                    update_session_flow(self.state.session_id, "gehele_tuin")
                    log_event(self.state.session_id, "flow_started", {"flow": "gehele_tuin", "from": "tuinontwerp"})
                return self.state, [self.state.flow.get_question()]
            if t_raw == "3":
                self.state.post_offer_mode = False
                self.state.post_offer_stage = None
                self.state.losse_flow = LosseOnderdelenFlow()
                self.state.flow_type = "losse_onderdelen"
                self.state.last_answers = None
                self.state.last_costs = None
                if _DB and self.state.session_id:
                    from db_logger import update_session_flow
                    update_session_flow(self.state.session_id, "losse_onderdelen")
                    log_event(self.state.session_id, "flow_started", {"flow": "losse_onderdelen", "from": "tuinontwerp"})
                return self.state, [self.state.losse_flow.start_question()]
            if t_raw == "4" or is_cancel(t_raw):
                return self._do_exit()
        elif self._is_losse():
            if t_raw == "2":
                self.state.post_offer_mode = False
                self.state.post_offer_stage = None
                self.state.losse_flow = LosseOnderdelenFlow.from_answers(self.state.last_answers or {})
                self.state.flow_type = "losse_onderdelen"
                return self.state, [self.state.losse_flow.start_question()]
            if t_raw == "3":
                self.state.post_offer_stage = "lower_costs_menu"
                return self.state, [self._lower_costs_menu()]
            if t_raw == "4" or is_cancel(t_raw):
                return self._do_exit()
        else:
            if t_raw == "2":
                self.state.post_offer_stage = "lower_costs_menu"
                return self.state, [self._lower_costs_menu()]
            if t_raw == "3" or is_cancel(t_raw):
                return self._do_exit()

        return self.state, [self._main_menu_text()]

    def _do_exit(self) -> Tuple[ChatState, List[str]]:
        self.state.post_offer_mode = False
        self.state.post_offer_stage = "end"
        self.state.ended = True
        self.state.end_reason = "no_contact"
        if _DB and self.state.session_id:
            update_session_ended(self.state.session_id)
            log_event(self.state.session_id, "session_ended", {"reason": "no_contact"})
            log_drop_off(self.state.session_id, "na_prijs_gezien")
            self._bereken_en_sla_leadscore(sessie_volledig=True, offerte_aangevraagd=False, drop_off=True)
        return self.state, [_EXIT_MSG]

    # ----------------------------------------------------------
    # Lower-costs menu routing
    # ----------------------------------------------------------

    def _handle_lower_costs_menu(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        if is_cancel(t_raw):
            self.state.post_offer_stage = "menu"
            return self.state, [self._main_menu_text()]
        if self._is_losse():
            return self._handle_lower_costs_menu_losse(t_raw)
        return self._handle_lower_costs_menu_gehele(t_raw)

    def _handle_lower_costs_menu_gehele(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu_text, mapping = lower_costs_menu_text(self.state.last_answers, self.state.last_costs)

        if t_raw not in mapping:
            return self.state, [menu_text]

        action = mapping[t_raw]

        if action == "more_green":
            menu, mg_mapping = more_green_choice_text(self.state.last_answers, self.state.last_costs)
            if not mg_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_more_green_choice"
            return self.state, [menu]

        if action == "material":
            self.state.post_offer_stage = "lc_material_part"
            menu, _ = material_part_menu_text(self.state.last_answers)
            return self.state, [menu]

        if action == "voegen":
            menu, vg_mapping = voegen_choice_menu_text(self.state.last_answers, self.state.last_costs)
            if not vg_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_voegen_choice"
            return self.state, [menu]

        if action == "overkapping":
            menu, ov_mapping = overkapping_choice_menu_text(self.state.last_answers, self.state.last_costs)
            if not ov_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_overkapping_choice"
            return self.state, [menu]

        if action == "verlichting":
            menu, vl_mapping = verlichting_choice_menu_text(self.state.last_answers, self.state.last_costs)
            if not vl_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_verlichting_choice"
            return self.state, [menu]

        if action == "beregening":
            ber_menu, ber_mapping = beregening_systeem_choice_text(self.state.last_answers, self.state.last_costs)
            if not ber_mapping:
                return self.state, [ber_menu, menu_text]
            self.state.post_offer_stage = "lc_beregening_systeem_choice"
            return self.state, [ber_menu]

        if action == "vlonder":
            menu, vl_mapping = vlonder_choice_menu_text(self.state.last_answers, self.state.last_costs)
            if not vl_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_vlonder_choice"
            return self.state, [menu]

        if action == "erfafscheiding":
            menu, erf_mapping = erf_item_select_menu_text(self.state.last_answers, self.state.last_costs)
            if not erf_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_erf_component"
            return self.state, [menu]

        return self.state, [menu_text]

    def _handle_lower_costs_menu_losse(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu_text, mapping = lower_costs_menu_losse_text(self.state.last_answers, self.state.last_costs)

        if t_raw not in mapping:
            return self.state, [menu_text]

        action = mapping[t_raw]

        if action == "material":
            self.state.post_offer_stage = "lc_material_part"
            menu, _ = material_part_menu_text(self.state.last_answers)
            return self.state, [menu]

        if action == "beregening":
            ber_menu, ber_mapping = beregening_systeem_choice_text(self.state.last_answers, self.state.last_costs)
            if not ber_mapping:
                return self.state, [ber_menu, menu_text]
            self.state.post_offer_stage = "lc_beregening_systeem_choice"
            return self.state, [ber_menu]

        if action in ("oprit_m2", "paden_m2", "terras_m2", "gazon_m2", "beplanting_m2"):
            new_a, expl = apply_remove_losse_component(dict(self.state.last_answers or {}), action)
            return self._apply_recalc(new_a, expl)

        _item_match = re.match(r'^(oprit|paden|terras)_item_(\d+)$', action)
        if _item_match:
            comp_base, index = _item_match.group(1), int(_item_match.group(2))
            new_a, expl = apply_remove_losse_item(dict(self.state.last_answers or {}), comp_base, index)
            return self._apply_recalc(new_a, expl)

        if action == "erfafscheiding":
            menu, erf_mapping = erf_item_select_menu_text(self.state.last_answers, self.state.last_costs)
            if not erf_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_erf_component"
            return self.state, [menu]

        if action == "vlonder":
            menu, vl_mapping = vlonder_choice_menu_text(self.state.last_answers, self.state.last_costs)
            if not vl_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_vlonder_choice"
            return self.state, [menu]

        if action == "overkapping":
            menu, ov_mapping = overkapping_choice_menu_text(self.state.last_answers, self.state.last_costs)
            if not ov_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_overkapping_choice"
            return self.state, [menu]

        if action == "verlichting":
            menu, vl_mapping = verlichting_choice_menu_text(self.state.last_answers, self.state.last_costs)
            if not vl_mapping:
                return self.state, [menu, menu_text]
            self.state.post_offer_stage = "lc_verlichting_choice"
            return self.state, [menu]

        return self.state, [menu_text]

    # ----------------------------------------------------------
    # Recalculation helper
    # ----------------------------------------------------------

    def _apply_recalc(
        self,
        new_answers: dict,
        explanation: str,
        preserve_direct_markers: bool = False,
    ) -> Tuple[ChatState, List[str]]:
        if not preserve_direct_markers:
            for _k in ("_flow_version", "_direct_oprit_m2", "_direct_terras_m2",
                       "_direct_paden_m2", "_direct_gazon_m2", "_direct_beplanting_m2"):
                new_answers.pop(_k, None)
        before_costs = dict(self.state.last_costs or {})
        new_costs = self._estimate_costs(new_answers)
        msgs = self._recalc_messages(before_costs, new_costs, explanation)
        self.state.recalc_count += 1
        self.state.heeft_herberekend = True
        self.state.last_answers = dict(new_answers)
        self.state.last_costs = dict(new_costs)
        if _DB and self.state.session_id:
            tr_old = before_costs.get("total_range_eur") or [0, 0]
            tr_new = new_costs.get("total_range_eur") or [0, 0]
            self.state.last_calc_id = log_price_calculation(
                self.state.session_id, self.state.flow_type or "onbekend", new_costs
            )
            log_event(self.state.session_id, "recalc_done", {
                "recalc_count": self.state.recalc_count,
                "old_min": tr_old[0], "old_max": tr_old[1],
                "new_min": tr_new[0], "new_max": tr_new[1],
                "explanation": explanation,
            })
        self.state.post_offer_stage = "menu"
        msgs.append(self._main_menu_text())
        return self.state, msgs

    # ----------------------------------------------------------
    # Sub-handlers (gehele tuin)
    # ----------------------------------------------------------

    def _handle_more_green_choice(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = more_green_choice_text(self.state.last_answers, self.state.last_costs)
        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]

        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            return self.state, [menu]
        if picked == "nee":
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        a = dict(self.state.last_answers or {})
        is_items_based = (
            float(a.get("_direct_terras_m2") or 0) > 0
            or float(a.get("_direct_paden_m2") or 0) > 0
            or float(a.get("_direct_oprit_m2") or 0) > 0
            or bool(a.get("terras_extra_items"))
            or bool(a.get("paden_extra_items"))
        )
        if is_items_based:
            new_a, expl = apply_ratio_proportional(a, mapping[picked])
            return self._apply_recalc(new_a, expl, preserve_direct_markers=True)
        else:
            new_a, expl = apply_set_ratio(a, mapping[picked])
            new_a.pop("terras_extra_items", None)
            new_a.pop("paden_extra_items", None)
            return self._apply_recalc(new_a, expl)

    def _handle_extras_select(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = extras_select_menu_text(self.state.last_answers, self.state.last_costs)
        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]

        if is_cancel(t_raw):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        parsed = parse_multi_digits(t_raw, allowed=tuple(mapping.keys()))
        if parsed is None:
            return self.state, [menu]
        if parsed == ("nee",):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        actions = [mapping[d] for d in parsed if d in mapping]
        if not actions:
            return self.state, [menu]

        if "beregening_downgrade" in actions:
            ber_menu, ber_mapping = beregening_systeem_choice_text(self.state.last_answers, self.state.last_costs)
            if not ber_mapping:
                return self.state, [ber_menu, menu]
            self.state.post_offer_stage = "lc_beregening_systeem_choice"
            return self.state, [ber_menu]

        new_a, expl = apply_remove_selected_extras(dict(self.state.last_answers or {}), actions)
        return self._apply_recalc(new_a, expl)

    # ----------------------------------------------------------
    # Sub-handlers (gedeeld: materiaal)
    # ----------------------------------------------------------

    def _handle_material_part(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        if is_cancel(t_raw):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        menu, part_mapping = material_part_menu_text(self.state.last_answers)
        if not part_mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]

        picked_digits = parse_material_parts(t_raw)
        if picked_digits is None:
            return self.state, [menu]
        if picked_digits == ("nee",):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        item_specs = tuple(part_mapping[d] for d in picked_digits if d in part_mapping)
        if not item_specs:
            return self.state, [menu]

        self.state.pending_material_part = item_specs
        menu2, allowed_choices = material_choice_menu_text_cheaper(
            self.state.last_answers, self.state.last_costs, item_specs
        )
        if not allowed_choices:
            self.state.post_offer_stage = "lc_material_part"
            return self.state, [menu2, menu]

        self.state.post_offer_stage = "lc_material_choice"
        return self.state, [menu2]

    def _handle_material_choice(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        part = self.state.pending_material_part or ("terras_0",)
        menu, allowed_choices = material_choice_menu_text_cheaper(
            self.state.last_answers, self.state.last_costs, part
        )
        if not allowed_choices:
            part_menu, _ = material_part_menu_text(self.state.last_answers)
            self.state.post_offer_stage = "lc_material_part"
            return self.state, [menu, part_menu]

        picked = parse_single_digit(t_raw, allowed=tuple(sorted(allowed_choices)))
        if picked is None:
            return self.state, [menu]
        if picked == "nee":
            part_menu, _ = material_part_menu_text(self.state.last_answers)
            self.state.post_offer_stage = "lc_material_part"
            return self.state, [part_menu]

        new_a, expl = apply_material_change(dict(self.state.last_answers or {}), part, picked)
        self.state.pending_material_part = None
        return self._apply_recalc(new_a, expl)

    # ----------------------------------------------------------
    # Sub-handlers (gehele tuin: vlonder + erfafscheiding)
    # ----------------------------------------------------------

    def _handle_overkapping_choice(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = overkapping_choice_menu_text(self.state.last_answers, self.state.last_costs)
        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]
        if is_cancel(t_raw):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]
        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            return self.state, [menu]
        new_a, expl = apply_overkapping_change(dict(self.state.last_answers or {}), mapping[picked])
        return self._apply_recalc(new_a, expl)

    def _handle_voegen_choice(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = voegen_choice_menu_text(self.state.last_answers, self.state.last_costs)
        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]
        if is_cancel(t_raw):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]
        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            return self.state, [menu]
        new_a, expl = apply_voegen_change(dict(self.state.last_answers or {}))
        return self._apply_recalc(new_a, expl)

    def _handle_verlichting_choice(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = verlichting_choice_menu_text(self.state.last_answers, self.state.last_costs)
        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]
        if is_cancel(t_raw):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]
        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            return self.state, [menu]
        new_a, expl = apply_verlichting_change(dict(self.state.last_answers or {}))
        return self._apply_recalc(new_a, expl)

    def _handle_vlonder_choice(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = vlonder_choice_menu_text(self.state.last_answers, self.state.last_costs)
        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]

        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            return self.state, [menu]
        if picked == "nee":
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        new_a, expl = apply_vlonder_change(dict(self.state.last_answers or {}), mapping[picked])
        return self._apply_recalc(new_a, expl)

    def _handle_erf_remove_select(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = erf_remove_select_menu_text(self.state.last_answers, self.state.last_costs)
        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]

        if is_cancel(t_raw):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        parsed = parse_multi_digits(t_raw, allowed=tuple(mapping.keys()))
        if parsed is None:
            return self.state, [menu]
        if parsed == ("nee",):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        actions = [mapping[d] for d in parsed if d in mapping]
        if not actions:
            return self.state, [menu]

        new_a, expl = apply_erf_changes(dict(self.state.last_answers or {}), actions)
        return self._apply_recalc(new_a, expl)

    def _handle_erf_component(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = erf_item_select_menu_text(self.state.last_answers, self.state.last_costs)
        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]

        if is_cancel(t_raw):
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            return self.state, [menu]
        if picked == "nee":
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        item_index = int(mapping[picked])
        self.state.erf_item_index = item_index

        items = list((self.state.last_answers or {}).get("erfafscheiding_items") or [])
        if item_index >= len(items):
            return self.state, [menu]

        t = (items[item_index].get("type") or "").strip().lower()
        if t == "haag":
            sub_menu, sub_mapping = erf_haag_menu_text(self.state.last_answers, self.state.last_costs, item_index)
        else:
            sub_menu, sub_mapping = erf_schutting_menu_text(self.state.last_answers, self.state.last_costs, item_index)

        if not sub_mapping:
            return self.state, [sub_menu, menu]

        self.state.post_offer_stage = "lc_erf_sub"
        return self.state, [sub_menu]

    def _handle_erf_sub(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        item_index = self.state.erf_item_index or 0
        items = list((self.state.last_answers or {}).get("erfafscheiding_items") or [])

        if item_index >= len(items):
            self.state.post_offer_stage = "lc_erf_component"
            comp_menu, _ = erf_item_select_menu_text(self.state.last_answers, self.state.last_costs)
            return self.state, [comp_menu]

        t = (items[item_index].get("type") or "").strip().lower()
        if t == "haag":
            menu, mapping = erf_haag_menu_text(self.state.last_answers, self.state.last_costs, item_index)
        else:
            menu, mapping = erf_schutting_menu_text(self.state.last_answers, self.state.last_costs, item_index)

        if not mapping:
            self.state.post_offer_stage = "lc_erf_component"
            comp_menu, _ = erf_item_select_menu_text(self.state.last_answers, self.state.last_costs)
            return self.state, [menu, comp_menu]

        if is_cancel(t_raw):
            self.state.post_offer_stage = "lc_erf_component"
            comp_menu, _ = erf_item_select_menu_text(self.state.last_answers, self.state.last_costs)
            return self.state, [comp_menu]

        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            return self.state, [menu]
        if picked == "nee":
            self.state.post_offer_stage = "lc_erf_component"
            comp_menu, _ = erf_item_select_menu_text(self.state.last_answers, self.state.last_costs)
            return self.state, [comp_menu]

        action = mapping[picked]
        if t == "haag":
            new_a, expl = apply_erf_item_haag_change(dict(self.state.last_answers or {}), item_index, action)
        else:
            new_a, expl = apply_erf_item_schutting_change(dict(self.state.last_answers or {}), item_index, action)

        self.state.erf_item_index = None
        return self._apply_recalc(new_a, expl)

    # ----------------------------------------------------------
    # Sub-handler (beregening systeem)
    # ----------------------------------------------------------

    def _handle_beregening_systeem_choice(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = beregening_systeem_choice_text(self.state.last_answers, self.state.last_costs)
        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [menu, self._lower_costs_menu()]

        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            return self.state, [menu]
        if picked == "nee":
            self.state.post_offer_stage = "lower_costs_menu"
            return self.state, [self._lower_costs_menu()]

        action = mapping[picked]
        if action == "remove":
            new_a, expl = apply_beregening_remove(dict(self.state.last_answers or {}))
        else:
            new_a, expl = apply_beregening_systeem_change(dict(self.state.last_answers or {}), action)
        return self._apply_recalc(new_a, expl)

    # ----------------------------------------------------------
    # Sub-handler (losse onderdelen: component verwijderen)
    # ----------------------------------------------------------

    def _handle_losse_component_remove(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        menu, mapping = losse_component_remove_menu_text(self.state.last_answers, self.state.last_costs)

        if is_cancel(t_raw):
            self.state.post_offer_stage = "lower_costs_menu"
            menu_text, _ = lower_costs_menu_losse_text(self.state.last_answers)
            return self.state, [menu_text]

        if not mapping:
            self.state.post_offer_stage = "lower_costs_menu"
            menu_text, _ = lower_costs_menu_losse_text(self.state.last_answers)
            return self.state, [menu, menu_text]

        picked = parse_single_digit(t_raw, allowed=tuple(mapping.keys()))
        if picked is None:
            return self.state, [menu]
        if picked == "nee":
            self.state.post_offer_stage = "lower_costs_menu"
            menu_text, _ = lower_costs_menu_losse_text(self.state.last_answers)
            return self.state, [menu_text]

        comp_key = mapping[picked]
        new_a, expl = apply_remove_losse_component(dict(self.state.last_answers or {}), comp_key)
        return self._apply_recalc(new_a, expl)
