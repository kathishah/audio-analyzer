"""rename session_id to recording_session_id

Revision ID: rename_session_id_001
Revises: update_fields_001
Create Date: 2025-01-03 16:42:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'rename_session_id_001'
down_revision = 'update_fields_001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column('recording_sessions', 'session_id',
                    new_column_name='recording_session_id')

def downgrade() -> None:
    op.alter_column('recording_sessions', 'recording_session_id',
                    new_column_name='session_id')
