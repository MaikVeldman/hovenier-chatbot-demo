# core/models/tenant.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class TenantConfig:
    slug:             str
    bedrijfsnaam:     str
    regio:            str
    contact_email:    str
    contact_telefoon: str
    begroeting:       Optional[str]
    primaire_kleur:   str
    prijzen:          Dict[str, Tuple[int, int]] = field(default_factory=dict)
    volume_kortingen: Dict[str, List] = field(default_factory=dict)
