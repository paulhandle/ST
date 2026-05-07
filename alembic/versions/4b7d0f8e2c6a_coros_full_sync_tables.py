"""coros full sync tables

Revision ID: 4b7d0f8e2c6a
Revises: 1ac50e58dbdb
Create Date: 2026-05-05 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4b7d0f8e2c6a"
down_revision: Union[str, Sequence[str], None] = "1ac50e58dbdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_sync_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("phase", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("metric_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("raw_record_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athlete_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_sync_jobs_athlete_id"), "provider_sync_jobs", ["athlete_id"], unique=False)
    op.create_index(op.f("ix_provider_sync_jobs_id"), "provider_sync_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_provider_sync_jobs_provider"), "provider_sync_jobs", ["provider"], unique=False)
    op.create_index(op.f("ix_provider_sync_jobs_status"), "provider_sync_jobs", ["status"], unique=False)

    op.create_table(
        "provider_sync_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("phase", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["provider_sync_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_sync_events_created_at"), "provider_sync_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_provider_sync_events_id"), "provider_sync_events", ["id"], unique=False)
    op.create_index(op.f("ix_provider_sync_events_job_id"), "provider_sync_events", ["job_id"], unique=False)

    op.create_table(
        "provider_raw_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("sync_job_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("record_type", sa.String(length=80), nullable=False),
        sa.Column("provider_record_id", sa.String(length=220), nullable=False),
        sa.Column("endpoint", sa.String(length=240), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athlete_profiles.id"]),
        sa.ForeignKeyConstraint(["sync_job_id"], ["provider_sync_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "record_type", "provider_record_id", name="uq_provider_raw_record"),
    )
    op.create_index(op.f("ix_provider_raw_records_athlete_id"), "provider_raw_records", ["athlete_id"], unique=False)
    op.create_index(op.f("ix_provider_raw_records_fetched_at"), "provider_raw_records", ["fetched_at"], unique=False)
    op.create_index(op.f("ix_provider_raw_records_id"), "provider_raw_records", ["id"], unique=False)
    op.create_index(op.f("ix_provider_raw_records_provider"), "provider_raw_records", ["provider"], unique=False)
    op.create_index(
        op.f("ix_provider_raw_records_provider_record_id"),
        "provider_raw_records",
        ["provider_record_id"],
        unique=False,
    )
    op.create_index(op.f("ix_provider_raw_records_record_type"), "provider_raw_records", ["record_type"], unique=False)
    op.create_index(op.f("ix_provider_raw_records_sync_job_id"), "provider_raw_records", ["sync_job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_provider_raw_records_sync_job_id"), table_name="provider_raw_records")
    op.drop_index(op.f("ix_provider_raw_records_record_type"), table_name="provider_raw_records")
    op.drop_index(op.f("ix_provider_raw_records_provider_record_id"), table_name="provider_raw_records")
    op.drop_index(op.f("ix_provider_raw_records_provider"), table_name="provider_raw_records")
    op.drop_index(op.f("ix_provider_raw_records_id"), table_name="provider_raw_records")
    op.drop_index(op.f("ix_provider_raw_records_fetched_at"), table_name="provider_raw_records")
    op.drop_index(op.f("ix_provider_raw_records_athlete_id"), table_name="provider_raw_records")
    op.drop_table("provider_raw_records")
    op.drop_index(op.f("ix_provider_sync_events_job_id"), table_name="provider_sync_events")
    op.drop_index(op.f("ix_provider_sync_events_id"), table_name="provider_sync_events")
    op.drop_index(op.f("ix_provider_sync_events_created_at"), table_name="provider_sync_events")
    op.drop_table("provider_sync_events")
    op.drop_index(op.f("ix_provider_sync_jobs_status"), table_name="provider_sync_jobs")
    op.drop_index(op.f("ix_provider_sync_jobs_provider"), table_name="provider_sync_jobs")
    op.drop_index(op.f("ix_provider_sync_jobs_id"), table_name="provider_sync_jobs")
    op.drop_index(op.f("ix_provider_sync_jobs_athlete_id"), table_name="provider_sync_jobs")
    op.drop_table("provider_sync_jobs")
