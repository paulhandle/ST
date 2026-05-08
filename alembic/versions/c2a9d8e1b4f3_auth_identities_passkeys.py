"""account aliases and passkeys

Revision ID: c2a9d8e1b4f3
Revises: b9c2e41a6f0d
Create Date: 2026-05-07 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2a9d8e1b4f3"
down_revision: Union[str, Sequence[str], None] = "b9c2e41a6f0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("phone", existing_type=sa.String(length=20), nullable=True)

    op.create_table(
        "account_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.Enum("PHONE", "EMAIL", "GOOGLE", "PASSKEY", name="authprovider"), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=160), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_account_alias_provider_subject"),
    )
    op.create_index(op.f("ix_account_aliases_email"), "account_aliases", ["email"], unique=False)
    op.create_index(op.f("ix_account_aliases_id"), "account_aliases", ["id"], unique=False)
    op.create_index(op.f("ix_account_aliases_provider"), "account_aliases", ["provider"], unique=False)
    op.create_index(op.f("ix_account_aliases_provider_subject"), "account_aliases", ["provider_subject"], unique=False)
    op.create_index(op.f("ix_account_aliases_user_id"), "account_aliases", ["user_id"], unique=False)

    op.create_table(
        "webauthn_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.String(length=512), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False),
        sa.Column("transports_json", sa.Text(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webauthn_credentials_credential_id"), "webauthn_credentials", ["credential_id"], unique=True)
    op.create_index(op.f("ix_webauthn_credentials_id"), "webauthn_credentials", ["id"], unique=False)
    op.create_index(op.f("ix_webauthn_credentials_user_id"), "webauthn_credentials", ["user_id"], unique=False)

    op.create_table(
        "auth_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.Enum("OTP_SEND", "OTP_VERIFY_FAIL", "PASSKEY_REGISTER", "PASSKEY_LOGIN", name="authchallengepurpose"), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("challenge", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("consumed", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_challenges_id"), "auth_challenges", ["id"], unique=False)
    op.create_index(op.f("ix_auth_challenges_ip_address"), "auth_challenges", ["ip_address"], unique=False)
    op.create_index(op.f("ix_auth_challenges_purpose"), "auth_challenges", ["purpose"], unique=False)
    op.create_index(op.f("ix_auth_challenges_subject"), "auth_challenges", ["subject"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_challenges_subject"), table_name="auth_challenges")
    op.drop_index(op.f("ix_auth_challenges_purpose"), table_name="auth_challenges")
    op.drop_index(op.f("ix_auth_challenges_ip_address"), table_name="auth_challenges")
    op.drop_index(op.f("ix_auth_challenges_id"), table_name="auth_challenges")
    op.drop_table("auth_challenges")
    op.drop_index(op.f("ix_webauthn_credentials_user_id"), table_name="webauthn_credentials")
    op.drop_index(op.f("ix_webauthn_credentials_id"), table_name="webauthn_credentials")
    op.drop_index(op.f("ix_webauthn_credentials_credential_id"), table_name="webauthn_credentials")
    op.drop_table("webauthn_credentials")
    op.drop_index(op.f("ix_account_aliases_user_id"), table_name="account_aliases")
    op.drop_index(op.f("ix_account_aliases_provider_subject"), table_name="account_aliases")
    op.drop_index(op.f("ix_account_aliases_provider"), table_name="account_aliases")
    op.drop_index(op.f("ix_account_aliases_id"), table_name="account_aliases")
    op.drop_index(op.f("ix_account_aliases_email"), table_name="account_aliases")
    op.drop_table("account_aliases")
    with op.batch_alter_table("users") as batch:
        batch.alter_column("phone", existing_type=sa.String(length=20), nullable=False)
