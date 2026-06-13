# Agent Quick Reference

## Environment

- **Python 3.14** on macOS (darwin)
- **Virtualenv required**: `.venv/bin/python` for all Python commands; `pytest` installed in venv only
- **No package manager**: stdlib only, no pip dependencies beyond `pytest`

## Project Structure

```
skills/
├── tech-research/          # Python CLI skill — structured technical research reports
│   ├── research.py         # CLI entrypoint (subcommands below)
│   ├── scripts/            # Internal modules (config, models, scope_validator, reporter)
│   ├── config.json         # Pre-configured: output_dir=docs/research, lang=zh
│   ├── SCOPE.md            # Scope interview reference
│   ├── RESEARCH.md         # Research phase reference
│   ├── SKILL.md            # Skill definition & workflow
│   └── tests/              # pytest suite
└── reading-grill/          # Markdown-only skill — Socratic comprehension quiz
    ├── SKILL.md            # Skill definition (no code, no CLI)
    └── tests/              # pytest suite
```

- **Two independent skills**: no shared code between them
- **Workfiles are ephemeral**: `scope.json`, `collected.json`, `analysis.json` — generated and cleaned by CLI

## Running Tests

```bash
# All tests (165 total)
.venv/bin/python -m pytest skills/ -v

# Single skill
.venv/bin/python -m pytest skills/tech-research/tests/ -v
.venv/bin/python -m pytest skills/reading-grill/tests/ -v
```

## Tech-Research CLI

**Run from**: `skills/tech-research/` directory

| Command                                   | Purpose                                                               |
| ----------------------------------------- | --------------------------------------------------------------------- |
| `generate <analysis.json>`                | Generate Markdown report (`--draft`, `--output-dir`, `--no-validate`) |
| `validate-scope <scope.json>`             | Validate scope.json schema                                            |
| `collect <sources.json>`                  | Merge sources into collected.json                                     |
| `filter`                                  | URL-deduplicate sources in collected.json                             |
| `init-config [--output-dir D] [--lang L]` | Create config.json                                                    |
| `show-config`                             | Display current config                                                |
| `clean`                                   | Remove scope/collected/analysis.json                                  |

**Workflow** (3-phase pipeline):

1. **Scope** → `scope.json` (goal_type, audience, time_constraint)
2. **Research** → `collected.json` → `filter` for dedup → `analysis.json` (claims, cross-validation, synthesis)
3. **Report** → `generate` → Markdown report in `docs/research/`

## Reading-Grill Skill

Markdown-only — no CLI, no code. Socratic questioning in 3 layers:

- **L1 Recall** → **L2 Understanding** → **L3 Critical reflection**
- One question per turn, never correct directly
- Stop on "停" or 3 consecutive L3 passes

## Testing Conventions

- `conftest.py` adds skill dir to `sys.path` for imports
- `tmp_path` fixture for file isolation
- `monkeypatch` to override `_SKILL_DIR` in integration tests
- CLI tests construct `Namespace` args directly (no subprocess)

## Task Planning Workflow

按任务复杂度选择规划方式。详见 `docs/task-planning-workflow.md`。

核心规则：grill-with-docs 不可跳过；每层约束逐级收紧；同文件 issue 串行执行。

## Common Mistakes

1. **Use venv Python**: always `.venv/bin/python`, never bare `python`
2. **Don't commit workfiles**: `scope.json`, `collected.json`, `analysis.json`, `docs/research/` are gitignored
3. **Don't modify config.json during research**: pre-configured; changes break reproducibility
4. **Path handling**: use `Path`, resolve early; `output_dir` resolved against project root (where `.git` is)
5. **URL normalization**: `_normalize_url()` lowercases, strips www, sorts query params — affects dedup
6. **Run CLI from skill dir**: `cd skills/tech-research` before running `research.py`
