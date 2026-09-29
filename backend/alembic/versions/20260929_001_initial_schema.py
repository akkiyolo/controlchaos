"""initial_schema

Revision ID: 20260929_001
Revises:
Create Date: 2026-09-29 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. entities
    op.create_table(
        "entities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entities_code", "entities", ["code"], unique=True)

    # 3. accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("normal_balance", sa.String(length=10), nullable=False),
        sa.Column("parent_code", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_code", "accounts", ["code"], unique=True)

    # 4. datasets
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("period_start", sa.String(length=10), nullable=False),
        sa.Column("period_end", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("is_baseline", sa.Boolean(), nullable=False),
        sa.Column("parent_dataset_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["parent_dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_datasets_is_baseline", "datasets", ["is_baseline"], unique=False)

    # 5. gl_entries
    op.create_table(
        "gl_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=64), nullable=False),
        sa.Column("posting_date", sa.String(length=10), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("account_code", sa.String(length=32), nullable=False),
        sa.Column("debit", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("credit", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("fx_rate", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("approved_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gl_dataset_period", "gl_entries", ["dataset_id", "period"])
    op.create_index("ix_gl_dataset_account", "gl_entries", ["dataset_id", "account_code"])
    op.create_index("ix_gl_batch_id", "gl_entries", ["dataset_id", "batch_id"])

    # 6. subledger_entries
    op.create_table(
        "subledger_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("ref_id", sa.String(length=64), nullable=False),
        sa.Column("gl_entry_id", sa.String(length=64), nullable=True),
        sa.Column("subledger_type", sa.String(length=32), nullable=False),
        sa.Column("counterparty", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("value_date", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subledger_dataset_type", "subledger_entries", ["dataset_id", "subledger_type"])
    op.create_index("ix_subledger_ref", "subledger_entries", ["dataset_id", "ref_id"])

    # 7. budget
    op.create_table(
        "budget",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("account_code", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_budget_dataset_period", "budget", ["dataset_id", "period"])

    # 8. treasury_positions
    op.create_table(
        "treasury_positions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("as_of_date", sa.String(length=10), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("cash_balance", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("hqla", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("outflows_30d", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("inflows_30d", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("funding_source", sa.String(length=64), nullable=False),
        sa.Column("funding_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("maturity_bucket", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 9. fx_rates
    op.create_table(
        "fx_rates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column("from_ccy", sa.String(length=3), nullable=False),
        sa.Column("to_ccy", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(precision=14, scale=6), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fx_lookup", "fx_rates", ["dataset_id", "date", "from_ccy", "to_ccy"])

    # 10. mutation_specs
    op.create_table(
        "mutation_specs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("class_name", sa.String(length=64), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("target_descriptor", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 11. mutation_ledger
    op.create_table(
        "mutation_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("mutation_id", sa.String(length=64), nullable=False),
        sa.Column("class_name", sa.String(length=64), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("affected_row_refs", sa.JSON(), nullable=False),
        sa.Column("expected_impact_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("injected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mutation_ledger_class", "mutation_ledger", ["dataset_id", "class_name"])

    # 12. control_definitions
    op.create_table(
        "control_definitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_control_definitions_key", "control_definitions", ["key"], unique=True)

    # 13. control_versions
    op.create_table(
        "control_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("control_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("diff", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["control_id"], ["control_definitions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_control_versions_control_id", "control_versions", ["control_id"])

    # 14. runs
    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("control_set_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 15. findings
    op.create_table(
        "findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("control_id", sa.String(length=64), nullable=False),
        sa.Column("finding_id", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("affected_row_refs", sa.JSON(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_findings_run_id", "findings", ["run_id"])

    # 16. detections
    op.create_table(
        "detections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("mutation_id", sa.String(length=64), nullable=False),
        sa.Column("detected", sa.Boolean(), nullable=False),
        sa.Column("detected_by", sa.JSON(), nullable=False),
        sa.Column("time_to_detect_ms", sa.Integer(), nullable=True),
        sa.Column("partial_credit", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_detections_run_mut", "detections", ["run_id", "mutation_id"])

    # 17. scores
    op.create_table(
        "scores",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("overall_detection_rate", sa.Float(), nullable=False),
        sa.Column("weighted_detection_rate", sa.Float(), nullable=False),
        sa.Column("by_class", sa.JSON(), nullable=False),
        sa.Column("by_control", sa.JSON(), nullable=False),
        sa.Column("false_positive_rate", sa.Float(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("f1", sa.Float(), nullable=False),
        sa.Column("cost_of_misses", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scores_run_id", "scores", ["run_id"], unique=True)

    # 18. proposals
    op.create_table(
        "proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("gap_class", sa.String(length=64), nullable=False),
        sa.Column("proposed_rule", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("backtest", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("maker", sa.String(length=255), nullable=False),
        sa.Column("checker", sa.String(length=255), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proposals_run_id", "proposals", ["run_id"])

    # 19. audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("prev_hash", sa.String(length=64), nullable=False),
        sa.Column("hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_ts", "audit_log", ["ts"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])

    # 20. jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("audit_log")
    op.drop_table("proposals")
    op.drop_table("scores")
    op.drop_table("detections")
    op.drop_table("findings")
    op.drop_table("runs")
    op.drop_table("control_versions")
    op.drop_table("control_definitions")
    op.drop_table("mutation_ledger")
    op.drop_table("mutation_specs")
    op.drop_table("fx_rates")
    op.drop_table("treasury_positions")
    op.drop_table("budget")
    op.drop_table("subledger_entries")
    op.drop_table("gl_entries")
    op.drop_table("datasets")
    op.drop_table("accounts")
    op.drop_table("entities")
    op.drop_table("users")
