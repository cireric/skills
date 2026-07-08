# ADR 0034: Gate Reverse-Computes collected_count from collected.json

Agents self-report `collected_count` in search_plan.json tasks, which is unverifiable — a production run showed all tasks marked collected_count=1 despite only 11 actual sources. The gate now reverse-computes each task's collected_count by matching collected.json entries to tasks: entries with `covered_directions` are matched by direction+tier; entries without `covered_directions` fall back to token-based direction matching (same logic as topic_coverage). Agent-written collected_count values are ignored. This makes it impossible to inflate compliance by self-reporting.

Status: accepted
