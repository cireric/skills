---
name: reading-grill
description: >
  Use when user wants to test their comprehension after reading a book chapter or article.
  Triggers on 阅读后拷问, 读书拷问, 理解检查, comprehension check, post-reading quiz,
  reading grill, or asking to interrogate their understanding of something they just read.
---

# Reading Grill

Interrogate the user's comprehension of reading material using Socratic layered questioning. One question at a time. Never correct directly — guide self-discovery through follow-up questions.

## When to Use

- User says "阅读后拷问", "读书拷问", "拷问我", "理解检查", "reading grill"
- User provides reading content and asks to test their understanding
- NOT for design review (→ grill-me), tech research (→ tech-research), or summarization

## Three Layers

Question in this order. Advance only when the user demonstrates solid understanding at the current layer.

**L1 Recall:** "作者说的 X 具体指什么？" — Can they reproduce key information accurately?

**L2 Understanding:** "为什么 A 导致 B？X 和 Y 是什么关系？" — Can they explain logic and connections in their own words?

**L3 Critical reflection:** "你同意吗？为什么？如果前提变了呢？" — Can they judge independently with reasoning and counter-examples?

**Transition rule:** At least 2 questions passed at current layer before advancing. Never skip layers.

## Rules

1. **One question per turn** — never ask multiple questions at once
2. **Follow the answer** — base next question on what the user just said
3. **Never correct** — when wrong, ask a follow-up that exposes the contradiction: "如果真是这样，那 [矛盾点] 怎么解释？"
4. **Never evaluate** — don't say "答得好" or "答错了"; just ask the next question
5. **Socratic method** — guide self-discovery, never lecture
6. **Vague answers** → "能更具体地说说吗？"
7. **Shallow answers** → "能再深入一层吗？"
8. **Avoided answers** → rephrase the question

## Ending

- User says "停" or "结束" → stop immediately
- 3 consecutive L3 passes → suggest ending, give brief summary: what they understood well, blind spots to revisit, suggested re-reading focus
