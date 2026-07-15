# Cross-ecosystem encoding contract: Fetcher encoding repair + BOM defense

DeepSeek 调查复盘发现两个编码问题：(1) 36kr/知乎源文件出现 GBK mojibake——`_fetch_requests()` 用 `requests.get()` 抓取中文站，`resp.text` 依赖 requests 的编码检测（HTTP header charset → fallback ISO-8859-1），对中文站不可靠，且此问题跨平台一致（与 Windows PowerShell 无关）；(2) subagent 用 PowerShell `[System.IO.File]::WriteAllText()` 写 JSON 时默认带 UTF-8 BOM，Python `json.loads` 不接受 BOM，导致 trust boundary 拒收。Pipeline 无 BOM 清洗层，代码中搜索 BOM/`utf-8-sig`/`\ufeff` 零结果。

## Decision

### 1. Fetcher 编码修复：`_fetch_requests` 内部二次解码

在 `_fetch_requests()` 中，对 `resp.text` 做编码可信度检查：用 `resp.content`（原始字节）尝试 UTF-8 解码，如果失败或解码结果包含大量替换字符（`\ufffd`），则用 `charset-normalizer` 检测实际编码后重新解码。修复在函数内部完成，返回值不变（仍是 `str | None`），对调用方透明。

选择 `charset-normalizer` 而非 `chardet`，因为前者是 `requests` 的官方推荐替代（requests 2.26+ 已切换），无 binary 依赖，纯 Python 实现。

此修复只影响 autonomous fetch 路径。中文社区源（知乎/微博）走 exa pipe mode，不受影响。但中文行业源（36kr 等 Tier 3）可能走 autonomous fetch fallback，此修复确保 fallback 路径的编码正确性。

### 2. BOM 防御：读取端剥离

在两处加 BOM 剥离（`content.lstrip('\ufeff')`）：

- `read_json()`（`lib/utils.py`）——所有 JSON 读取的统一入口，一处修改覆盖所有场景
- `trust_boundary.py` 的 `json.loads(raw_json)`——subagent 输入点，接收内存中的字符串，不经过 `read_json`

选择读取端防御而非写入端约束，因为：(1) 防御式设计优于约定式设计——无法控制所有写入端（subagent 可能用 PowerShell、.NET、或其他工具），但可以控制所有读取端；(2) 一处修改覆盖所有场景，而非要求每个写入端都记住用 `new UTF8Encoding($false)`。

`proceed.py` 中直接用 `json.loads(path.read_text(...))` 读取 fix_report/fix_list 的地方，应统一改用 `read_json` 以受益于 BOM 防御。

## Consequences

autonomous fetch 抓中文站不再乱码。任何来源的 BOM 污染不再阻断 JSON 解析。新增 `charset-normalizer` 依赖。`_fetch_requests` 内部逻辑略增复杂，但返回值不变，不影响调用方。

Status: accepted
