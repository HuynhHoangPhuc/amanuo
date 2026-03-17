"""SQLAlchemy ORM model for role assignments (RBAC)."""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class RoleAssignmentORM(Base):
    """Workspace-scoped role assignment for a user.

    Supported roles: viewer, member, reviewer, approver, admin.
    A user can hold multiple roles within the same workspace.
    """

    __tablename__ = "role_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", "role", name="uq_user_workspace_role"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    granted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


# Valid roles for validation
VALID_ROLES = ("viewer", "member", "reviewer", "approver", "admin")
