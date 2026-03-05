"""Tests for the /health endpoint and passive API status tracking."""


import main as main_module


class TestHealthEndpoint:
    async def test_healthy_response(self, test_client, reset_globals):
        resp = await test_client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "uptime" in body

    async def test_503_when_client_missing(self, test_client, reset_globals):
        main_module.orion_client = None
        assert (await test_client.get("/health")).status_code == 503

    async def test_degraded_when_api_unhealthy(self, test_client, reset_globals):
        main_module.api_status.update(
            healthy=False, last_checked="2026-01-01T00:00:00+00:00",
            message="quota exhausted",
        )
        resp = await test_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"

    async def test_no_api_calls_made(self, test_client, reset_globals):
        """The whole point: /health must NOT call the Orionoid API."""
        mock = main_module.orion_client
        for _ in range(3):
            await test_client.get("/health")
        mock.get_user_info.assert_not_called()
        mock.search_streams.assert_not_called()


class TestUpdateApiStatus:
    def test_preserves_user_info_when_omitted(self, reset_globals):
        main_module.api_status["user_info"] = {"username": "keep_me"}
        main_module._update_api_status(healthy=True, message="ok")
        assert main_module.api_status["user_info"] == {"username": "keep_me"}

    def test_overwrites_user_info_when_passed(self, reset_globals):
        main_module._update_api_status(
            healthy=True, message="ok", user_info={"username": "new"}
        )
        assert main_module.api_status["user_info"] == {"username": "new"}
