import yaml
from pathlib import Path

from lib.selectors import Platform, detect_platform, is_article_page, is_list_page, load_platform_configs


_SKILL_DIR = Path(__file__).parent.parent


class TestLoadPlatformConfigs:
    def test_loads_all_platforms_from_yaml(self):
        configs = load_platform_configs(_SKILL_DIR / "platforms.yaml")
        assert set(configs.keys()) == {Platform.WECHAT, Platform.ZHIHU, Platform.JIANSHU, Platform.BILIBILI, Platform.SSPAI, Platform.REDDIT, Platform.XTWITTER, Platform.GENERIC}

    def test_wechat_config_has_required_fields(self):
        configs = load_platform_configs(_SKILL_DIR / "platforms.yaml")
        wc = configs[Platform.WECHAT]
        for key in ["name", "article_patterns", "list_patterns", "article_selector", "title_selector", "author_selector", "date_selector", "list_link_selector", "needs_scroll", "wait_selector", "tail_noise_markers", "noise_html_patterns", "keep_query_params", "wait_until"]:
            assert key in wc, f"wechat config missing key: {key}"

    def test_generic_has_tail_noise_markers(self):
        configs = load_platform_configs(_SKILL_DIR / "platforms.yaml")
        assert "tail_noise_markers" in configs[Platform.GENERIC]
        assert isinstance(configs[Platform.GENERIC]["tail_noise_markers"], list)

    def test_custom_yaml_path(self, tmp_path):
        yaml_content = {
            "platforms": {
                "generic": {
                    "name": "Test",
                    "article_patterns": [],
                    "list_patterns": [],
                    "article_selector": "article",
                    "title_selector": "h1",
                    "author_selector": ".author",
                    "date_selector": ".date",
                    "list_link_selector": "a",
                    "needs_scroll": False,
                    "tail_noise_markers": [],
                }
            }
        }
        p = tmp_path / "platforms.yaml"
        p.write_text(yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8")
        configs = load_platform_configs(p)
        assert configs[Platform.GENERIC]["name"] == "Test"


class TestDetectPlatform:
    def test_wechat_article(self):
        assert detect_platform("https://mp.weixin.qq.com/s/abc123") == Platform.WECHAT

    def test_wechat_list(self):
        assert detect_platform("https://mp.weixin.qq.com/mp/profile_ext") == Platform.WECHAT

    def test_zhihu_article(self):
        assert detect_platform("https://zhuanlan.zhihu.com/p/12345") == Platform.ZHIHU

    def test_zhihu_answer_article(self):
        assert detect_platform("https://www.zhihu.com/question/12345/answer/67890") == Platform.ZHIHU

    def test_zhihu_question_list(self):
        assert detect_platform("https://www.zhihu.com/question/12345") == Platform.ZHIHU

    def test_zhihu_question_list_with_query(self):
        assert detect_platform("https://www.zhihu.com/question/12345?sort=vote_count") == Platform.ZHIHU

    def test_zhihu_question_list_trailing_slash(self):
        # 回归：带尾斜杠的问题页 URL 不得被误判为 GENERIC
        assert detect_platform("https://www.zhihu.com/question/12345/") == Platform.ZHIHU
        assert is_list_page("https://www.zhihu.com/question/12345/") is True

    def test_zhihu_answer_article_trailing_slash(self):
        assert detect_platform("https://www.zhihu.com/question/12345/answer/67890/") == Platform.ZHIHU

    def test_jianshu_article(self):
        assert detect_platform("https://www.jianshu.com/p/abc123") == Platform.JIANSHU

    def test_bilibili_article(self):
        assert detect_platform("https://www.bilibili.com/read/cv12345") == Platform.BILIBILI

    def test_sspai_article(self):
        assert detect_platform("https://sspai.com/post/111297") == Platform.SSPAI

    def test_sspai_list(self):
        assert detect_platform("https://sspai.com/matrix") == Platform.SSPAI

    def test_generic(self):
        assert detect_platform("https://example.com/article") == Platform.GENERIC


class TestRedditPlatform:
    def test_www_reddit_comments_article(self):
        url = "https://www.reddit.com/r/slaythespire/comments/17rn2ie/what_design_choices_makes_slay_the_spire_one_of/"
        assert detect_platform(url) == Platform.REDDIT
        assert is_article_page(url) is True

    def test_old_reddit_comments_article(self):
        url = "https://old.reddit.com/r/IAmA/comments/aj6sq1/were_mega_crit_games_creators_of_slay_the_spire/"
        assert detect_platform(url) == Platform.REDDIT
        assert is_article_page(url) is True

    def test_short_comments_url(self):
        # 无 r/ 子版块前缀、无标题 slug 的短链接也是文章页
        url = "https://www.reddit.com/comments/17rn2ie/"
        assert detect_platform(url) == Platform.REDDIT
        assert is_article_page(url) is True

    def test_subreddit_page_not_article(self):
        assert is_article_page("https://www.reddit.com/r/slaythespire/") is False

    def test_config_has_required_fields(self):
        configs = load_platform_configs(_SKILL_DIR / "platforms.yaml")
        rc = configs[Platform.REDDIT]
        for key in ["name", "article_patterns", "list_patterns", "article_selector", "title_selector", "author_selector", "date_selector", "list_link_selector", "needs_scroll", "tail_noise_markers", "noise_html_patterns", "keep_query_params", "wait_until"]:
            assert key in rc, f"reddit config missing key: {key}"


class TestXTwitterPlatform:
    def test_x_status_article(self):
        url = "https://x.com/MegaCrit/status/2035125930876678627"
        assert detect_platform(url) == Platform.XTWITTER
        assert is_article_page(url) is True

    def test_twitter_com_status_article(self):
        url = "https://twitter.com/MegaCrit/status/1234567890"
        assert detect_platform(url) == Platform.XTWITTER
        assert is_article_page(url) is True

    def test_x_profile_not_article(self):
        assert is_article_page("https://x.com/MegaCrit") is False

    def test_config_has_required_fields(self):
        configs = load_platform_configs(_SKILL_DIR / "platforms.yaml")
        xc = configs[Platform.XTWITTER]
        for key in ["name", "article_patterns", "list_patterns", "article_selector", "title_selector", "author_selector", "date_selector", "list_link_selector", "needs_scroll", "tail_noise_markers", "noise_html_patterns", "keep_query_params", "wait_until"]:
            assert key in xc, f"x config missing key: {key}"


class TestRedditSelectorsAgainstNewDom:
    """www.reddit.com 新版 DOM（shreddit web components）选择器约定."""

    def test_title_uses_title_slot(self):
        configs = load_platform_configs(_SKILL_DIR / "platforms.yaml")
        assert "[slot='title']" in configs[Platform.REDDIT]["title_selector"]

    def test_content_targets_main_landmark(self):
        configs = load_platform_configs(_SKILL_DIR / "platforms.yaml")
        assert "main" in configs[Platform.REDDIT]["article_selector"]

    def test_wait_selector_targets_shreddit_post(self):
        # 回归：old.reddit 已登录墙化，必须走 www 新 DOM 且等待 shreddit-post 水合完成，
        # 否则 SPA 导航会打断 page.evaluate（Execution context destroyed）
        configs = load_platform_configs(_SKILL_DIR / "platforms.yaml")
        assert "shreddit-post" in configs[Platform.REDDIT].get("wait_selector", "")


class TestIsArticlePage:
    def test_wechat_article_true(self):
        assert is_article_page("https://mp.weixin.qq.com/s/abc123") is True

    def test_wechat_list_false(self):
        assert is_article_page("https://mp.weixin.qq.com/mp/profile_ext") is False

    def test_generic_false(self):
        assert is_article_page("https://example.com/article") is False

    def test_zhihu_answer_true(self):
        assert is_article_page("https://www.zhihu.com/question/12345/answer/67890") is True

    def test_zhihu_question_false(self):
        assert is_article_page("https://www.zhihu.com/question/12345") is False

    def test_zhihu_question_query_false(self):
        assert is_article_page("https://www.zhihu.com/question/12345?sort=vote_count") is False

    def test_zhihu_column_true(self):
        assert is_article_page("https://zhuanlan.zhihu.com/p/12345") is True


class TestIsListPage:
    def test_wechat_list_true(self):
        assert is_list_page("https://mp.weixin.qq.com/mp/profile_ext") is True

    def test_wechat_article_false(self):
        assert is_list_page("https://mp.weixin.qq.com/s/abc123") is False

    def test_generic_false(self):
        assert is_list_page("https://example.com/article") is False

    def test_zhihu_question_true(self):
        assert is_list_page("https://www.zhihu.com/question/12345") is True

    def test_zhihu_question_query_true(self):
        assert is_list_page("https://www.zhihu.com/question/12345?sort=vote_count") is True

    def test_zhihu_answer_false(self):
        assert is_list_page("https://www.zhihu.com/question/12345/answer/67890") is False

    def test_zhihu_column_false(self):
        assert is_list_page("https://zhuanlan.zhihu.com/p/12345") is False
