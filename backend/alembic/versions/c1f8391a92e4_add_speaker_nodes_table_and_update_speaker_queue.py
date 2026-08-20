"""add speaker_nodes table and update speaker_queue

Revision ID: c1f8391a92e4
Revises: 0f87936842f8
Create Date: 2026-08-20 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f8391a92e4'
down_revision: Union[str, None] = '0f87936842f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create speaker_nodes table
    op.create_table(
        'speaker_nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('mac_address', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('zone', sa.String(length=50), nullable=False, server_default='College-Wide'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='OFFLINE'),
        sa.Column('volume', sa.Integer(), nullable=False, server_default='80'),
        sa.Column('cpu_usage', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('memory_usage', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('disk_space', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_speaker_nodes_id'), 'speaker_nodes', ['id'], unique=False)
    op.create_index(op.f('ix_speaker_nodes_mac_address'), 'speaker_nodes', ['mac_address'], unique=True)

    # Add columns to speaker_queue
    with op.batch_alter_table('speaker_queue') as batch_op:
        batch_op.add_column(sa.Column('speaker_node_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('duration_seconds', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('failure_reason', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.create_foreign_key('fk_speaker_queue_speaker_node_id', 'speaker_nodes', ['speaker_node_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('speaker_queue') as batch_op:
        batch_op.drop_constraint('fk_speaker_queue_speaker_node_id', type_='foreignkey')
        batch_op.drop_column('error_count')
        batch_op.drop_column('failure_reason')
        batch_op.drop_column('duration_seconds')
        batch_op.drop_column('speaker_node_id')

    op.drop_index(op.f('ix_speaker_nodes_mac_address'), table_name='speaker_nodes')
    op.drop_index(op.f('ix_speaker_nodes_id'), table_name='speaker_nodes')
    op.drop_table('speaker_nodes')
