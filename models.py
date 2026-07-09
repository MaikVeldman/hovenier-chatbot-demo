# models.py — backward-compatible re-export, verwijder in fase 12
from infrastructure.db.db_models import (
    DbTenant, DbUser, DbTenantConfig, DbSession,
    DbMessage, DbFlowEvent, DbPriceCalculation, DbContactSubmission,
)
