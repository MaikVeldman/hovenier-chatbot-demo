from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.tenant import TenantConfig
    from core.pricing.price_table import PriceTable
    from infrastructure.db.repositories.session_repository import SessionRepository


@dataclass
class TenantContext:
    config: TenantConfig
    price_table: PriceTable
    repo: SessionRepository = field(default_factory=lambda: _default_repo())


def _default_repo():
    from infrastructure.db.repositories.session_repository import SessionRepository
    return SessionRepository()
