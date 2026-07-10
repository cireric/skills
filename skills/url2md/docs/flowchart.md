```
┌─────────────────────────────────────────────────────────────────────────────┐
│  crawl.py — CLI 入口                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  用户 /url2md <URL> [flags]                                                 │
│       │                                                                     │
│       ▼                                                                     │
│  stdout.reconfigure(utf-8)                                                  │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─ --preflight ? ─┐                                                        │
│  │ yes              │ no                                                     │
│  ▼                  ▼                                                        │
│  preflight_check()  load_config("config.yaml")                              │
│  · config.yaml 存在?                                                        │
│  · playwright 装包?                                                         │
│  · 系统 Chrome 存在?                                                        │
│  · pyyaml 装包?                                                             │
│  · (strict) aiohttp/aiofiles?     │                                        │
│       │                            ▼                                        │
│  ┌─ OK? ─┐                    合并 CLI flags + config                       │
│  │ OK    │ FAIL                    │                                        │
│  ▼      ▼                         ▼                                        │
│  exit 0  exit 1              crawl_url(url, **kwargs)                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  api.py — 路由 + 同步桥接                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  crawl_url(url, output_dir, download_images, ...)                           │
│       │                                                                     │
│       ▼                                                                     │
│  detect_platform(url)                                                       │
│  URL 正则匹配 → WECHAT / ZHIHU / JIANSHU / BILIBILI / GENERIC              │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────── URL 类型? ───────────┐                                        │
│  │ 文章页        │ 列表页       │ 未知  │                                    │
│  ▼              ▼              ▼      │                                    │
│  _crawl_article _crawl_list_page  兜底→_crawl_article                       │
│       │              │                                                     │
│       └──────┬───────┘                                                     │
│              ▼                                                              │
│  _run_async() → configure_asyncio() → asyncio.run()                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  browser.py — Playwright 管理                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BrowserManager(headless=True)                                              │
│       │                                                                     │
│       ▼                                                                     │
│  playwright.chromium.launch(                                                │
│      channel="chrome",                                                      │
│      args=[--disable-blink-features=AutomationControlled,                   │
│            --disable-dev-shm-usage,                                         │
│            --no-sandbox]                                                    │
│  )                                                                         │
│       │                                                                     │
│       ▼                                                                     │
│  browser.new_context(                                                       │
│      user_agent=Chrome/120, viewport=1920×1080,                             │
│      locale=zh-CN, timezone=Asia/Shanghai,                                 │
│      cookies ← cookies_file (可选)                                          │
│  )                                                                         │
│       │                                                                     │
│       ▼                                                                     │
│  context.new_page()                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  核心抓取流程 — 文章页                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  page.goto(url, wait_until="networkidle")                                   │
│       │                                                                     │
│       ▼                                                                     │
│  _scroll_page() — 逐屏滚动加载懒加载内容                                     │
│       │                                                                     │
│       ▼                                                                     │
│  extract_article(page, platform)                                            │
│  ┌─────────────────────────────────────────────┐                            │
│  │  读取平台配置 (selectors.py)                  │                            │
│  │  · title_selector  → page.query_selector     │                            │
│  │  · author_selector → page.query_selector     │                            │
│  │  · date_selector   → page.query_selector     │                            │
│  │  · article_selector→ inner_html              │                            │
│  │  · img[data-src|src] → clean_image_url()     │                            │
│  │      (保留 wx_fmt/tp 参数, 去其余参数)       │                            │
│  └─────────────────────────────────────────────┘                            │
│       │                                                                     │
│       ▼                                                                     │
│  ArticleData(title, author, date, url, content_html, images[])              │
│       │                                                                     │
│       ▼                                                                     │
│  ┌── download_images ? ──┐                                                  │
│  │ yes                │ no │                                                 │
│  ▼                    │   │                                                  │
│  downloader.py        │   │                                                  │
│  ┌──────────────────┐ │   │                                                  │
│  │ URL 去重 (path)  │ │   │                                                  │
│  │        ▼         │ │   │                                                  │
│  │ aiohttp 并发下载 │ │   │                                                  │
│  │ Semaphore(3)     │ │   │                                                  │
│  │        ▼         │ │   │                                                  │
│  │ 指数退避重试     │ │   │                                                  │
│  │ (max_retries=3)  │ │   │                                                  │
│  │        ▼         │ │   │                                                  │
│  │ Content-Type     │ │   │                                                  │
│  │ → 扩展名校正     │ │   │                                                  │
│  │        ▼         │ │   │                                                  │
│  │ 保存本地文件     │ │   │                                                  │
│  │        ▼         │ │   │                                                  │
│  │ content 中远程URL│ │   │                                                  │
│  │ → 本地相对路径   │ │   │                                                  │
│  │ (正斜杠)         │ │   │                                                  │
│  └──────────────────┘ │   │                                                  │
│       └───────────────┘   │                                                  │
│               ▼           ▼                                                  │
│          convert_to_markdown(article, platform)                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  extractor.py — Markdown 生成管线                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  HTML 原文                                                                  │
│       │                                                                     │
│       ▼                                                                     │
│  ① remove_noise_elements()  — HTML 阶段正则清理                             │
│     · <div class="ad|qr-code|recommend">                                    │
│     · <section class="js_ad|mp_profile_popup">                              │
│     · <a class="appmsg_card">                                               │
│       │                                                                     │
│       ▼                                                                     │
│  ② _convert_html_to_markdown() — 24 步正则替换                              │
│     · h1-h6 → # ~ ######                                                   │
│     · strong/b → ** **                                                      │
│     · em/i → * *                                                            │
│     · p → 段落, br → 换行                                                   │
│     · ul/ol/li → 列表                                                       │
│     · <a href> → [text](url)                                                │
│     · <img> → ![alt](url){width="600"}                                      │
│     · &nbsp; &amp; &lt; &gt; → 实体解码                                     │
│     · 剥除残余 HTML 标签                                                     │
│     · 合并多余空行                                                           │
│       │                                                                     │
│       ▼                                                                     │
│  ③ truncate_tail_noise(content, markers)  — 文末噪音截断                     │
│     · 扫描最后 30 行                                                         │
│     · 匹配平台噪音标记词:                                                    │
│       好文推荐 / 会议推荐 / 广告 / 推广 / 扫码关注                           │
│       阅读原文 / 转载请联系 / ...                                            │
│     · 从首个匹配行截断, 回吃上方空行                                          │
│       │                                                                     │
│       ▼                                                                     │
│  ④ 拼装最终 Markdown                                                        │
│     # {title}                                                               │
│     **作者：** {author}                                                      │
│     **发布时间：** {date}                                                    │
│     **来源：** {url}                                                         │
│     ---                                                                     │
│     {正文}                                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  输出                                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  sanitize_filename(title)  — 去非法字符, 空格→_, 截断 200 字符              │
│       │                                                                     │
│       ▼                                                                     │
│  写入 <output_dir>/<filename>.md  (utf-8)                                   │
│       │                                                                     │
│       ▼                                                                     │
│  CrawlResult(success, files[], error, article_count)                         │
│       │                                                                     │
│       ▼                                                                     │
│  报告用户: "已保存到: <path>"                                                │
│       + JSON 行: ["<path>"]                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
  列表页分支 (与文章页并行)
═══════════════════════════════════════════════════════════════════════════════

  page.goto(list_url, networkidle)
       │
       ▼
  extract_list_links(page, platform)
  ┌──────────────────────────────────────────────┐
  │  needs_scroll?                                │
  │  ├─ yes: 增量滚动, 每次收集新 <a> href        │
  │  │        直到连续 3 次无新链接                │
  │  └─ no:  一次性收集                           │
  │       │                                       │
  │       ▼                                       │
  │  is_article_page() 过滤非文章链接              │
  │       │                                       │
  │       ▼                                       │
  │  limit 截断                                   │
  └──────────────────────────────────────────────┘
       │
       ▼
  page.close()
       │
       ▼
  for link in links:
      ├── sleep(random(delay, delay+3))  ← 请求间随机延迟
      └── crawl_single_article(link)     ← 复用同一 BrowserManager
              │
              ▼
         (进入上方"核心抓取流程 — 文章页")
```
