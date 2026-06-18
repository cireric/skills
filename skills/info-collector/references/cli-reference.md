# CLI Commands Reference

| Command | Description |
|---------|-------------|
| `proceed --from X --to Y` | Run phase transition gate |
| `gateway` | Run all gateway checks standalone (useful for debugging) |
| `report [flags]` | Generate final report from analysis.json |
| `source <goal_type>` | Show recommended sources for a goal_type |
| `clean` | Remove `.workdir/` |
| `reset --phase <X>` | Reset pipeline to a given phase (scope, search, analysis, review) |

## Report Command Flags

| Flag | Description |
|------|-------------|
| `--quality` | Quality value: passed, degraded, unreviewed |
| `--search-rounds` | Number of search rounds performed |
| `--source-count` | Number of sources collected |
| `--output DIR` | Override config.json `output_dir` for this report |

## Quality Values

| Value      | Meaning                                        |
| ---------- | ---------------------------------------------- |
| passed     | Subagent review ran + gateway heuristics clean |
| degraded   | Gateway quality_heuristics fired WARN(s)       |
| unreviewed | User skipped subagent + gateway clean          |
