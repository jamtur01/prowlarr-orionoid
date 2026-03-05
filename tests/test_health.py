"""Tests for the /health endpoint and passive API status tracking."""

from datetime import datetime, timezone

import pytest

import main as main_module


@pytest.fixture(autouse=True)
def _reset(reset_globals):
    """Auto-apply reset_globals for every test in this module."""


class TestHealthEndpoint:
    async def test_returns_200_when_client_initialized(self, test_client):
        resp = await test_client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "uptime" in body
        assert "orionoid_api" in body
        assert "search" in body

    async def test_returns_503_when_client_not_initialized(self, test_client):
        main_module.orion_client = None
        resp = await test_client.get("/health")
        assert resp.status_code == 503
        assert resp.json()["status"] == "unhealthy"

    async def test_reflects_degraded_api_status(self, test_client):
        main_module.api_status["healthy"] = False
        main_module.api_status["last_checked"] = "2026-01-01T00:00:00+00:00"
        main_module.api_status["message"] = "quota exhausted"

        resp = await test_client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["orionoid_api"]["message"] == "quota exhausted"

    async def test_warning_when_never_checked(self, test_client):
        main_module.api_status["healthy"] = False
        main_module.api_status["last_checked"] = None

        resp = await test_client.get("/health")
        body = resp.json()
        assert body["status"] == "warning"

    async def test_search_status_idle_when_no_searches(self, test_client):
        main_module.last_successful_search = None
        resp = await test_client.get("/health")
        assert resp.json()["search"]["status"] == "idle"
        assert resp.json()["search"]["lastSuccess"] is None

    async def test_search_status_stale_after_5_minutes(self, test_client):
        five_min_ago = datetime(2020, 1, 1, tzinfo=timezone.utc)
        main_module.last_successful_search = five_min_ago
        resp = await test_client.get("/health")
        assert resp.json()["search"]["status"] == "stale"

    async def test_includes_user_info_from_api_status(self, test_client):
        resp = await test_client.get("/health")
        user_info = resp.json()["orionoid_api"]["userInfo"]
        assert user_info["username"] == "test@example.com"
        assert user_info["premium"] is True

    async def test_no_api_calls_on_health_check(self, test_client):
        """The whole point: /health must NOT call the Orionoid API."""
        mock_client = main_module.orion_client
        await test_client.get("/health")
        await test_client.get("/health")
        await test_client.get("/health")
        mock_client.get_user_info.assert_not_called()
        mock_client.search_streams.assert_not_called()


class TestUpdateApiStatus:
    def test_preserves_user_info_when_omitted(self):
        main_module.api_status["user_info"] = {"username": "keep_me"}
        main_module._update_api_status(healthy=True, message="ok")
        assert main_module.api_status["user_info"] == {"username": "keep_me"}

    def test_overwrites_user_info_when_passed(self):
        main_module.api_status["user_info"] = {"username": "old"}
        main_module._update_api_status(
            healthy=True, message="ok", user_info={"username": "new"}
        )
        assert main_module.api_status["user_info"] == {"username": "new"}

    def test_can_clear_user_info_with_none(self):
        main_module.api_status["user_info"] = {"username": "old"}
        main_module._update_api_status(healthy=False, message="err", user_info=None)
        assert main_module.api_status["user_info"] is None

    def test_sets_last_checked_timestamp(self):
        main_module.api_status["last_checked"] = None
        main_module._update_api_status(healthy=True, message="ok")
        assert main_module.api_status["last_checked"] is not None
