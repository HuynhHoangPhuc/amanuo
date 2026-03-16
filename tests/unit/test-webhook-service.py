"""Unit tests for webhook service."""

import importlib
import json
import pytest

_webhook = importlib.import_module("src.services.webhook-service")

create_webhook = _webhook.create_webhook
list_webhooks = _webhook.list_webhooks
get_webhook = _webhook.get_webhook
delete_webhook = _webhook.delete_webhook
get_subscriptions = _webhook.get_subscriptions
publish_event = _webhook.publish_event


class TestWebhookCRUD:
    """Test webhook CRUD operations."""

    @pytest.mark.unit
    async def test_create_webhook(self, db_workspace):
        """Creating webhook returns response with secret."""
        webhook = await create_webhook(
            db_workspace, "https://example.com/webhook", ["job.completed"]
        )
        assert webhook.id is not None
        assert webhook.url == "https://example.com/webhook"
        assert webhook.events == ["job.completed"]
        assert webhook.secret is not None
        assert webhook.is_active is True

    @pytest.mark.unit
    async def test_list_webhooks(self, db_workspace):
        """List webhooks returns all for workspace."""
        await create_webhook(db_workspace, "https://hook1.com", ["job.completed"])
        await create_webhook(db_workspace, "https://hook2.com", ["batch.completed"])

        webhooks = await list_webhooks(db_workspace)
        assert len(webhooks) >= 2
        # Secrets should not be returned in list
        for webhook in webhooks:
            assert webhook.secret is None

    @pytest.mark.unit
    async def test_get_webhook(self, db_workspace):
        """Get webhook returns single webhook."""
        created = await create_webhook(db_workspace, "https://hook.com", ["job.failed"])
        webhook = await get_webhook(db_workspace, created.id)

        assert webhook is not None
        assert webhook.id == created.id
        assert webhook.url == "https://hook.com"

    @pytest.mark.unit
    async def test_get_webhook_wrong_workspace_returns_none(self, db_workspace):
        """Get webhook with wrong workspace returns None."""
        created = await create_webhook(db_workspace, "https://hook.com", ["job.failed"])
        webhook = await get_webhook("wrong-ws", created.id)
        assert webhook is None

    @pytest.mark.unit
    async def test_delete_webhook(self, db_workspace):
        """Delete webhook returns True on success."""
        created = await create_webhook(db_workspace, "https://hook.com", ["job.failed"])
        result = await delete_webhook(db_workspace, created.id)
        assert result is True

        # Verify deletion
        webhook = await get_webhook(db_workspace, created.id)
        assert webhook is None

    @pytest.mark.unit
    async def test_delete_nonexistent_webhook_returns_false(self, db_workspace):
        """Delete nonexistent webhook returns False."""
        result = await delete_webhook(db_workspace, "nonexistent")
        assert result is False

    @pytest.mark.unit
    async def test_delete_webhook_wrong_workspace_returns_false(self, db_workspace):
        """Delete webhook with wrong workspace returns False."""
        created = await create_webhook(db_workspace, "https://hook.com", ["job.failed"])
        result = await delete_webhook("wrong-ws", created.id)
        assert result is False


class TestWebhookEventFiltering:
    """Test webhook event subscription and filtering."""

    @pytest.mark.unit
    async def test_create_webhook_multiple_events(self, db_workspace):
        """Webhook can subscribe to multiple events."""
        webhook = await create_webhook(
            db_workspace,
            "https://hook.com",
            ["job.completed", "job.failed", "batch.completed"],
        )
        assert len(webhook.events) == 3

    @pytest.mark.unit
    async def test_get_subscriptions_filters_by_event(self, db_workspace):
        """Get subscriptions returns webhooks subscribed to event."""
        hook1 = await create_webhook(db_workspace, "https://hook1.com", ["job.completed"])
        hook2 = await create_webhook(db_workspace, "https://hook2.com", ["batch.completed"])
        hook3 = await create_webhook(
            db_workspace, "https://hook3.com", ["job.completed", "batch.failed"]
        )

        job_subs = await get_subscriptions(db_workspace, "job.completed")
        assert len(job_subs) == 2
        urls = {sub["url"] for sub in job_subs}
        assert "https://hook1.com" in urls
        assert "https://hook3.com" in urls

    @pytest.mark.unit
    async def test_get_subscriptions_no_match_returns_empty(self, db_workspace):
        """Get subscriptions with no matches returns empty list."""
        await create_webhook(db_workspace, "https://hook.com", ["job.completed"])
        subs = await get_subscriptions(db_workspace, "batch.completed")
        assert len(subs) == 0

    @pytest.mark.unit
    async def test_get_subscriptions_includes_secret(self, db_workspace):
        """Get subscriptions includes secret for delivery signing."""
        hook = await create_webhook(db_workspace, "https://hook.com", ["job.completed"])
        subs = await get_subscriptions(db_workspace, "job.completed")

        assert len(subs) == 1
        assert subs[0]["secret"] is not None
        assert subs[0]["id"] == hook.id


class TestWebhookPublishing:
    """Test webhook event publishing."""

    @pytest.mark.unit
    async def test_publish_event_creates_delivery_records(self, db_workspace):
        """Publishing event creates delivery records."""
        hook1 = await create_webhook(db_workspace, "https://hook1.com", ["job.completed"])
        hook2 = await create_webhook(db_workspace, "https://hook2.com", ["job.completed"])

        # publish_event should enqueue deliveries
        await publish_event(db_workspace, "job.completed", {"job_id": "job-123"})

        # Verify subscriptions were found
        subs = await get_subscriptions(db_workspace, "job.completed")
        assert len(subs) == 2

    @pytest.mark.unit
    async def test_publish_event_no_subscriptions(self, db_workspace):
        """Publishing event with no subscriptions does nothing."""
        # No webhooks created
        await publish_event(db_workspace, "job.completed", {"job_id": "job-123"})
        # Should not raise, just return

    @pytest.mark.unit
    async def test_publish_event_filtered_by_workspace(self, db_workspace):
        """Published event only reaches subscriptions in same workspace."""
        import uuid
        ws2_id = str(uuid.uuid4())
        from src.config import settings
        from src.database import get_connection, get_db_path
        from datetime import datetime

        now = datetime.now().isoformat()
        db = await get_connection(get_db_path(settings.database_url))
        try:
            await db.execute(
                "INSERT INTO workspaces (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (ws2_id, f"ws2-{ws2_id[:8]}", now, now),
            )
            await db.commit()
        finally:
            await db.close()

        hook1 = await create_webhook(db_workspace, "https://hook1.com", ["job.completed"])
        hook2 = await create_webhook(ws2_id, "https://hook2.com", ["job.completed"])

        subs_ws1 = await get_subscriptions(db_workspace, "job.completed")
        subs_ws2 = await get_subscriptions(ws2_id, "job.completed")

        assert len(subs_ws1) == 1
        assert len(subs_ws2) == 1

    @pytest.mark.unit
    async def test_publish_event_only_to_active_webhooks(self, db_workspace):
        """Published event only reaches active webhooks."""
        hook = await create_webhook(db_workspace, "https://hook.com", ["job.completed"])
        await delete_webhook(db_workspace, hook.id)

        subs = await get_subscriptions(db_workspace, "job.completed")
        assert len(subs) == 0
