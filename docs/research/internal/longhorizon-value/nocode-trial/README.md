# nocode-trial — design doc → built-ins → code, walk-away

The trial: `[design-plan.md] → [Claude Code built-ins] → output code`, unattended.
**All cognition is built-in** — the planning session decides its own task breakdown,
implementation is a plain fresh session per task, review/fix is `/code-review --fix`,
quality is `/simplify`. The runner ([runner.py](runner.py), ~200 lines) is orchestration
glue ONLY: it sequences fresh headless sessions, reads **git state**, runs the manifest's
checks, and stops. It never parses model prose for control flow.

Deliberately NOT comparable to the arm experiments: the model picks its own task count and
shapes; no ratified plan contracts, no walls, no independent oracle. That's the point of
the trial.

## The mechanical rules (the two things the operator asked to automate)

- **Escalation meter** = review churn, read from git: a `/code-review --fix` pass that
  leaves the tree dirty applied findings (runner commits them, reviews again). A **second**
  dirty pass = the task is churning → revert to the task's base, re-implement fresh at the
  escalate model, review again. Churn after escalation → **HALT** (operator judgment).
- **Chaining / walk-away**: the runner's loop starts the next task only after the previous
  one's checks pass; any session failure, timeout, no-commit session, or post-escalation
  churn halts the whole run with state on `.runner/ledger.jsonl`. Re-running skips
  completed tasks and starts every task from a mechanically cleaned tree.
- `/simplify` is trust-but-verify: the runner re-runs the task's checks itself afterward;
  red → the simplify commit is reverted (noted on the ledger) and the run continues.

## Kickoff

```sh
mkdir ~/repos/eaitl-nocode && cd ~/repos/eaitl-nocode && git init
cp ~/repos/eaitl/design-draft.md . && git add -A && git commit -m "seed"
# optional but recommended: a CLAUDE.md with the conventions (stdlib-only, mypy --strict,
# unittest) — the built-in reviewers enforce CLAUDE.md rules by quotation.

python3 <outrigger>/docs/research/internal/longhorizon-value/nocode-trial/runner.py \
    --repo ~/repos/eaitl-nocode --plan design-draft.md --yes
```

Defaults: implement = Sonnet 5 @ xhigh, review/simplify/escalate/plan = Opus 4.8 @ xhigh
(effort via `CLAUDE_CODE_EFFORT_LEVEL`, model via `--model` — both per-session). Every
session's full JSON result (incl. usage) is archived under `.runner/<ts>/` for post-hoc
cost analysis; ledger records per-task escalation and simplify-revert flags.

Estimated spend at eaitl scale (~10 tasks the planner will likely choose): plan ~$3-5;
per task ~$5-12 (implement + 1-2 review passes with subagent fan-out + simplify);
closure review ~$5-10 → **~$60-130 total**. Note plainly: review-heavy is not cheap —
the difference vs the gated harness is where the money goes (applied, validated fixes
vs hidden-test gates), not that it's free.

## Known fidelity gaps (accepted for this trial)

Spec admission is the planner's own judgment (no preflight, no ratification); no
independent end oracle (closure is a report-only whole-diff review); stop semantics are
halt-on-mechanical-signal only. If the trial's output warrants a real verdict, grade it
afterward against an independently authored spec-derived suite — that machinery exists
one directory up.
