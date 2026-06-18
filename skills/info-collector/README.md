# Info-Collector

结构化技术调研报告 skill。从 web 源收集、组织、综合信息，生成质量门控报告。

## 触发词

调研, research, 技术选型, tech selection, 竞品分析, competitive analysis, 市场分析, market research, 可行性评估, feasibility assessment, 事实核查, fact-check

斜杠命令：`/info-collector`

## CLI

**运行目录**: `skills/info-collector/`

| 命令 | 用途 |
|------|------|
| `proceed --from X --to Y` | 阶段转换门禁 |
| `gateway` | 独立运行 gateway 检查 |
| `report [flags]` | 从 analysis.json 生成报告 |
| `source <goal_type>` | 推荐来源 |
| `clean` | 清除 `.workdir/` |

## 工作流

1. **Scope** → `scope.json` (topic, goal_type, depth, audience, search_directions)
2. **Search** → `collected.json` → 阶段门禁验证
3. **Analysis** → `analysis.json` → `report` → Markdown 报告

详细流程见 [SKILL.md](./SKILL.md)。

## 测试

```bash
# 从项目根目录
.venv\Scripts\python.exe -m pytest skills/info-collector/tests/ -v
```

## 配置

`config.json` 预配置: output_dir, default_report_language=zh, default_depth=standard。首次运行时进入 setup wizard。
