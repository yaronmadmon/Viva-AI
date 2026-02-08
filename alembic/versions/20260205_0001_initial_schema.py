"""Initial schema - RAMP Phase 1A

Revision ID: 0001
Revises: 
Create Date: 2026-02-05

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
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, default='student'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mastery_tier', sa.Integer(), nullable=False, default=0),
        sa.Column('ai_disclosure_level', sa.Integer(), nullable=False, default=0),
        sa.Column('total_words_written', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Refresh tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), nullable=False, index=True),
        sa.Column('token_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Research projects table
    op.create_table(
        'research_projects',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('discipline_type', sa.String(50), nullable=False, default='mixed'),
        sa.Column('status', sa.String(50), nullable=False, default='draft'),
        sa.Column('owner_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('integrity_score', sa.Float(), nullable=False, default=100.0),
        sa.Column('export_blocked', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Project shares table
    op.create_table(
        'project_shares',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('research_projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('permission_level', sa.String(50), nullable=False, default='view'),
        sa.Column('invited_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('research_projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('parent_id', sa.Uuid(), sa.ForeignKey('artifacts.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('position', sa.Integer(), nullable=False, default=0),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False, default=''),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('contribution_category', sa.String(50), nullable=False, default='primarily_human'),
        sa.Column('ai_modification_ratio', sa.Float(), nullable=False, default=1.0),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_artifacts_project_parent', 'artifacts', ['project_id', 'parent_id'])
    op.create_index('ix_artifacts_project_type', 'artifacts', ['project_id', 'artifact_type'])
    
    # Artifact versions table
    op.create_table(
        'artifact_versions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('artifact_id', sa.Uuid(), sa.ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('created_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('contribution_category', sa.String(50), nullable=False, default='primarily_human'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_artifact_versions_artifact_version', 'artifact_versions', ['artifact_id', 'version_number'], unique=True)
    
    # Artifact links table
    op.create_table(
        'artifact_links',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('source_artifact_id', sa.Uuid(), sa.ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('target_artifact_id', sa.Uuid(), sa.ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('link_type', sa.String(50), nullable=False),
        sa.Column('strength', sa.Float(), nullable=False, default=1.0),
        sa.Column('created_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('annotation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_artifact_links_source_target', 'artifact_links', ['source_artifact_id', 'target_artifact_id'])
    
    # Comment threads table
    op.create_table(
        'comment_threads',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('artifact_id', sa.Uuid(), sa.ForeignKey('artifacts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Comments table
    op.create_table(
        'comments',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('thread_id', sa.Uuid(), sa.ForeignKey('comment_threads.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('author_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    
    # Event logs table (append-only)
    op.create_table(
        'event_logs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.Uuid(), nullable=False, index=True),
        sa.Column('user_id', sa.Uuid(), nullable=True, index=True),
        sa.Column('payload', sa.JSON(), nullable=False, default={}),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )
    op.create_index('ix_event_logs_entity', 'event_logs', ['entity_type', 'entity_id'])
    op.create_index('ix_event_logs_user_time', 'event_logs', ['user_id', 'created_at'])
    op.create_index('ix_event_logs_type_time', 'event_logs', ['event_type', 'created_at'])
    
    # Permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.Uuid(), nullable=False),
        sa.Column('level', sa.String(50), nullable=False),
        sa.Column('granted_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, default=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_permissions_user_resource', 'permissions', ['user_id', 'resource_type', 'resource_id'])
    op.create_index('ix_permissions_resource', 'permissions', ['resource_type', 'resource_id'])


def downgrade() -> None:
    op.drop_table('permissions')
    op.drop_table('event_logs')
    op.drop_table('comments')
    op.drop_table('comment_threads')
    op.drop_table('artifact_links')
    op.drop_table('artifact_versions')
    op.drop_table('artifacts')
    op.drop_table('project_shares')
    op.drop_table('research_projects')
    op.drop_table('refresh_tokens')
    op.drop_table('users')
