"""Initial local research storage, compatible with pre-migration prototype tables."""
from alembic import op
import sqlalchemy as sa

revision='0001'
down_revision=None
branch_labels=None
depends_on=None


def upgrade():
    existing=set(sa.inspect(op.get_bind()).get_table_names())
    definitions={
        'snapshots':[sa.Column('id',sa.String(),primary_key=True),sa.Column('kind',sa.String(),nullable=False),sa.Column('mode',sa.String(),nullable=False),sa.Column('symbol',sa.String(),nullable=False),sa.Column('payload',sa.JSON(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False)],
        'watchlist':[sa.Column('id',sa.String(),primary_key=True),sa.Column('mode',sa.String(),nullable=False),sa.Column('symbol',sa.String(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('mode','symbol')],
        'prompts':[sa.Column('id',sa.String(),primary_key=True),sa.Column('kind',sa.String(),nullable=False),sa.Column('version',sa.Integer(),nullable=False),sa.Column('content',sa.Text(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint('kind','version')],
        'jobs':[sa.Column('id',sa.String(),primary_key=True),sa.Column('kind',sa.String(),nullable=False),sa.Column('mode',sa.String(),nullable=False),sa.Column('symbol',sa.String(),nullable=False),sa.Column('idempotency_key',sa.String(),nullable=False,unique=True),sa.Column('status',sa.String(),nullable=False),sa.Column('step',sa.String(),nullable=False),sa.Column('payload',sa.JSON(),nullable=False),sa.Column('result',sa.JSON(),nullable=True),sa.Column('error',sa.JSON(),nullable=True),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False)],
        'cache_epochs':[sa.Column('mode',sa.String(),primary_key=True),sa.Column('invalidated_at',sa.DateTime(timezone=True),nullable=False)],
    }
    for table,columns in definitions.items():
        if table not in existing: op.create_table(table,*columns)
    indexes={'snapshots':['kind','mode','symbol'],'prompts':['kind'],'jobs':['status']}
    inspector=sa.inspect(op.get_bind())
    for table,columns in indexes.items():
        names={i['name'] for i in inspector.get_indexes(table)}
        for column in columns:
            name=f'ix_{table}_{column}'
            if name not in names: op.create_index(name,table,[column])


def downgrade():
    raise RuntimeError('Initial storage downgrade is intentionally unsupported; restore an explicit database backup instead.')
