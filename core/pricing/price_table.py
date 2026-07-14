# core/pricing/price_table.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.pricing.constants import PRIJZEN, VOLUME_KORTINGEN, GRONDWERK_DIEPTES

if TYPE_CHECKING:
    from core.models.tenant import TenantConfig


class PriceTable:
    """
    Prijstabel voor één tenant. Combineert de standaard PRIJZEN met
    eventuele tenant-overrides. Dit is de SaaS-schakelaar: elke tenant
    krijgt zijn eigen instantie met zijn eigen tarieven.
    """

    def __init__(self, tenant_config: TenantConfig = None):
        overrides = (tenant_config.prijzen or {}) if tenant_config else {}
        self._data: Dict[str, Tuple[int, int]] = {**PRIJZEN, **overrides}
        self.volume_kortingen: Dict[str, List[Tuple[float, float]]] = dict(VOLUME_KORTINGEN)
        vk_overrides = (tenant_config.volume_kortingen or {}) if tenant_config else {}
        for cat, rows in vk_overrides.items():
            if rows:
                self.volume_kortingen[cat] = [(float(r[0]), float(r[1])) for r in rows]
        self.grondwerk_dieptes: Dict[str, float] = dict(GRONDWERK_DIEPTES)

    def get(self, key: str, default: Any = (0, 0)) -> Tuple[int, int]:
        return self._data.get(key, default)

    def __getitem__(self, key: str) -> Tuple[int, int]:
        return self._data[key]

    def schaal_factor(self, volume: float, soort: str) -> float:
        for drempel, factor in self.volume_kortingen.get(soort, []):
            if volume >= drempel:
                return factor
        return 1.0


class _DefaultPriceTable(PriceTable):
    """
    Leest live uit pricing module globals zodat de demo monkey-patching
    blijft werken. Tenant PriceTables kopiëren de waarden juist wel.
    """

    def __init__(self):
        pass  # geen kopie — altijd live lezen

    def get(self, key: str, default: Any = (0, 0)):
        from core.pricing.pricing import PRIJZEN as _P
        return _P.get(key, default)

    def __getitem__(self, key: str):
        from core.pricing.pricing import PRIJZEN as _P
        return _P[key]

    @property
    def grondwerk_dieptes(self):
        from core.pricing.pricing import GRONDWERK_DIEPTES as _GD
        return _GD

    def schaal_factor(self, volume: float, soort: str) -> float:
        from core.pricing.pricing import VOLUME_KORTINGEN as _VK
        for drempel, factor in _VK.get(soort, []):
            if volume >= drempel:
                return factor
        return 1.0


DEFAULT_PRICE_TABLE = _DefaultPriceTable()
