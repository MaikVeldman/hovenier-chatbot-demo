from __future__ import annotations

from typing import List, Optional, Tuple

from core.models.chat_state import ChatState

try:
    from infrastructure.db.db_logger import (
        log_event,
        log_price_calculation,
        update_session_flow,
        update_session_completed,
        log_prijs_gezien,
        increment_terug_actie,
        log_offerte_aangevraagd,
    )
    _DB = True
except Exception:
    _DB = False

from core.pricing.pricing import (
    estimate_tuinaanleg_costs,
    estimate_losse_onderdelen_costs,
    estimate_tuinontwerp_costs,
    format_costs_as_chat_html,
    format_tuinontwerp_costs_as_chat_html,
)

INITIAL_GREETING = (
    "Bereken in 2 minuten wat uw tuin kost 👇\n\n"
    "1) De gehele tuin aanleggen – ik stel een paar vragen en reken de totale tuin door\n"
    "2) Losse onderdelen – kies zelf wat u wilt laten aanleggen (bijv. alleen een terras of gazon)\n"
    "3) Tuinontwerp – ik wil eerst een professioneel ontwerp met 3D visualisatie\n\n"
    "Reageer met 1, 2 of 3.\n\n"
    "_Door verder te gaan gaat u akkoord met onze [privacyverklaring](https://www.veldmanhoveniers.nl/privacybeleid/)._"
)


class ChatController:
    def __init__(self, state: ChatState, tenant_ctx=None):
        self.state = state
        self.tenant_ctx = tenant_ctx

    def handle(self, user_text: str) -> Tuple[ChatState, List[str]]:
        if self.state.ended:
            if self.state.end_reason == "contact_submitted":
                msg = (
                    "Uw aanvraag is al ontvangen. We nemen zo snel mogelijk contact met u op.\n\n"
                    "_Ververs de pagina om een nieuwe indicatie te starten._"
                )
            else:
                msg = "Deze sessie is afgesloten. Ververs de pagina om opnieuw een indicatie te starten."
            return self.state, [msg]

        t_raw = user_text.strip()

        if self.state.post_offer_mode:
            from core.controllers.post_offer_controller import PostOfferController
            ctrl = PostOfferController(self.state)
            return ctrl.handle(t_raw)

        if self.state.flow_type is None:
            return self._handle_flow_keuze(t_raw)

        if self.state.flow_type == "gehele_tuin" and self.state.flow is not None:
            return self._handle_intake(t_raw)

        if self.state.flow_type == "losse_onderdelen" and self.state.losse_flow is not None:
            return self._handle_losse_intake(t_raw)

        if self.state.flow_type == "tuinontwerp" and self.state.tuinontwerp_flow is not None:
            return self._handle_tuinontwerp_intake(t_raw)

        return self.state, []

    # ----------------------------------------------------------
    # Flow-keuze
    # ----------------------------------------------------------

    def _handle_flow_keuze(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        from core.flows.tuinaanleg import TuinaanlegFlowV2
        from core.flows.losse_onderdelen import LosseOnderdelenFlow
        from core.flows.tuinontwerp import TuinontWerpFlow

        if t_raw == "1":
            self.state.flow_type = "gehele_tuin"
            self.state.flow = TuinaanlegFlowV2()
            if _DB and self.state.session_id:
                update_session_flow(self.state.session_id, "gehele_tuin")
                log_event(self.state.session_id, "flow_started", {"flow": "gehele_tuin"})
            return self.state, [self.state.flow.get_question()]
        if t_raw == "2":
            self.state.flow_type = "losse_onderdelen"
            self.state.losse_flow = LosseOnderdelenFlow()
            if _DB and self.state.session_id:
                update_session_flow(self.state.session_id, "losse_onderdelen")
                log_event(self.state.session_id, "flow_started", {"flow": "losse_onderdelen"})
            return self.state, [self.state.losse_flow.start_question()]
        if t_raw == "3":
            self.state.flow_type = "tuinontwerp"
            self.state.tuinontwerp_flow = TuinontWerpFlow()
            if _DB and self.state.session_id:
                update_session_flow(self.state.session_id, "tuinontwerp")
                log_event(self.state.session_id, "flow_started", {"flow": "tuinontwerp"})
            return self.state, [self.state.tuinontwerp_flow.get_question()]
        return self.state, ["Typ **1**, **2** of **3** om een keuze te maken."]

    # ----------------------------------------------------------
    # Intake flows
    # ----------------------------------------------------------

    def _handle_intake(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        from core.pricing.savings import post_offer_choices_text
        flow = self.state.flow
        if t_raw.strip().lower() in ("terug", "back", "vorige") and _DB and self.state.session_id:
            increment_terug_actie(self.state.session_id, stap=str(flow.step_index))
        reply, done = flow.handle(t_raw)
        msgs: List[str] = [reply] if reply else []

        if done:
            answers_for_pricing = flow.to_answers()
            costs = estimate_tuinaanleg_costs(answers_for_pricing)
            msgs.append(self._format_costs(answers_for_pricing, costs))
            self.state.last_answers = dict(answers_for_pricing)
            self.state.last_costs = dict(costs)
            self.state.flow = None
            self.state.post_offer_mode = True
            self.state.post_offer_stage = "menu"
            if _DB and self.state.session_id:
                tr = costs.get("total_range_eur") or [0, 0]
                self.state.last_calc_id = log_price_calculation(
                    self.state.session_id, "gehele_tuin", costs
                )
                update_session_completed(self.state.session_id)
                log_event(self.state.session_id, "flow_completed", {
                    "flow": "gehele_tuin", "total_min": tr[0], "total_max": tr[1]
                })
                log_prijs_gezien(self.state.session_id, int(tr[0]), int(tr[1]))
            msgs.append(post_offer_choices_text())

        return self.state, msgs

    def _handle_losse_intake(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        from core.pricing.savings import post_offer_choices_losse_text
        flow = self.state.losse_flow
        if t_raw.strip().lower() in ("terug", "back", "vorige") and _DB and self.state.session_id:
            increment_terug_actie(self.state.session_id, stap=str(getattr(flow, "step_index", "?")))
        reply, done = flow.handle(t_raw)
        msgs: List[str] = [reply] if reply else []

        if done:
            answers = flow.to_answers()
            costs = estimate_losse_onderdelen_costs(answers)
            msgs.append(self._format_costs(answers, costs))
            self.state.last_answers = answers
            self.state.last_costs = dict(costs)
            self.state.losse_flow = None
            self.state.post_offer_mode = True
            self.state.post_offer_stage = "menu"
            if _DB and self.state.session_id:
                tr = costs.get("total_range_eur") or [0, 0]
                self.state.last_calc_id = log_price_calculation(
                    self.state.session_id, "losse_onderdelen", costs
                )
                update_session_completed(self.state.session_id)
                log_event(self.state.session_id, "flow_completed", {
                    "flow": "losse_onderdelen", "total_min": tr[0], "total_max": tr[1]
                })
                log_prijs_gezien(self.state.session_id, int(tr[0]), int(tr[1]))
            msgs.append(post_offer_choices_losse_text())

        return self.state, msgs

    def _handle_tuinontwerp_intake(self, t_raw: str) -> Tuple[ChatState, List[str]]:
        from core.pricing.savings import post_offer_choices_tuinontwerp_text
        flow = self.state.tuinontwerp_flow
        reply, done = flow.handle(t_raw)
        msgs: List[str] = [reply] if reply else []

        if done:
            answers = flow.to_answers()
            costs = estimate_tuinontwerp_costs(answers)
            msgs.append(format_tuinontwerp_costs_as_chat_html(costs))
            self.state.last_answers = answers
            self.state.last_costs = dict(costs)
            self.state.tuinontwerp_flow = None
            self.state.post_offer_mode = True
            self.state.post_offer_stage = "menu"
            if _DB and self.state.session_id:
                tr = costs.get("total_range_eur") or [0, 0]
                self.state.last_calc_id = log_price_calculation(
                    self.state.session_id, "tuinontwerp", costs
                )
                update_session_completed(self.state.session_id)
                log_event(self.state.session_id, "flow_completed", {
                    "flow": "tuinontwerp", "total_min": tr[0], "total_max": tr[1]
                })
                log_prijs_gezien(self.state.session_id, int(tr[0]), int(tr[1]))
            msgs.append(post_offer_choices_tuinontwerp_text())

        return self.state, msgs

    # ----------------------------------------------------------
    # Internal helper
    # ----------------------------------------------------------

    @staticmethod
    def _format_costs(answers: dict, costs: dict) -> str:
        ft = (answers or {}).get("_flow_type")
        if ft == "tuinontwerp":
            return format_tuinontwerp_costs_as_chat_html(costs)
        flow_type = "losse_onderdelen" if ft == "losse_onderdelen" else "gehele_tuin"
        return format_costs_as_chat_html(costs, flow_type)
