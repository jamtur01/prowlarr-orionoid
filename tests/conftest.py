import time
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

import main as main_module


def _make_orion_response(streams=None):
    """Build a minimal successful Orionoid API response."""
    return {
        "result": {"status": "success"},
        "data": {
            "streams": streams or [],
            "count": len(streams) if streams else 0,
        },
    }


FAKE_USER_INFO = {
    "result": {"status": "success"},
    "data": {
        "email": "test@example.com",
        "subscription": {"package": {"premium": True}},
        "requests": {"streams": {"daily": {"remaining": 500}}},
    },
}

SAMPLE_STREAM = {
    "id": "abc123",
    "file": {
        "name": "Test.Movie.2024.1080p.WEB.x264",
        "size": 1_500_000_000,
        "hash": "deadbeef",
    },
    "video": {"quality": "1080", "codec": "h264"},
    "audio": {"codec": "aac"},
    "meta": {"title": "Test Movie", "imdb": "1234567"},
    "links": ["magnet:?xt=urn:btih:deadbeef"],
    "stream": {"type": "torrent", "seeds": 42},
    "time": {"added": 1700000000},
}


@pytest.fixture()
def reset_globals():
    """Reset main module globals before each test."""
    original = {
        "orion_client": main_module.orion_client,
        "startup_time": main_module.startup_time,
        "last_successful_search": main_module.last_successful_search,
        "api_status": main_module.api_status.copy(),
    }
    yield
    main_module.orion_client = original["orion_client"]
    main_module.startup_time = original["startup_time"]
    main_module.last_successful_search = original["last_successful_search"]
    main_module.api_status.update(original["api_status"])


@pytest.fixture()
def test_client(reset_globals):
    """Create an httpx AsyncClient that talks to the app without lifespan.

    Injects a mock OrionoidClient so the app thinks it started normally.
    """
    mock_client = AsyncMock()
    main_module.orion_client = mock_client
    main_module.startup_time = time.time()
    main_module.api_status.update({
        "healthy": True,
        "message": "Connected to Orionoid API",
        "last_checked": "2026-01-01T00:00:00+00:00",
        "user_info": {
            "username": "test@example.com",
            "premium": True,
            "apiCallsRemaining": 500,
        },
    })

    transport = ASGITransport(app=main_module.app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture()
def mock_search(test_client):
    """Configure the mock OrionoidClient.search_streams return value.

    Depends on test_client so the mock instance is already injected.
    """
    result = _make_orion_response([SAMPLE_STREAM])
    main_module.orion_client.search_streams.return_value = result
    return main_module.orion_client.search_streams
