---
name: deep-research
description: >
  **Superseded by info-collector deep_dive phase (ADR 0064).** This skill is no
  longer maintained. Iterative deep-dive capability has been merged into
  info-collector as the deep_dive pipeline phase, activated when depth=deep.
disable-model-invocation: true
---

> **Status: Superseded by info-collector deep_dive phase (ADR 0064)**
>
> This skill's iterative deep-dive capability has been merged into info-collector
> as a new pipeline phase (`deep_dive`) between analysis and review. It activates
> when `scope.json` depth is "deep". The merge preserves deep-research's core
> value (iterative deepening with convergence control) within info-collector's
> robust infrastructure (fetch, gate, claim validation, review, report).
>
> Key mapping:
> - dual-loop convergence → deep_dive phase with hard/natural/soft convergence
> - inner loop 3-question judgment → identify_deep_dive_targets() trigger conditions
> - choreographer progressive disclosure → deep-dive-plan + deep-dive-converge CLI commands
> - flat deepening → deep_dive → search re-loop transition
>
> See: `skills/info-collector/docs/adr/0064-deep-dive-phase-from-deep-research-merge.md`

# Deep-Research Skill

## 定位

info-collector 做广度（全景地图），deep-research 做深度（迭代深挖）。
互补不取代。

## 架构

编排器（Choreographer）模式。一个 Python 脚本 `orchestrator.py` 管理状态机，
不执行具体任务。Agent 按编排器的指令执行搜索、发现、合成。

**核心原则：编排器是流程的唯一入口。Agent 不得跳过编排器自行推进。**

```
编排器(orchestrator.py) → 输出当前阶段指令
     ↓
Agent 执行指令（搜索、记录、判断）
     ↓
编排器 → 门控检查 → 输出下一阶段指令
```

## 使用方式

### 启动

```
.venv\Scripts\python.exe skills\deep-research\scripts\orchestrator.py init --seed "你的研究问题"
```

编排器输出 Phase 1（Scope）的指令。Agent 按指令执行。

### 推进

每个阶段完成后运行 `next` 进入下一阶段：

```
.venv\Scripts\python.exe skills\deep-research\scripts\orchestrator.py next
```

编排器检查当前阶段是否完整。通过则输出下一阶段指令；不通过则报错。

### 查看进度

```
.venv\Scripts\python.exe skills\deep-research\scripts\orchestrator.py status
```

### 换题

```
.venv\Scripts\python.exe skills\deep-research\scripts\orchestrator.py abort
```

## Agent 规则

1. **编排器不可绕过** — 每次 `next` 是唯一获得下一阶段指令的途径
2. **搜索必记录** — 每次搜索调用必须在 `research_trace.json` 的 `search_log` 中记录
3. **降级不跳过** — 搜索工具不可用时先降级，不能直接跳到合成
4. **发现必扫描** — 即使没有矛盾/新奇，也必须在 `inner_loop_results` 中记录"无发现"
5. **报告必溯源** — 每条 claim 必须 inline cite 来源 URL

## 设计文档

- `docs/orchestrator-interface.md` — 完整接口协议规范
