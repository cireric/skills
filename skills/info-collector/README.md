# Info-Collector

结构化技术调研 pipeline。从 web 源收集、组织、综合信息，生成带有可追溯来源的全景地图——深度研究的起点，而非可引用的权威。

## 定位

Info-collector 产出的报告是 **research starting point**，不是 citable authority。核心转变：从"消除虚构"到"让虚构可见"。

- 报告中 † 标记 = 数据未在来源中找到
- 报告中 ‡ 标记 = 数据来自间接来源
- `verification_required: true` 写入 front matter，提醒后续使用者需要自行验证

## 注意事项

- **不要盲信报告中的数字**：即使通过全部门禁，仍可能存在 fabrication。门禁验证的是结构，不是语义真实性
- **review gate 不再阻塞**：claim_verified 已降级为 WARN，review→review 自循环为 no-op（advisory-only）
- **source_verification 由代码计算**：三级别分类（source_confirmed / source_absent / source_indirect）由确定性代码完成，不经 LLM 判断。indirect 优先级高于 confirmed/absent
- **只通过 `/info-collector` 显式调用**：已移除所有自动触发词
- **`quality` 已重命名为 `review_status`**：CLI 参数 `--quality` → `--review-status`

## CLI

**运行目录**: `skills/info-collector/`

| 命令 | 用途 |
|------|------|
| `proceed --from X --to Y` | 阶段转换门禁 |
| `gateway` | 独立运行 gateway 检查 |
| `report --review-status <passed\|degraded\|unreviewed>` | 从 analysis.json 生成报告 |
| `source <goal_type>` | 推荐来源 |
| `clean` | 清除 `.workdir/` |

## 工作流

1. **Scope** → `scope.json` (topic, goal_type, depth, audience, search_directions)
2. **Search** → `collected.json` → 搜索门禁验证
3. **Analysis** → `analysis.json` → 写回 source_verification + verified → 分析门禁验证
4. **Review** → `review_report.md` → 语义检查（advisory-only，不阻塞）
5. **Final** → 报告生成（†/‡ 标记 + 验证摘要表）→ 最终门禁

详细流程见 [SKILL.md](./SKILL.md)，术语定义见 [CONTEXT.md](./CONTEXT.md)。

## 测试

```bash
# 从项目根目录
.venv\Scripts\python.exe -m pytest skills/info-collector/tests/ -v
```

## 配置

`config.json` 预配置: output_dir, default_report_language=zh, default_depth=standard。首次运行时进入 setup wizard。

## 架构决策

| ADR | 主题 |
|-----|------|
| 0005 | verified 字段 |
| 0025 | 门禁阶段职责 |
| 0026 | BLOCKER report checks 升级 |
| 0027 | ClaimValidator 门禁集成 |
| 0028 | 重新定位为 research starting point |
