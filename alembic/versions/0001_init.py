from alembic import op
import sqlalchemy as sa

revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('participants',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(320)),
        sa.Column('tz', sa.String(64), nullable=False),
        sa.Column('consent_version', sa.String(32), nullable=False),
        sa.Column('strava_athlete_id', sa.BigInteger, unique=True),
        sa.Column('strava_access_token', sa.String(512)),
        sa.Column('strava_refresh_token', sa.String(512)),
        sa.Column('strava_token_expires_at', sa.Integer),
        sa.Column('revoked_at', sa.DateTime),
    )

    op.create_table('activities',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('source', sa.String(32), nullable=False),
        sa.Column('athlete_id', sa.Integer, sa.ForeignKey('participants.id'), nullable=False),
        sa.Column('strava_activity_id', sa.BigInteger, nullable=False),
        sa.Column('start_date_local', sa.DateTime, nullable=False),
        sa.Column('distance_m', sa.Float, nullable=False),
        sa.Column('moving_time_s', sa.Integer, nullable=False),
        sa.Column('sport_type', sa.String(64), nullable=False),
        sa.Column('trainer', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_virtual', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_ebike', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('flagged', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('raw_json', sa.Text),
        sa.UniqueConstraint('source', 'strava_activity_id', name='uq_source_activity')
    )
    op.create_index('idx_activities_date', 'activities', ['start_date_local'])

    op.create_table('daily_rollups',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('athlete_id', sa.Integer, sa.ForeignKey('participants.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('km_total', sa.Float, nullable=False, server_default='0'),
        sa.Column('km_outdoor', sa.Float, nullable=False, server_default='0'),
        sa.Column('km_indoor', sa.Float, nullable=False, server_default='0'),
        sa.Column('met_25km', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('first_start_time_local', sa.DateTime),
        sa.Column('early_bird', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('night_owl', sa.Boolean, nullable=False, server_default='false'),
        sa.UniqueConstraint('athlete_id', 'date', name='uq_rollup_day')
    )

    op.create_table('awards',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('category', sa.String(64), nullable=False),
        sa.Column('athlete_id', sa.Integer, sa.ForeignKey('participants.id'), nullable=False),
        sa.Column('value_num', sa.Float, nullable=False)
    )

    op.create_table('points',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('athlete_id', sa.Integer, sa.ForeignKey('participants.id'), nullable=False),
        sa.Column('daily_points', sa.Integer, nullable=False, server_default='0'),
        sa.Column('cumulative_points', sa.Integer, nullable=False, server_default='0')
    )

def downgrade():
    op.drop_table('points')
    op.drop_table('awards')
    op.drop_table('daily_rollups')
    op.drop_index('idx_activities_date', table_name='activities')
    op.drop_table('activities')
    op.drop_table('participants')
