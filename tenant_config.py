# tenant_config.py — backward-compatible re-export, verwijder in fase 12
from core.models.tenant import TenantConfig
from infrastructure.db.repositories.tenant_repository import TenantRepository

_repo = TenantRepository()

def laad_tenant(slug):           return _repo.get(slug)
def laad_tenant_of_default(slug): return _repo.get_or_default(slug)
