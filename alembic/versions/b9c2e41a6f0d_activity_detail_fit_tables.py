"""activity detail fit tables

Revision ID: b9c2e41a6f0d
Revises: 4b7d0f8e2c6a
Create Date: 2026-05-06 13:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9c2e41a6f0d"
down_revision: Union[str, Sequence[str], None] = "4b7d0f8e2c6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_detail_exports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_activity_id", sa.String(length=160), nullable=False),
        sa.Column("source_format", sa.String(length=20), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("file_url_host", sa.String(length=120), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(), nullable=False),
        sa.Column("parsed_at", sa.DateTime(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("lap_count", sa.Integer(), nullable=False),
        sa.Column("warnings_json", sa.Text(), nullable=True),
        sa.Column("raw_file_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["activity_id"], ["athlete_activities.id"]),
        sa.ForeignKeyConstraint(["athlete_id"], ["athlete_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id", "source_format", name="uq_activity_detail_export_format"),
    )
    op.create_index(op.f("ix_activity_detail_exports_activity_id"), "activity_detail_exports", ["activity_id"], unique=False)
    op.create_index(op.f("ix_activity_detail_exports_athlete_id"), "activity_detail_exports", ["athlete_id"], unique=False)
    op.create_index(op.f("ix_activity_detail_exports_downloaded_at"), "activity_detail_exports", ["downloaded_at"], unique=False)
    op.create_index(op.f("ix_activity_detail_exports_id"), "activity_detail_exports", ["id"], unique=False)
    op.create_index(op.f("ix_activity_detail_exports_provider"), "activity_detail_exports", ["provider"], unique=False)
    op.create_index(
        op.f("ix_activity_detail_exports_provider_activity_id"),
        "activity_detail_exports",
        ["provider_activity_id"],
        unique=False,
    )

    op.create_table(
        "activity_detail_samples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("sample_index", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("elapsed_sec", sa.Float(), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("altitude_m", sa.Float(), nullable=True),
        sa.Column("heart_rate", sa.Float(), nullable=True),
        sa.Column("cadence", sa.Float(), nullable=True),
        sa.Column("speed_mps", sa.Float(), nullable=True),
        sa.Column("pace_sec_per_km", sa.Float(), nullable=True),
        sa.Column("power_w", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["athlete_activities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id", "sample_index", name="uq_activity_detail_sample_index"),
    )
    op.create_index(op.f("ix_activity_detail_samples_activity_id"), "activity_detail_samples", ["activity_id"], unique=False)
    op.create_index(op.f("ix_activity_detail_samples_id"), "activity_detail_samples", ["id"], unique=False)
    op.create_index(op.f("ix_activity_detail_samples_timestamp"), "activity_detail_samples", ["timestamp"], unique=False)

    op.create_table(
        "activity_detail_laps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("activity_id", sa.Integer(), nullable=False),
        sa.Column("lap_index", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("avg_hr", sa.Float(), nullable=True),
        sa.Column("max_hr", sa.Float(), nullable=True),
        sa.Column("min_hr", sa.Float(), nullable=True),
        sa.Column("avg_cadence", sa.Float(), nullable=True),
        sa.Column("max_cadence", sa.Float(), nullable=True),
        sa.Column("avg_speed_mps", sa.Float(), nullable=True),
        sa.Column("max_speed_mps", sa.Float(), nullable=True),
        sa.Column("avg_power_w", sa.Float(), nullable=True),
        sa.Column("elevation_gain_m", sa.Float(), nullable=True),
        sa.Column("elevation_loss_m", sa.Float(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("avg_temperature_c", sa.Float(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["athlete_activities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("activity_id", "lap_index", name="uq_activity_detail_lap_index"),
    )
    op.create_index(op.f("ix_activity_detail_laps_activity_id"), "activity_detail_laps", ["activity_id"], unique=False)
    op.create_index(op.f("ix_activity_detail_laps_id"), "activity_detail_laps", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_detail_laps_id"), table_name="activity_detail_laps")
    op.drop_index(op.f("ix_activity_detail_laps_activity_id"), table_name="activity_detail_laps")
    op.drop_table("activity_detail_laps")
    op.drop_index(op.f("ix_activity_detail_samples_timestamp"), table_name="activity_detail_samples")
    op.drop_index(op.f("ix_activity_detail_samples_id"), table_name="activity_detail_samples")
    op.drop_index(op.f("ix_activity_detail_samples_activity_id"), table_name="activity_detail_samples")
    op.drop_table("activity_detail_samples")
    op.drop_index(op.f("ix_activity_detail_exports_provider_activity_id"), table_name="activity_detail_exports")
    op.drop_index(op.f("ix_activity_detail_exports_provider"), table_name="activity_detail_exports")
    op.drop_index(op.f("ix_activity_detail_exports_id"), table_name="activity_detail_exports")
    op.drop_index(op.f("ix_activity_detail_exports_downloaded_at"), table_name="activity_detail_exports")
    op.drop_index(op.f("ix_activity_detail_exports_athlete_id"), table_name="activity_detail_exports")
    op.drop_index(op.f("ix_activity_detail_exports_activity_id"), table_name="activity_detail_exports")
    op.drop_table("activity_detail_exports")
