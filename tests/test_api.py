"""Tests for the /api Torznab endpoint."""

from lxml import etree

import main as main_module


def _parse_xml(text: str) -> etree._Element:
    return etree.fromstring(text.encode())


class TestCapabilities:
    async def test_returns_valid_xml_with_search_types(
        self, test_client, reset_globals
    ):
        resp = await test_client.get("/api?t=caps")
        assert resp.status_code == 200
        searching = _parse_xml(resp.text).find("searching")
        assert searching.find("search") is not None
        assert searching.find("tv-search") is not None
        assert searching.find("movie-search") is not None


class TestSearch:
    async def test_movie_search(self, test_client, mock_search, reset_globals):
        await test_client.get("/api?t=movie&q=test")
        kw = mock_search.call_args.kwargs
        assert kw["media_type"] == "movie"
        assert kw["query"] == "test"

    async def test_tv_search_with_season_episode(
        self, test_client, mock_search, reset_globals
    ):
        await test_client.get("/api?t=tvsearch&q=test&season=2&ep=5")
        kw = mock_search.call_args.kwargs
        assert kw["media_type"] == "show"
        assert kw["season"] == 2
        assert kw["episode"] == 5

    async def test_no_category_searches_both(
        self, test_client, mock_search, reset_globals
    ):
        await test_client.get("/api?t=search&q=test")
        assert mock_search.call_count == 2
        types = {c.kwargs["media_type"] for c in mock_search.call_args_list}
        assert types == {"movie", "show"}

    async def test_strips_tt_prefix_from_imdb_id(
        self, test_client, mock_search, reset_globals
    ):
        await test_client.get("/api?t=movie&imdbid=tt1234567")
        assert mock_search.call_args.kwargs["imdb_id"] == "1234567"


class TestConnectionTest:
    async def test_empty_search_returns_synthetic_result_without_api_call(
        self, test_client, reset_globals
    ):
        """Prowlarr connection test returns a synthetic item (no API call)."""
        resp = await test_client.get("/api?t=search")
        assert resp.status_code == 200
        root = _parse_xml(resp.text)
        assert root.tag == "rss"
        assert len(root.findall(".//item")) >= 1
        main_module.orion_client.search_streams.assert_not_called()


class TestNotFoundHandling:
    async def test_not_found_treated_as_empty_results(
        self, test_client, reset_globals
    ):
        """Orionoid 'not found' is empty results, not an API error."""
        main_module.orion_client.search_streams.return_value = {
            "result": {
                "status": "error",
                "message": "The streams could not be found or do not exist yet.",
            },
        }
        resp = await test_client.get("/api?t=movie&q=obscure")
        assert resp.status_code == 200
        root = _parse_xml(resp.text)
        assert root.tag == "rss"
        assert len(root.findall(".//item")) == 0
        # Should NOT mark API as unhealthy
        assert main_module.api_status["healthy"] is True


class TestSearchUpdatesApiStatus:
    async def test_success_sets_healthy_and_preserves_user_info(
        self, test_client, mock_search, reset_globals
    ):
        main_module.api_status["healthy"] = False
        main_module.api_status["user_info"] = {"username": "preserve_me"}
        await test_client.get("/api?t=movie&q=test")
        assert main_module.api_status["healthy"] is True
        assert main_module.api_status["user_info"] == {"username": "preserve_me"}

    async def test_failure_sets_unhealthy(self, test_client, reset_globals):
        main_module.orion_client.search_streams.return_value = {
            "result": {"status": "error", "message": "quota exceeded"},
        }
        await test_client.get("/api?t=movie&q=test")
        assert main_module.api_status["healthy"] is False
        assert "quota exceeded" in main_module.api_status["message"]
