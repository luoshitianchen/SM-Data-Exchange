"""新增业务表：数据交换伙伴、协议与任务。

Revision ID: 0002_business_tables
Revises: 0001_initial
Create Date: 2026-09-23
"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# 本迁移的版本号，下游 0003 及以后迁移以此为 down_revision
revision: str = '0002_business_tables'
# 上一版本，承接 0001_initial
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Alembic 自动生成开始，按模型元数据建立业务表 ###
    # 数据交换伙伴表：记录外部对接方信息
    op.create_table('exchange_partners',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('partner_type', sa.String(length=16), nullable=False),
    sa.Column('endpoint', sa.String(length=512), nullable=False),
    sa.Column('auth_type', sa.String(length=16), nullable=False),
    sa.Column('contact_email', sa.String(length=256), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exchange_partners_code'), 'exchange_partners', ['code'], unique=True)
    op.create_index(op.f('ix_exchange_partners_partner_type'), 'exchange_partners', ['partner_type'], unique=False)
    op.create_index(op.f('ix_exchange_partners_status'), 'exchange_partners', ['status'], unique=False)
    # 数据交换协议表：描述与伙伴之间的对接协议配置
    op.create_table('exchange_protocols',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('protocol_type', sa.String(length=16), nullable=False),
    sa.Column('partner_id', sa.String(length=64), nullable=True),
    sa.Column('config', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exchange_protocols_code'), 'exchange_protocols', ['code'], unique=True)
    op.create_index(op.f('ix_exchange_protocols_partner_id'), 'exchange_protocols', ['partner_id'], unique=False)
    op.create_index(op.f('ix_exchange_protocols_protocol_type'), 'exchange_protocols', ['protocol_type'], unique=False)
    op.create_index(op.f('ix_exchange_protocols_status'), 'exchange_protocols', ['status'], unique=False)
    # 数据交换任务表：调度并记录每次数据交换执行
    op.create_table('exchange_tasks',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('partner_id', sa.String(length=64), nullable=False),
    sa.Column('protocol_id', sa.String(length=64), nullable=False),
    sa.Column('direction', sa.String(length=16), nullable=False),
    sa.Column('schedule_cron', sa.String(length=128), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('stats', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exchange_tasks_code'), 'exchange_tasks', ['code'], unique=True)
    op.create_index(op.f('ix_exchange_tasks_direction'), 'exchange_tasks', ['direction'], unique=False)
    op.create_index(op.f('ix_exchange_tasks_partner_id'), 'exchange_tasks', ['partner_id'], unique=False)
    op.create_index(op.f('ix_exchange_tasks_protocol_id'), 'exchange_tasks', ['protocol_id'], unique=False)
    op.create_index(op.f('ix_exchange_tasks_status'), 'exchange_tasks', ['status'], unique=False)
    # ### Alembic 自动生成结束 ###


def downgrade() -> None:
    # ### Alembic 自动生成开始，按逆序删除业务表与索引 ###
    op.drop_index(op.f('ix_exchange_tasks_status'), table_name='exchange_tasks')
    op.drop_index(op.f('ix_exchange_tasks_protocol_id'), table_name='exchange_tasks')
    op.drop_index(op.f('ix_exchange_tasks_partner_id'), table_name='exchange_tasks')
    op.drop_index(op.f('ix_exchange_tasks_direction'), table_name='exchange_tasks')
    op.drop_index(op.f('ix_exchange_tasks_code'), table_name='exchange_tasks')
    op.drop_table('exchange_tasks')
    op.drop_index(op.f('ix_exchange_protocols_status'), table_name='exchange_protocols')
    op.drop_index(op.f('ix_exchange_protocols_protocol_type'), table_name='exchange_protocols')
    op.drop_index(op.f('ix_exchange_protocols_partner_id'), table_name='exchange_protocols')
    op.drop_index(op.f('ix_exchange_protocols_code'), table_name='exchange_protocols')
    op.drop_table('exchange_protocols')
    op.drop_index(op.f('ix_exchange_partners_status'), table_name='exchange_partners')
    op.drop_index(op.f('ix_exchange_partners_partner_type'), table_name='exchange_partners')
    op.drop_index(op.f('ix_exchange_partners_code'), table_name='exchange_partners')
    op.drop_table('exchange_partners')
    # ### Alembic 自动生成结束 ###
