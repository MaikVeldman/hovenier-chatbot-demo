# core/pricing/losse_pricer.py
from __future__ import annotations

from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.pricing.price_table import PriceTable


class LossePricer:
    def __init__(self, price_table: PriceTable):
        self.prices = price_table

    def estimate(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        from core.pricing.pricing import estimate_losse_onderdelen_costs
        return estimate_losse_onderdelen_costs(answers, price_table=self.prices)
