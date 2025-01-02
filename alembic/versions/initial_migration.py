"""initial migration

Revision ID: initial
Revises: 
Create Date: 2025-01-01 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('recording_sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_name', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('audio_format', sa.String(), nullable=True),
        sa.Column('microphone_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('speaker_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('s3_location', sa.String(), nullable=True),
        sa.Column('analysis_output', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('session_id')
    )

def downgrade() -> None:
    op.drop_table('recording_sessions')
