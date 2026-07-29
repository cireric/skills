# Skill Observation Log

Observations captured during task-oriented work.

**Status key:** OPEN = not yet actioned | ACTIONED (YYYY-MM-DD) = skill updated/created | DECLINED (YYYY-MM-DD) = user decided not to pursue — resolved statuses always carry their resolution date

---

### Observation 1: AGENTS.md 要求 agent 在任务会话开始时自动加载 task-observer，但本次会话 agent 没有自动执行，用户需要手动 /task-ob

**Status:** OPEN
**Date:** 2026-07-29
**Session context:** 用户询问 task-observer 是否需要每次新建 session 手动触发
**Skill:** task-observer
**Type:** internal
**Phase/Area:** Session Start Protocol

**Issue:** AGENTS.md 要求 agent 在任务会话开始时自动加载 task-observer，但本次会话 agent 没有自动执行，用户需要手动 /task-observer:init 才能激活

**Suggested improvement:** Session Start Protocol 应增加一条 fallback：若 agent 未在第一条 tool-using message 前自动加载，用户应触发什么机制？或者在 init 脚本层面增加 session-level persistence 检测

**Principle:** 依赖 agent 自觉执行的规则不可靠，应增加辅助检测或强制机制
