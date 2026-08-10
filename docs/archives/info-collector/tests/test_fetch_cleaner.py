from __future__ import annotations
from scripts.fetch_cleaner import clean


class TestCleanSkipsForExaAndPiped:
    def test_exa_content_unchanged(self):
        content = "# Paper Title\n\nAbstract text with $x^2$ formula."
        assert clean(content, "exa_web_fetch_exa") == content

    def test_piped_content_unchanged(self):
        content = "# Paper Title\n\nSome content."
        assert clean(content, "piped") == content


class TestCleanRemovesNav:
    def test_removes_nav_block(self):
        html = "<nav><a href='/'>Home</a><a href='/about'>About</a></nav><main>Real content</main>"
        result = clean(html, "webfetch")
        assert "Home" not in result
        assert "Real content" in result


class TestCleanRemovesFooter:
    def test_removes_footer_block(self):
        html = "<main>Content</main><footer>Copyright 2025</footer>"
        result = clean(html, "webfetch")
        assert "Copyright" not in result
        assert "Content" in result


class TestCleanRemovesAside:
    def test_removes_aside_block(self):
        html = "<main>Content</main><aside>Sidebar links</aside>"
        result = clean(html, "webfetch")
        assert "Sidebar links" not in result
        assert "Content" in result


class TestCleanRemovesCookieBanner:
    def test_removes_cookie_text(self):
        md = "# Title\n\nWe use cookies to enhance your experience. Accept cookies to continue.\n\nReal content here."
        result = clean(md, "webfetch")
        assert "cookies" not in result.lower()
        assert "Real content" in result


class TestCleanRemovesSocialShare:
    def test_removes_share_buttons(self):
        md = "# Title\n\nShare on Twitter | Share on Facebook | 分享到微信\n\nContent."
        result = clean(md, "webfetch")
        assert "Share on Twitter" not in result
        assert "分享到微信" not in result
        assert "Content" in result


class TestCleanRemovesBreadcrumb:
    def test_removes_breadcrumb(self):
        md = "Home > Research > 2025 > Paper Title\n\n# Paper Title\n\nContent."
        result = clean(md, "webfetch")
        assert "Home > Research" not in result
        assert "Content" in result


class TestCleanRemovesComments:
    def test_removes_comment_section_with_next_heading(self):
        md = "# Article\n\nContent.\n\n## Comments\n\nUser1: Great!\nUser2: Nice.\n\n## References\n\n[1] Ref"
        result = clean(md, "webfetch")
        assert "User1" not in result
        assert "References" in result

    def test_removes_comment_section_at_end_of_document(self):
        md = "# Article\n\nContent.\n\n## Comments\n\nUser1: Great!\nUser2: Nice."
        result = clean(md, "webfetch")
        assert "User1" not in result
        assert "Content." in result


class TestCleanRemovesRelatedArticles:
    def test_removes_related_section(self):
        md = "# Article\n\nContent.\n\n## Related Articles\n\n- Article A\n- Article B\n\n## Next Section\n\nMore."
        result = clean(md, "webfetch")
        assert "Article A" not in result
        assert "Next Section" in result

    def test_removes_related_section_at_end_of_document(self):
        md = "# Article\n\nContent.\n\n## Related Articles\n\n- Article A\n- Article B"
        result = clean(md, "webfetch")
        assert "Article A" not in result
        assert "Content." in result


class TestCleanPreservesLatex:
    def test_preserves_dollar_signs(self):
        md = "# Title\n\nThe formula $P_{t}$ and $R_{g}$ are defined."
        result = clean(md, "webfetch")
        assert "$P_{t}$" in result
        assert "$R_{g}$" in result

    def test_preserves_dagger_markers(self):
        md = "# Title\n\n††journalyear: 2026††copyright: rightsretained\n\nContent."
        result = clean(md, "webfetch")
        assert "††" in result


class TestCleanPreservesTables:
    def test_preserves_markdown_table(self):
        md = "# Title\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\nContent."
        result = clean(md, "webfetch")
        assert "| A | B |" in result


class TestCleanPreservesCodeBlocks:
    def test_preserves_code_block(self):
        md = "# Title\n\n```python\nprint('hello')\n```\n\nContent."
        result = clean(md, "webfetch")
        assert "print('hello')" in result


class TestCleanEdgeCases:
    def test_all_noise_returns_empty(self):
        md = "<nav>Menu</nav><footer>Copyright</footer>\nWe use cookies.\nShare on Twitter."
        result = clean(md, "webfetch")
        assert result.strip() == ""
