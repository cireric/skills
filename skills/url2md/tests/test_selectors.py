from lib.selectors import Platform, detect_platform, is_article_page, is_list_page


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
