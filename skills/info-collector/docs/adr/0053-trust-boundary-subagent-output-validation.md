# Trust boundary: subagent output validation with retry

v3 运行中 6 个 section 有 4 个产生结构性损坏（claims 为字符串而非对象、sources 为空数组、中文引号破坏 JSON），1 个枚举值越界。根因是子代理输出未经验证即写入 section_file，损坏在后续合并/gate 阶段才被发现，此时只能整体重写 section。缺点 1/2/4 共享一个根因：**信任边界缺失**——subagent（不可信 producer）的输出直接进入 section_file（可信 artifact），中间无验证。

## Decision

引入**信任边界**（trust boundary），在子代理输出写入 section_file 之前执行两层验证：

### 1. 结构验证

- `json.loads()` 验证 JSON 合法性
- Schema 检查：`id`/`title`/`content`/`depth_strategy` 存在且类型正确
- `key_insights`/`tensions` 为对象数组且每项有 `summary` + `sources`
- `claims` 为对象数组且每项有 `summary` + `sources` + `evidence_type`（在枚举内）+ `confidence` + `precision`（在枚举内）+ `source_metadata`
- `sources` 数组非空

### 2. 语义验证

- `sources` 和 content 中 `{{ref:URL}}` 的 URL 必须精确匹配 collected.json 中的 URL
- 信任边界直接读 collected.json 获取 URL 列表，不依赖 prompt 注入

### 重试机制

验证失败时将**完整结构化验证报告**回注 prompt，重试最多 2 次。验证报告格式：

```json
{
  "validation_errors": [
    {
      "path": "claims[0]",
      "error": "type_mismatch",
      "expected": "object with {summary, sources, evidence_type, confidence, precision}",
      "actual": "string"
    }
  ],
  "retry_count": 1,
  "max_retries": 2
}
```

### 失败终态

3 次验证全失败 → BLOCK 管道（`proceed --from analysis --to review` 失败），orchestrator 手动重写 section。orchestrator 重写也失败 → section 标记 `status: "incomplete"`，review_status 必然为 `degraded`。

### 中文引号代码防御

在 `_repair_json_text()` 之前增加预处理：全角引号 `""` 替换为单角引号 `''`。这是确定性防御，不依赖 prompt 约束 LLM 行为。prompt 中的反例提示（subagent-template.md Common Mistakes）保留作为辅助。

### Prompt 反例增强

在 subagent-template.md 的 Common Mistakes 部分增加：
- `❌ "claims": ["text as string"]` → `✅ "claims": [{"summary": "...", "sources": ["url"]}]`
- `❌ 中文全角引号 ""内的内容"` → `✅ 用单引号或反引号代替`
- `❌ "evidence_type": "quantitative"` → `✅ "evidence_type": "official_data" | "independent_benchmark" | "third_party_estimate" | "qualitative_trend" | "expert_opinion"`

### 分步输出（1c）暂不实施

子代理分步输出（先 content 再 claims）保持"中"优先级。先观察信任边界实施后的实际重试率，若重试率仍高（>30%）再考虑。

## Consequences

子代理输出质量在写入前即被拦截，消除 80%+ 的 section 重写。重试增加子代理调用次数但减少总修复时间。`ref_marker_validity` 和 `claim_source_ref_coverage` 保留在 gate 中作为防御纵深——正常路径上不会触发，但能拦截绕过信任边界的情况（如手动编辑 section_file）。不取代任何旧 ADR。

Status: accepted
