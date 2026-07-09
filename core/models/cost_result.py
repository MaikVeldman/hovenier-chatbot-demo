# core/models/cost_result.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class BreakdownItem:
    key: str
    label: str
    unit: str
    qty: Any
    range_eur: Optional[Tuple[int, int]]
    notes: str = ""


@dataclass
class CostResult:
    flow_type: str
    total_range_eur: Tuple[int, int]
    breakdown: List[BreakdownItem] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
