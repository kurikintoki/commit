# RESULT5 — Implement PLAN5: `SKILL.md` arguments wording

Source: chat instruction "implement @03_plans/PLAN5.md and write results in RESULT5.md" (no prompt
file; PROMPT5 asked for the PLAN). Date: 2026-11-21

## Task

Implement [[PLAN5]] (Confirmed): reword `/commit`'s `SKILL.md` so the arguments placeholder appears
only on the `Arguments:` line, add a test that guards this, and update the docs.

## Result

| File | Change |
|---|---|
| `.claude/skills/commit/SKILL.md` | Step 1's "Followed from another skill" bullet now reads "ignore the Arguments line above. It is either empty or an unfilled placeholder. Use the file list and the suggested subject that skill gave you instead." The Spec line adds `03_plans/PLAN5.md` (wording) |
| `.claude/skills/commit/test_select_paths.py` | New `TestSkillMd`: the placeholder appears exactly once in `SKILL.md`, on a line starting with `Arguments:` |
| `CLAUDE.md` | Spec line adds PLAN5. New convention: write the placeholder only on the `Arguments:` line (a test checks this) |
| `README.md` | Spec line adds PLAN5 |

No behavior change: `select_paths.py`, the procedure's steps and the exit codes are as before.

### Verification

- `python3 .claude/skills/commit/test_select_paths.py` → `Ran 30 tests … OK` (29 before + the guard).
- `grep -c 'ARGUMENTS' .claude/skills/commit/SKILL.md` → `1`.
- Manual checks (yours): the next typed `/commit` should show step 1's second bullet as "ignore the
  Arguments line above …", with no empty backticks. `/prompt --commit` waits for PLAN16 in the
  prompt project.

### After the commit

Mark PLAN5 `Implemented · SHA: <sha>` (`> Status: Implemented · Depends-on: PLAN3 · SHA: <sha>`)
and rebuild `03_plans/INDEX.md`. That needs the SHA of the commit containing this work, so it's a
separate step.

## Items Requiring Confirmation（要確認）

None.
