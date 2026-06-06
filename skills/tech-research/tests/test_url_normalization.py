"""Tests for _normalize_url() — core deduplication logic."""

import pytest

from research import _normalize_url


class TestNormalizeUrlBasic:
    """Basic URL normalization behavior."""

    def test_basic_url_unchanged(self):
        assert _normalize_url("https://example.com/path") == "https://example.com/path"

    def test_http_url_unchanged_scheme(self):
        assert _normalize_url("http://example.com/path") == "http://example.com/path"

    def test_removes_trailing_slash(self):
        assert _normalize_url("https://example.com/path/") == "https://example.com/path"

    def test_root_path_becomes_slash(self):
        assert _normalize_url("https://example.com") == "https://example.com/"

    def test_empty_string(self):
        assert _normalize_url("") == "/"

    def test_single_slash(self):
        assert _normalize_url("/") == "/"


class TestNormalizeUrlLowercasing:
    """URL scheme and host should be lowercased."""

    def test_uppercase_scheme(self):
        result = _normalize_url("HTTPS://example.com/path")
        assert result == "https://example.com/path"

    def test_uppercase_host(self):
        result = _normalize_url("https://EXAMPLE.COM/path")
        assert result == "https://example.com/path"

    def test_mixed_case_full_url(self):
        result = _normalize_url("HTTPS://EXAMPLE.COM/PATH/TO/RESOURCE")
        assert result == "https://example.com/path/to/resource"

    def test_url_with_encoded_chars(self):
        result = _normalize_url("https://example.com/search?q=hello%20world")
        assert result == "https://example.com/search?q=hello+world"

    def test_url_with_special_path_chars(self):
        result = _normalize_url("https://example.com/path/to/resource-1.0/")
        assert result == "https://example.com/path/to/resource-1.0"


class TestNormalizeUrlWwwStripping:
    """www. prefix should be stripped from hostname."""

    def test_removes_www_prefix(self):
        assert _normalize_url("https://www.example.com") == "https://example.com/"

    def test_removes_www_with_path(self):
        assert _normalize_url("https://www.example.com/blog") == "https://example.com/blog"

    def test_www_subdomain_other(self):
        result = _normalize_url("https://www2.example.com")
        assert result == "https://www2.example.com/"

    def test_no_www_on_normal_url(self):
        result = _normalize_url("https://example.com")
        assert result == "https://example.com/"


class TestNormalizeUrlQueryParams:
    """Query parameters should be sorted for consistent deduplication."""

    def test_sorts_query_params(self):
        result = _normalize_url("https://example.com?b=2&a=1")
        assert result == "https://example.com/?a=1&b=2"

    def test_single_query_param(self):
        result = _normalize_url("https://example.com?z=last")
        assert result == "https://example.com/?z=last"

    def test_multiple_params_same_value(self):
        result = _normalize_url("https://example.com?c=3&b=2&a=1")
        assert result == "https://example.com/?a=1&b=2&c=3"

    def test_query_params_with_trailing_slash(self):
        result = _normalize_url("https://example.com/?b=2&a=1")
        assert result == "https://example.com/?a=1&b=2"

    def test_empty_query_string(self):
        result = _normalize_url("https://example.com?")
        assert result == "https://example.com/"


class TestNormalizeUrlFragments:
    """URL fragments (anchors) should be removed."""

    def test_removes_fragment(self):
        assert _normalize_url("https://example.com#section") == "https://example.com/"

    def test_removes_fragment_with_path(self):
        assert _normalize_url("https://example.com/path#section") == "https://example.com/path"

    def test_removes_fragment_and_query(self):
        result = _normalize_url("https://example.com?a=1#section")
        assert result == "https://example.com/?a=1"


class TestNormalizeUrlPort:
    """Port numbers should be preserved in normalized URL."""

    def test_preserves_port_8080(self):
        result = _normalize_url("https://example.com:8080/path")
        assert result == "https://example.com:8080/path"

    def test_preserves_port_with_www(self):
        result = _normalize_url("https://www.example.com:3000")
        assert result == "https://example.com:3000/"

    def test_standard_port_443(self):
        result = _normalize_url("https://example.com:443/path")
        assert result == "https://example.com:443/path"


class TestNormalizeUrlEdgeCases:
    """Edge cases and special scenarios."""

    def test_duplicate_detection_example_com(self):
        a = _normalize_url("https://example.com/page")
        b = _normalize_url("https://example.com/page/")
        assert a == b

    def test_duplicate_detection_www_vs_no_www(self):
        a = _normalize_url("https://www.example.com")
        b = _normalize_url("https://example.com")
        assert a == b

    def test_duplicate_detection_query_order(self):
        a = _normalize_url("https://example.com?x=1&y=2")
        b = _normalize_url("https://example.com?y=2&x=1")
        assert a == b

    def test_duplicate_detection_mixed_case(self):
        a = _normalize_url("HTTPS://WWW.EXAMPLE.COM/PAGE")
        b = _normalize_url("https://example.com/page")
        assert a == b

    def test_url_with_params_and_fragment(self):
        result = _normalize_url("https://www.EXAMPLE.com:8080/path/?z=9&a=1#hash")
        assert result == "https://example.com:8080/path?a=1&z=9"


class TestNormalizeUrlDedupRealWorld:
    """Real-world deduplication scenarios."""

    def test_same_origin_different_trailing_slash(self):
        urls = [
            "https://docs.python.org/3/library/",
            "https://docs.python.org/3/library",
        ]
        normalized = [_normalize_url(u) for u in urls]
        assert len(set(normalized)) == 1

    def test_www_variants(self):
        urls = [
            "https://www.wikipedia.org/wiki/Python",
            "https://wikipedia.org/wiki/Python",
        ]
        normalized = [_normalize_url(u) for u in urls]
        assert len(set(normalized)) == 1

    def test_query_param_reordering(self):
        urls = [
            "https://api.github.com/search?q=python&sort=stars",
            "https://api.github.com/search?sort=stars&q=python",
        ]
        normalized = [_normalize_url(u) for u in urls]
        assert len(set(normalized)) == 1

    def test_case_insensitive_host(self):
        urls = [
            "https://GITHUB.COM/api",
            "https://github.com/api",
        ]
        normalized = [_normalize_url(u) for u in urls]
        assert len(set(normalized)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
