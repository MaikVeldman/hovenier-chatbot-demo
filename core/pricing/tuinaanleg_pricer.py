# core/pricing/tuinaanleg_pricer.py
from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.pricing.price_table import PriceTable


class TuinaanlegPricer:
    def __init__(self, price_table: PriceTable):
        self.prices = price_table

    def estimate(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        from pricing import estimate_tuinaanleg_costs
        return estimate_tuinaanleg_costs(answers, price_table=self.prices)
