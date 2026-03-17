"""Unit tests for approval policy service."""

import importlib

import pytest

_policy_service = importlib.import_module("src.services.approval-policy-service")


@pytest.mark.unit
async def test_create_chain_policy(db_with_users_and_roles):
    data = db_with_users_and_roles
    result = await _policy_service.create_policy(
        workspace_id=data["workspace_id"],
        name="Legal Review",
        policy_type="chain",
        config={"steps": [{"role": "reviewer", "label": "L1"}, {"role": "approver", "label": "Final"}]},
    )
    assert result["name"] == "Legal Review"
    assert result["policy_type"] == "chain"
    assert len(result["config"]["steps"]) == 2


@pytest.mark.unit
async def test_create_quorum_policy(db_with_users_and_roles):
    data = db_with_users_and_roles
    result = await _policy_service.create_policy(
        workspace_id=data["workspace_id"],
        name="Peer Review",
        policy_type="quorum",
        config={"required": 2, "pool_size": 3, "pool_role": "reviewer"},
        deadline_hours=48,
    )
    assert result["policy_type"] == "quorum"
    assert result["config"]["required"] == 2
    assert result["deadline_hours"] == 48


@pytest.mark.unit
async def test_create_policy_invalid_chain_config(db_with_users_and_roles):
    data = db_with_users_and_roles
    with pytest.raises(ValueError, match="steps"):
        await _policy_service.create_policy(
            workspace_id=data["workspace_id"],
            name="Bad Chain",
            policy_type="chain",
            config={"steps": []},
        )


@pytest.mark.unit
async def test_create_policy_invalid_quorum_config(db_with_users_and_roles):
    data = db_with_users_and_roles
    with pytest.raises(ValueError, match="required"):
        await _policy_service.create_policy(
            workspace_id=data["workspace_id"],
            name="Bad Quorum",
            policy_type="quorum",
            config={"required": 0, "pool_size": 3, "pool_role": "reviewer"},
        )


@pytest.mark.unit
async def test_create_policy_quorum_pool_too_small(db_with_users_and_roles):
    data = db_with_users_and_roles
    with pytest.raises(ValueError, match="pool_size"):
        await _policy_service.create_policy(
            workspace_id=data["workspace_id"],
            name="Small Pool",
            policy_type="quorum",
            config={"required": 3, "pool_size": 2, "pool_role": "reviewer"},
        )


@pytest.mark.unit
async def test_list_policies(db_with_users_and_roles):
    data = db_with_users_and_roles
    await _policy_service.create_policy(
        workspace_id=data["workspace_id"], name="P1",
        policy_type="chain",
        config={"steps": [{"role": "reviewer", "label": "R"}]},
    )
    policies = await _policy_service.list_policies(data["workspace_id"])
    assert len(policies) >= 1
    assert any(p["name"] == "P1" for p in policies)


@pytest.mark.unit
async def test_get_policy(db_with_users_and_roles):
    data = db_with_users_and_roles
    created = await _policy_service.create_policy(
        workspace_id=data["workspace_id"], name="Get Me",
        policy_type="chain",
        config={"steps": [{"role": "reviewer", "label": "R"}]},
    )
    fetched = await _policy_service.get_policy(created["id"], data["workspace_id"])
    assert fetched is not None
    assert fetched["name"] == "Get Me"


@pytest.mark.unit
async def test_get_policy_wrong_workspace(db_with_users_and_roles):
    data = db_with_users_and_roles
    created = await _policy_service.create_policy(
        workspace_id=data["workspace_id"], name="Wrong WS",
        policy_type="chain",
        config={"steps": [{"role": "reviewer", "label": "R"}]},
    )
    fetched = await _policy_service.get_policy(created["id"], "other-workspace")
    assert fetched is None


@pytest.mark.unit
async def test_delete_policy_soft_deletes(db_with_users_and_roles):
    data = db_with_users_and_roles
    created = await _policy_service.create_policy(
        workspace_id=data["workspace_id"], name="Delete Me",
        policy_type="chain",
        config={"steps": [{"role": "reviewer", "label": "R"}]},
    )
    deleted = await _policy_service.delete_policy(created["id"], data["workspace_id"])
    assert deleted is True
    # Should not appear in list (soft deleted)
    fetched = await _policy_service.get_policy(created["id"], data["workspace_id"])
    assert fetched is None


@pytest.mark.unit
async def test_update_policy(db_with_users_and_roles):
    data = db_with_users_and_roles
    created = await _policy_service.create_policy(
        workspace_id=data["workspace_id"], name="Update Me",
        policy_type="chain",
        config={"steps": [{"role": "reviewer", "label": "R"}]},
    )
    updated = await _policy_service.update_policy(
        created["id"], data["workspace_id"], name="Updated Name"
    )
    assert updated["name"] == "Updated Name"
