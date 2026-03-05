"""Tests for TorznabBuilder XML generation."""

import pytest
from lxml import etree

from tests.conftest import SAMPLE_STREAM, _make_orion_response
from torznab_builder import TorznabBuilder

TORZNAB_NS = "http://torznab.com/schemas/2015/feed"


def _parse_xml(text: str) -> etree._Element:
    return etree.fromstring(text.encode())


def _get_torznab_attr(item: etree._Element, name: str) -> str | None:
    for attr in item.findall(f"{{{TORZNAB_NS}}}attr"):
        if attr.get("name") == name:
            return attr.get("value")
    return None


class TestBuildCapabilities:
    def test_returns_valid_xml(self):
        xml = TorznabBuilder.build_capabilities()
        root = _parse_xml(xml)
        assert root.tag == "caps"

    def test_has_server_info(self):
        root = _parse_xml(TorznabBuilder.build_capabilities())
        server = root.find("server")
        assert server is not None
        assert server.get("title") == "Orionoid Torznab"

    def test_has_search_types(self):
        root = _parse_xml(TorznabBuilder.build_capabilities())
        searching = root.find("searching")
        for search_type in ("search", "tv-search", "movie-search"):
            elem = searching.find(search_type)
            assert elem is not None
            assert elem.get("available") == "yes"

    def test_has_movie_and_tv_categories(self):
        root = _parse_xml(TorznabBuilder.build_capabilities())
        categories = root.find("categories")
        ids = {c.get("id") for c in categories.findall("category")}
        assert "2000" in ids
        assert "5000" in ids

    def test_has_subcategories(self):
        root = _parse_xml(TorznabBuilder.build_capabilities())
        categories = root.find("categories")
        subcats = [s.get("id") for c in categories for s in c.findall("subcat")]
        assert "2040" in subcats  # Movies/HD
        assert "5040" in subcats  # TV/HD


class TestBuildSearchResults:
    def test_empty_results(self):
        results = _make_orion_response([])
        xml = TorznabBuilder.build_search_results(results, "search")
        root = _parse_xml(xml)
        assert root.tag == "rss"
        items = root.findall(".//item")
        assert len(items) == 0

    def test_single_stream(self):
        results = _make_orion_response([SAMPLE_STREAM])
        xml = TorznabBuilder.build_search_results(results, "search")
        root = _parse_xml(xml)
        items = root.findall(".//item")
        assert len(items) == 1

    def test_item_has_title(self):
        results = _make_orion_response([SAMPLE_STREAM])
        xml = TorznabBuilder.build_search_results(results, "search")
        item = _parse_xml(xml).findall(".//item")[0]
        title = item.find("title").text
        assert "Test.Movie.2024.1080p.WEB.x264" in title

    def test_item_has_magnet_link(self):
        results = _make_orion_response([SAMPLE_STREAM])
        xml = TorznabBuilder.build_search_results(results, "search")
        item = _parse_xml(xml).findall(".//item")[0]
        link = item.find("link").text
        assert link.startswith("magnet:")

    def test_item_has_enclosure(self):
        results = _make_orion_response([SAMPLE_STREAM])
        xml = TorznabBuilder.build_search_results(results, "search")
        item = _parse_xml(xml).findall(".//item")[0]
        enclosure = item.find("enclosure")
        assert enclosure is not None
        assert enclosure.get("type") == "application/x-bittorrent"
        assert enclosure.get("url").startswith("magnet:")

    def test_torznab_seeders_attribute(self):
        results = _make_orion_response([SAMPLE_STREAM])
        xml = TorznabBuilder.build_search_results(results, "search")
        item = _parse_xml(xml).findall(".//item")[0]
        assert _get_torznab_attr(item, "seeders") == "42"

    def test_torznab_infohash_attribute(self):
        results = _make_orion_response([SAMPLE_STREAM])
        xml = TorznabBuilder.build_search_results(results, "search")
        item = _parse_xml(xml).findall(".//item")[0]
        assert _get_torznab_attr(item, "infohash") == "deadbeef"

    def test_torznab_imdbid_attribute(self):
        results = _make_orion_response([SAMPLE_STREAM])
        xml = TorznabBuilder.build_search_results(results, "search")
        item = _parse_xml(xml).findall(".//item")[0]
        assert _get_torznab_attr(item, "imdbid") == "1234567"

    def test_response_total_count(self):
        results = _make_orion_response([SAMPLE_STREAM, SAMPLE_STREAM])
        xml = TorznabBuilder.build_search_results(results, "search")
        root = _parse_xml(xml)
        ns = {"newznab": "http://www.newznab.com/DTD/2010/feeds/attributes/"}
        response_elem = root.find(".//newznab:response", ns)
        assert response_elem.get("total") == "2"

    def test_nzb_stream_type(self):
        nzb_stream = {
            **SAMPLE_STREAM,
            "stream": {"type": "usenet"},
            "links": ["https://example.com/nzb"],
        }
        results = _make_orion_response([nzb_stream])
        xml = TorznabBuilder.build_search_results(results, "search")
        item = _parse_xml(xml).findall(".//item")[0]
        enclosure = item.find("enclosure")
        assert enclosure.get("type") == "application/x-nzb"

    def test_malformed_stream_is_skipped(self):
        bad_stream = None  # Will cause exception in _build_item
        results = {
            "result": {"status": "success"},
            "data": {"streams": [bad_stream, SAMPLE_STREAM]},
        }
        xml = TorznabBuilder.build_search_results(results, "search")
        items = _parse_xml(xml).findall(".//item")
        assert len(items) == 1


class TestDetermineCategory:
    @pytest.mark.parametrize(
        ("quality", "query_type", "expected"),
        [
            ("1080", "movie", 2040),
            ("720", "movie", 2040),
            ("hd", "tvsearch", 5040),
            ("2160", "movie", 2060),
            ("4k", "tvsearch", 5080),
            ("sd", "movie", 2030),
            ("480", "tvsearch", 5030),
            ("", "movie", 2000),
            ("", "tvsearch", 5000),
        ],
    )
    def test_quality_category_mapping(self, quality, query_type, expected):
        stream = {"video": {"quality": quality}, "meta": {}}
        assert TorznabBuilder._determine_category(stream, query_type) == expected

    def test_media_type_marker_overrides_query_type(self):
        stream = {"video": {"quality": "1080"}, "_media_type": "show", "meta": {}}
        assert TorznabBuilder._determine_category(stream, "search") == 5040

    def test_episode_metadata_implies_tv(self):
        stream = {"video": {"quality": "1080"}, "meta": {"episode": {"season": 1}}}
        assert TorznabBuilder._determine_category(stream, "search") == 5040


class TestBuildError:
    def test_error_xml_structure(self):
        xml = TorznabBuilder.build_error(100, "test error")
        root = _parse_xml(xml)
        assert root.tag == "error"
        assert root.get("code") == "100"
        assert root.get("description") == "test error"
