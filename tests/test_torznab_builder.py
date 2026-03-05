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


class TestBuildSearchResults:
    def test_stream_produces_correct_item(self):
        """Title, enclosure, and key torznab attributes all set correctly."""
        results = _make_orion_response([SAMPLE_STREAM])
        xml = TorznabBuilder.build_search_results(results, "search")
        item = _parse_xml(xml).findall(".//item")[0]

        assert "Test.Movie.2024.1080p.WEB.x264" in item.find("title").text
        assert item.find("enclosure").get("type") == "application/x-bittorrent"
        assert _get_torznab_attr(item, "seeders") == "42"
        assert _get_torznab_attr(item, "infohash") == "deadbeef"

    def test_malformed_stream_skipped(self):
        results = {
            "result": {"status": "success"},
            "data": {"streams": [None, SAMPLE_STREAM]},
        }
        xml = TorznabBuilder.build_search_results(results, "search")
        assert len(_parse_xml(xml).findall(".//item")) == 1


class TestDetermineCategory:
    @pytest.mark.parametrize(
        ("quality", "query_type", "expected"),
        [
            ("1080", "movie", 2040),
            ("hd", "tvsearch", 5040),
            ("2160", "movie", 2060),
            ("4k", "tvsearch", 5080),
            ("sd", "movie", 2030),
            ("", "movie", 2000),
            ("", "tvsearch", 5000),
        ],
    )
    def test_quality_to_category(self, quality, query_type, expected):
        stream = {"video": {"quality": quality}, "meta": {}}
        assert TorznabBuilder._determine_category(stream, query_type) == expected

    def test_media_type_marker_overrides_query_type(self):
        stream = {"video": {"quality": "1080"}, "_media_type": "show", "meta": {}}
        assert TorznabBuilder._determine_category(stream, "search") == 5040
