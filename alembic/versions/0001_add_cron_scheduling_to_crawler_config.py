"""add_cron_scheduling_to_crawler_config

Revision ID: 0001
Revises: 
Create Date: 2026-02-05 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cron scheduling columns to crawler_configs table"""
    # Add new columns
    op.add_column('crawler_configs', sa.Column('cron_expression', sa.String(length=50), nullable=True))
    op.add_column('crawler_configs', sa.Column('timezone', sa.String(length=50), nullable=True, default='UTC'))
    op.add_column('crawler_configs', sa.Column('last_scheduled_at', sa.DateTime(), nullable=True))
    
    # Set default timezone for existing records
    op.execute("UPDATE crawler_configs SET timezone = 'UTC' WHERE timezone IS NULL")
    
    # Convert existing frequency values to cron expressions
    op.execute("""
        UPDATE crawler_configs 
        SET cron_expression = CASE 
            WHEN frequency = 'hourly' THEN '0 * * * *'
            WHEN frequency = 'daily' THEN '0 2 * * *'  
            WHEN frequency = 'weekly' THEN '0 2 * * 0'
            ELSE '0 2 * * *'
        END
        WHERE frequency IS NOT NULL
    """)


def downgrade() -> None:
    """Remove cron scheduling columns"""
    op.drop_column('crawler_configs', 'last_scheduled_at')
    op.drop_column('crawler_configs', 'timezone')
    op.drop_column('crawler_configs', 'cron_expression')