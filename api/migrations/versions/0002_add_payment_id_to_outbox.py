"""add payment_id, drop payload and published_at from outbox

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outbox",
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_outbox_payment_id", "outbox", ["payment_id"])
    op.drop_column("outbox", "payload")
    op.drop_column("outbox", "published_at")


def downgrade() -> None:
    op.add_column(
        "outbox",
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.add_column(
        "outbox",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_index("ix_outbox_payment_id", table_name="outbox")
    op.drop_column("outbox", "payment_id")