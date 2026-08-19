# hash_edit dsh 插件需求文档

> 调研基础：oh-my-openagent (OmO) `packages/hashline-core` 源码（code-yeongyu/oh-my-openagent@dev，一手通读 hash-computation/constants/types/edit-operations/AGENTS.md）+ amplifthq/oh-my-dsh `packages/editor` 源码（v0.1.7，一手通读）
> 整理时间：2026-08-19 ｜ 复盘核实：2026-08-19（OmO 已升至官方仓一手源码验证）

---

## 一、问题定义（为什么要 hash_edit）

**Harness Problem**：传统行号/字符串匹配编辑要求模型从记忆中"重现已看过的内容"，而空白、格式化、并发修改都会让读取和写入之间的内容失配——这是 Agent 编辑失败的主因，不是模型能力问题。

- OmO 实测：仅更换编辑工具（hashline-edit），Grok Code Fast 1 的核心编辑成功率 **6.7% → 68.3%**
- dsh 现状：内置编辑器为 str_replace_editor（字符串替换式），同样存在此问题；且**独立形态的 hash_edit 插件在 dsh 生态中尚为空位**（oh-my-dsh 有实现，但它是完整 overlay 发行版，非独立插件）

### 1.1 与 dsh 默认编辑器 str_replace_editor 的关系

dsh 内置 `@deepseek-ai/dsh-tool-str-replace-editor`（Claude Code 同款），四命令 `view / create / str_replace / insert`，`str_replace` 要求 `old_str` **精确匹配且在文件中唯一**（制表符/空格/换行全敏感）。

**关键澄清：str_replace_editor 是"安全但脆弱"，不是"会静默损坏"**——失配或不唯一时它大声报错，不会写坏代码；问题在失败率高（模型重不出精确空白、凑不出唯一上下文）。这正是 hash_edit 要补的短板。

| 场景 | str_replace_editor | hash_edit |
|---|---|---|
| 多行大段编辑 / 长会话 / 并发修改 / CRLF 文件 | 脆弱，失败率高 | 明显更优 |
| 单行小改 / 新建文件 | 够用且更轻 | 无 create 操作，非其所长 |
| 官方 benchmark / 模型评测 | **不可替代**（V4-Pro 官方评测 minimal 环境就是它） | 不应介入评测环境 |

**结论：互补非替代。** 这决定了 AR5 共存策略——插件不强制卸载 str_replace_editor，靠系统提示词（FR7）引导多行修改优先走 hash_edit，小改/建文件仍用内置工具。6.7%→68.3% 是 Grok Code Fast 1 单点数据，机制虽模型无关，但在 DeepSeek V4 上的实际增益需按验收标准第 7 条自测验证。

---

## 二、两者原理研究

### 2.1 共同核心机制

```
读取阶段：每行渲染为「行号 + 内容哈希」锚点
    12:a1b2c3d4| function hello() {
编辑阶段：模型引用锚点（而非重写行内容）
校验阶段：应用前重读文件，逐锚点比对哈希
写入阶段：校验通过才原子写入；任何失配 → 整体中止，提示重读
```

### 2.2 实现差异对比

| 维度 | OmO hashline-edit | oh-my-dsh hash_edit（omd-editor） |
|---|---|---|
| 哈希算法 | xxHash32，**自带 `xxhash32.ts`**（优先 `Bun.hash.xxHash32`、回退纯 JS，Bun/Node 双跑）；seed=0，无字母数字行以行号为 seed 防冲突 | SHA-256 前 8 位 hex（node:crypto，零额外依赖） |
| 哈希空间 | 2 字符 / 256 值（NIBBLE_STR 字典编码） | 8 位 hex / 42 亿值，碰撞可忽略 |
| 行内容归一化 | 去除 `\r` + trimEnd（哈希不受尾空白/换行符差异影响）；额外有 BOM + LF/CRLF **canonicalization 层**（canonicalizeFileText/restoreFileText） | **无归一化**，原始行直接哈希（CRLF 文件哈希值含 `\r`） |
| 锚点格式 | `11#VK\|` 行号#2字符 | `12:a1b2c3d4\|` 行号:8hex，正则 `^([1-9]\d*):([a-f0-9]{8})$` |
| 锚点注入方式 | **hook 增强**：拦截所有 read 工具输出自动加锚（hashlineReadEnhancer，tool.execute.after） | **工具自带 read 操作**：hash_edit 自己的 `operation: 'read'` 返回带锚内容 |
| 编辑操作 | **判别联合 `replace\|append\|prepend`**，字段 `op/pos/end/lines`；pos/end 为锚点、lines 为内容；**非**逐行 `{line,hash,new_content}` 数组 | 三操作：`replace`（start/end anchor 范围替换 + **expected_anchors 全行覆盖校验**）、`insert_after`（单锚点后插入）、空 text = 删除 |
| 应用流程 | dedupeEdits → 按行号**降序**排序（避免行号位移）→ `validateLineRefs` 一次性校验全部锚点 → 检测 overlap → 逐个应用（已校验故 skipValidation）→ 返回 report（noop/dedup 计数） | 逐操作 verifyAnchor（行存在+哈希匹配）→ writeText |
| 并发防护 | 仅哈希校验，**应用前一次性校验全部锚点，失配即抛 HashlineMismatchError 整体中止** | 哈希校验 + **fs 层 version guard**：`writeText(target, after, {kind: 'replaceIfVersion', version})`，写入时再验文件版本；`ctx.waterfall('fs/edit-intent')` 允许其他插件参与版本决策 |
| 额外机制 | autocorrect（前缀/缩进/echo 剥离）、unified diff 生成、legacy 哈希兼容、流式分块（200 行/64KB） | 无（实现极简，仅锚点校验+版本守卫） |
| 错误语义 | 失配中止 + HashlineMismatchError | 明确错误信息 + 恢复引导："stale anchor ... read the file again"；系统提示词明确"陈旧锚点是安全信号，重读而非猜测" |
| 生态集成 | OmO hooks 体系；包名 `@oh-my-opencode/hashline-core`；被 `omo-opencode/src/tools/hashline-edit/` 下 ~15 个 shim 消费；Codex/Light 版**不含** | dsh 原生 seam：`ctx.tools.register` / `ctx.fs`（含沙箱策略）/ `ctx.systemPrompt.section`（order 111）/ `fs/observed` 事件 / `fs/edit-intent` waterfall |
| 灵感来源 | 受 [oh-my-pi](https://github.com/can1357/oh-my-pi) 启发 | dsh 原生实现 |
| 许可证 | **SUL-1.0（NOASSERTION，源码可见但限制衍生）** | **MIT**（可 fork 改造） |

### 2.3 关键洞察

1. **两者都达成"应用前一次性校验、失配整体中止"的原子性**，但路径不同：OmO 靠 `validateLineRefs` 批量预校验全部锚点 + overlap 检测；oh-my-dsh 靠 `expected_anchors` 全行覆盖校验（替换范围每一行锚点必须连续有序提供）。oh-my-dsh 的全覆盖要求额外逼模型"看见过"要改的每一行，杜绝盲改。
2. **version guard 是 oh-my-dsh 独有、OmO 缺失的双保险**：哈希防"读后内容变"，version guard 防"校验后、写入前内容变"（TOCTOU 窗口）。这是需求文档要向 OmO 借鉴补上的关键点。
3. **OmO 的工程化程度更高**（autocorrect 前缀/缩进/echo 剥离、dedup、overlap 检测、unified diff、BOM+LF/CRLF canonicalization、流式分块 200 行/64KB、legacy 哈希兼容）；oh-my-dsh 实现极简（仅锚点校验+版本守卫）。**融合两者最优** = OmO 的工程化套件 + oh-my-dsh 的 fs version guard。
4. **OmO 的 hook 注入方式对模型更无感**（所有读取自动带锚），oh-my-dsh 的独立 read 操作更显式但要求模型主动选择。
5. **CRLF 处理**：OmO 有 canonicalization 层（BOM + LF/CRLF 归一化）最稳；oh-my-dsh 原始哈希在行尾被外部转换（如编辑器 CRLF→LF）时会锚点失效——正常单会话内 read/verify 一致不致错，但跨编辑器协作场景有坑。FR8 采用 OmO 归一化方案正是为此。
6. **许可证决定实现路径**：OmO = SUL-1.0（源码可见但限制衍生，**不可直接 fork 改造**，仅可读源学原理）；oh-my-dsh = MIT（可 fork 改造）。故 D1 推荐路径"抽出 oh-my-dsh editor 改造"在许可上安全；OmO 仅作原理参考。

---

## 三、dsh 插件需求规格

### 3.1 目标 / 非目标

**目标**：做一个**独立的、轻量的** hash_edit dsh 插件（单包，可 `dsh plugin --profile web add` 一键安装），融合两者最优设计。
**非目标**：不重造 oh-my-dsh 整套 overlay（proposal 体系、LSP、kernel 等不在范围）；不修改 dsh 本体。

### 3.2 功能需求

| # | 需求 | 说明 |
|---|---|---|
| FR1 | 带锚读取 | `read(file_path, offset, limit)`：每行渲染 `{line}:{hash8}\|{content}`；默认 200 行、上限 1000；尾部 footer `[N more lines; resume at offset X]` 引导续读 |
| FR2 | 范围替换 | `replace(file_path, start_anchor, end_anchor, expected_anchors[], text)`：闭区间替换；expected_anchors 必须连续、有序、全覆盖、首尾吻合 start/end；text 为空 = 删除范围 |
| FR3 | 锚点后插入 | `insert_after(file_path, anchor, text)` |
| FR4 | 逐锚校验 | 应用前重读文件，逐锚验证行号存在 + 哈希一致；任何失配 → **整体中止**（不允许部分应用），错误信息含当前实际哈希 + "read the file again" 引导 |
| FR5 | 版本守卫 | 写入走 `ctx.fs.writeText` + `{kind: 'replaceIfVersion', version}`；支持 `fs/edit-intent` waterfall；发出 `fs/observed` 事件 |
| FR6 | 沙箱合规 | 复用 `ctx.fs` + `SandboxPolicyService`，映射 `FS_SANDBOX_DENIED`；不绕过 dsh 工作区/审批策略 |
| FR7 | 系统提示引导 | `ctx.systemPrompt.section` 注册工具偏好说明："多行修改优先 hash_edit；陈旧锚点是安全信号，重读而非猜测" |
| FR8 | CRLF 归一化 | **采用 OmO 方案**：哈希前去除 `\r`、trimEnd——锚点不受行尾差异影响（Windows 环境硬需求）；写入时保持文件原有行尾风格 |
| FR9 | 哈希算法 | SHA-256 前 8 位 hex（node:crypto，零依赖、42 亿空间）；归一化后内容含字母数字 → seed 固定；纯空白行退化用行号参与派生防碰撞（借鉴 OmO） |
| FR10 | 锚点注入增强（可选二期） | 提供 hook 形态：拦截 dsh 原生 read 工具输出自动加锚（对标 OmO hashlineReadEnhancer），让模型在普通读取时也拿到锚点；与 @file/mentions 类插件预留联动（引用内容渲染为 hash_edit 锚点） |
| FR11 | 工程化套件（可选二期，借鉴 OmO） | autocorrect（前缀/缩进/echo 剥离，容错模型贴错上下文）、edit dedup（去重等价编辑）、overlap 检测（拒绝重叠范围）、unified diff 输出（变更可视化）、流式分块 read（200 行/64KB，对标 OmO chunk formatter） |

### 3.3 dsh 架构集成需求

| # | 需求 |
|---|---|
| AR1 | Cordis 插件形态：`export const inject = ['tools', 'fs', 'systemPrompt']`，`apply(ctx)` 内 `ctx.tools.register(defineTool({...}))` |
| AR2 | package.json 声明 `dsh.bundle.patch`（否则装上不激活）；打 `dsh-plugin` topic 进目录 |
| AR3 | import 白名单：仅 `@deepseek-ai/cordis`、`@deepseek-ai/dsh-tools`、`@deepseek-ai/dsh-fs`、`@deepseek-ai/dsh-sandbox(-policy)`、`node:crypto` |
| AR4 | 版本锁定：明确声明支持的 dsh 版本（当前 0.1.0-rc.7），README 标注 preview 破坏性变更风险 |
| AR5 | 与 str_replace_editor 共存：不强制卸载内置编辑器，靠 FR7 的系统提示引导偏好；提供配置项可禁用内置编辑器 |

### 3.4 非功能需求

| # | 需求 | 理由 |
|---|---|---|
| NFR1 | **缓存稳定性**：同内容同参数的 read 输出必须字节级一致（哈希确定性、渲染无时间戳/随机因子） | dsh 的核心成本优势就是前缀缓存；任何非确定渲染都会打爆命中率 |
| NFR2 | **压缩友好**：锚点行是普通文本，天然兼容 dsh compaction 的确定性裁剪；工具 schema 保持精简（控制 instruction budget） | 参考 dsh-context-doctor 的账单逻辑 |
| NFR3 | 性能：SHA-256 逐行哈希在 1000 行内 <10ms；不做全文哈希缓存以外的事 | 编辑工具在热路径上 |
| NFR4 | 跨平台：Windows 原生可用（dsh 标准模式 pwsh 环境），不依赖 bash-only 特性 | 你的主力环境是 Windows；oh-my-dsh portable 版不支持原生 Windows 正是痛点 |
| NFR5 | 安全：无动态 import/require；无网络访问；不 eval；≤32KiB 源码纪律（对齐 oh-my-dsh plugin_forge 静态纪律） | 供应链可审计 |
| NFR6 | MIT 许可；附最小测试集（见第四节） | 开源发布 |

### 3.5 待决策项（需要你拍板）

| # | 决策 | 选项 A | 选项 B |
|---|---|---|---|
| D1 | 实现路径 | **从 oh-my-dsh packages/editor 抽出改造**（MIT，加归一化 + FR8/FR9/FR10，最快） | 从零写（完全掌控，但重复劳动） |
| D2 | 锚点注入策略 | 工具自带 read（oh-my-dsh 式，显式可控） | hook 增强所有读取（OmO 式，模型无感但侵入性高） |
| D3 | 发布形态 | 独立插件仓（dsh-hash-edit） | 只在自用 profile，不发布 |
| D4 | 编辑操作粒度 | 范围替换 + insert_after（oh-my-dsh 式，token 省） | 判别联合 replace/append/prepend + op/pos/end/lines（OmO 式，更灵活，含 end 可选单行替换） |

---

## 四、验收标准

1. **陈旧行拒绝**：读取后外部修改目标行 → 编辑被拒，错误信息含 expected vs actual 哈希；文件未被部分修改
2. **TOCTOU 拒绝**：校验通过后、写入前文件被改（模拟）→ version guard 拒绝写入
3. **expected_anchors 完整性**：跳行、乱序、数量不符、首尾不吻合 → 四种情况均拒绝
4. **CRLF 稳定**：同一文件 LF/CRLF 两种行尾，read→edit 全流程通过；锚点值不受行尾影响
5. **缓存稳定**：同一文件连续两次 read（无修改）输出字节级一致
6. **Windows**：在 dsh 标准 profile（pwsh）完成全流程冒烟
7. **基准对比**：构造 10 个多行编辑任务，hash_edit vs str_replace_editor 成功率对比（参考 OmO 6.7%→68.3% 的测试方法）

---

## 五、建议实现路径（若决策项均选 A）

1. Fork oh-my-dsh `packages/editor`（9.7KB 单文件，理解成本低）→ 独立仓 `dsh-hash-edit`
2. 改造点：①增加 CRLF 归一化（FR8）②空行 seed 派生（FR9）③补测试（第四节 1-5 项）
3. `dsh plugin --profile web add "github:<you>/dsh-hash-edit#main"` 自用验证
4. 达标后打 dsh-plugin topic 提交 awesome-dsh-plugin 收录——生态里这个位置还空着，首发有红利
