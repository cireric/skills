You are performing a lightweight review verification. Your task is to check ONLY whether specific BLOCKER-level issues have been fixed — not a full review.

Read these files from the skill's .workdir/:
- analysis.json — the current analysis (after fixes were applied)
- collected.json — source materials

## Issues to Verify

The following BLOCKER issues were identified in the previous review. Check ONLY these issues:

{{BLOCKER_ISSUES_LIST}}

## Verification Process

For each issue listed above:
1. Check if the fix described in the recommendation has been applied
2. Verify the fix did not introduce new problems (e.g., new unsourced claims, broken JSON structure)

## Output

Write a simple verification report to .workdir/lightweight_review_result.json:

```json
{
  "all_blockers_fixed": true,
  "remaining_blockers": []
}
```

Or if issues remain:

```json
{
  "all_blockers_fixed": false,
  "remaining_blockers": [
    {"issue_id": 2, "description": "Issue still not fixed: ..."}
  ]
}
```

Do NOT perform a full review. Only verify the specific BLOCKER issues listed above.
