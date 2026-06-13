# Book-Grill Skill Implementation Plan

## TL;DR

> **Quick Summary**: Build the Phase 1 (P0) core loop of `/book-grill` — a global skill for post-reading deep reflection with type-adaptive questioning, automatic note generation, and reading history accumulation.
>
> **Deliverables**:
>
> - `~/.agents/skills/book-grill/SKILL.md` — Main skill entry (120-150 lines)
> - `~/.agents/skills/book-grill/templates/fiction.md` — Fiction question template
> - `~/.agents/skills/book-grill/templates/nonfiction.md` — Nonfiction question template
> - `~/.agents/skills/book-grill/templates/biography.md` — Biography question template
> - `~/.agents/skills/book-grill/templates/technical.md` — Technical question template
> - `~/.agents/skills/book-grill/strategies.md` — Follow-up strategies + exploration handling
> - `~/.local/share/book-grill/config.json` — Basic user config
> - `~/.local/share/book-grill/notes/` — Runtime notes directory
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 (SKILL.md) → Task 7 (Integration test)

---

## Context

### Original Request

根据需求设计文档 `.omo/requirements/book-grill-skill-requirements.md` (v1.0.0, 定稿) 生成详细实施计划，构建 book-grill skill 的 Phase 1 核心闭环。

### Interview Summary

**Key Discussions**:

- Multi-turn state: grill-me 隐式模式（依赖对话历史自然流动）
- SKILL.md 行数: 120-150 行（需求文档目标，超出 write-a-skill 推荐的 100 行）
- config.json: Phase 1 实现基础版
- 测试策略: 纯手动 QA

**Research Findings**:

- 文件引用: 标准 Markdown 链接（`[file](./path)`），不用 `@` 前缀
- grill-me 模式: "Ask one question at a time" 隐式对话流
- 现有 skill 行数范围: 10-236 行
- `~/.agents/skills/book-grill/` 目录已存在但为空

### Metis Review

**Identified Gaps** (all resolved):

- Platform path: `~/.local/share/` 在 macOS 上可用（用户已使用类似路径）
- Template loading: SKILL.md 中明确指示 LLM 读取对应模板文件
- Note naming: `<书名>-YYYY-MM-DD.md`（需求文档已定义）
- Special characters: Phase 1 实现基础清理（`/` `\` `:` `*` `?` `"` `<` `>` `|` → `-`）
- Manual QA: 将在计划中定义结构化测试协议

---

## Work Objectives

### Core Objective

Build the Phase 1 core loop of `/book-grill` skill: type-adaptive questioning (4 book types × 4 stages), automatic note generation, and reading history file accumulation.

### Concrete Deliverables

- `~/.agents/skills/book-grill/SKILL.md` — Skill entry with frontmatter, dialogue flow, output format
- `~/.agents/skills/book-grill/templates/fiction.md` — Fiction A→B→C→D questions + follow-up directions
- `~/.agents/skills/book-grill/templates/nonfiction.md` — Nonfiction A→B→C→D questions + follow-up directions
- `~/.agents/skills/book-grill/templates/biography.md` — Biography A→B→C→D questions + follow-up directions
- `~/.agents/skills/book-grill/templates/technical.md` — Technical A→B→C→D questions + follow-up directions
- `~/.agents/skills/book-grill/strategies.md` — Socratic follow-up strategy table + exploration handling logic
- `~/.local/share/book-grill/config.json` — Basic config with default fields
- `~/.local/share/book-grill/notes/` — Runtime notes directory (created on first use)

### Definition of Done

- [ ] `/book-grill <书名>` triggers type confirmation → 4-stage questioning → note generation
- [ ] 4 book types produce different question sequences
- [ ] Note file written to `~/.local/share/book-grill/notes/<书名>-YYYY-MM-DD.md` with correct frontmatter + sections
- [ ] Dialogue control works: "跳过"/"结束"/"不知道" all handled correctly
- [ ] SKILL.md ≤ 150 lines, each template ≤ 100 lines

### Must Have

- Type confirmation flow (≤ 1 round interaction)
- 4 book type × 4 stage question templates with follow-up directions
- Post-reading note generation with frontmatter (title, author, type, date, tags) + structured sections
- Basic dialogue control ("跳过", "结束", "不知道")
- Progress indicator per question
- Exploration item tracking in notes
- Closing question ("用一句话总结这本书对你的意义")
- D1 pass fallback to closing question
- Basic filename sanitization (special chars → `-`)
- config.json with default fields

### Must NOT Have (Guardrails)

- No notepad (实时札记) — Phase 2
- No real-time exploration tracking — Phase 2
- No INDEX.md — Phase 2
- No websearch integration — Phase 3
- No reading state adaptation (部分阅读/重读/听书) — Phase 3
- No mixed type handling — Phase 2
- No session recovery — Phase 2
- No cross-book comparison — Phase 4
- No inline template content in SKILL.md (use file references)
- File references: use `@` prefix for auto-inline (e.g., `@./templates/fiction.md`), which oh-my-openagent resolves automatically. Markdown links `[text](./path)` are fallback for human readability but require agent to manually `read` the file
- No explicit state declaration (use grill-me implicit pattern)
- No automated tests (manual QA only)
- No external npm dependencies

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision

- **Infrastructure exists**: NO (skill is prompt-based, not code)
- **Automated tests**: None
- **Framework**: N/A
- **Primary verification**: Agent-executed QA scenarios (manual dialogue testing + file structure checks)

### QA Policy

Every task MUST include agent-executed QA scenarios.
Evidence saved to `.omo/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Skill files**: Use Bash — verify file existence, line counts, frontmatter fields, content patterns
- **Dialogue flow**: Use interactive_bash (tmux) — trigger skill, simulate dialogue, verify responses
- **Note generation**: Use Bash — verify file creation, frontmatter, section structure

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately - independent file creation):
├── Task 1: SKILL.md main entry file [quick]
├── Task 2: Fiction template [quick]
├── Task 3: Nonfiction template [quick]
├── Task 4: Biography template [quick]
├── Task 5: Technical template [quick]
└── Task 6: Strategies + config.json [quick]

Wave 2 (After Wave 1 - integration verification):
└── Task 7: Full dialogue flow integration test [deep]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Content quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: Task 1 → Task 7 → F1-F4 → user okay
Parallel Speedup: ~75% faster than sequential (6 files created in parallel)
Max Concurrent: 6 (Wave 1)
```

### Dependency Matrix

| Task | Depends On  | Blocks    | Wave  |
| ---- | ----------- | --------- | ----- |
| 1    | -           | 7         | 1     |
| 2    | -           | 7         | 1     |
| 3    | -           | 7         | 1     |
| 4    | -           | 7         | 1     |
| 5    | -           | 7         | 1     |
| 6    | -           | 7         | 1     |
| 7    | 1,2,3,4,5,6 | F1-F4     | 2     |
| F1   | 7           | user okay | FINAL |
| F2   | 7           | user okay | FINAL |
| F3   | 7           | user okay | FINAL |
| F4   | 7           | user okay | FINAL |

### Agent Dispatch Summary

- **Wave 1**: **6** — T1-T5 → `quick`, T6 → `quick`
- **Wave 2**: **1** — T7 → `deep`
- **FINAL**: **4** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. SKILL.md — Main Skill Entry File

  **What to do**:
  - Create `~/.agents/skills/book-grill/SKILL.md` with valid frontmatter (`name: book-grill`, `description: ...`)
  - Description must follow convention: "First sentence: what it does. Second sentence: Use when [triggers]"
  - Description triggers: `/book-grill`, "grill me on this book", "book reflection", "读后反思", "读书笔记"
  - Include complete dialogue flow:
    1. **Type confirmation** (1 round): LLM infers book type → asks user to confirm → user confirms or corrects → LLM briefly explains question flow
    2. **Deep questioning** (4 stages): After type confirmed, read corresponding template file (`@./templates/fiction.md` etc. — `@` prefix auto-inlines via oh-my-openagent), then ask questions one at a time from A→B→C→D stages
    3. **Closing**: After D1, ask closing question ("用一句话总结这本书对你的意义")
    4. **Note generation**: After closing, generate structured note and write to `~/.local/share/book-grill/notes/<书名>-YYYY-MM-DD.md`
  - Include dialogue control rules:
    - "跳过"/"下一个"/"next" → skip current question, move to next
    - "结束"/"done"/"就到这里" → terminate dialogue, generate note
    - "不知道"/"pass"/"没想过" → mark as exploration item, move to next question
    - D1 pass → skip to closing question directly
  - Include progress indicator format: `【进度】第 X/Y 题 | 阶段: [阶段名](阶段字母) | 已发现 N 个待探索项`
  - Include note output format (frontmatter + sections) per requirements doc §7.3
  - Include filename sanitization rule: replace `/` `\` `:` `*` `?` `"` `<` `>` `|` `+` with `-`, collapse consecutive `-`, truncate to 100 chars
  - Include template file references using `@` prefix for auto-inline: `@./templates/fiction.md`, `@./strategies.md` (oh-my-openagent's `resolveFileReferencesInText()` resolves `@` paths automatically, injecting file content into LLM context). Markdown links like `[text](./path)` are for human readability only and require agent to manually `read` the file.
  - Target: 120-150 lines

  **Must NOT do**:
  - No inline template question content (use file references)
  - File references must use `@` prefix for auto-inline resolution (not just markdown links)
  - No `@` prefix file references
  - No explicit state declaration (grill-me implicit pattern)
  - No notepad, websearch, reading state, mixed type, INDEX.md logic
  - No external npm dependencies

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file creation with clear requirements from spec
  - **Skills**: [`write-a-skill`]
    - `write-a-skill`: Authoritative guide on skill format, frontmatter, description rules

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2-6)
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **Pattern References** (existing code to follow):
  - `~/.agents/skills/grill-me/SKILL.md` — Core grill pattern ("Ask one question at a time"), minimal structure reference
  - `~/.agents/skills/grill-with-docs/SKILL.md` — XML section pattern (`<what-to-do>` / `<supporting-info>`), file reference pattern (`[ADR-FORMAT.md](./ADR-FORMAT.md)`), one-question-at-a-time pattern
  - `~/.agents/skills/caveman/SKILL.md` — Multi-turn persistence pattern reference (DO NOT copy — implicit mode chosen instead)
  - `~/.agents/skills/write-a-skill/SKILL.md` — Authoritative guide on frontmatter fields, description format, file structure

  **API/Type References** (contracts to implement against):
  - `.omo/requirements/book-grill-skill-requirements.md:§3` — Core design decisions table (trigger, install scope, type handling, question strategy, note format, storage, naming, INDEX.md, exploration tracking, info source, classification basis)
  - `.omo/requirements/book-grill-skill-requirements.md:§5` — Question depth progression (A理解确认 → B批判分析 → C个人共鸣 → D超越书本)
  - `.omo/requirements/book-grill-skill-requirements.md:§7.3` — Complete note output format (frontmatter fields + section structure + knowledge cards + exploration directions)
  - `.omo/requirements/book-grill-skill-requirements.md:§10` — Dialogue control rules and progress indicator format
  - `.omo/requirements/book-grill-skill-requirements.md:§11.2` — Detailed interaction flow (trigger → type confirm → deep questioning → closing → note generation)

  **External References**:
  - N/A — no external libraries

  **WHY Each Reference Matters**:
  - `grill-me/SKILL.md`: Shows the exact "one question at a time" pattern that book-grill inherits
  - `grill-with-docs/SKILL.md`: Shows how to structure multi-section skill with XML tags; note its markdown link references work for human readability but require agent to manually `read` files
  - `write-a-skill/SKILL.md`: Enforces frontmatter conventions — the only authoritative source for description format
  - **Critical**: oh-my-openagent's `resolveFileReferencesInText()` auto-inlines `@./path` references into LLM context. This is the correct way to reference templates/strategies from SKILL.md. Markdown links `[text](path)` are fallback only.
  - Requirements §3: All core design decisions in one table — must be faithfully implemented
  - Requirements §7.3: Complete note format — must be reproduced exactly in SKILL.md
  - Requirements §10: Exact dialogue control rules — must match precisely
  - Requirements §11.2: Step-by-step flow — the main "algorithm" for SKILL.md

  **Acceptance Criteria**:
  - [ ] File exists: `~/.agents/skills/book-grill/SKILL.md`
  - [ ] File line count ≤ 150
  - [ ] Frontmatter contains `name: book-grill` and `description:`
  - [ ] Description includes "Use when" trigger phrase
  - [ ] Contains type confirmation flow (1 round)
  - [ ] Contains 4-stage questioning flow (A→B→C→D)
  - [ ] Contains dialogue control rules (跳过/结束/不知道)
  - [ ] Contains D1 pass → closing fallback rule
  - [ ] Contains progress indicator format
  - [ ] Contains note output format with frontmatter fields
  - [ ] Contains filename sanitization rule
  - [ ] References templates via `@` prefix (`@./templates/fiction.md` etc.) for auto-inline
  - [ ] References strategies via `@` prefix (`@./strategies.md`) for auto-inline
  - [ ] No inline question content from templates
  - [ ] No `@`-less-only file references (must use `@` prefix for auto-inline)
  - [ ] No Phase 2+ features (notepad, websearch, etc.)

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: File structure and frontmatter validation
    Tool: Bash
    Preconditions: SKILL.md has been created
    Steps:
      1. test -f ~/.agents/skills/book-grill/SKILL.md
      2. head -20 ~/.agents/skills/book-grill/SKILL.md | grep "name: book-grill"
      3. head -20 ~/.agents/skills/book-grill/SKILL.md | grep "description:"
      4. wc -l ~/.agents/skills/book-grill/SKILL.md → verify ≤ 150
    Expected Result: File exists, has valid frontmatter with name and description, line count ≤ 150
    Failure Indicators: File missing, no frontmatter, line count > 150
    Evidence: .omo/evidence/task-1-structure.txt

  Scenario: Content completeness check
    Tool: Bash
    Preconditions: SKILL.md has been created
    Steps:
      1. grep -c "@./templates/fiction.md" ~/.agents/skills/book-grill/SKILL.md → ≥ 1
      2. grep -c "@./templates/nonfiction.md" ~/.agents/skills/book-grill/SKILL.md → ≥ 1
      3. grep -c "@./templates/biography.md" ~/.agents/skills/book-grill/SKILL.md → ≥ 1
      4. grep -c "@./templates/technical.md" ~/.agents/skills/book-grill/SKILL.md → ≥ 1
      5. grep -c "@./strategies.md" ~/.agents/skills/book-grill/SKILL.md → ≥ 1
      6. grep -c "跳过" ~/.agents/skills/book-grill/SKILL.md → ≥ 1
      7. grep -c "结束" ~/.agents/skills/book-grill/SKILL.md → ≥ 1
      8. grep -c "不知道" ~/.agents/skills/book-grill/SKILL.md → ≥ 1
      9. grep -c "进度" ~/.agents/skills/book-grill/SKILL.md → ≥ 1
    Expected Result: All required content patterns present
    Failure Indicators: Any grep count = 0
    Evidence: .omo/evidence/task-1-content.txt
  ```

  **Commit**: YES (groups with Tasks 2-6)
  - Message: `feat(skill): add book-grill skill — Phase 1 core loop`
  - Files: `~/.agents/skills/book-grill/SKILL.md`, templates/\*.md, strategies.md, config.json
  - Pre-commit: `test -f ~/.agents/skills/book-grill/SKILL.md && wc -l ~/.agents/skills/book-grill/SKILL.md`

- [x] 2. Fiction Template

  **What to do**:
  - Create `~/.agents/skills/book-grill/templates/fiction.md`
  - Include all fiction questions from requirements doc §4.2:
    - A1: 故事的主要情节线是什么？有没有哪条支线让你觉得特别意外？
    - A2: 主人公的决策和成长轨迹你认同吗？有没有什么行为让你觉得不合理？
    - A3: 作者在叙事手法上有什么特别之处？（视角切换/时间线/语言风格）
    - B1: 这个故事在探讨什么更深层的主题？它通过情节传达了哪些关于人性/社会的观点？
    - B2: 如果换一个不同的结局，你觉得故事的核心信息会变吗？
    - C1: 故事中有没有哪个人物让你联想到自己认识的人？或者让你想到自己的某段经历？
    - C2: 读完这个故事，你对哪些以前没想过的问题开始有了自己的看法？
    - D1: 这本书带给你的认知变化，会如何影响你未来的思考或行动？→ 追问方向：如果这个启示被广泛应用，世界会因此变得更好还是更坏？
  - Include question depth labels (A理解确认/B批判分析/C个人共鸣/D超越书本)
  - Include follow-up direction for D1
  - Target: ≤ 100 lines

  **Must NOT do**:
  - No implementation logic or state tracking
  - No examples or lengthy explanations beyond question text
  - No content from other book type templates

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Direct content extraction from requirements doc
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3-6)
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `~/.agents/skills/tdd/tests.md` — Example of sibling reference file structure and format

  **API/Type References**:
  - `.omo/requirements/book-grill-skill-requirements.md:§4.2 (Fiction section)` — Complete question set with exact wording
  - `.omo/requirements/book-grill-skill-requirements.md:§5` — Depth progression labels (A理解确认/B批判分析/C个人共鸣/D超越书本)
  - `.omo/requirements/book-grill-skill-requirements.md:§4.1` — Fiction type definition: 检测信号、提问侧重、包含/不包含

  **External References**: N/A

  **WHY Each Reference Matters**:
  - Requirements §4.2: Source of truth for all question text — must reproduce exactly
  - Requirements §5: Stage labels and depth descriptions — needed for section headers
  - Requirements §4.1: Type boundary definition — ensures template covers correct scope

  **Acceptance Criteria**:
  - [ ] File exists: `~/.agents/skills/book-grill/templates/fiction.md`
  - [ ] File line count ≤ 100
  - [ ] Contains A1, A2, A3 questions
  - [ ] Contains B1, B2 questions
  - [ ] Contains C1, C2 questions
  - [ ] Contains D1 question with follow-up direction
  - [ ] Contains stage labels (理解确认/批判分析/个人共鸣/超越书本)
  - [ ] No content from nonfiction/biography/technical templates

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: File existence and content validation
    Tool: Bash
    Preconditions: fiction.md has been created
    Steps:
      1. test -f ~/.agents/skills/book-grill/templates/fiction.md
      2. wc -l ~/.agents/skills/book-grill/templates/fiction.md → verify ≤ 100
      3. grep -c "A1" ~/.agents/skills/book-grill/templates/fiction.md → ≥ 1
      4. grep -c "B1" ~/.agents/skills/book-grill/templates/fiction.md → ≥ 1
      5. grep -c "C1" ~/.agents/skills/book-grill/templates/fiction.md → ≥ 1
      6. grep -c "D1" ~/.agents/skills/book-grill/templates/fiction.md → ≥ 1
      7. grep -c "理解确认" ~/.agents/skills/book-grill/templates/fiction.md → ≥ 1
    Expected Result: File exists, ≤ 100 lines, contains all required questions
    Failure Indicators: File missing, line count > 100, any question missing
    Evidence: .omo/evidence/task-2-fiction.txt

  Scenario: No cross-contamination from other templates
    Tool: Bash
    Preconditions: fiction.md has been created
    Steps:
      1. grep -c "核心观点/主张" ~/.agents/skills/book-grill/templates/fiction.md → 0 (this is nonfiction)
      2. grep -c "传记" ~/.agents/skills/book-grill/templates/fiction.md → 0 (this is biography)
      3. grep -c "前置知识" ~/.agents/skills/book-grill/templates/fiction.md → 0 (this is technical)
    Expected Result: Zero matches for other template content
    Failure Indicators: Any grep count > 0
    Evidence: .omo/evidence/task-2-no-cross-contam.txt
  ```

  **Commit**: YES (groups with Tasks 1, 3-6)
  - Message: see Task 1
  - Files: `~/.agents/skills/book-grill/templates/fiction.md`

- [x] 3. Nonfiction Template

  **What to do**:
  - Create `~/.agents/skills/book-grill/templates/nonfiction.md`
  - Include all nonfiction questions from requirements doc §4.2:
    - A1: 这本书的核心观点/主张是什么？作者在试图解决什么问题？
    - A2: 作者用了哪些论据来支撑这个观点？你觉得最有说服力的是哪一个？
    - A3: 你能用自己的话复述一下作者的论证逻辑吗？作者的叙事方式（如果有的）对理解有什么影响？
    - B1: 作者的论证中有没有隐藏的假设？他的视角可能忽略了什么？
    - B2: 对于这个问题，有没有其他合理的解释或对立观点？作者是如何回应的？
    - C1: 这本书改变了你对这个议题的哪些既有认知？
    - C2: 你会因为这本书而改变什么实际行为或决策方式吗？
    - D1: 这本书带给你的认知变化，会如何影响你未来的思考或行动？→ 追问方向：重新回答第一阶段的问题，你的答案改变了吗？是什么让你改变？
  - Include question depth labels
  - Target: ≤ 100 lines

  **Must NOT do**:
  - Same as Task 2

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **API/Type References**:
  - `.omo/requirements/book-grill-skill-requirements.md:§4.2 (Nonfiction section)` — Complete question set
  - `.omo/requirements/book-grill-skill-requirements.md:§5` — Depth progression labels
  - `.omo/requirements/book-grill-skill-requirements.md:§4.1` — Nonfiction type definition

  **External References**: N/A

  **WHY Each Reference Matters**: Same as Task 2

  **Acceptance Criteria**:
  - [ ] File exists: `~/.agents/skills/book-grill/templates/nonfiction.md`
  - [ ] File line count ≤ 100
  - [ ] Contains A1, A2, A3 questions (nonfiction-specific)
  - [ ] Contains B1, B2 questions (nonfiction-specific)
  - [ ] Contains C1, C2 questions (nonfiction-specific)
  - [ ] Contains D1 with follow-up direction (cognitive loop: revisit A-stage answers)
  - [ ] Contains stage labels

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: File existence and content validation
    Tool: Bash
    Preconditions: nonfiction.md has been created
    Steps:
      1. test -f ~/.agents/skills/book-grill/templates/nonfiction.md
      2. wc -l ~/.agents/skills/book-grill/templates/nonfiction.md → verify ≤ 100
      3. grep -c "核心观点" ~/.agents/skills/book-grill/templates/nonfiction.md → ≥ 1
      4. grep -c "论据" ~/.agents/skills/book-grill/templates/nonfiction.md → ≥ 1
      5. grep -c "D1" ~/.agents/skills/book-grill/templates/nonfiction.md → ≥ 1
    Expected Result: File exists, ≤ 100 lines, contains nonfiction-specific questions
    Failure Indicators: File missing, line count > 100, key terms absent
    Evidence: .omo/evidence/task-3-nonfiction.txt
  ```

  **Commit**: YES (groups with Tasks 1-2, 4-6)
  - Files: `~/.agents/skills/book-grill/templates/nonfiction.md`

- [x] 4. Biography Template

  **What to do**:
  - Create `~/.agents/skills/book-grill/templates/biography.md`
  - Include all biography questions from requirements doc §4.2:
    - A1: 从这本书中，你读到的是一个怎样的人？他的哪些特质对你触动最大？
    - A2: 他人生中哪些关键决策塑造了后来的轨迹？如果是你，你在那个时刻会怎么做？
    - A3: 这本书所处的历史/社会背景中，有哪些因素深刻影响了他的选择和命运？
    - B1: 作者对这个人物是褒是贬？作者的倾向是否影响了叙述的客观性？
    - B2: 传记中是否有美化的成分？有没有什么信息被刻意弱化或省略了？
    - C1: 这个人的经历让你对自己的人生有什么反思？
    - C2: 书中哪些教训或经验可以应用到你的工作或生活中？
    - D1: 这本书带给你的认知变化，会如何影响你未来的思考或行动？→ 追问方向：这种拷问式反思方法，对你理解这个人/这段历史带来了哪些不同？
  - Include question depth labels
  - Include a brief note explaining why biography is a separate category (per §4.1: "传记阅读需要同时关注'人被时代塑造'和'人主动选择'两个维度")
  - Target: ≤ 100 lines

  **Must NOT do**:
  - Same as Task 2

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **API/Type References**:
  - `.omo/requirements/book-grill-skill-requirements.md:§4.2 (Biography section)` — Complete question set
  - `.omo/requirements/book-grill-skill-requirements.md:§4.1` — Biography type definition and "why separate category" explanation
  - `.omo/requirements/book-grill-skill-requirements.md:§5` — Depth progression labels

  **External References**: N/A

  **WHY Each Reference Matters**: Same as Task 2

  **Acceptance Criteria**:
  - [ ] File exists: `~/.agents/skills/book-grill/templates/biography.md`
  - [ ] File line count ≤ 100
  - [ ] Contains A1, A2, A3 questions (biography-specific)
  - [ ] Contains B1, B2 questions (author bias/objectivity focus)
  - [ ] Contains C1, C2 questions (personal reflection focus)
  - [ ] Contains D1 with follow-up direction (meta-cognitive reflection)
  - [ ] Contains stage labels
  - [ ] Contains brief note on why biography is separate from nonfiction

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: File existence and content validation
    Tool: Bash
    Preconditions: biography.md has been created
    Steps:
      1. test -f ~/.agents/skills/book-grill/templates/biography.md
      2. wc -l ~/.agents/skills/book-grill/templates/biography.md → verify ≤ 100
      3. grep -c "人物" ~/.agents/skills/book-grill/templates/biography.md → ≥ 1
      4. grep -c "客观性" ~/.agents/skills/book-grill/templates/biography.md → ≥ 1
      5. grep -c "D1" ~/.agents/skills/book-grill/templates/biography.md → ≥ 1
    Expected Result: File exists, ≤ 100 lines, contains biography-specific questions
    Failure Indicators: File missing, line count > 100, key terms absent
    Evidence: .omo/evidence/task-4-biography.txt
  ```

  **Commit**: YES (groups with Tasks 1-3, 5-6)
  - Files: `~/.agents/skills/book-grill/templates/biography.md`

- [x] 5. Technical Template

  **What to do**:
  - Create `~/.agents/skills/book-grill/templates/technical.md`
  - Include all technical questions from requirements doc §4.2:
    - A0: 你读这本书前具备哪些相关基础或前置知识？
    - A1: 这本书主要教什么？它的目标读者是谁？你是否符合这个画像？
    - A2: 读完之后你掌握了哪些之前不会的概念或技能？哪些部分是已经知道的？
    - A3: 作者的教学方式（示例/练习/讲解）你觉得有效吗？
    - B1: 这本书提到的技术/方法，在你的实际场景中真的可用吗？有什么限制？
    - B2: 书中给出的建议或最佳实践，有没有过时或者有争议的内容？
    - C1: 你打算把这本书的内容应用到什么具体项目中？第一步做什么？
    - C2: 这本书让你对哪些相关领域产生了兴趣？接下来想学什么？
    - D1: 这本书带给你的认知变化，会如何影响你未来的思考或行动？→ 追问方向：如果让你用一句话向同事推荐这本书，你会怎么说？（对比 A1 的回答）
  - Note: Technical has A0 (extra question) in addition to A1-A3, making it A0-A3 (4 questions in stage A)
  - Include question depth labels
  - Target: ≤ 100 lines

  **Must NOT do**:
  - Same as Task 2
  - No skipping the A0 question — it's unique to technical type

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **API/Type References**:
  - `.omo/requirements/book-grill-skill-requirements.md:§4.2 (Technical section)` — Complete question set, including unique A0
  - `.omo/requirements/book-grill-skill-requirements.md:§4.1` — Technical type definition
  - `.omo/requirements/book-grill-skill-requirements.md:§5` — Depth progression labels

  **External References**: N/A

  **WHY Each Reference Matters**:
  - Requirements §4.2: Technical has A0 (unique), must not be missed
  - The D1 follow-up direction for technical is "一句话推荐对比A1" — distinctive pattern

  **Acceptance Criteria**:
  - [ ] File exists: `~/.agents/skills/book-grill/templates/technical.md`
  - [ ] File line count ≤ 100
  - [ ] Contains A0, A1, A2, A3 questions (A0 unique to technical)
  - [ ] Contains B1, B2 questions (practical applicability focus)
  - [ ] Contains C1, C2 questions (action plan focus)
  - [ ] Contains D1 with follow-up direction (one-sentence recommendation vs A1)
  - [ ] Contains stage labels

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: File existence and content validation
    Tool: Bash
    Preconditions: technical.md has been created
    Steps:
      1. test -f ~/.agents/skills/book-grill/templates/technical.md
      2. wc -l ~/.agents/skills/book-grill/templates/technical.md → verify ≤ 100
      3. grep -c "A0" ~/.agents/skills/book-grill/templates/technical.md → ≥ 1
      4. grep -c "前置知识" ~/.agents/skills/book-grill/templates/technical.md → ≥ 1
      5. grep -c "D1" ~/.agents/skills/book-grill/templates/technical.md → ≥ 1
    Expected Result: File exists, ≤ 100 lines, contains technical-specific questions including A0
    Failure Indicators: File missing, line count > 100, A0 missing
    Evidence: .omo/evidence/task-5-technical.txt
  ```

  **Commit**: YES (groups with Tasks 1-4, 6)
  - Files: `~/.agents/skills/book-grill/templates/technical.md`

- [x] 6. Strategies + Config.json

  **What to do**:

  **Part A: strategies.md**
  - Create `~/.agents/skills/book-grill/strategies.md`
  - Include Socratic follow-up strategy table from requirements doc §4.4:
    | 用户回答特征 | 追问策略 | 示例 |
    |---|---|---|
    | 回答模糊（< 10字） | 要求具体化 | "你能具体说说吗？" / "你说的'X'具体指什么？" |
    | 回答泛泛 | 要求举例 | "能举一个书中的例子吗？" |
    | 回答矛盾 | 指出矛盾并引导关联 | "你刚才说...，但现在又说...，这两者之间有什么联系？" |
    | 回答深入 | 横向拓展 | "这个观察很有趣，如果把它应用到另一个场景会怎样？" |
    | 回答偏离书本 | 拉回文本 | "这个观点和书中的哪个案例有关联？" |
  - Include exploration handling logic from requirements doc §6.2:
    - User says "不知道"/"没想过"/"说不清楚" → mark as exploration item → gentle next question (max 1 follow-up) → note marks as 「待探索」
    - D1 pass → skip to closing question
  - Include exploration display format from requirements doc §6.3 (待探索方向 section with 💡 hints)
  - Include grill-me vs book-grill follow-up differentiation example from §4.3
  - Target: ≤ 80 lines

  **Part B: config.json**
  - Create `~/.local/share/book-grill/config.json` with basic default fields:
    ```json
    {
    	"version": "1.0.0",
    	"notes_dir": "~/.local/share/book-grill/notes"
    }
    ```
  - Ensure `~/.local/share/book-grill/notes/` directory exists (create if not)

  **Must NOT do**:
  - No Phase 2+ strategies (real-time notepad, mixed type)
  - No websearch strategy
  - No complex config.json schema (keep minimal for Phase 1)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Two small files with clear content from requirements
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 7
  - **Blocked By**: None

  **References**:

  **API/Type References**:
  - `.omo/requirements/book-grill-skill-requirements.md:§4.3` — Follow-up differentiation example (grill-me vs book-grill)
  - `.omo/requirements/book-grill-skill-requirements.md:§4.4` — Complete Socratic follow-up strategy table
  - `.omo/requirements/book-grill-skill-requirements.md:§6.2` — Exploration handling logic
  - `.omo/requirements/book-grill-skill-requirements.md:§6.3` — Exploration display format in notes
  - `.omo/requirements/book-grill-skill-requirements.md:§7.4` — Runtime data directory structure

  **External References**: N/A

  **WHY Each Reference Matters**:
  - §4.4: Complete strategy table — must reproduce exactly
  - §6.2: Exploration handling algorithm — core Phase 1 feature
  - §6.3: Display format for exploration items in notes
  - §4.3: Differentiation example — helps LLM understand book-grill's unique follow-up style

  **Acceptance Criteria**:
  - [ ] File exists: `~/.agents/skills/book-grill/strategies.md`
  - [ ] strategies.md line count ≤ 80
  - [ ] Contains 5 follow-up strategies (模糊/泛泛/矛盾/深入/偏离书本)
  - [ ] Contains exploration handling logic (不知道 → 标记 → 下一题)
  - [ ] Contains D1 pass → closing fallback rule
  - [ ] Contains exploration display format (💡 hints)
  - [ ] File exists: `~/.local/share/book-grill/config.json`
  - [ ] config.json is valid JSON with version and notes_dir fields
  - [ ] Directory exists: `~/.local/share/book-grill/notes/`

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Strategies file validation
    Tool: Bash
    Preconditions: strategies.md has been created
    Steps:
      1. test -f ~/.agents/skills/book-grill/strategies.md
      2. wc -l ~/.agents/skills/book-grill/strategies.md → verify ≤ 80
      3. grep -c "具体化" ~/.agents/skills/book-grill/strategies.md → ≥ 1
      4. grep -c "举例" ~/.agents/skills/book-grill/strategies.md → ≥ 1
      5. grep -c "矛盾" ~/.agents/skills/book-grill/strategies.md → ≥ 1
      6. grep -c "拉回" ~/.agents/skills/book-grill/strategies.md → ≥ 1
      7. grep -c "待探索" ~/.agents/skills/book-grill/strategies.md → ≥ 1
      8. grep -c "closing" ~/.agents/skills/book-grill/strategies.md → ≥ 1
    Expected Result: File exists, ≤ 80 lines, contains all 5 strategies + exploration handling
    Failure Indicators: File missing, line count > 80, any strategy missing
    Evidence: .omo/evidence/task-6-strategies.txt

  Scenario: Config and directory validation
    Tool: Bash
    Preconditions: config.json and notes/ directory created
    Steps:
      1. test -f ~/.local/share/book-grill/config.json
      2. cat ~/.local/share/book-grill/config.json | python3 -m json.tool → valid JSON
      3. test -d ~/.local/share/book-grill/notes/
    Expected Result: config.json is valid JSON, notes/ directory exists
    Failure Indicators: File missing, invalid JSON, directory missing
    Evidence: .omo/evidence/task-6-config.txt
  ```

  **Commit**: YES (groups with Tasks 1-5)
  - Files: `~/.agents/skills/book-grill/strategies.md`, `~/.local/share/book-grill/config.json`

- [x] 7. Full Dialogue Flow Integration Test

  **What to do**:
  - Trigger `/book-grill 三体` in OpenCode and execute full dialogue flow:
    1. **Type confirmation**: LLM should infer "fiction" → ask user → confirm
    2. **A-stage**: Answer A1-A3 with realistic reader responses
    3. **B-stage**: Answer B1-B2
    4. **C-stage**: Answer C1-C2
    5. **D-stage**: Answer D1
    6. **Closing**: Answer closing question
    7. **Note generation**: Verify note file created
  - Test dialogue control:
    - During A-stage, say "跳过" for one question → verify it moves to next
    - During B-stage, say "不知道" for one question → verify it marks as exploration item and continues
    - Test "结束" early termination → verify partial note generated
  - Test D1 pass fallback:
    - In a separate invocation, say "pass" at D1 → verify it skips to closing question
  - Verify note file:
    - File path: `~/.local/share/book-grill/notes/三体-YYYY-MM-DD.md`
    - Frontmatter: title=三体, type=fiction, date=correct
    - Sections: 核心内容, 批判分析, 个人共鸣, 超越书本, 一句话总结, 关键问答摘录, 待探索方向
  - Fix any issues found during testing (update SKILL.md, templates, or strategies as needed)

  **Must NOT do**:
  - No automated test scripts
  - No changes to requirements doc
  - No Phase 2+ features added

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Multi-step integration testing requiring careful verification and potential fixes
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after Wave 1)
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 1-6

  **References**:

  **Pattern References**:
  - `~/.agents/skills/book-grill/SKILL.md` — The skill just created, to be tested
  - `~/.agents/skills/book-grill/templates/fiction.md` — Fiction template to verify against
  - `~/.agents/skills/book-grill/strategies.md` — Strategies to verify against

  **API/Type References**:
  - `.omo/requirements/book-grill-skill-requirements.md:§11.2` — Complete interaction flow for testing
  - `.omo/requirements/book-grill-skill-requirements.md:§7.3` — Note format for verification
  - `.omo/requirements/book-grill-skill-requirements.md:§10` — Dialogue control rules for testing
  - `.omo/requirements/book-grill-skill-requirements.md:§6` — Exploration item handling for testing

  **External References**: N/A

  **WHY Each Reference Matters**:
  - §11.2: The step-by-step flow that must work end-to-end
  - §7.3: The exact note format to verify against
  - §10: The exact dialogue control behavior to test
  - §6: Exploration handling to verify "不知道" triggers correctly

  **Acceptance Criteria**:
  - [ ] `/book-grill 三体` triggers type confirmation (LLM infers fiction)
  - [ ] Type confirmation completes in ≤ 1 round
  - [ ] Fiction-specific questions are asked (not nonfiction/biography/technical)
  - [ ] Questions follow A→B→C→D progression
  - [ ] "跳过" moves to next question
  - [ ] "不知道" marks exploration item and continues
  - [ ] "结束" terminates dialogue and generates partial note
  - [ ] D1 "pass" skips to closing question
  - [ ] Progress indicator appears after each question
  - [ ] Note file created at correct path with correct frontmatter
  - [ ] Note file contains all required sections
  - [ ] Exploration items appear in note's 待探索方向 section

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: Complete dialogue flow (happy path)
    Tool: interactive_bash (tmux)
    Preconditions: All skill files created (Tasks 1-6 complete)
    Steps:
      1. Start OpenCode session
      2. Send: /book-grill 三体
      3. Verify LLM responds with type inference (should suggest fiction)
      4. Confirm type: "对"
      5. Answer A1: "三体讲述了一个关于外星文明入侵地球的故事，主要围绕叶文洁发出信号引发三体人入侵展开"
      6. Answer A2: "叶文洁的决定我理解但不完全认同，她在绝望中做出了不可逆的选择"
      7. Answer A3: "刘慈欣用了多视角叙事，从文革到现代再到未来，时间跨度很大"
      8. Answer B1: "这本书在探讨文明的生存与道德的冲突，黑暗森林法则揭示了宇宙的残酷本质"
      9. Answer B2: "如果结局是人类成功反击，核心信息可能就变成了人类的韧性而非宇宙的冷酷"
      10. Answer C1: "叶文洁让我想到那些在极端环境下做出艰难选择的人"
      11. Answer C2: "让我开始思考技术进步是否真的对人类有利"
      12. Answer D1: "让我更加关注科技伦理问题，在工作中会更审慎地评估技术影响"
      13. Answer closing: "三体让我意识到，在未知面前，人类的渺小恰恰是我们团结的理由"
      14. Verify note file created: ls ~/.local/share/book-grill/notes/三体-*.md
      15. Read note file and verify frontmatter + sections
    Expected Result: Complete dialogue flows through all stages, note file created with correct structure
    Failure Indicators: LLM doesn't trigger skill, type not inferred, wrong template loaded, note not created, missing sections
    Evidence: .omo/evidence/task-7-happy-path.txt

  Scenario: Dialogue control - "跳过" and "不知道"
    Tool: interactive_bash (tmux)
    Preconditions: All skill files created
    Steps:
      1. Start OpenCode session
      2. Send: /book-grill 人类简史
      3. Confirm type: nonfiction
      4. Answer A1 normally
      5. For A2, send: "跳过"
      6. Verify LLM moves to A3 (not stuck on A2)
      7. For B1, send: "不知道"
      8. Verify LLM marks as exploration item and moves to B2
      9. Verify progress indicator shows exploration count ≥ 1
      10. Complete remaining questions normally
      11. Verify note contains 待探索方向 section with B1 marked
    Expected Result: "跳过" moves forward, "不知道" marks exploration and continues
    Failure Indicators: LLM re-asks skipped question, doesn't mark exploration item
    Evidence: .omo/evidence/task-7-dialogue-control.txt

  Scenario: Early termination with "结束"
    Tool: interactive_bash (tmux)
    Preconditions: All skill files created
    Steps:
      1. Start OpenCode session
      2. Send: /book-grill 设计模式
      3. Confirm type: technical
      4. Answer A0, A1, A2
      5. Send: "结束"
      6. Verify LLM generates note with partial content (A-stage only)
      7. Verify note file created
    Expected Result: Partial note generated after early termination
    Failure Indicators: No note created, or note missing A-stage content
    Evidence: .omo/evidence/task-7-early-termination.txt

  Scenario: D1 pass → closing fallback
    Tool: interactive_bash (tmux)
    Preconditions: All skill files created
    Steps:
      1. Start OpenCode session
      2. Send: /book-grill 百年孤独
      3. Confirm type: fiction
      4. Complete A1-A3, B1-B2, C1-C2 normally
      5. For D1, send: "pass"
      6. Verify LLM skips to closing question ("用一句话总结这本书对你的意义")
      7. Answer closing question
      8. Verify note created with D1 marked as exploration item
    Expected Result: D1 pass triggers closing question, not another D-stage follow-up
    Failure Indicators: LLM continues with D-stage follow-up instead of closing
    Evidence: .omo/evidence/task-7-d1-pass.txt
  ```

  **Commit**: YES (if fixes needed)
  - Message: `fix(skill): book-grill integration adjustments`
  - Files: Any files modified during testing
  - Pre-commit: Verify all previous acceptance criteria still pass

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
      Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, check content). For each "Must NOT Have": search skill files for forbidden patterns — reject with file:line if found. Check evidence files exist in .omo/evidence/. Compare deliverables against plan.
      Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Content Quality Review** — `unspecified-high`
      Review all skill files for: correct frontmatter, valid markdown links, consistent terminology, no AI slop (excessive comments, generic names, over-abstraction). Check SKILL.md line count ≤ 150. Check each template ≤ 100 lines. Verify strategies.md covers all 5 follow-up strategies from requirements.
      Output: `SKILL.md [N lines] | Templates [N/N valid] | Strategies [complete/incomplete] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
      Start from clean state. Execute full dialogue flow: trigger `/book-grill 三体`, confirm type (fiction), answer A1-A3, B1-B2, C1-C2, D1, closing. Verify note file created with correct frontmatter and sections. Test dialogue control: "跳过", "结束", "不知道". Test D1 pass → closing fallback. Save evidence to `.omo/evidence/final-qa/`.
      Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
      For each task: read "What to do", read actual file content. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect Phase 2+ features accidentally included. Flag unaccounted content.
      Output: `Tasks [N/N compliant] | Creep [CLEAN/N issues] | Unaccounted [CLEAN/N items] | VERDICT`

---

## Commit Strategy

- **Wave 1 (all 6 files)**: `feat(skill): add book-grill skill — Phase 1 core loop` — SKILL.md, templates/\*.md, strategies.md, config.json
- **Wave 2 (fixes)**: `fix(skill): book-grill integration adjustments` — any fixes from Task 7
- **Pre-commit**: Verify file structure with `ls -la ~/.agents/skills/book-grill/` and `ls -la ~/.agents/skills/book-grill/templates/`

---

## Success Criteria

### Verification Commands

```bash
# File structure
test -f ~/.agents/skills/book-grill/SKILL.md && echo "SKILL.md exists"
test -f ~/.agents/skills/book-grill/templates/fiction.md && echo "fiction.md exists"
test -f ~/.agents/skills/book-grill/templates/nonfiction.md && echo "nonfiction.md exists"
test -f ~/.agents/skills/book-grill/templates/biography.md && echo "biography.md exists"
test -f ~/.agents/skills/book-grill/templates/technical.md && echo "technical.md exists"
test -f ~/.agents/skills/book-grill/strategies.md && echo "strategies.md exists"
test -f ~/.local/share/book-grill/config.json && echo "config.json exists"

# Line counts
test $(wc -l < ~/.agents/skills/book-grill/SKILL.md) -le 150 && echo "SKILL.md ≤ 150 lines"
test $(wc -l < ~/.agents/skills/book-grill/templates/fiction.md) -le 100 && echo "fiction.md ≤ 100 lines"
test $(wc -l < ~/.agents/skills/book-grill/templates/nonfiction.md) -le 100 && echo "nonfiction.md ≤ 100 lines"
test $(wc -l < ~/.agents/skills/book-grill/templates/biography.md) -le 100 && echo "biography.md ≤ 100 lines"
test $(wc -l < ~/.agents/skills/book-grill/templates/technical.md) -le 100 && echo "technical.md ≤ 100 lines"

# Frontmatter
head -5 ~/.agents/skills/book-grill/SKILL.md | grep -q "name:" && echo "SKILL.md has name field"
head -5 ~/.agents/skills/book-grill/SKILL.md | grep -q "description:" && echo "SKILL.md has description field"

# Content patterns — @ prefix file references
grep -q "@./templates/fiction.md" ~/.agents/skills/book-grill/SKILL.md && echo "SKILL.md references fiction template via @"
grep -q "@./strategies.md" ~/.agents/skills/book-grill/SKILL.md && echo "SKILL.md references strategies via @"
```

### Final Checklist

- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] SKILL.md ≤ 150 lines
- [ ] All templates ≤ 100 lines
- [ ] All `@` prefix file references valid (relative paths, auto-inlined by oh-my-openagent)
- [ ] No markdown-only file references without `@` prefix for critical content
- [ ] No Phase 2+ features included
- [ ] config.json has valid JSON structure
