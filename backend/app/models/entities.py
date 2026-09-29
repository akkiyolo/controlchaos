"""SQLAlchemy ORM models for ControlChaos."""

import datetime
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base

# Universal JSON type that works with PostgreSQL JSONB or SQLite JSON for unit tests
JSONType = JSON().with_variant(JSONB, "postgresql")


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="analyst")  # admin, control_owner, reviewer, analyst, auditor
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )


class LegalEntity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    region: Mapped[str] = mapped_column(String(64), nullable=False)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # asset, liability, equity, revenue, expense
    normal_balance: Mapped[str] = mapped_column(String(10), nullable=False)  # debit, credit
    parent_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    params: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    period_start: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM
    period_end: Mapped[str] = mapped_column(String(10), nullable=False)    # YYYY-MM
    status: Mapped[str] = mapped_column(String(50), default="ready", nullable=False)  # pending, ready, failed
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    parent_dataset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )

    __table_args__ = (
        Index("ix_datasets_is_baseline", "is_baseline"),
    )


class GLEntry(Base):
    __tablename__ = "gl_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    entry_id: Mapped[str] = mapped_column(String(64), nullable=False)
    posting_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    period: Mapped[str] = mapped_column(String(7), nullable=False)        # YYYY-MM
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    account_code: Mapped[str] = mapped_column(String(32), nullable=False)
    debit: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    credit: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate: Mapped[float] = mapped_column(Numeric(12, 6), default=1.0, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        Index("ix_gl_dataset_period", "dataset_id", "period"),
        Index("ix_gl_dataset_account", "dataset_id", "account_code"),
        Index("ix_gl_batch_id", "dataset_id", "batch_id"),
    )


class SubledgerEntry(Base):
    __tablename__ = "subledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    ref_id: Mapped[str] = mapped_column(String(64), nullable=False)
    gl_entry_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    subledger_type: Mapped[str] = mapped_column(String(32), nullable=False)  # AR, AP, FA, payroll, cash
    counterparty: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    value_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    status: Mapped[str] = mapped_column(String(32), default="posted", nullable=False)

    __table_args__ = (
        Index("ix_subledger_dataset_type", "dataset_id", "subledger_type"),
        Index("ix_subledger_ref", "dataset_id", "ref_id"),
    )


class Budget(Base):
    __tablename__ = "budget"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    account_code: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)

    __table_args__ = (
        Index("ix_budget_dataset_period", "dataset_id", "period"),
    )


class TreasuryPosition(Base):
    __tablename__ = "treasury_positions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    as_of_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    cash_balance: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    hqla: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    outflows_30d: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    inflows_30d: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    funding_source: Mapped[str] = mapped_column(String(64), nullable=False)
    funding_amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    maturity_bucket: Mapped[str] = mapped_column(String(32), nullable=False)  # overnight, 7d, 30d, 90d, 1y+


class FXRate(Base):
    __tablename__ = "fx_rates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    from_ccy: Mapped[str] = mapped_column(String(3), nullable=False)
    to_ccy: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)

    __table_args__ = (
        Index("ix_fx_lookup", "dataset_id", "date", "from_ccy", "to_ccy"),
    )


class MutationSpec(Base):
    __tablename__ = "mutation_specs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    class_name: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)  # low, medium, high, critical
    target_descriptor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class MutationLedger(Base):
    __tablename__ = "mutation_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    mutation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    class_name: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    affected_row_refs: Mapped[List[str]] = mapped_column(JSONType, default=list, nullable=False)
    expected_impact_amount: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)
    injected_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )

    __table_args__ = (
        Index("ix_mutation_ledger_class", "dataset_id", "class_name"),
    )


class ControlDefinition(Base):
    __tablename__ = "control_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    params: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active, draft, retired
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )


class ControlVersion(Base):
    __tablename__ = "control_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    control_id: Mapped[str] = mapped_column(String(36), ForeignKey("control_definitions.id"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    params: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )
    diff: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    control_set_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)  # pending, running, completed, failed, cancelled
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )
    finished_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    config: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    control_id: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_id: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)  # low, medium, high, critical
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_row_refs: Mapped[List[str]] = mapped_column(JSONType, default=list, nullable=False)
    amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    detected_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    mutation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detected_by: Mapped[List[str]] = mapped_column(JSONType, default=list, nullable=False)
    time_to_detect_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    partial_credit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    __table_args__ = (
        Index("ix_detections_run_mut", "run_id", "mutation_id"),
    )


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    overall_detection_rate: Mapped[float] = mapped_column(Float, nullable=False)
    weighted_detection_rate: Mapped[float] = mapped_column(Float, nullable=False)
    by_class: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    by_control: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    false_positive_rate: Mapped[float] = mapped_column(Float, nullable=False)
    precision: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    f1: Mapped[float] = mapped_column(Float, nullable=False)
    cost_of_misses: Mapped[float] = mapped_column(Numeric(18, 4), default=0.0, nullable=False)


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False)
    gap_class: Mapped[str] = mapped_column(String(64), nullable=False)
    proposed_rule: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    backtest: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)  # pending, approved, rejected, superseded
    maker: Mapped[str] = mapped_column(String(255), nullable=False)
    checker: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        Index("ix_audit_log_ts", "ts"),
        Index("ix_audit_log_action", "action"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)  # pending, running, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False
    )
