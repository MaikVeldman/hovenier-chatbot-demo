# interfaces/formatters/price_formatter.py
from __future__ import annotations

from typing import Any, Dict, List


class PriceFormatter:
    """
    Verzamelt alle weergave-logica voor prijsberekeningen.
    Delegeert voorlopig naar pricing.py (implementatie verhuist in fase 12).
    """

    def to_chat_html(self, costs: Dict[str, Any], flow_type: str = "gehele_tuin") -> str:
        from core.pricing.pricing import format_costs_as_chat_html
        return format_costs_as_chat_html(costs, flow_type)

    def to_tuinontwerp_html(self, costs: Dict[str, Any]) -> str:
        from core.pricing.pricing import format_tuinontwerp_costs_as_chat_html
        return format_tuinontwerp_costs_as_chat_html(costs)

    def breakdown_grouped(self, breakdown: List[Dict[str, Any]]) -> str:
        from core.pricing.pricing import format_breakdown_grouped
        return format_breakdown_grouped(breakdown)

    def to_customer_summary(self, costs: Dict[str, Any]) -> str:
        from core.pricing.pricing import format_tuinaanleg_choices_for_customer
        return format_tuinaanleg_choices_for_customer(costs)

    def to_losse_summary(self, costs: Dict[str, Any]) -> str:
        from core.pricing.pricing import format_losse_onderdelen_choices_for_customer
        return format_losse_onderdelen_choices_for_customer(costs)

    def to_tuinaanleg_costs_summary(self, costs: Dict[str, Any]) -> str:
        from core.pricing.pricing import format_tuinaanleg_costs_for_customer
        return format_tuinaanleg_costs_for_customer(costs)
