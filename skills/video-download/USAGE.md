# video-download 使用指南

封装 yt-dlp 的视频下载技能。从 YouTube、B 站、抖音等 1700+ 站点下载视频、查元数据、提取音频。
所有命令参数白名单校验、默认安全（不覆盖文件、无 shell、单视频），错误码可预期。

## 前置条件

- `yt-dlp`（macOS：`brew install yt-dlp`；Linux：`apt install yt-dlp` 或 `pipx install "yt-dlp[default]"`；Windows：`winget install yt-dlp`）
- `ffmpeg`（合并音视频流、提取音频必需）

验证环境：

```bash
.venv/bin/python skills/video-download/cli.py version
```

输出 yt-dlp 版本 + ffmpeg 路径，两者都在才可完整工作。

## 运行方式

### 斜杠命令（对话中直接调用）

skill 已注册为斜杠命令，在对话里输入：

```
/video-download 把这个视频下载到桌面：https://www.bilibili.com/video/BVxxxxxx
/video-download 把 https://youtu.be/xxxx 转成 mp3
```

参数直接跟在斜杠命令后面用自然语言描述即可，agent 会解析出 URL/清晰度/输出目录并调用 CLI。

### 自然语言触发（agent 自动加载）

无需显式调用。用户说「下载这个视频」「把 YouTube 视频存下来」「这个视频要 mp3」等，agent 会根据 SKILL.md 的 description 自动加载本技能并使用 CLI。

### 直接命令行（绕过 agent）

所有命令从项目根目录执行，Python 一律用 venv：

```bash
.venv/bin/python skills/video-download/cli.py <操作> [选项] <URL>
```

## 操作速查

### 下载视频（最常用）

```bash
# 默认：单视频、最佳质量、不覆盖已存在文件
.venv/bin/python skills/video-download/cli.py download "https://www.youtube.com/watch?v=ID" --output-dir ~/Downloads

# 指定清晰度（720p）
.venv/bin/python skills/video-download/cli.py download "URL" --format "bv*[height<=720]+ba/b"

# 限速（避免被封）
.venv/bin/python skills/video-download/cli.py download "URL" --limit-rate 2M
```

成功时输出 `Downloaded: <完整路径>`——看到这行才算成功。

### 提取音频

```bash
.venv/bin/python skills/video-download/cli.py audio "URL" --output-dir ~/Music
.venv/bin/python skills/video-download/cli.py audio "URL" --audio-format m4a   # 默认 mp3，可选 m4a/opus/wav/flac/aac
```

### 查元数据（不下载）

```bash
.venv/bin/python skills/video-download/cli.py info "URL"      # 标题/时长/分辨率
.venv/bin/python skills/video-download/cli.py formats "URL"   # 格式表（format_id/编码）
```

下载前不确定画质时先跑 `info`。

### 播放列表

```bash
# 默认单视频，加 --playlist 才整单下载
.venv/bin/python skills/video-download/cli.py download "播放列表URL" --playlist --playlist-items "1:3,5"
```

## 常见场景

| 场景 | 命令 |
|---|---|
| 下载 B 站视频到桌面 | `download "https://www.bilibili.com/video/BV..." --output-dir ~/Desktop` |
| 要 1080p | `download "URL" --format "bv*[height<=1080]+ba/b"` |
| 视频转 mp3 | `audio "URL" --output-dir ~/Music` |
| 带中英字幕 | `download "URL" --subs --sub-langs "en.*,zh.*"` |
| 封面图内嵌 | `download "URL" --embed-thumbnail` |
| 登录/年龄限制/机器人检测 | `download "URL" --cookies-from-browser chrome` |
| Cloudflare 403 反爬 | `download "URL" --impersonate`（需 curl_cffi 版 yt-dlp，见下方说明） |
| 地区限制 | `download "URL" --proxy "socks5://127.0.0.1:1080/"` |
| 文件名纯 ASCII（跨平台安全） | `download "URL" --restrict-filenames` |

### Cloudflare 站点下载（`--impersonate`）

部分站点（missav 等流媒体/成人站）用 Cloudflare 反爬，会同时校验 TLS 指纹——仅靠 cookies 也会 403。
解法：用一个带 curl_cffi 的 yt-dlp，并加 `--impersonate`：

```bash
# ① 安装带 curl_cffi 的 yt-dlp（brew 版不带）
.venv/bin/pip install "yt-dlp[curl-cffi]"

# ② 指向它并加 --impersonate
VIDEO_DOWNLOAD_YTDLP_BIN=.venv/bin/yt-dlp \
  .venv/bin/python skills/video-download/cli.py download "URL" --impersonate --output-dir ~/Downloads

# ③ 先跑 version 确认 impersonation 可用
VIDEO_DOWNLOAD_YTDLP_BIN=.venv/bin/yt-dlp .venv/bin/python skills/video-download/cli.py version
```

`version` 会报告 impersonation 是否可用（available / UNAVAILABLE）。

### 反爬绕过：安全优先级

| 手段 | 隐私风险 | 说明 |
|---|---|---|
| `--impersonate`（首选） | **低** | 纯 TLS 指纹伪装，不碰浏览器凭据，最干净 |
| `--cookies-from-browser` | 中 | 会带上真实浏览器 session；尽量用专用 profile，别用日常主浏览器 |
| 浏览器导出 cookies 喂给 yt-dlp | 中高 | **cookies 只允许在内存中传递，禁止落盘到文件**——它们是你的浏览器会话凭据 |
| 代理 + 一次性环境 | 最低 | 下载流量与日常网络隔离 |

两条底线：
1. **cookies 绝不写入磁盘文件**（会泄露浏览器会话凭据）；如需透传，用 `--cookies-from-browser` 或内存传递
2. **`--impersonate` 能过的就别用 cookies**——指纹伪装优先，减少真实浏览器凭据暴露面

## 常见错误速查（看 stderr）

| 报错 | 含义 | 处理 |
|---|---|---|
| `This video is DRM protected` | DRM 加密 | 无解，告知用户 |
| `not available in your country` | 地区限制 | `--proxy` 或 `--cookies-from-browser` |
| `Login details are needed` / `Sign in to confirm you're not a bot` | 登录墙/机器人检测 | `--cookies-from-browser` + 限速 |
| `try again later` / `HTTP Error 429` | 被限流 | 等待、`--limit-rate` 降速、换 cookies |
| `Unsupported URL` | 站点不支持 | 确认 URL 完整；`yt-dlp -U` 升级 |
| `please report this issue` | 站点改版，extractor 坏了 | `yt-dlp -U` 升级（或 nightly）后重试 |

## 测试

```bash
.venv/bin/python -m pytest skills/video-download/tests/ -v
```

26 个单元测试用 fake yt-dlp 二进制验证命令构建与校验逻辑，不依赖真实网络。

## 配置

`skills/video-download/config.json`（用户可编辑，运行期不被改写）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `output_dir` | `""` | 默认输出目录（空 = 当前目录） |
| `format` | `""` | 默认 `--format` 选择器（空 = yt-dlp 默认最佳质量合并） |
| `audio_format` | `"mp3"` | 默认音频编码 |
| `overwrite` | `false` | 全局默认是否覆盖已存在文件 |
| `metadata_timeout` | `120` | `info`/`formats` 超时秒数 |
| `default_sub_langs` | `"en.*,zh.*"` | `--subs` 时的字幕语言 |

格式选择器与取值范围是代码内硬约束，config.json 无法放宽。
