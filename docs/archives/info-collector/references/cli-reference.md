# CLI Commands Reference

| Command | Description |
|---------|-------------|
| `proceed --from X --to Y` | Run phase transition gate |
| `gateway` | Run all gateway checks standalone (useful for debugging) |
| `report [flags]` | Generate final report from analysis.json |
| `source <goal_type>` | Show recommended sources for a goal_type |
| `fetch <url> [flags]` | Fetch single URL and save as source file |
| `batch-fetch [flags]` | Batch-process multiple URLs from stdin, update collected.json |
| `clean` | Remove `.workdir/` |
| `reset --phase <X>` | Reset pipeline to a given phase (scope, search, analysis, review) |

## Fetch Command Flags

| Flag | Description |
|------|-------------|
| `--tier N` | Source tier (auto-inferred if omitted) |
| `--no-playwright` | Skip Playwright fallback |
| `--from-stdin` | Read fetched content from stdin instead of autonomous fetch |

## Batch-Fetch Command Flags

| Flag | Description |
|------|-------------|
| `--from-stdin` | Read batch JSON from stdin (array of `{url, content, tier?}`) |
| `--pending` | List URLs that still need fetching |
| `--workdir PATH` | Path to .workdir (default: auto-detect) |

## Report Command Flags

| Flag | Description |
|------|-------------|
| `--review-status` | Review outcome: passed, degraded |
| `--search-rounds` | Number of search rounds performed |
| `--source-count` | Number of sources collected |
| `--output DIR` | Override config.json `output_dir` for this report |

## Review Status Values

| Value    | Meaning                                        |
| -------- | ---------------------------------------------- |
| passed   | Independent subagent review ran + gateway clean |
| degraded | Review independence lost (same LLM wrote and reviewed); minimum level when subagent fails |
