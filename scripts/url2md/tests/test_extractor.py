import asyncio
from unittest.mock import AsyncMock

from lib.extractor import (
    ZHIHU_QUESTION_RE,
    _convert_html_to_markdown,
    _parse_x_tweet_lines,
    build_author_text_html,
    build_x_thread_html,
    clean_image_url,
    convert_img_tag,
    convert_to_markdown,
    extract_answer_ids_from_initial_data,
    filter_x_thread_tweets,
    ArticleData,
    remove_noise_elements,
    truncate_tail_noise,
)
from lib.selectors import Platform


class TestExtractAnswerIdsFromInitialData:
    def test_returns_answer_ids_in_order(self):
        script = '{"initialState": {"entities": {"answers": {"111": null, "222": null, "333": null}}}}'
        assert extract_answer_ids_from_initial_data(script) == ["111", "222", "333"]

    def test_filters_non_numeric_keys(self):
        script = '{"initialState": {"entities": {"answers": {"abc": null, "222": null}}}}'
        assert extract_answer_ids_from_initial_data(script) == ["222"]

    def test_missing_structure_returns_empty(self):
        assert extract_answer_ids_from_initial_data('{"other": 1}') == []
        assert extract_answer_ids_from_initial_data("") == []

    def test_invalid_json_returns_empty(self):
        assert extract_answer_ids_from_initial_data("not json {") == []


class TestZhihuPatterns:
    def test_question_re_matches_trailing_slash(self):
        # 回归：带尾斜杠的问题页 URL 必须仍被识别为知乎问题页
        m = ZHIHU_QUESTION_RE.search("https://www.zhihu.com/question/12345/")
        assert m is not None
        assert m.group("qid") == "12345"

    def test_question_re_matches_query_and_fragment(self):
        assert ZHIHU_QUESTION_RE.search("https://www.zhihu.com/question/12345?sort=vote_count")
        assert ZHIHU_QUESTION_RE.search("https://www.zhihu.com/question/12345#top")
        assert not ZHIHU_QUESTION_RE.search("https://www.zhihu.com/question/abc")


class TestExtractArticleWaitsForSelector:
    def test_waits_for_wait_selector(self):
        from lib.extractor import extract_article
        page = AsyncMock()
        page.url = "https://mp.weixin.qq.com/s/test"
        page.title = AsyncMock(return_value="Test Title")
        content_elem = AsyncMock()
        content_elem.inner_html = AsyncMock(return_value="<p>Content</p>")
        page.query_selector = AsyncMock(return_value=content_elem)
        page.query_selector_all = AsyncMock(return_value=[])
        asyncio.run(extract_article(page, Platform.WECHAT))
        page.wait_for_selector.assert_awaited_once_with("#js_content")

    def test_no_wait_when_no_wait_selector(self):
        from lib.extractor import extract_article
        page = AsyncMock()
        page.url = "https://example.com/article"
        page.title = AsyncMock(return_value="Test Title")
        content_elem = AsyncMock()
        content_elem.inner_html = AsyncMock(return_value="<p>Content</p>")
        page.query_selector = AsyncMock(return_value=content_elem)
        page.query_selector_all = AsyncMock(return_value=[])
        asyncio.run(extract_article(page, Platform.GENERIC))
        page.wait_for_selector.assert_not_awaited()

    def test_images_collected_from_all_selector_matches(self):
        """恢复旧行为：图片从每个 article_selector 匹配里收集（<sel> img），
        而不是只取第一个匹配元素内的图（首个选择器命中局部区块时会漏图）。"""
        from lib.extractor import extract_article
        page = AsyncMock()
        page.url = "https://example.com/article"
        page.title = AsyncMock(return_value="Test Title")
        content_elem = AsyncMock()
        content_elem.inner_html = AsyncMock(return_value="<p>Content</p>")
        # Py3.14 下 AsyncMock 子属性 awaited 结果是 AsyncMock，.strip() 为异步 mock；
        # 显式给内文/标题返回值，保证字段提取返回真实字符串
        content_elem.inner_text = AsyncMock(return_value="Fake Title")
        page.query_selector = AsyncMock(return_value=content_elem)

        def _img(src):
            img = AsyncMock()
            img.get_attribute = AsyncMock(
                side_effect=lambda name: src if name == "data-src" else None
            )
            return img

        # generic article_selector: "article, main, .content, .post, .entry"
        imgs_by_selector = {
            "article img": [_img("https://a.example/1.jpg")],
            "main img": [],
            ".content img": [
                _img("https://a.example/1.jpg"),
                _img("https://b.example/2.jpg"),
            ],
            ".post img": [],
            ".entry img": [],
        }
        page.query_selector_all = AsyncMock(
            side_effect=lambda sel: imgs_by_selector.get(sel, [])
        )
        article = asyncio.run(extract_article(page, Platform.GENERIC))
        assert sorted(article.images) == [
            "https://a.example/1.jpg",
            "https://b.example/2.jpg",
        ]
        for sel in ("article", "main", ".content", ".post", ".entry"):
            page.query_selector_all.assert_any_await(f"{sel} img")

    def test_images_fallback_to_page_when_no_content(self):
        from lib.extractor import extract_article
        page = AsyncMock()
        page.url = "https://example.com/article"
        page.title = AsyncMock(return_value="Test Title")
        page.query_selector = AsyncMock(return_value=None)
        page.query_selector_all = AsyncMock(return_value=[])
        asyncio.run(extract_article(page, Platform.GENERIC))
        # 无内容元素时仍按配置的子选择器查询 img（旧行为）
        for sel in ("article", "main", ".content", ".post", ".entry"):
            page.query_selector_all.assert_any_await(f"{sel} img")


class TestCleanImageUrl:
    def test_amp_entity(self):
        assert clean_image_url("https://x.com/img.jpg&amp;w=1") == "https://x.com/img.jpg&w=1"

    def test_keep_wx_fmt(self):
        url = clean_image_url("https://mmbiz.qpic.cn/img?wx_fmt=png&other=1&tp=webp", platform=Platform.WECHAT)
        assert "wx_fmt=png" in url
        assert "other=1" not in url

    def test_strip_all_params_no_platform(self):
        url = clean_image_url("https://x.com/img.jpg?random=1&foo=2")
        assert "?" not in url

    def test_generic_strips_wx_fmt(self):
        url = clean_image_url("https://mmbiz.qpic.cn/img?wx_fmt=png&other=1", platform=Platform.GENERIC)
        assert "wx_fmt" not in url

    def test_empty(self):
        assert clean_image_url("") == ""

    def test_none(self):
        assert clean_image_url(None) is None


class TestRemoveNoiseElements:
    def test_ad_div(self):
        html = '<div class="ad-banner">Buy now</div><p>Content</p>'
        result = remove_noise_elements(html, platform=Platform.WECHAT)
        assert "Buy now" not in result
        assert "Content" in result

    def test_qr_code(self):
        html = '<div class="qr-code-popup">Scan me</div><p>Text</p>'
        result = remove_noise_elements(html, platform=Platform.WECHAT)
        assert "Scan me" not in result

    def test_wechat_patterns_not_applied_to_generic(self):
        html = '<div class="qr-code-popup">Scan me</div><p>Text</p>'
        result = remove_noise_elements(html, platform=Platform.GENERIC)
        assert "Scan me" in result

    def test_no_platform_applies_all_patterns(self):
        html = '<div class="ad-banner">Buy now</div><p>Content</p>'
        result = remove_noise_elements(html)
        assert "Buy now" not in result


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

    def test_image_map_uses_local_path(self):
        # 回归 #1：下载后应通过 image_map 把远程 URL 替换为本地相对路径
        image_map = {"https://x.com/img.jpg": "images/abc.jpg"}
        result = convert_img_tag('<img src="https://x.com/img.jpg" alt="photo">', image_map=image_map)
        assert "images/abc.jpg" in result
        assert "https://x.com/img.jpg" not in result

    def test_image_map_escaped_amp_matches(self):
        # 回归 #1：content 中 & 被转义为 &amp;，clean 后应与 map 键（clean 后 URL）匹配
        cleaned = "https://x.com/a?wx_fmt=png&tp=webp"
        image_map = {cleaned: "images/abc.jpg"}
        tag = '<img src="https://x.com/a?wx_fmt=png&amp;tp=webp" alt="p">'
        result = convert_img_tag(tag, platform=Platform.WECHAT, image_map=image_map)
        assert "images/abc.jpg" in result
        assert cleaned not in result

    def test_image_map_stripped_query_matches(self):
        # 回归 #1：清理后去除查询参数（如 utm），map 键为 clean 后 URL，
        # content 中的原始 ?utm=1 不应残留在最终本地路径上
        image_map = {"https://x.com/a.jpg": "images/abc.jpg"}
        tag = '<img src="https://x.com/a.jpg?utm=1" alt="p">'
        result = convert_img_tag(tag, platform=Platform.GENERIC, image_map=image_map)
        assert "images/abc.jpg" in result
        assert "utm=1" not in result
        assert "https://x.com/a.jpg" not in result

    def test_data_uri_placeholder_falls_back_to_data_actualsrc(self):
        # 回归：知乎懒加载占位图 src 为 data:image/svg+xml（内含含 `>` 的 SVG），
        # 必须回退取 data-actualsrc 的真实地址，而非渲染占位 SVG
        tag = (
            '<img src="data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\''
            ' width=\'0\' height=\'0\'></svg>" data-actualsrc="https://x.com/real.jpg">'
        )
        result = convert_img_tag(tag)
        assert "![image]" in result
        assert "https://x.com/real.jpg" in result
        assert "data:image" not in result

    def test_data_uri_only_placeholder_returns_empty(self):
        # 仅有 data: 占位、没有真实地址的图片应被跳过，避免输出 data: 图片
        tag = (
            '<img src="data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\'>'
            '</svg>" data-caption="" class="content_image lazy">'
        )
        assert convert_img_tag(tag) == ""


class TestZhihuLazyImageFigure:
    FIGURE = (
        '<figure data-size="normal">'
        '<noscript><img src="https://picx.zhimg.com/50/v2-abc_720w.jpg?source=2c26e567"'
        ' data-caption="" data-size="normal" data-original-token="v2-abc"'
        ' class="content_image"/></noscript>'
        '<div class="RichText-ConditionalImagePortal">'
        '<img src="data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\''
        ' width=\'0\' height=\'0\'></svg>" data-caption="" data-size="normal"'
        ' data-original-token="v2-abc" class="content_image lazy"'
        ' data-actualsrc="https://picx.zhimg.com/50/v2-abc_720w.jpg?source=2c26e567">'
        '</div></figure>'
    )

    def test_no_leaked_attributes(self):
        # 回归：含 `>` 的 SVG data URI 不应切断 img 标签，导致 data-caption /
        # data-actualsrc 等属性碎片泄漏到正文（合法图片行自带的 {width=...} 除外）
        md = _convert_html_to_markdown(self.FIGURE, platform=Platform.ZHIHU)
        assert "data-caption" not in md
        assert "data-actualsrc" not in md
        assert "data-original-token" not in md
        # 不应出现脱离图片链接、单独成行的 {width=...} 属性碎片
        assert "\n{width" not in md
        assert md.count("![image]") >= 1

    def test_single_deduped_image(self):
        # <noscript> 兜底图与懒加载图 data-actualsrc 指向同一地址，去重后只渲染一张
        md = _convert_html_to_markdown(self.FIGURE, platform=Platform.ZHIHU)
        assert md.count("![image]") == 1
        assert "https://picx.zhimg.com/50/v2-abc_720w.jpg" in md

    def test_working_pair_keeps_both_variants(self):
        # 正常懒加载图（src 为真实 webp，非 data: 占位）应保留其变体，并与
        # <noscript> 兜底图去重（二者地址不同，故保留两张）
        figure = (
            '<figure><noscript><img src="https://picx.zhimg.com/50/v2-xyz_720w.jpg"'
            ' class="content_image"/></noscript>'
            '<div class="RichText-ConditionalImagePortal">'
            '<img src="https://pic1.zhimg.com/80/v2-xyz_720w.webp?source=2c26e567"'
            ' class="content_image lazy"'
            ' data-actualsrc="https://pic1.zhimg.com/50/v2-xyz_720w.jpg?source=2c26e567">'
            '</div></figure>'
        )
        md = _convert_html_to_markdown(figure, platform=Platform.ZHIHU)
        assert md.count("![image]") == 2
        assert "v2-xyz_720w.webp" in md
        assert "v2-xyz_720w.jpg" in md


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

    def test_custom_labels(self):
        article = ArticleData(
            title="Test",
            author="Author",
            date="2024-01-01",
            url="https://example.com",
            content="<p>Hello</p>",
        )
        md = convert_to_markdown(article, labels={"author": "Author:", "date": "Date:", "source": "Source:"})
        assert "**Author:** Author" in md
        assert "**Source:** https://example.com" in md


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


class TestCodeBlockConversion:
    def test_pre_basic(self):
        html = "<p>Text</p><pre>code here</pre><p>More</p>"
        md = _convert_html_to_markdown(html)
        assert "```" in md
        assert "code here" in md

    def test_pre_with_language(self):
        html = '<pre class="language-python">print("hello")</pre>'
        md = _convert_html_to_markdown(html)
        assert "```python" in md
        assert 'print("hello")' in md

    def test_pre_with_code_tag(self):
        html = '<pre><code class="language-javascript">const x = 1;</code></pre>'
        md = _convert_html_to_markdown(html)
        assert "```javascript" in md
        assert "const x = 1;" in md

    def test_pre_with_lang_prefix(self):
        html = '<pre><code class="lang-bash">echo hello</code></pre>'
        md = _convert_html_to_markdown(html)
        assert "```bash" in md
        assert "echo hello" in md

    def test_pre_preserves_html_entities(self):
        html = "<pre>x &lt; 10 &amp;&amp; y &gt; 5</pre>"
        md = _convert_html_to_markdown(html)
        assert "x < 10 && y > 5" in md

    def test_pre_preserves_nbsp(self):
        html = "<pre>line1&nbsp;&nbsp;&nbsp;line2</pre>"
        md = _convert_html_to_markdown(html)
        assert "line1   line2" in md

    def test_inline_code(self):
        html = "<p>Use <code>pip install</code> to install</p>"
        md = _convert_html_to_markdown(html)
        assert "`pip install`" in md

    def test_pre_multiline(self):
        html = "<pre>line1\nline2\nline3</pre>"
        md = _convert_html_to_markdown(html)
        assert "```" in md
        assert "line1\nline2" in md

    def test_pre_no_language(self):
        html = "<pre>plain code block</pre>"
        md = _convert_html_to_markdown(html)
        assert "```\nplain code block\n```" in md

    def test_pre_with_br(self):
        html = "<pre>line1<br/>line2</pre>"
        md = _convert_html_to_markdown(html)
        assert "line1\nline2" in md

    def test_pre_numeric_entities(self):
        html = "<pre>a &#39;b&#39; c &#x2F; d</pre>"
        md = _convert_html_to_markdown(html)
        assert "a 'b' c / d" in md

    def test_inline_code_not_multiline(self):
        html = "<p>text</p>\n<code>line1\nline2</code>\n<p>more</p>"
        md = _convert_html_to_markdown(html)
        assert "`line1\nline2`" not in md


class TestFilterXThreadTweets:
    def test_keeps_root_author_chain_in_order(self):
        tweets = [
            {"author": "@megacrit", "text": "(1/4) hello"},
            {"author": "@someone", "text": "a reply"},
            {"author": "@megacrit", "text": "(2/4) world"},
        ]
        assert filter_x_thread_tweets(tweets) == [
            {"author": "@megacrit", "text": "(1/4) hello"},
            {"author": "@megacrit", "text": "(2/4) world"},
        ]

    def test_empty_input_returns_empty(self):
        assert filter_x_thread_tweets([]) == []

    def test_no_root_author_keeps_all(self):
        tweets = [{"author": "", "text": "a"}, {"author": "@b", "text": "b"}]
        assert len(filter_x_thread_tweets(tweets)) == 2


class TestBuildXThreadHtml:
    def test_escapes_html_in_text(self):
        out = build_x_thread_html([{"author": "@a", "text": "<b>bold</b> & more"}])
        assert "<b>bold</b>" not in out
        assert "&lt;b&gt;bold&lt;/b&gt; &amp; more" in out

    def test_skips_tweets_without_text(self):
        out = build_x_thread_html([{"author": "@a", "text": ""}, {"author": "@a", "text": "hi"}])
        assert out.count("<p><strong>@a</strong></p>") == 1

    def test_joins_blocks_with_hr(self):
        out = build_x_thread_html([
            {"author": "@a", "text": "one"},
            {"author": "@a", "text": "two"},
        ])
        assert "<hr>" in out
        assert "one" in out and "two" in out

    def test_empty_input_returns_empty_string(self):
        assert build_x_thread_html([]) == ""

    def test_dedupes_adjacent_identical_tweets(self):
        out = build_x_thread_html([
            {"author": "@a", "text": "same"},
            {"author": "@a", "text": "same"},
            {"author": "@a", "text": "diff"},
        ])
        assert out.count("same") == 1
        assert "diff" in out


class TestParseXTweetLines:
    """x.com 未登录页已剥离 data-testid/div[lang]，只能解析 article innerText 行."""

    def test_parses_handle_date_and_text(self):
        lines = [
            "Mega Crit on X:",
            "@MegaCrit",
            "3月20日",
            "The first BIG balance pass is out!",
            "Patch notes below.",
            "216",
            "285",
        ]
        d = _parse_x_tweet_lines(lines)
        assert d["author"] == "@MegaCrit"
        assert d["text"] == "The first BIG balance pass is out!\nPatch notes below."

    def test_no_handle_returns_empty(self):
        assert _parse_x_tweet_lines(["hello world"]) == {"author": "", "text": ""}

    def test_stops_at_engagement_noise(self):
        lines = ["@a", "real content here", "Views", "should be dropped"]
        assert _parse_x_tweet_lines(lines)["text"] == "real content here"

    def test_stops_at_pure_number_line(self):
        lines = ["@a", "line one", "5179", "ignored"]
        assert _parse_x_tweet_lines(lines)["text"] == "line one"

    def test_date_line_is_skipped_only_if_date_like(self):
        # 短行若是日期形态（3月20日 / Mar 20 / 3h）则跳过；普通短词不跳过
        assert "text" not in _parse_x_tweet_lines(["@a", "3月20日", "body"])["author"]
        d1 = _parse_x_tweet_lines(["@a", "3月20日", "body"])
        assert d1["text"] == "body"
        d2 = _parse_x_tweet_lines(["@a", "OK", "longer body text"])
        assert d2["text"] == "OK\nlonger body text"

    def test_stops_at_full_timestamp_line(self):
        lines = ["@a", "real content", "6:46 · 2026年3月21日", "dropped tail"]
        assert _parse_x_tweet_lines(lines)["text"] == "real content"

    def test_stops_at_gif_marker(self):
        lines = ["@a", "real content", "GIF", "dropped"]
        assert _parse_x_tweet_lines(lines)["text"] == "real content"


class TestBuildAuthorTextHtml:
    def test_is_same_renderer_as_x_thread_variant(self):
        posts = [{"author": "@a", "text": "one"}, {"author": "@b", "text": "two"}]
        assert build_author_text_html(posts) == build_x_thread_html(posts)
