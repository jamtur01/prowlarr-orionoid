"""Tests for the /api Torznab endpoint."""

import pytest
from lxml import etree

import main as main_module


@pytest.fixture(autouse=True)
def _reset(reset_globals):
    pass


def _parse_xml(text: str) -> etree._Element:
    return etree.fromstring(text.encode())


class TestCapabilities:
    async def test_caps_returns_xml(self, test_client):
        resp = await test_client.get("/api?t=caps")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]

    async def test_caps_has_search_types(self, test_client):
        resp = await test_client.get("/api?t=caps")
        root = _parse_xml(resp.text)
        searching = root.find("searching")
        assert searching.find("search") is not None
        assert searching.find("tv-search") is not None
        assert searching.find("movie-search") is not None

    async def test_caps_has_categories(self, test_client):
        resp = await test_client.get("/api?t=caps")
        root = _parse_xml(resp.text)
        categories = root.find("categories")
        cat_ids = [c.get("id") for c in categories.findall("category")]
        assert "2000" in cat_ids
        assert "5000" in cat_ids

    async def test_caps_no_auth_required(self, test_client):
        """Capabilities should work without an API key."""
        resp = await test_client.get("/api?t=caps")
        assert resp.status_code == 200


class TestSearch:
    async def test_movie_search(self, test_client, mock_search):
        resp = await test_client.get("/api?t=movie&q=test")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["media_type"] == "movie"
        assert call_kwargs["query"] == "test"

    async def test_tv_search_passes_season_episode(self, test_client, mock_search):
        resp = await test_client.get("/api?t=tvsearch&q=test&season=2&ep=5")
        assert resp.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["media_type"] == "show"
        assert call_kwargs["season"] == 2
        assert call_kwargs["episode"] == 5

    async def test_search_with_tv_category_routes_to_show(self, test_client, mock_search):
        resp = await test_client.get("/api?t=search&q=test&cat=5040")
        assert resp.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["media_type"] == "show"

    async def test_search_with_movie_category_routes_to_movie(self, test_client, mock_search):
        resp = await test_client.get("/api?t=search&q=test&cat=2040")
        assert resp.status_code == 200
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["media_type"] == "movie"

    async def test_search_without_category_searches_both(self, test_client, mock_search):
        resp = await test_client.get("/api?t=search&q=test")
        assert resp.status_code == 200
        assert mock_search.call_count == 2
        media_types = {c.kwargs["media_type"] for c in mock_search.call_args_list}
        assert media_types == {"movie", "show"}

    async def test_unknown_function_returns_error_xml(self, test_client):
        resp = await test_client.get("/api?t=badfunction")
        assert resp.status_code == 200
        root = _parse_xml(resp.text)
        assert root.tag == "error"
        assert root.get("code") == "201"

    async def test_search_results_contain_items(self, test_client, mock_search):
        resp = await test_client.get("/api?t=movie&q=test")
        root = _parse_xml(resp.text)
        items = root.findall(".//item")
        assert len(items) == 1
        title = items[0].find("title").text
        assert "Test.Movie.2024.1080p.WEB.x264" in title


class TestIMDbCleaning:
    async def test_strips_tt_prefix(self, test_client, mock_search):
        await test_client.get("/api?t=movie&imdbid=tt1234567")
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["imdb_id"] == "1234567"

    async def test_passes_bare_id_unchanged(self, test_client, mock_search):
        await test_client.get("/api?t=movie&imdbid=1234567")
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["imdb_id"] == "1234567"


class TestSearchUpdatesApiStatus:
    async def test_successful_search_sets_healthy(self, test_client, mock_search):
        main_module.api_status["healthy"] = False
        await test_client.get("/api?t=movie&q=test")
        assert main_module.api_status["healthy"] is True

    async def test_failed_search_sets_unhealthy(self, test_client):
        error_response = {"result": {"status": "error", "message": "quota exceeded"}}
        main_module.orion_client.search_streams.return_value = error_response
        await test_client.get("/api?t=movie&q=test")
        assert main_module.api_status["healthy"] is False
        assert "quota exceeded" in main_module.api_status["message"]

    async def test_successful_search_preserves_user_info(self, test_client, mock_search):
        main_module.api_status["user_info"] = {"username": "preserve_me"}
        await test_client.get("/api?t=movie&q=test")
        assert main_module.api_status["user_info"] == {"username": "preserve_me"}


class TestIndexerIdRoute:
    async def test_proxied_route_works(self, test_client, mock_search):
        resp = await test_client.get("/1/api?t=movie&q=test")
        assert resp.status_code == 200
        mock_search.assert_called_once()
