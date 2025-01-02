"""update recording session fields

Revision ID: update_fields_001
Revises: initial
Create Date: 2025-01-01 18:50:00.000000

"""
from alembic import op
from sqlalchemy import Column, String, JSON, Text, Numeric
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_fields_001'
down_revision = 'initial'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Convert microphone_details and speaker_details from JSON to String
    op.alter_column('recording_sessions', 'microphone_details',
        type_=String(),
        postgresql_using='microphone_details::text',
        existing_type=postgresql.JSON(),
        existing_nullable=True
    )
    op.alter_column('recording_sessions', 'speaker_details',
        type_=String(),
        postgresql_using='speaker_details::text',
        existing_type=postgresql.JSON(),
        existing_nullable=True
    )
    
    # Convert analysis_output from Text to JSON
    op.alter_column('recording_sessions', 'analysis_output',
        type_=postgresql.JSON(),
        postgresql_using='analysis_output::json',
        existing_type=Text(),
        existing_nullable=True
    )
    
    # Add analysis_score column
    op.add_column('recording_sessions',
        Column('analysis_score', Numeric(precision=5, scale=2), nullable=True)
    )

def downgrade() -> None:
    # Convert microphone_details and speaker_details back to JSON
    op.alter_column('recording_sessions', 'microphone_details',
        type_=postgresql.JSON(),
        postgresql_using='microphone_details::json',
        existing_type=String(),
        existing_nullable=True
    )
    op.alter_column('recording_sessions', 'speaker_details',
        type_=postgresql.JSON(),
        postgresql_using='speaker_details::json',
        existing_type=String(),
        existing_nullable=True
    )
    
    # Convert analysis_output back to Text
    op.alter_column('recording_sessions', 'analysis_output',
        type_=Text(),
        postgresql_using='analysis_output::text',
        existing_type=postgresql.JSON(),
        existing_nullable=True
    )
    
    # Remove analysis_score column
    op.drop_column('recording_sessions', 'analysis_score')
