# ADR 0001: Video Download Skill Design

Status: Accepted
Date: 2026-08-10

## Background

The user needs a reusable skill to download videos from YouTube, Bilibili and other sites.
yt-dlp is a powerful external CLI (installed via Homebrew) but agent-built raw commands are
error-prone: wrong format selectors, overwriting files, shell injection via URLs with `&`,
and unparseable output. Facts verified against the yt-dlp README and source at commit
`5d6b8c8` (latest release 2026.07.04); key behaviors (`-J` clean JSON, `--print
after_move:filepath`, exit codes 0/1/2, `-x` audio extraction) verified empirically against
the local binary before this ADR was written.

## Decisions

### 1. Python CLI wrapper, not raw yt-dlp instructions

- stdlib `subprocess` wraps the system yt-dlp binary; the repo rule "仅 stdlib，除 pytest
  外无 pip 依赖" stays intact (yt-dlp is an external binary like ffmpeg, not a pip dep)
- argument whitelists and range validation are hardcoded in code; config.json holds only
  user defaults, never safety constraints
- tested via a fake yt-dlp script + monkeypatched `YTDLP_BIN`, matching the ffmpeg-toolkit
  test harness convention

被取代方案: pure-Markdown instruction skill (command correctness relies on agent
self-discipline, untestable).

### 2. Subcommand design

| Subcommand | Purpose | Key options |
|---|---|---|
| `info` | metadata via `-J` (title/duration/resolutions) | — |
| `formats` | format table via `-J` | — |
| `download` | video download | `--output-dir`, `--format`, `--playlist` + `--playlist-items`, `--limit-rate`, `--cookies-from-browser`, `--cookies`, `--proxy`, `--subs` + `--sub-langs`, `--embed-thumbnail`, `--restrict-filenames`, `--audio-only`, `--overwrite` |
| `audio` | download + extract audio (`-x --audio-format`) | same as download |
| `version` | environment check (yt-dlp + ffmpeg presence) | — |

### 3. Machine-readable interface

- metadata: `yt-dlp -J` — clean JSON on stdout (implies quiet); parse stdout only, never
  progress/status text (README explicitly warns against parsing normal stdout)
- download result: `--print after_move:filepath` — prints the final file path per video on
  stdout; verified empirically that it does NOT imply simulate (real download + path printed)
- `--no-progress` keeps captured stdout clean
- exit codes: `0` success · `1` yt-dlp failure · `2` validation/argument error (argparse
  SystemExit normalized to 2 so `cli.main()` always returns an int)

### 4. Safety and defaults

- no `shell=True`; args passed as a list; URLs starting with `-` rejected
- no overwrite by default (`--no-overwrites`); `--overwrite` maps to `--force-overwrites`
- single video by default (`--no-playlist`); `--playlist` opts into full playlists
- output dir auto-created; metadata calls time out (config `metadata_timeout`, default 120s)
- `YTDLP_BIN` is a module-level `shutil.which` result, monkeypatchable in tests
- common site failure modes (DRM/geo/login/bot-check/429/403/extractor breakage) documented
  in SKILL.md with concrete remedies, so the agent recovers without guessing

## Consequences

- predictable, tested command surface; the agent cannot build destructive commands
- a wrapper layer on top of yt-dlp means new operations require code + tests
- yt-dlp itself updates independently (brew/pip); `version` surfaces drift and missing ffmpeg
