# Skills 合集

Agent 使用的 OpenCode skill 合集。每个 skill 独立，互不依赖。

## 环境

- **Python 3.14** on Windows/macOS
- **Virtualenv**: Windows `.venv\Scripts\python.exe`，macOS/Linux `.venv/bin/python`，所有 Python 命令必须使用；`pytest` 仅安装在 venv 中
- **无包管理器**: 仅 stdlib，除 `pytest` 外无 pip 依赖

## 项目结构

```
skills/
├── info-collector/        # 结构化技术调研报告（Python CLI）
├── reading-grill/         # 苏格拉底式阅读拷问（纯 Markdown）
└── book-grill/            # 读书反思与笔记（纯 Markdown）
```

- 各 skill 互相独立，无共享代码
- 工作文件是临时的: `scope.json`, `collected.json`, `analysis.json` — 由 CLI 生成和清理

## Skills

| Skill | 说明 | 详情 |
|-------|------|------|
| [info-collector](./skills/info-collector/README.md) | 结构化技术调研报告 | Python CLI，scope→search→analyze→review→report 管道 |
| reading-grill | 苏格拉底式阅读拷问 | 纯 Markdown，L1 回忆→L2 理解→L3 批判性反思 |
| book-grill | 读书反思与笔记 | 纯 Markdown，4 阶段类型自适应提问 |

## 运行测试

```bash
# 全部测试
.venv\Scripts\python.exe -m pytest skills/ -v

# 单个 skill
.venv\Scripts\python.exe -m pytest skills/info-collector/tests/ -v
.venv\Scripts\python.exe -m pytest skills/reading-grill/tests/ -v
```

## 实现细节

- **路径处理**: 使用 `Path`，尽早 resolve；`output_dir` 相对于项目根目录（含 `.git` 的目录）
- **URL 规范化**: `_normalize_url()` 小写化、去 www、排序 query params — 影响去重
- **CLI 运行目录**: 必须在对应 skill 目录下执行（如 `cd skills/info-collector` 再运行 `cli.py`）
