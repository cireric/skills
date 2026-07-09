from lib.extractor import (
    clean_image_url,
    convert_img_tag,
    convert_to_markdown,
    ArticleData,
    remove_noise_elements,
    truncate_tail_noise,
)


class TestCleanImageUrl:
    def test_amp_entity(self):
        assert clean_image_url("https://x.com/img.jpg&amp;w=1") == "https://x.com/img.jpg&w=1"

    def test_keep_wx_fmt(self):
        url = clean_image_url("https://mmbiz.qpic.cn/img?wx_fmt=png&other=1&tp=webp")
        assert "wx_fmt=png" in url
        assert "other=1" not in url

    def test_strip_all_params(self):
        url = clean_image_url("https://x.com/img.jpg?random=1&foo=2")
        assert "?" not in url

    def test_empty(self):
        assert clean_image_url("") == ""

    def test_none(self):
        assert clean_image_url(None) is None


class TestRemoveNoiseElements:
    def test_ad_div(self):
        html = '<div class="ad-banner">Buy now</div><p>Content</p>'
        result = remove_noise_elements(html)
        assert "Buy now" not in result
        assert "Content" in result

    def test_qr_code(self):
        html = '<div class="qr-code-popup">Scan me</div><p>Text</p>'
        result = remove_noise_elements(html)
        assert "Scan me" not in result


class TestConvertImgTag:
    def test_basic(self):
        result = convert_img_tag('<img src="https://x.com/img.jpg" alt="photo">')
        assert "![photo]" in result
        assert "https://x.com/img.jpg" in result

    def test_data_src(self):
        result = convert_img_tag('<img data-src="https://x.com/img.jpg">')
        assert "![image]" in result

    def test_no_src(self):
        assert convert_img_tag("<img>") == ""


class TestConvertToMarkdown:
    def test_basic_article(self):
        article = ArticleData(
            title="Test",
            author="Author",
            date="2024-01-01",
            url="https://example.com",
            content="<p>Hello</p>",
        )
        md = convert_to_markdown(article)
        assert "# Test" in md
        assert "**作者：** Author" in md
        assert "**来源：** https://example.com" in md
        assert "Hello" in md

    def test_no_author(self):
        article = ArticleData(
            title="Test",
            author="",
            date="2024-01-01",
            url="https://example.com",
            content="<p>Text</p>",
        )
        md = convert_to_markdown(article)
        assert "作者" not in md


class TestTruncateTailNoise:
    MARKERS = ["今日好文推荐", "会议推荐", "广告", "转载请联系"]

    def test_truncate_at_marker(self):
        content = "正文第一段\n\n正文第二段\n\n今日好文推荐\n\n推荐文章1\n\n推荐文章2"
        result = truncate_tail_noise(content, self.MARKERS)
        assert "今日好文推荐" not in result
        assert "推荐文章" not in result
        assert "正文第二段" in result

    def test_no_marker_no_truncate(self):
        content = "正文第一段\n\n正文第二段\n\n结论"
        result = truncate_tail_noise(content, self.MARKERS)
        assert result == content

    def test_marker_in_middle_not_truncated(self):
        lines = ["广告投放策略分析", "", "这是正文"] + ["正文续" + str(i) for i in range(30)] + ["", "结论"]
        content = "\n".join(lines)
        result = truncate_tail_noise(content, self.MARKERS, scan_lines=5)
        assert "广告投放策略分析" in result
        assert "结论" in result

    def test_empty_content(self):
        assert truncate_tail_noise("", self.MARKERS) == ""

    def test_empty_markers(self):
        content = "正文\n\n今日好文推荐"
        assert truncate_tail_noise(content, []) == content

    def test_truncate_strips_trailing_blank_lines(self):
        content = "正文\n\n\n\n今日好文推荐\n\n推荐文章"
        result = truncate_tail_noise(content, self.MARKERS)
        assert not result.endswith("\n\n")

    def test_multiple_markers_first_wins(self):
        content = "正文\n\n会议推荐\n\n会议信息\n\n广告\n\n广告内容"
        result = truncate_tail_noise(content, self.MARKERS)
        assert "会议推荐" not in result
        assert "广告" not in result
        assert "正文" in result
