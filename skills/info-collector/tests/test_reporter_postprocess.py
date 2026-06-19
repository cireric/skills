from __future__ import annotations

from scripts.reporter import _clean_url, _post_process


class TestCleanUrl:
    def test_preview_https_removed(self):
        assert _clean_url("https://preview-www.nature.com/article") == "https://www.nature.com/article"

    def test_preview_http_removed(self):
        assert _clean_url("http://preview-www.example.com") == "https://www.example.com"

    def test_no_preview_prefix(self):
        url = "https://www.example.com"
        assert _clean_url(url) == url

    def test_http_no_preview(self):
        url = "http://www.example.com"
        assert _clean_url(url) == url

    def test_empty_string(self):
        assert _clean_url("") == ""

    def test_preview_double_prefix(self):
        """Only one preview- prefix is removed per regex pass."""
        assert _clean_url("https://preview-preview-www.example.com") == "https://preview-www.example.com"


class TestPostProcess:
    def test_literal_newline_replaced(self):
        """\\n (literal backslash-n) becomes a real newline."""
        result = _post_process("hello\\nworld")
        assert result == "hello\nworld"

    def test_escaped_newline_preserved(self):
        """\\\\n (escaped backslash + n) stays as-is because \\ protects it."""
        result = _post_process("hello\\\\nworld")
        assert result == "hello\\\\nworld"

    def test_preview_url_cleaned(self):
        md = "Check http://preview-x.com for details."
        result = _post_process(md)
        assert "https://x.com" in result
        assert "preview-" not in result

    def test_bare_url_converted_to_link(self):
        md = "See https://example.com for more.\n\n## References\n"
        result = _post_process(md)
        assert result == "See [https://example.com](https://example.com) for more.\n\n## References\n"

    def test_http_bare_url_converted_to_https_link(self):
        """http:// bare URLs get https:// in both link text and href."""
        md = "See http://example.com\n\n## References\n"
        result = _post_process(md)
        assert result == "See [https://example.com](https://example.com)\n\n## References\n"

    def test_url_in_references_not_converted(self):
        md = "Body text\n\n## References\nhttps://ref.com"
        result = _post_process(md)
        assert "## References\nhttps://ref.com" in result

    def test_url_in_references_zh_not_converted(self):
        md = "Body text\n\n## 参考文献\nhttps://ref.com"
        result = _post_process(md)
        assert "## 参考文献\nhttps://ref.com" in result

    def test_bare_url_in_body_before_references_converted(self):
        """URL in body before References section gets converted; URL in refs stays bare."""
        md = "See https://example.com\n\n## References\nhttps://ref.com"
        result = _post_process(md)
        assert "[https://example.com](https://example.com)" in result
        assert "## References\nhttps://ref.com" in result

    def test_existing_markdown_link_unchanged(self):
        """[text](url) should not be double-wrapped."""
        md = "See [example](https://example.com)."
        result = _post_process(md)
        assert result == "See [example](https://example.com)."

    def test_mixed_content(self):
        """All three transformations together: literal \\n, preview- URL, bare URL."""
        md = "Line1\\nLine2\n\nVisit http://preview-x.com or https://example.com\n\n## References\n"
        result = _post_process(md)
        assert "Line1\nLine2" in result  # literal \n → newline
        assert "https://x.com" in result  # preview- cleaned
        assert "[https://example.com](https://example.com)" in result  # bare URL → link

    def test_no_urls_unchanged(self):
        md = "Just plain text.\nNo URLs here."
        assert _post_process(md) == md

    def test_url_after_references_zh_body_only(self):
        """Only body (before ## 参考文献) gets URL conversion."""
        md = "Body https://example.com\n\n## 参考文献\nhttps://ref1.com\nhttps://ref2.com"
        result = _post_process(md)
        assert "[https://example.com](https://example.com)" in result
        assert "## 参考文献\nhttps://ref1.com" in result
        assert "https://ref2.com" in result
