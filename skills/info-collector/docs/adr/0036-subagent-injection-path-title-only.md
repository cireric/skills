# ADR 0036: Subagent Injection — Source File Path + Title Only, No Preview

Production run injected 500-char previews (which were all abstracts/summaries) into subagent prompts. Subagents then rephrased these previews as analysis content rather than reading full source files — 81% of claims were source_indirect. The 500-char preview creates a "I already know the content" illusion that discourages deeper reading. Replace with: source_file path + title (from collected.json) only. Titles provide relevance screening so subagents decide which sources to Read; no body text is pre-exposed, forcing subagents to consult original text for any claim detail. This removes the shortcut of paraphrasing injected previews.

Status: accepted
