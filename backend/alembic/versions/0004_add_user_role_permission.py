"""add user, role, permission

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def upgrade() -> None:
    # permission
    op.create_table(
        "permission",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource", sa.String(length=100), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # role
    op.create_table(
        "role",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organization.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id", "name", name="uq_role_org_name"),
    )
    op.create_index("ix_role_org_id", "role", ["org_id"], unique=False)

    # role_permission
    op.create_table(
        "role_permission",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permission.id"], ondelete="CASCADE"),
    )

    # user
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_2fa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organization.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("org_id", "email", name="uq_user_org_email"),
    )
    op.create_index("ix_user_org_id", "user", ["org_id"], unique=False)
    op.create_index("ix_user_role_id", "user", ["role_id"], unique=False)

    # Seed roles
    roles = [
        ("Admin", "System administrator with full access"),
        ("Owner", "Property owner"),
        ("Manager", "Property manager"),
        ("Partner", "Business partner"),
        ("Guest", "Guest user"),
    ]
    role_ids = [str(uuid.uuid4()) for _ in roles]
    for i, (name, desc) in enumerate(roles):
        op.execute(
            sa.text(
                "INSERT INTO role (id, org_id, name, description) VALUES (:id, :org_id, :name, :description)"
            ).bindparams(
                id=uuid.UUID(role_ids[i]),
                org_id=DEFAULT_ORG_ID,
                name=name,
                description=desc,
            )
        )

    # Seed base permissions
    permissions = [
        ("property:read", "Read properties", "property", "read"),
        ("property:write", "Write properties", "property", "write"),
        ("room_type:read", "Read room types", "room_type", "read"),
        ("room_type:write", "Write room types", "room_type", "write"),
        ("user:read", "Read users", "user", "read"),
        ("user:write", "Write users", "user", "write"),
    ]
    perm_ids = [str(uuid.uuid4()) for _ in permissions]
    for i, (name, desc, resource, action) in enumerate(permissions):
        op.execute(
            sa.text(
                "INSERT INTO permission (id, name, description, resource, action) VALUES (:id, :name, :description, :resource, :action)"
            ).bindparams(
                id=uuid.UUID(perm_ids[i]),
                name=name,
                description=desc,
                resource=resource,
                action=action,
            )
        )

    # Link Admin role to all permissions
    for perm_id in perm_ids:
        op.execute(
            sa.text(
                "INSERT INTO role_permission (role_id, permission_id) VALUES (:role_id, :perm_id)"
            ).bindparams(
                role_id=uuid.UUID(role_ids[0]),  # Admin
                perm_id=uuid.UUID(perm_id),
            )
        )


def downgrade() -> None:
    op.drop_index("ix_user_role_id", table_name="user")
    op.drop_index("ix_user_org_id", table_name="user")
    op.drop_table("user")
    op.drop_table("role_permission")
    op.drop_index("ix_role_org_id", table_name="role")
    op.drop_table("role")
    op.drop_table("permission")
