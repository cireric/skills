import yaml
from pathlib import Path

from lib.selectors import Platform, detect_platform, is_article_page, is_list_page, load_platform_configs


_SKILL_DIR = Path(__file__).parent.parent


class TestLoadPlatformConfigs:
    def test_loads_all_platforms_from_yaml(self):
        configs = load_platform_configs(_SKILL_DIR / "platforms.yaml")
        assert set(configs.keys()) == {Platform.WECHAT, Platform.ZHIHU, Platform.JIANSHU, Platform.BILIBILI, Platform.SSPAI, Platform.GENERIC}

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


class TestIsArticlePage:
    def test_wechat_article_true(self):
        assert is_article_page("https://mp.weixin.qq.com/s/abc123") is True

    def test_wechat_list_false(self):
        assert is_article_page("https://mp.weixin.qq.com/mp/profile_ext") is False

    def test_generic_false(self):
        assert is_article_page("https://example.com/article") is False


class TestIsListPage:
    def test_wechat_list_true(self):
        assert is_list_page("https://mp.weixin.qq.com/mp/profile_ext") is True

    def test_wechat_article_false(self):
        assert is_list_page("https://mp.weixin.qq.com/s/abc123") is False

    def test_generic_false(self):
        assert is_list_page("https://example.com/article") is False
