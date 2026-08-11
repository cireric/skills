---
name: video-download
description: >
  Video download skill — wraps yt-dlp behind a unified, tested CLI
  (skills/video-download/cli.py) to download videos from YouTube, Bilibili, Douyin,
  and 1700+ other sites; list available formats/resolutions; extract audio (mp3/m4a);
  download playlists; and fetch video metadata. Use this skill whenever the user wants
  to download or save a video from the internet — "download this video", "save this
  video", 「下载这个视频」「下载 B 站视频」「下载抖音视频」「把 YouTube 视频存下来」,
  asks what resolutions/formats a video has, or mentions yt-dlp — even if they never
  say the word "download". Never hand-build yt-dlp commands; always go through cli.py.
---

# Video Download 视频下载

You fulfill the user's video-download needs through this skill's CLI. **Never hand-build
yt-dlp commands** — always go through `cli.py`, which validates arguments, applies safe
defaults (no overwrite, no shell, single-video by default), and returns predictable exit
codes. Hand-built commands are how files get clobbered, URLs with `&` get mangled, and
format selectors go wrong.

## Environment requirements

- Requires system-installed `yt-dlp` and `ffmpeg`. Detect: `which yt-dlp ffmpeg`
- Not installed: macOS `brew install yt-dlp ffmpeg`; Linux `apt install yt-dlp ffmpeg`
  or `pipx install "yt-dlp[default]"`; Windows `winget install yt-dlp`
- **Cloudflare-protected sites** (many adult/streaming sites) need TLS-fingerprint
  impersonation: brew's yt-dlp lacks `curl_cffi`. Install one that has it
  (`pip install "yt-dlp[curl-cffi]"`) and point the CLI at it:
  `VIDEO_DOWNLOAD_YTDLP_BIN=/path/to/yt-dlp` (e.g. the repo venv's `.venv/bin/yt-dlp`),
  then pass `--impersonate` on downloads. `version` reports whether impersonation is
  available — run it first when a Cloudflare site fails.
- Unsure? Run `version` first — it reports the yt-dlp version and whether ffmpeg is present.
- CLI path: `skills/video-download/cli.py` (run from the project root)
- Run: `.venv/bin/python skills/video-download/cli.py <operation> [options] <url>`
- Exit codes: `0` success · `1` yt-dlp failed (stderr has the reason) · `2` validation/argument error

## Core workflow

1. **Clarify the request.** Users often say something vague ("把这个视频下载下来"). Ask what
   matters: which URL/ID, quality preference (default = best available; `--format` for explicit
   control), audio-only?, where to save (`--output-dir`, default: config or current dir). A bare
   video ID (e.g. `dQw4w9WgXcQ`) works too — yt-dlp resolves IDs for supported sites.
2. **Check metadata first when unsure.** If the user wants a specific resolution, or you don't
   know what the site offers, run `info <url>` before downloading — no bytes are transferred.
   Note: for **direct-file URLs** (e.g. a plain `.mp4` link, not a site page), yt-dlp's generic
   extractor reports sparse metadata — `info`/`formats` may show no duration or resolution. When
   the user needs those fields for a direct file, supplement with `ffprobe <url>` (or the
   ffmpeg-toolkit skill's `info` subcommand) — the fields are there even though yt-dlp leaves
   them empty.
3. **Run the operation.** Pick the subcommand from the quick reference below.
4. **Verify.** A successful download prints `Downloaded: <final path>`. Only claim success when
   that line names a path that exists on disk. If the file already exists, it is skipped (no
   overwrite by default) — tell the user, and offer `--overwrite` if they want a fresh copy.

## Operation quick reference

### Inspect metadata (no download)
```bash
.venv/bin/python skills/video-download/cli.py info "https://www.youtube.com/watch?v=ID"
```
Prints title, ID, uploader, duration, available resolutions.

### List formats
```bash
.venv/bin/python skills/video-download/cli.py formats "https://www.bilibili.com/video/BV1xx411c7mD"
```
Table of format_id / ext / resolution / codecs — pick a `format_id` or selector for `download --format`.

### Download a video
```bash
.venv/bin/python skills/video-download/cli.py download "https://www.youtube.com/watch?v=ID" \
  --output-dir ~/Downloads
.venv/bin/python skills/video-download/cli.py download "URL" --format "bv*[height<=1080]+ba/b"
.venv/bin/python skills/video-download/cli.py download "URL" --limit-rate 2M
```
- Defaults: single video (even if the URL sits in a playlist), best available quality, no overwrite.
- `--format` takes yt-dlp selectors: `bv*[height<=720]+ba/b` (720p), `bv*[vcodec~='^((he|a)vc|h26[45])']+ba/b`
  (H.264), or a `format_id` from `formats`. Merging separate video+audio streams requires ffmpeg.
- `--playlist` downloads the whole playlist (`--playlist-items "1:3,5"` to pick items); without it,
  only the single video is fetched.
- Auth/geo/bot walls? `--cookies-from-browser firefox` (or chrome/edge/safari) uses the browser's
  logged-in session and resolves most of them. `--proxy "socks5://127.0.0.1:1080/"` for geo workarounds.
  **Cloudflare 403?** add `--impersonate` (requires a curl_cffi-capable yt-dlp, see Environment
  requirements) — the only thing that fakes the TLS fingerprint Cloudflare checks.

### Extract audio
```bash
.venv/bin/python skills/video-download/cli.py audio "URL" --output-dir ~/Music
.venv/bin/python skills/video-download/cli.py audio "URL" --audio-format m4a
```
Extracts the audio track (default mp3; also m4a/opus/wav/flac/aac). Requires ffmpeg.

### Environment check
```bash
.venv/bin/python skills/video-download/cli.py version
```

Other flags: `--subs` (`--sub-langs "en.*,zh.*"`), `--embed-thumbnail`, `--restrict-filenames`,
`--overwrite`, `--verbose` (prints the exact yt-dlp command).

## Behavior conventions (follow these)

- **Overwrite protection**: existing files are never overwritten by default (`--no-overwrites`);
  use `--overwrite` explicitly. This is a feature, not a bug.
- **Exit codes**: `0` success · `1` yt-dlp failure (stderr has the reason) · `2` validation error.
- **Don't fabricate success**: only report a download as done when the `Downloaded:` line names a
  real path on disk. On failure, read stderr, fix the cause, retry. If the user explicitly wants an
  option the CLI doesn't expose, say so and ask before going direct — don't silently bypass the CLI.
- **Common failures** — read stderr and respond:

| Symptom in stderr | Meaning | What to do |
|---|---|---|
| `This video is DRM protected` | DRM-locked content | Not downloadable — inform the user, no workaround |
| `not available in your country` | Geo-blocked | `--proxy` or `--cookies-from-browser` |
| `Login details are needed` / `Sign in to confirm you're not a bot` | Auth wall / bot check | `--cookies-from-browser <browser>`; add `--limit-rate` and patience for bot checks |
| `try again later` / `HTTP Error 429` | Rate-limited | Wait, slow down (`--limit-rate`), fresh cookies, or proxy |
| `HTTP Error 403` | Cloudflare / anti-bot | **Escalate**: ① `--cookies-from-browser` (fresh login) → ② still 403? run `version` — if impersonation UNAVAILABLE, set `VIDEO_DOWNLOAD_YTDLP_BIN` to a `yt-dlp[curl-cffi]` build → ③ retry with `--impersonate`. Cookies alone fail because Cloudflare also checks the TLS fingerprint, which only impersonation can fake. |
| `Unsupported URL` | Not a supported site | Verify the URL is complete; update yt-dlp |
| `please report this issue` / extractor traceback | Site changed, extractor broken | Update yt-dlp (`yt-dlp -U`, or to nightly) and retry |

- **No shell**: the CLI never uses `shell=True` — URLs with `&`, `?`, quotes are safe as-is.
- **URLs starting with `-`** are rejected (they could be misread as flags) — ask the user for the full URL.
- **Privacy when bypassing anti-bot walls**: prefer `--impersonate` (TLS-fingerprint only, no browser
  credentials) over `--cookies-from-browser`; **never write browser cookies to a disk file** — they are
  the user's session credentials. If a user asks you to extract cookies via a browser, pass them in
  memory only, or use `--cookies-from-browser` with a dedicated profile.

## Config

`config.json` (in the skill dir, user-editable, not changed at runtime):

| Key | Default | Meaning |
|---|---|---|
| `output_dir` | `""` | Default output directory (empty = current working dir) |
| `format` | `""` | Default `--format` selector (empty = yt-dlp's default best-quality merge) |
| `audio_format` | `"mp3"` | Default audio codec for `audio` / `--audio-only` |
| `overwrite` | `false` | Global default for overwriting existing files |
| `metadata_timeout` | `120` | Seconds before `info`/`formats` time out |
| `default_sub_langs` | `"en.*,zh.*"` | Subtitle languages when `--subs` is given |

Format selectors and value whitelists are hard constraints in code — config.json cannot widen them.

## Tests

```bash
.venv/bin/python -m pytest skills/video-download/tests/ -v
```
Tests run against a fake yt-dlp binary (logs argv, simulates metadata and downloads) — no real
network or downloads needed.
