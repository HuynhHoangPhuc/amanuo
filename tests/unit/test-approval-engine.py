"""Unit tests for approval engine — chain, quorum, conflict detection, escalation."""

import importlib
import json
import uuid
from datetime import datetime

import pytest

from src.database import get_connection, get_db_path
from src.config import settings

_engine = importlib.import_module("src.services.approval-engine")
_policy_service = importlib.import_module("src.services.approval-policy-service")
_conflict = importlib.import_module("src.services.approval-engine-conflict")


async def _create_job(workspace_id: str, schema_id: str | None = None) -> str:
    """Helper: create a job in pending_review status."""
    job_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    db = await get_connection(get_db_path(settings.database_url))
    try:
        await db.execute(
            """INSERT INTO jobs (id, workspace_id, status, mode, schema_id, created_at)
               VALUES (?, ?, 'pending_review', 'auto', ?, ?)""",
            (job_id, workspace_id, schema_id, now),
        )
        await db.commit()
    finally:
        await db.close()
    return job_id


async def _create_chain_policy(workspace_id: str) -> dict:
    return await _policy_service.create_policy(
        workspace_id=workspace_id,
        name=f"chain-{uuid.uuid4().hex[:6]}",
        policy_type="chain",
        config={"steps": [
            {"role": "reviewer", "label": "Level 1"},
            {"role": "approver", "label": "Final Approval"},
        ]},
    )


async def _create_quorum_policy(workspace_id: str) -> dict:
    return await _policy_service.create_policy(
        workspace_id=workspace_id,
        name=f"quorum-{uuid.uuid4().hex[:6]}",
        policy_type="quorum",
        config={"required": 2, "pool_size": 3, "pool_role": "reviewer", "escalation_role": "approver"},
    )


# --- Chain Tests ---

class TestChainWorkflow:
    @pytest.mark.unit
    async def test_start_approval_creates_first_round(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_chain_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        result = await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        assert result["round_number"] == 1
        assert result["policy_type"] == "chain"

    @pytest.mark.unit
    async def test_submit_approved_advances_chain(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_chain_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        status = await _engine.get_review_status(job_id)
        round_id = status["assignments"][0]["id"] if status["assignments"] else None

        # Assign reviewer and submit
        assignments = await _engine.assign_reviewers(
            # Get round_id from DB
            (await _get_current_round_id(job_id)),
            [data["reviewer_ids"][0]],
        )
        result = await _engine.submit_review(
            assignments[0]["id"], data["reviewer_ids"][0], "approved"
        )
        assert result["action"] == "next_round"
        assert result["round_number"] == 2

    @pytest.mark.unit
    async def test_chain_rejected_stops(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_chain_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        round_id = await _get_current_round_id(job_id)
        assignments = await _engine.assign_reviewers(round_id, [data["reviewer_ids"][0]])

        result = await _engine.submit_review(
            assignments[0]["id"], data["reviewer_ids"][0], "rejected"
        )
        assert result["action"] == "chain_rejected"
        assert result["job_status"] == "rejected"

    @pytest.mark.unit
    async def test_chain_full_approval(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_chain_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        await _engine.start_approval(job_id, policy["id"], data["workspace_id"])

        # Round 1: reviewer approves
        round_id = await _get_current_round_id(job_id)
        a1 = await _engine.assign_reviewers(round_id, [data["reviewer_ids"][0]])
        await _engine.submit_review(a1[0]["id"], data["reviewer_ids"][0], "approved")

        # Round 2: approver approves
        round_id = await _get_current_round_id(job_id)
        a2 = await _engine.assign_reviewers(round_id, [data["approver_id"]])
        result = await _engine.submit_review(a2[0]["id"], data["approver_id"], "approved")
        assert result["action"] == "chain_completed"
        assert result["job_status"] == "approved"


# --- Quorum Tests ---

class TestQuorumWorkflow:
    @pytest.mark.unit
    async def test_start_quorum_creates_round(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_quorum_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        result = await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        assert result["round_number"] == 1
        assert result["policy_type"] == "quorum"

    @pytest.mark.unit
    async def test_quorum_approved_no_conflicts(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_quorum_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        round_id = await _get_current_round_id(job_id)
        assignments = await _engine.assign_reviewers(round_id, data["reviewer_ids"])

        # All 3 approve — no conflicts
        for a in assignments[:2]:
            await _engine.submit_review(a["id"], a["user_id"], "approved")

        result = await _engine.submit_review(
            assignments[2]["id"], assignments[2]["user_id"], "approved"
        )
        assert result["action"] == "quorum_approved"

    @pytest.mark.unit
    async def test_quorum_rejected(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_quorum_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        round_id = await _get_current_round_id(job_id)
        assignments = await _engine.assign_reviewers(round_id, data["reviewer_ids"])

        # All reject
        for a in assignments[:2]:
            await _engine.submit_review(a["id"], a["user_id"], "rejected")

        result = await _engine.submit_review(
            assignments[2]["id"], assignments[2]["user_id"], "rejected"
        )
        assert result["action"] == "quorum_rejected"


# --- Conflict Detection Tests ---

class TestConflictDetection:
    @pytest.mark.unit
    def test_detect_no_conflicts(self):
        """No conflicts when all corrected values match."""

        class FakeAssignment:
            def __init__(self, status, corrected_result):
                self.status = status
                self.corrected_result = corrected_result

        a1 = FakeAssignment("corrected", json.dumps([{"label": "name", "value": "John"}]))
        a2 = FakeAssignment("corrected", json.dumps([{"label": "name", "value": "John"}]))
        conflicts = _conflict.detect_conflicts([a1, a2])
        assert len(conflicts) == 0

    @pytest.mark.unit
    def test_detect_conflicts_different_values(self):
        class FakeAssignment:
            def __init__(self, status, corrected_result):
                self.status = status
                self.corrected_result = corrected_result

        a1 = FakeAssignment("corrected", json.dumps([{"label": "name", "value": "John"}]))
        a2 = FakeAssignment("corrected", json.dumps([{"label": "name", "value": "Jane"}]))
        conflicts = _conflict.detect_conflicts([a1, a2])
        assert "name" in conflicts
        assert len(conflicts["name"]) == 2

    @pytest.mark.unit
    def test_build_conflict_summary(self):
        conflicts = {"name": ["John", "Jane"], "age": ["25", "30"]}
        summary = _conflict.build_conflict_summary(conflicts)
        assert len(summary) == 2
        assert summary[0]["field"] == "age" or summary[0]["field"] == "name"


# --- Edge Case Tests ---

class TestEdgeCases:
    @pytest.mark.unit
    async def test_submit_review_wrong_user(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_chain_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        round_id = await _get_current_round_id(job_id)
        assignments = await _engine.assign_reviewers(round_id, [data["reviewer_ids"][0]])

        with pytest.raises(ValueError, match="not assigned"):
            await _engine.submit_review(
                assignments[0]["id"], data["reviewer_ids"][1], "approved"
            )

    @pytest.mark.unit
    async def test_submit_review_invalid_status(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_chain_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        round_id = await _get_current_round_id(job_id)
        assignments = await _engine.assign_reviewers(round_id, [data["reviewer_ids"][0]])

        with pytest.raises(ValueError, match="Status must be"):
            await _engine.submit_review(
                assignments[0]["id"], data["reviewer_ids"][0], "maybe"
            )

    @pytest.mark.unit
    async def test_double_submit_fails(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_chain_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        round_id = await _get_current_round_id(job_id)
        assignments = await _engine.assign_reviewers(round_id, [data["reviewer_ids"][0]])

        await _engine.submit_review(assignments[0]["id"], data["reviewer_ids"][0], "approved")

        with pytest.raises(ValueError, match="already completed"):
            await _engine.submit_review(
                assignments[0]["id"], data["reviewer_ids"][0], "approved"
            )


# --- Audit Log Tests ---

class TestAuditLog:
    @pytest.mark.unit
    async def test_audit_log_captures_actions(self, db_with_users_and_roles):
        data = db_with_users_and_roles
        policy = await _create_chain_policy(data["workspace_id"])
        job_id = await _create_job(data["workspace_id"])

        await _engine.start_approval(job_id, policy["id"], data["workspace_id"])
        log = await _engine.get_audit_log(job_id)
        assert len(log) >= 1
        assert log[0]["action"] == "approval.started"


# --- Helper ---

async def _get_current_round_id(job_id: str) -> str:
    """Get the latest round ID for a job."""
    from sqlalchemy import select
    from src.database import get_session_factory
    _round_model = importlib.import_module("src.models.review-round")

    async with get_session_factory()() as session:
        result = await session.execute(
            select(_round_model.ReviewRoundORM)
            .where(_round_model.ReviewRoundORM.job_id == job_id)
            .order_by(_round_model.ReviewRoundORM.round_number.desc())
            .limit(1)
        )
        rnd = result.scalar_one()
        return rnd.id
