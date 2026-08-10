import pytest

from scripts.lib.utils import (
    normalize_url,
    compute_url_hash,
    infer_tier_from_url,
    build_domain_tier_map,
    build_collected_by_url,
    build_collected_url_set,
)


class TestNormalizeUrl:
    def test_lowercase_scheme_and_host(self):
        assert normalize_url("HTTP://ARXIV.ORG/paper") == "http://arxiv.org/paper"

    def test_strip_www(self):
        assert normalize_url("http://www.arxiv.org/paper") == "http://arxiv.org/paper"

    def test_strip_trailing_slash(self):
        assert normalize_url("http://arxiv.org/paper/") == "http://arxiv.org/paper"

    def test_root_path_preserved(self):
        result = normalize_url("http://arxiv.org")
        assert result.endswith("/")

    def test_query_sorting(self):
        a = normalize_url("http://a.com/page?z=1&a=2")
        b = normalize_url("http://a.com/page?a=2&z=1")
        assert a == b

    def test_fragment_removed(self):
        result = normalize_url("http://a.com/page#section")
        assert "#" not in result

    def test_empty_string(self):
        result = normalize_url("")
        assert isinstance(result, str)

    def test_whitespace_trimmed(self):
        result = normalize_url("  http://a.com/page  ")
        assert result == "http://a.com/page"


class TestComputeUrlHash:
    def test_deterministic(self):
        h1 = compute_url_hash("http://arxiv.org/paper1")
        h2 = compute_url_hash("http://arxiv.org/paper1")
        assert h1 == h2

    def test_different_urls_different_hash(self):
        h1 = compute_url_hash("http://arxiv.org/paper1")
        h2 = compute_url_hash("http://arxiv.org/paper2")
        assert h1 != h2

    def test_hash_length(self):
        h = compute_url_hash("http://arxiv.org/paper1")
        assert len(h) == 12

    def test_normalization_affects_hash(self):
        h1 = compute_url_hash("http://ARXIV.ORG/paper")
        h2 = compute_url_hash("http://arxiv.org/paper")
        assert h1 == h2


class TestInferTierFromUrl:
    def test_known_domain(self):
        domain_map = {"arxiv.org": 1, "github.com": 2, "medium.com": 3, "reddit.com": 4}
        assert infer_tier_from_url("http://arxiv.org/paper", domain_map) == 1
        assert infer_tier_from_url("http://github.com/repo", domain_map) == 2

    def test_subdomain_match(self):
        domain_map = {"arxiv.org": 1}
        assert infer_tier_from_url("http://sub.arxiv.org/paper", domain_map) == 1

    def test_unknown_domain_defaults_tier3(self):
        assert infer_tier_from_url("http://unknown.xyz/page", {"arxiv.org": 1}) == 3

    def test_empty_map_defaults_tier3(self):
        assert infer_tier_from_url("http://arxiv.org/paper", None) == 3
        assert infer_tier_from_url("http://arxiv.org/paper", {}) == 3

    def test_www_prefix_stripped(self):
        domain_map = {"arxiv.org": 1}
        assert infer_tier_from_url("http://www.arxiv.org/paper", domain_map) == 1


class TestBuildDomainTierMap:
    def test_from_config(self):
        config = {
            "sources": {
                "1": {"sources": [{"domain": "arxiv.org"}, {"domain": "cnki.net"}]},
                "2": {"sources": [{"domain": "github.com"}]},
            }
        }
        result = build_domain_tier_map(config)
        assert result["arxiv.org"] == 1
        assert result["cnki.net"] == 1
        assert result["github.com"] == 2

    def test_empty_config(self):
        assert build_domain_tier_map({}) == {}

    def test_invalid_tier_key_skipped(self):
        config = {"sources": {"invalid": {"sources": [{"domain": "a.com"}]}}}
        result = build_domain_tier_map(config)
        assert "a.com" not in result


class TestBuildCollectedByUrl:
    def test_basic(self):
        collected = [{"url": "http://a.com", "title": "A"}, {"url": "http://b.com", "title": "B"}]
        result = build_collected_by_url(collected)
        assert len(result) == 2

    def test_empty_url_skipped(self):
        collected = [{"url": "", "title": "Empty"}, {"url": "http://a.com", "title": "A"}]
        result = build_collected_by_url(collected)
        assert len(result) == 1


class TestBuildCollectedUrlSet:
    def test_basic(self):
        collected = [{"url": "http://a.com"}, {"url": "http://b.com"}]
        result = build_collected_url_set(collected)
        assert len(result) == 2

    def test_normalizes(self):
        collected = [{"url": "HTTP://A.COM/Page/"}]
        result = build_collected_url_set(collected)
        assert any("a.com" in url for url in result)
