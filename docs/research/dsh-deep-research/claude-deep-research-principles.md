# Claude Deep Research 原理与架构

> 基于 Moksa《Claude Research 完整教學：Multi Agent 6 大應用情境》与 Anthropic 官方《How we built our multi-agent research system》整理。
>
> 本文重点不是介绍产品操作，而是从 **Agent Architecture / Tool Use / Context / Planning / Evaluation** 的角度，抽象 Claude Research / Deep Research 的可迁移原理。

---

## 1. 核心结论

**Claude Deep Research 本质上不是“更强的联网搜索”，而是一个 Long-Running Agent System（长程 Agent 系统）。**

其核心结构可以抽象为：

```text
User Question
    ↓
Research Planner / Lead Agent
    ↓
Problem Decomposition
    ↓
Parallel Research Agents
    ↓
Tool Loop
(Search → Read → Evaluate → Search ...)
    ↓
Findings / Evidence
    ↓
Adaptive Re-planning
    ↓
Cross-source Synthesis
    ↓
Citation / Evidence Verification
    ↓
Final Research Report
```

最重要的不是“Multi-Agent”三个字，而是下面这条闭环：

```text
Understand
→ Decompose
→ Delegate
→ Explore
→ Observe
→ Evaluate
→ Re-plan
→ Synthesize
→ Verify
```

这是一种 **Agentic Investigation（代理式调查）**，而不是传统的 Retrieval Pipeline（检索流水线）。

---

## 2. Claude Deep Research 与普通 Web Search 的根本区别

### 2.1 普通 Web Search

```text
Question
  ↓
Search Query
  ↓
Search Results
  ↓
LLM Summary
  ↓
Answer
```

它更适合事实速查、单点问题和低成本查询。

### 2.2 Deep Research

```text
Question
  ↓
Research Plan
  ↓
Multiple Search Paths
  ↓
Read / Analyze / Verify
  ↓
Discover New Questions
  ↓
Adjust Research Plan
  ↓
Continue Research
  ↓
Evidence Synthesis
  ↓
Citation Verification
  ↓
Report
```

所以可以把二者理解成：

> **Web Search = Retrieval**  
> **Deep Research = Investigation**

---

## 3. 总体架构：Orchestrator–Worker

Claude Research 最值得借鉴的架构是 **Orchestrator–Worker**。

```text
                        ┌────────────────────┐
                        │   User Question    │
                        └─────────┬──────────┘
                                  ↓
                        ┌────────────────────┐
                        │   Lead / Planner   │
                        │                    │
                        │ Understand         │
                        │ Decompose         │
                        │ Prioritize         │
                        │ Spawn              │
                        └─────────┬──────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ↓                   ↓                   ↓
      ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
      │ Research A   │    │ Research B   │    │ Research C   │
      │ 市场规模      │    │ 产品能力      │    │ 竞争格局      │
      └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
             │                   │                   │
             ↓                   ↓                   ↓
        Tool Loop           Tool Loop           Tool Loop
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 ↓
                        ┌────────────────────┐
                        │  Findings / State  │
                        └─────────┬──────────┘
                                  ↓
                        ┌────────────────────┐
                        │ Lead Evaluation    │
                        │ Enough?            │
                        └───────┬─────┬──────┘
                                │NO   │YES
                                │     ↓
                                │  Synthesis
                                ↓     ↓
                         Re-plan     Verify
                                │     ↓
                                └──→ Report
```

### 3.1 Lead Agent 的职责

Lead Agent 不负责把所有资料亲自查完，它主要负责：

1. **理解问题**：判断问题属于事实查找、比较、调查、市场研究、文献综述等哪一种。
2. **拆解问题**：把复杂问题转成相对独立的子问题。
3. **规划研究路径**：确定哪些方向应该并行，哪些存在依赖。
4. **调度 Agent**：为不同子问题创建 Research Agent。
5. **整合结果**：把局部 findings 汇总成全局模型。
6. **判断是否继续**：如果证据不足，则重新规划并继续研究。

---

## 4. 第一原理：Problem Decomposition

复杂问题的第一个瓶颈不是 Search，而是 **正确拆题**。

例如：

> “研究 2026 年 AI Coding Agent 市场，并比较 Claude Code、Cursor、Codex、Gemini CLI。”

可以拆成：

```text
Q0：总体市场
├── Q1：市场规模与增速
├── Q2：主要参与者
├── Q3：技术路线
├── Q4：商业模式
├── Q5：用户与开发者趋势
│
├── Q6：Claude Code
├── Q7：Cursor
├── Q8：Codex
├── Q9：Gemini CLI
│
├── Q10：横向比较
└── Q11：未来 3 年趋势
```

拆解的目标不是“制造更多任务”，而是：

> **让每个研究单元拥有清晰的问题边界，并能够独立寻找证据。**

---

## 5. 第二原理：Parallel Exploration

传统单 Agent 是串行探索：

```text
A → B → C → D
```

Multi-Agent 可以变成：

```text
A ──┐
B ──┼──→ Lead
C ──┤
D ──┘
```

这样做有三个价值。

### 5.1 速度

多个研究方向同时执行。

### 5.2 覆盖率

不同 Agent 可以从不同角度探索，降低遗漏关键证据的概率。

### 5.3 降低路径依赖

单 Agent 容易出现：

```text
第一次搜索得到 X
      ↓
默认 X 很重要
      ↓
后续搜索全部围绕 X
      ↓
研究路径逐渐收窄
```

多个独立 Agent 则可以形成多条探索轨迹：

```text
Agent A → Path A
Agent B → Path B
Agent C → Path C
```

这也是 Multi-Agent 对广度型研究特别有价值的原因。

---

## 6. 第三原理：Subagent 本身也是 Agent

不要把 Subagent 理解成一个 Search API。

一个真正的 Research Subagent 是一个完整的 Tool-Using Agent：

```text
Goal
 ↓
Think
 ↓
Choose Tool
 ↓
Search / Read
 ↓
Observe
 ↓
Evaluate
 ↓
Modify Query
 ↓
Search Again
 ↓
Extract Findings
```

可以抽象成：

```python
while not research_complete:
    thought = reason(state)
    action = choose_tool(thought)
    observation = execute(action)
    state = update(state, observation)
```

关键在于：**工具调用是循环，而不是一次性的函数调用。**

---

## 7. 第四原理：Interleaved Thinking

优秀 Research Agent 不会简单执行：

```text
search(query1)
search(query2)
search(query3)
search(query4)
```

而是：

```text
search(query1)
    ↓
理解结果
    ↓
发现新实体 / 新线索 / 新疑问
    ↓
修改研究假设
    ↓
search(query2)
    ↓
再次评估
```

即：

> **Reasoning 与 Tool Use 交替进行。**

这使研究过程具备真正的 Adaptive Behavior。

---

## 8. 第五原理：Start Wide, Then Narrow

Deep Research 很适合采用：

> **先广后深（Breadth First → Depth First）**

### 第一阶段：建立地图

```text
AI Coding Agent
↓
主要产品
↓
主要公司
↓
关键技术
↓
关键术语
```

### 第二阶段：选择方向

```text
发现 Claude Code
发现 Cursor
发现 Codex
发现 Gemini CLI
```

### 第三阶段：深入

```text
Claude Code
  ↓
Pricing
  ↓
Users
  ↓
Features
  ↓
Distribution
  ↓
Roadmap
```

这样比一开始就构造一个极其复杂的 Search Query 更可靠。

---

## 9. 第六原理：Dynamic Scaling

不是所有问题都需要相同数量的 Agent。

可以把计算预算理解成：

```text
Question Complexity
       ↓
Research Effort
       ↓
Agent Count
       ↓
Tool Calls
       ↓
Token Budget
```

例如：

```text
简单事实
→ 1 Agent
→ 少量 Tool Calls

产品比较
→ 2~5 Agents
→ 每个方向独立调查

复杂市场研究
→ 5~10+ Agents
→ 多轮搜索 + 交叉验证
```

核心思想：

> **Research Effort 应该与 Question Complexity 成比例。**

也就是说，Deep Research 实际上实现了一种 **Dynamic Compute Allocation**。

---

## 10. 第七原理：两层并行

Deep Research 的并行不只有 Agent 层。

### 第一层：Agent Parallelism

```text
Lead
├── Agent A
├── Agent B
└── Agent C
```

### 第二层：Tool Parallelism

单个 Agent 内部也可以同时获取多个来源：

```text
Agent A
├── Web Search
├── Documentation
├── Database
└── Calculator
```

因此完整结构是：

```text
                       Lead
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
       Agent A       Agent B       Agent C
          │             │             │
      ┌───┼───┐     ┌───┼───┐     ┌───┼───┐
      ↓   ↓   ↓     ↓   ↓   ↓     ↓   ↓   ↓
     Web Doc DB    Web Doc API    Web Doc DB
```

这解释了为什么 Multi-Agent Research 能把大量探索时间压缩到可接受范围内。

---

## 11. 第八原理：Independent Context

一个复杂研究任务可能产生大量上下文：

```text
10k tokens
50k tokens
100k tokens
150k tokens
...
```

如果所有信息都塞进一个 Agent，很容易发生：

- Context Overflow
- 信息稀释
- 关键证据被埋没
- Reasoning 成本上升

因此 Multi-Agent 的另一个价值其实是 **Context Partitioning**：

```text
Lead Context
   │
   ├── Research A Context
   ├── Research B Context
   ├── Research C Context
   └── Research D Context
```

每个 Subagent 在自己的局部上下文里深挖，最后只把压缩后的 Findings 返回给 Lead。

这可以理解为：

> **Multi-Agent 不仅是并行计算模型，也是 Context Scaling 模型。**

---

## 12. 第九原理：Research 是层级化的信息压缩

研究过程可以看作一棵不断压缩的信息树：

```text
Internet / Web / Internal Knowledge
                ↓
        大量原始信息
                ↓
          Research Agents
                ↓
       局部筛选 + 局部总结
                ↓
         Findings / Evidence
                ↓
          Lead Agent
                ↓
        Cross-source Synthesis
                ↓
           Final Report
```

所以 Research 的本质可以描述为：

> **Large Information Space → Parallel Exploration → Local Compression → Global Synthesis**

Subagent 的作用类似“智能过滤器”：不是把所有页面都搬回来，而是只回传值得影响最终结论的信息。

---

## 13. 第十原理：Adaptive Re-planning

真正的 Deep Research 不是：

```text
Plan → Execute → Finish
```

而是：

```text
Plan
 ↓
Research
 ↓
Evaluate
 ↓
Enough?
 ├─ Yes → Synthesize
 └─ No  → Re-plan
             ↓
         More Research
             ↓
         Re-evaluate
```

研究过程中可能发生：

```text
原计划：研究公司 A
        ↓
发现 A 实际属于 B 集团
        ↓
新问题：B 集团是谁？
        ↓
追加研究 B
        ↓
发现关键事实
        ↓
重新解释 A
```

这说明 Research Agent 实际上维护的是一个不断变化的 **Research State**，而不是一份静态 TODO。

---

## 14. Research State 可以怎样建模

可以把研究状态抽象为：

```typescript
type ResearchState = {
  objective: string
  plan: ResearchTask[]
  activeTasks: ResearchTask[]
  completedTasks: ResearchTask[]
  findings: Finding[]
  evidence: Evidence[]
  openQuestions: Question[]
  hypotheses: Hypothesis[]
  sourceMap: SourceMap
  confidence: number
  budget: ResearchBudget
}
```

其中最关键的是：

```text
findings
openQuestions
evidence
hypotheses
```

因为这些字段决定下一轮研究应该往哪里走。

---

## 15. 第十一原理：Evidence Attribution

Research 的最终价值不只是“回答得像真的”，而是：

> **每一个关键 Claim 都应该能够回溯到 Evidence。**

可以把最终结构看成：

```text
Claim
  ↕
Evidence
  ↕
Source
```

例如：

```text
Claim:
某产品在企业开发者中的渗透率快速增长

Evidence:
某份行业报告 / 公司披露 / 调研结果

Source:
原始网页 / PDF / 官方文档
```

因此 Citation 不是简单的“在文章末尾放链接”，而是一层 **Evidence Attribution Layer**。

---

## 16. Citation Agent 的作用

可以抽象为：

```text
Draft Claims
      ↓
Locate Evidence
      ↓
Find Supporting Source
      ↓
Check Claim ↔ Source Alignment
      ↓
Attach Citation
```

目标不是“每段都加 URL”，而是：

```text
Claim A → Source 1
Claim B → Source 2
Claim C → Source 3 + Source 4
```

这样最终报告才具备：

- Traceability
- Auditability
- Verifiability

---

## 17. Citation 仍然不是绝对可靠

即使存在 Citation Agent，仍然可能出现：

```text
URL 是真的
   ↓
页面也是相关的
   ↓
但原文并没有真正支持该 Claim
```

所以高价值研究仍然需要 Human Spot Check。

推荐的交付原则：

```text
AI Discovery
     ↓
AI Synthesis
     ↓
AI Citation
     ↓
Human Verification
     ↓
Final Delivery
```

因此：

> **Multi-Agent 可以提高 Discovery Efficiency，但不能自动等价于 Evidence Certainty。**

---

## 18. Deep Research 与 RAG 的架构差异

### RAG

```text
Question
 ↓
Retrieval
 ↓
Top-K Chunks
 ↓
LLM
 ↓
Answer
```

RAG 的重点是：

> 从已知知识库中找到相关内容。

### Deep Research

```text
Question
 ↓
Planner
 ↓
Search Graph
 ├── Search
 ├── Read
 ├── Search
 ├── Verify
 └── Search
 ↓
Evidence Graph
 ↓
Synthesis
 ↓
Citation
```

Deep Research 的重点是：

> 在开放世界中主动探索未知信息，并根据新信息动态改变研究路径。

因此：

> **RAG 是 Retrieval Pipeline；Deep Research 是 Agentic Investigation。**

---

## 19. 深入理解：Research 是一个搜索图（Search Graph）

传统搜索可以看成一条链：

```text
Q → R1 → R2 → R3 → Answer
```

Deep Research 更接近一个图：

```text
                Q
                │
        ┌───────┼───────┐
        ↓       ↓       ↓
       R1      R2      R3
        │       │       │
       R4      R5      R6
        │       └──┐    │
        ↓          ↓    ↓
       R7         R8   R9
        └───────┬──────┘
                ↓
            Synthesis
```

每一个新的 Research Result 都可能增加新的节点和边。

因此它本质上更接近：

> **Dynamic Research Graph**

而不是固定 Pipeline。

---

## 20. 评价 Deep Research 的几个关键维度

可以用以下指标评价一个 Research Agent：

### 20.1 Coverage

是否覆盖了问题的主要维度？

### 20.2 Source Quality

是否优先使用 Primary Source、官方数据、论文、监管文件等高质量来源？

### 20.3 Evidence Alignment

Claim 是否真的被 Source 支持？

### 20.4 Diversity

是否从多个独立来源获得证据？

### 20.5 Path Diversity

多个 Agent 是否真正走了不同研究路径，而不是重复搜索？

### 20.6 Cost

消耗多少：

- Token
- Tool Calls
- Agent Runs
- Wall-clock Time

### 20.7 Confidence

最终结论的置信度如何？哪些是事实，哪些是推断，哪些是不确定信息？

---

## 21. 为什么 Multi-Agent 能提升研究质量

可以把研究质量粗略看成：

```text
Research Quality
≈
Coverage
× Source Quality
× Path Diversity
× Verification
× Synthesis Quality
```

Multi-Agent 主要提升：

```text
Coverage
Path Diversity
Parallelism
Context Capacity
```

但它不会自动解决：

```text
Bad Source
Bad Reasoning
Bad Verification
```

因此：

> **Multi-Agent 是研究能力的放大器，不是研究正确性的保证器。**

---

## 22. “更多 Token”为什么重要

Deep Research 的一个关键现实是：

> 高质量研究通常需要显著更多的计算预算。

普通对话：

```text
Question
 ↓
Few tool calls
 ↓
Answer
```

Deep Research：

```text
Question
 ↓
Planning
 ↓
Many tool calls
 ↓
Parallel agents
 ↓
Multiple reasoning loops
 ↓
Cross-check
 ↓
Synthesis
```

Anthropic 的公开工程文章也强调，研究效果与 **token usage、tool calls、model choice** 密切相关，其中 token usage 是重要因素之一。

所以 Deep Research 可以理解为：

> **把更多 Compute Budget 花在问题上，而不是只依赖单次模型推理。**

---

## 23. 一个通用 Deep Research Agent 的伪代码

```python
def deep_research(question: str):
    state = initialize_state(question)

    while True:
        plan = planner(state)

        tasks = decompose(plan)

        workers = spawn_parallel_agents(tasks)

        findings = parallel_execute(workers)

        state = merge_findings(state, findings)

        state = evaluate_evidence(state)

        if is_sufficient(state):
            break

        state = update_open_questions(state)
        state = replan(state)

    draft = synthesize(state)

    verified_report = verify_claims_and_citations(
        draft,
        state.evidence
    )

    return verified_report
```

这个模型已经足以构造一个可运行的 Research Agent Framework。

---

## 24. 如果进一步拆成系统组件

可以得到下面这套通用架构：

```text
┌──────────────────────────────────────────────┐
│                Research System               │
├──────────────────────────────────────────────┤
│                                              │
│  1. Planner                                  │
│     - Understand                             │
│     - Decompose                              │
│     - Prioritize                             │
│                                              │
│  2. Orchestrator                             │
│     - Spawn                                  │
│     - Schedule                               │
│     - Budget                                 │
│                                              │
│  3. Research Workers                         │
│     - Search                                 │
│     - Read                                   │
│     - Analyze                                │
│     - Verify                                 │
│                                              │
│  4. State / Memory                           │
│     - Findings                               │
│     - Questions                              │
│     - Evidence                               │
│     - Hypotheses                             │
│                                              │
│  5. Re-planner                               │
│     - Gap Detection                          │
│     - Strategy Update                        │
│                                              │
│  6. Synthesizer                              │
│     - Compare                                │
│     - Consolidate                            │
│     - Infer                                  │
│                                              │
│  7. Citation / Verification                  │
│     - Claim ↔ Evidence ↔ Source              │
│                                              │
└──────────────────────────────────────────────┘
```

---

## 25. 与 AI-SDLC 的同构关系

Claude Deep Research 与 AI-SDLC 的结构其实高度相似。

### Deep Research

```text
Question
 ↓
Research Plan
 ↓
Subtasks
 ↓
Parallel Investigation
 ↓
Findings
 ↓
Synthesis
 ↓
Verification
```

### AI-SDLC

```text
Requirement
 ↓
PRD
 ↓
Architecture
 ↓
Tasks
 ↓
Parallel Implementation
 ↓
Tests / Review
 ↓
Integration
 ↓
Verification
```

抽象之后是同一个 Agent Pattern：

```text
Understand
    ↓
Decompose
    ↓
Delegate
    ↓
Execute
    ↓
Observe
    ↓
Evaluate
    ↓
Re-plan
    ↓
Synthesize
    ↓
Verify
```

所以 Deep Research 的真正价值，不只是学习“如何做搜索”，而是学习一种 **Long-Running Agent Orchestration Pattern**。

---

## 26. 对 OpenCode / OMO / Superpowers 的启示

如果把 Deep Research 的思想迁移到代码 Agent，可以得到：

```text
User Requirement
       ↓
   Lead Agent
       ↓
   Task Decompose
       ↓
┌──────┼────────┐
↓      ↓        ↓
Explore Arch  Tests
↓      ↓        ↓
Workers Workers Workers
└──────┼────────┘
       ↓
 Findings
       ↓
 Lead Evaluation
       ↓
 Missing?
 ├─ Yes → New Tasks
 └─ No  → Implementation
       ↓
 Code Review
       ↓
 Tests
       ↓
 Final Verification
```

这和一个成熟的 AI-SDLC Framework 非常接近。

---

## 27. 最值得迁移的 7 个设计原则

如果只保留最核心的部分，可以浓缩成：

### 1. Decomposition
复杂问题必须拆成可验证的子问题。

### 2. Parallel Exploration
独立方向尽量并行，而不是串行。

### 3. Independent Context
不同研究方向拥有相对独立的上下文空间。

### 4. Tool Loop
Tool Call 必须位于持续的 Think → Act → Observe 循环内。

### 5. Adaptive Planning
新信息出现后允许修改原计划。

### 6. Evidence Attribution
每一个重要 Claim 都应该能够追溯到 Evidence / Source。

### 7. Effort Scaling
计算预算、Agent 数量、Tool Calls 应随问题复杂度动态增长。

---

## 28. 最终抽象：Deep Research 是一种 Agent Operating Pattern

可以把 Claude Deep Research 最终抽象成：

```text
                 ┌──────────────┐
                 │    Question  │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │    Planner   │
                 └──────┬───────┘
                        ↓
               ┌───────────────┐
               │  Task Graph   │
               └───────┬───────┘
                       ↓
          ┌────────────┼────────────┐
          ↓            ↓            ↓
       Worker A     Worker B     Worker C
          │            │            │
       Tool Loop    Tool Loop    Tool Loop
          │            │            │
          └────────────┼────────────┘
                       ↓
                  Evidence
                       ↓
               ┌───────────────┐
               │  Evaluate Gap │
               └───────┬───────┘
                       │
                 ┌─────┴─────┐
                 │           │
                No          Yes
                 │           │
                 ↓           ↓
             Synthesis    Re-plan
                 │           │
                 ↓           └──────→ More Research
             Citation
             Verification
                 ↓
              Report
```

一句话定义：

> **Deep Research = Planner 驱动的多 Agent、工具调用、动态再规划、证据综合与验证的长程研究系统。**

---

## 29. 参考资料与事实边界

### 29.1 用户指定文章

Moksa：**Claude Research 完整教學：Multi Agent 6 大應用情境**  
https://moksaweb.com/claude-research/

文章对 Orchestrator–Worker、并行 Subagent、动态研究、Citation、Google Workspace 等产品/架构进行了整理。

### 29.2 Anthropic 官方工程文章

Anthropic：**How we built our multi-agent research system**  
https://www.anthropic.com/engineering/multi-agent-research-system

这是本文讨论架构原则时优先采用的官方依据，尤其用于理解：

- Orchestrator–Worker
- Subagent Parallelism
- Tool Use
- Interleaved Thinking
- Research Planning
- Dynamic Scaling
- Context / Long-running Task
- Citation / Research Synthesis

### 29.3 事实边界说明

Moksa 文章中包含一些会随产品版本变化的具体信息，例如模型分工、Research 模式命名、套餐、运行时间、配额等。这类信息不应与长期稳定的架构原则混为一谈。

尤其需要区分：

```text
稳定的架构原则
≠
当前版本的产品实现细节
```

对于研究 Agent 的架构设计，应优先吸收前者。

---

## 30. 一句话总结

**Claude Deep Research 的核心不是“搜索得更多”，而是“让 Agent 自己建立研究任务图，并通过并行探索、独立上下文、工具循环、动态再规划和证据验证，让一个复杂问题逐步收敛”。**

从工程角度看，它最值得复用的并不是 Claude Research 这个产品本身，而是这套通用模式：

```text
Plan
→ Decompose
→ Parallelize
→ Tool Loop
→ Evaluate
→ Re-plan
→ Synthesize
→ Verify
```

这套模式可以直接迁移到 Research Agent、AI-SDLC、代码审查、Competitive Intelligence、文献综述和复杂决策支持系统中。
