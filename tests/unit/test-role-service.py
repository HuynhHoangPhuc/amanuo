"""Unit tests for role assignment service."""

import importlib
import uuid

import pytest

_role_service = importlib.import_module("src.services.role-service")


@pytest.mark.unit
async def test_assign_role_creates_record(db_with_users_and_roles):
    data = db_with_users_and_roles
    result = await _role_service.assign_role(
        data["reviewer_ids"][0], data["workspace_id"], "member"
    )
    assert result["status"] == "assigned"


@pytest.mark.unit
async def test_assign_role_idempotent(db_with_users_and_roles):
    data = db_with_users_and_roles
    uid = data["reviewer_ids"][0]
    # Reviewer already has 'reviewer' role from fixture
    result = await _role_service.assign_role(uid, data["workspace_id"], "reviewer")
    assert result["status"] == "already_assigned"


@pytest.mark.unit
async def test_assign_role_invalid_role(db_with_users_and_roles):
    data = db_with_users_and_roles
    with pytest.raises(ValueError, match="Invalid role"):
        await _role_service.assign_role(
            data["admin_id"], data["workspace_id"], "superadmin"
        )


@pytest.mark.unit
async def test_remove_role(db_with_users_and_roles):
    data = db_with_users_and_roles
    uid = data["reviewer_ids"][0]
    removed = await _role_service.remove_role(uid, data["workspace_id"], "reviewer")
    assert removed is True


@pytest.mark.unit
async def test_remove_role_nonexistent(db_with_users_and_roles):
    data = db_with_users_and_roles
    removed = await _role_service.remove_role(
        data["admin_id"], data["workspace_id"], "viewer"
    )
    assert removed is False


@pytest.mark.unit
async def test_get_user_roles(db_with_users_and_roles):
    data = db_with_users_and_roles
    roles = await _role_service.get_user_roles(
        data["reviewer_ids"][0], data["workspace_id"]
    )
    assert "reviewer" in roles


@pytest.mark.unit
async def test_has_role_true(db_with_users_and_roles):
    data = db_with_users_and_roles
    assert await _role_service.has_role(
        data["admin_id"], data["workspace_id"], "admin"
    ) is True


@pytest.mark.unit
async def test_has_role_false(db_with_users_and_roles):
    data = db_with_users_and_roles
    assert await _role_service.has_role(
        data["admin_id"], data["workspace_id"], "viewer"
    ) is False


@pytest.mark.unit
async def test_check_permission_admin_passes_all(db_with_users_and_roles):
    data = db_with_users_and_roles
    assert await _role_service.check_permission(
        data["admin_id"], data["workspace_id"], ["reviewer"]
    ) is True


@pytest.mark.unit
async def test_check_permission_reviewer_passes_reviewer(db_with_users_and_roles):
    data = db_with_users_and_roles
    assert await _role_service.check_permission(
        data["reviewer_ids"][0], data["workspace_id"], ["reviewer"]
    ) is True


@pytest.mark.unit
async def test_check_permission_reviewer_fails_admin(db_with_users_and_roles):
    data = db_with_users_and_roles
    assert await _role_service.check_permission(
        data["reviewer_ids"][0], data["workspace_id"], ["admin"]
    ) is False


@pytest.mark.unit
async def test_list_workspace_users(db_with_users_and_roles):
    data = db_with_users_and_roles
    users = await _role_service.list_workspace_users(data["workspace_id"])
    assert len(users) == 5  # admin + 3 reviewers + 1 approver
    emails = {u["email"] for u in users}
    assert "admin@test.com" in emails
    assert "approver@test.com" in emails
