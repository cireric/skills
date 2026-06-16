# Skills 合集

Agent 使用的 OpenCode skill 合集。每个 skill 独立，互不依赖。

## 环境

- **Python 3.14** on macOS (darwin)
- **Virtualenv**: `.venv/bin/python`，所有 Python 命令必须使用；`pytest` 仅安装在 venv 中
- **无包管理器**: 仅 stdlib，除 `pytest` 外无 pip 依赖

## 项目结构

```
skills/
├── info-collector/        # Python CLI skill — 结构化技术调研报告
│   ├── scripts/           # 内部模块 (cli, gateway, proceed, reporter, lib/)
│   ├── config.json        # 预配置: output_dir, lang=zh
│   ├── SKILL.md           # Skill 定义 & 工作流
│   └── tests/             # pytest 套件
├── tech-research/         # Python CLI skill — 结构化技术研究报告
│   ├── research.py        # CLI 入口
│   ├── scripts/           # 内部模块 (config, models, scope_validator, reporter)
│   ├── config.json        # 预配置: output_dir=docs/research, lang=zh
│   ├── SCOPE.md           # Scope 面谈参考
│   ├── RESEARCH.md        # Research 阶段参考
│   ├── SKILL.md           # Skill 定义 & 工作流
│   └── tests/             # pytest 套件
├── reading-grill/         # Markdown-only skill — 苏格拉底式阅读拷问
│   ├── SKILL.md           # Skill 定义 (无代码, 无 CLI)
│   └── tests/             # pytest 套件
└── book-grill/            # Markdown-only skill — 读书反思与笔记
    └── SKILL.md
```

- 各 skill 互相独立，无共享代码
- 工作文件是临时的: `scope.json`, `collected.json`, `analysis.json` — 由 CLI 生成和清理

## 运行测试

```bash
# 全部测试
.venv/bin/python -m pytest skills/ -v

# 单个 skill
.venv/bin/python -m pytest skills/tech-research/tests/ -v
.venv/bin/python -m pytest skills/reading-grill/tests/ -v
.venv/bin/python -m pytest skills/info-collector/tests/ -v
```

## Info-Collector CLI

**运行目录**: `skills/info-collector/`

| 命令 | 用途 |
|------|------|
| `proceed --from X --to Y` | 阶段转换门禁 |
| `gateway` | 独立运行 gateway 检查 |
| `report [flags]` | 从 analysis.json 生成报告 |
| `source <goal_type>` | 推荐来源 |
| `clean` | 清除 `.workdir/` |

**工作流** (3 阶段管道):

1. **Scope** → `scope.json` (topic, goal_type, depth, audience, search_directions)
2. **Search** → `collected.json` → 阶段门禁验证
3. **Analysis** → `analysis.json` → `report` → Markdown 报告

## Tech-Research CLI

**运行目录**: `skills/tech-research/`

| 命令 | 用途 |
|------|------|
| `generate <analysis.json>` | 生成 Markdown 报告 (`--draft`, `--output-dir`, `--no-validate`) |
| `validate-scope <scope.json>` | 验证 scope.json schema |
| `collect <sources.json>` | 合并来源到 collected.json |
| `filter` | URL 去重 |
| `init-config [--output-dir D] [--lang L]` | 创建 config.json |
| `show-config` | 显示当前配置 |
| `clean` | 删除 scope/collected/analysis.json |

**工作流** (3 阶段管道):

1. **Scope** → `scope.json` (goal_type, audience, time_constraint)
2. **Research** → `collected.json` → `filter` 去重 → `analysis.json`
3. **Report** → `generate` → `docs/research/` 下生成 Markdown 报告

## Reading-Grill Skill

纯 Markdown — 无 CLI，无代码。苏格拉底式拷问 3 层：

- **L1 回忆** → **L2 理解** → **L3 批判性反思**
- 每轮一问，不直接纠正
- 遇"停"或连续 3 次 L3 通过即停

## 实现细节

- **路径处理**: 使用 `Path`，尽早 resolve；`output_dir` 相对于项目根目录（含 `.git` 的目录）
- **URL 规范化**: `_normalize_url()` 小写化、去 www、排序 query params — 影响去重
- **CLI 运行目录**: 必须在对应 skill 目录下执行（如 `cd skills/tech-research` 再运行 `research.py`）
