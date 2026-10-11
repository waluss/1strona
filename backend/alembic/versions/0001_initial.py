"""Initial baseline migration

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_tenant_id'), 'users', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.create_table(
        'contractor_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='candidate'),
        sa.Column('competencies', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('exclusions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('regions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('cpv_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('scoring_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contractor_profiles_tenant_id'), 'contractor_profiles', ['tenant_id'], unique=False)

    op.create_table(
        'tenders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_system', sa.String(length=50), nullable=False),
        sa.Column('source_proceeding_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('buyer_name', sa.String(length=500), nullable=True),
        sa.Column('buyer_nip', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('submission_deadline_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('location_voivodeship', sa.String(length=100), nullable=True),
        sa.Column('cpv_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('estimated_value_net', sa.Float(), nullable=True),
        sa.Column('raw_notice', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('current_notice_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requires_scoring', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('view_version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_system', 'source_proceeding_id', name='uq_tender_source_system_proceeding')
    )
    op.create_index(op.f('ix_tenders_source_proceeding_id'), 'tenders', ['source_proceeding_id'], unique=False)
    op.create_index(op.f('ix_tenders_source_published_at'), 'tenders', ['source_published_at'], unique=False)
    op.create_index(op.f('ix_tenders_source_system'), 'tenders', ['source_system'], unique=False)
    op.create_index(op.f('ix_tenders_submission_deadline_at'), 'tenders', ['submission_deadline_at'], unique=False)
    op.create_index(op.f('ix_tenders_tenant_id'), 'tenders', ['tenant_id'], unique=False)

    op.create_table(
        'tender_notices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_system', sa.String(length=50), nullable=False),
        sa.Column('notice_id', sa.String(length=255), nullable=False),
        sa.Column('notice_number', sa.String(length=255), nullable=True),
        sa.Column('notice_kind', sa.String(length=100), nullable=True),
        sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_delta', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('needs_review', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('review_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_system', 'notice_id', name='uq_notice_source_system_notice_id')
    )
    op.create_index(op.f('ix_tender_notices_notice_id'), 'tender_notices', ['notice_id'], unique=False)
    op.create_index(op.f('ix_tender_notices_published_at'), 'tender_notices', ['published_at'], unique=False)
    op.create_index(op.f('ix_tender_notices_source_system'), 'tender_notices', ['source_system'], unique=False)
    op.create_index(op.f('ix_tender_notices_tender_id'), 'tender_notices', ['tender_id'], unique=False)

    op.create_table(
        'tender_notice_revisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tender_notice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('previous_payload_hash', sa.String(length=64), nullable=False),
        sa.Column('previous_raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['tender_notice_id'], ['tender_notices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tender_notice_revisions_tender_notice_id'), 'tender_notice_revisions', ['tender_notice_id'], unique=False)

    op.create_table(
        'tender_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contractor_profile_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scoring_version', sa.String(length=50), nullable=False, server_default='1.0'),
        sa.ForeignKeyConstraint(['contractor_profile_id'], ['contractor_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tender_id'], ['tenders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tender_scores_contractor_profile_id'), 'tender_scores', ['contractor_profile_id'], unique=False)
    op.create_index(op.f('ix_tender_scores_tender_id'), 'tender_scores', ['tender_id'], unique=False)

    op.create_table(
        'import_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_system', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('statistics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_import_runs_tenant_id'), 'import_runs', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_table('import_runs')
    op.drop_table('tender_scores')
    op.drop_table('tender_notice_revisions')
    op.drop_table('tender_notices')
    op.drop_table('tenders')
    op.drop_table('contractor_profiles')
    op.drop_table('users')
    op.drop_table('tenants')
