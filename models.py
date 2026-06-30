# models.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ============================================================
# Fase 2 — Multi-tenant
# ============================================================

class DbTenant(Base):
    __tablename__ = "tenants"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    slug          = Column(String(100), unique=True, nullable=False)   # bijv. "veldman-hoveniers"
    naam          = Column(String(200), nullable=False)
    actief        = Column(Boolean, default=True, nullable=False)
    aangemaakt_op = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    users    = relationship("DbUser",         back_populates="tenant", cascade="all, delete-orphan")
    config   = relationship("DbTenantConfig", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("DbSession",      back_populates="tenant")


class DbUser(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email           = Column(String(200), unique=True, nullable=False)
    wachtwoord_hash = Column(String(256), nullable=False)
    is_superadmin   = Column(Boolean, default=False, nullable=False)
    aangemaakt_op   = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    tenant = relationship("DbTenant", back_populates="users")


class DbTenantConfig(Base):
    __tablename__ = "tenant_configs"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id        = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    bedrijfsnaam     = Column(String(200), nullable=False)
    regio            = Column(String(200), nullable=True)
    contact_email    = Column(String(200), nullable=True)
    contact_telefoon = Column(String(50),  nullable=True)
    begroeting       = Column(Text, nullable=True)
    primaire_kleur   = Column(String(20),  default="#5c6b1e", nullable=False)
    prijzen          = Column(JSON, nullable=True)   # {"sleutel": [min, max], ...}
    bijgewerkt_op    = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    tenant = relationship("DbTenant", back_populates="config")


class DbSession(Base):
    __tablename__ = "sessions"

    id               = Column(String(36), primary_key=True, default=_uuid)
    started_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at         = Column(DateTime, nullable=True)
    flow_type        = Column(String(50), nullable=True)   # "gehele_tuin" | "losse_onderdelen"
    completed        = Column(Boolean, default=False, nullable=False)   # prijsindicatie getoond
    contact_submitted = Column(Boolean, default=False, nullable=False)
    user_agent       = Column(Text, nullable=True)
    # Leadscore (Fase 1 — vervallen maar kolommen blijven voor bestaande data)
    leadscore        = Column(Integer, nullable=True)
    lead_label       = Column(String(50), nullable=True)
    score_breakdown  = Column(JSON, nullable=True)
    terug_acties     = Column(Integer, default=0, nullable=False)

    # Fase 2 — tenant koppeling
    tenant_id        = Column(Integer, ForeignKey("tenants.id"), nullable=True)

    tenant              = relationship("DbTenant",            back_populates="sessions")
    messages            = relationship("DbMessage",           back_populates="session", cascade="all, delete-orphan")
    events              = relationship("DbFlowEvent",         back_populates="session", cascade="all, delete-orphan")
    price_calculations  = relationship("DbPriceCalculation",  back_populates="session", cascade="all, delete-orphan")
    contact_submissions = relationship("DbContactSubmission", back_populates="session", cascade="all, delete-orphan")


class DbMessage(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp  = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    role       = Column(String(10), nullable=False)    # "user" | "bot"
    content    = Column(Text, nullable=False)
    flow_step  = Column(String(100), nullable=True)    # bijv. "tuin_m2", "materiaal_terras"

    session = relationship("DbSession", back_populates="messages")


class DbFlowEvent(Base):
    __tablename__ = "flow_events"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp  = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=True)

    session = relationship("DbSession", back_populates="events")

    # event_type waarden:
    #   flow_started       – welke flow gekozen
    #   flow_completed     – prijsindicatie getoond
    #   price_shown        – totaalbedrag + breakdown
    #   recalc_done        – herberekening na kostenbesparing
    #   contact_submitted  – naam/tel/mail ingevuld
    #   session_ended      – sessie afgesloten


class DbPriceCalculation(Base):
    __tablename__ = "price_calculations"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp    = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    flow_type    = Column(String(50), nullable=False)
    inputs       = Column(JSON, nullable=True)    # alle antwoorden / keuzes
    total_min_eur = Column(Integer, nullable=True)
    total_max_eur = Column(Integer, nullable=True)
    breakdown    = Column(JSON, nullable=True)    # volledige breakdown array

    session             = relationship("DbSession",          back_populates="price_calculations")
    contact_submissions = relationship("DbContactSubmission", back_populates="price_calculation")


class DbContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    session_id           = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp            = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    naam                 = Column(String(200), nullable=True)
    telefoon             = Column(String(50),  nullable=True)
    email                = Column(String(200), nullable=True)
    adres                = Column(String(300), nullable=True)
    woonplaats           = Column(String(200), nullable=True)
    notitie              = Column(Text, nullable=True)
    price_calculation_id = Column(Integer, ForeignKey("price_calculations.id"), nullable=True)
    email_sent_at        = Column(DateTime, nullable=True)

    session           = relationship("DbSession",          back_populates="contact_submissions")
    price_calculation = relationship("DbPriceCalculation", back_populates="contact_submissions")
