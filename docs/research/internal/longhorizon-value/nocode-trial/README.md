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

## The plan-review A/B

One planning session, forked into two arms; the only delta is one adversarial
prose-review pass ([/plan-review](../../../../../.claude/skills/plan-review/SKILL.md))
over the same specs before any implementation:

```sh
# &&-chained ON PURPOSE: if the plan stage fails, nothing forks and no arm
# re-plans on its own — a planless fork would silently break the shared-plan
# premise (measured live on the first kickoff attempt).
python3 runner.py --repo ~/repos/eaitl-nocode --plan design-draft.md --stop-after-plan --yes && \
cp -R ~/repos/eaitl-nocode ~/repos/eaitl-nocode-A && \
cp -R ~/repos/eaitl-nocode ~/repos/eaitl-nocode-B && \
python3 runner.py --repo ~/repos/eaitl-nocode-A --yes && \
python3 runner.py --repo ~/repos/eaitl-nocode-B --plan-review --yes
```
The fork (`cp -R`) carries `.runner/` — the ledger — so both arms resume from the
identical post-plan state: arm A goes straight to implementation, arm B runs
`/plan-review --fix` first.

Arm B installs the canonical skill (outrigger `.claude/skills/plan-review/`) into the
trial repo for one session and uninstalls it after, so its task-phase tree differs from
arm A's only by the spec amendments + `plan-review-report.md`. The runner halts if the
session leaves no report file — the silent-no-op guard: an unresolved slash command
answers "Unknown command" and exits 0 having done nothing (the review-probe's measured
failure mode). Run the arms serially for clean wall-clock telemetry. Arm B adds one
review-model session, ~$3–8.

**Measurement at grading time** (decided then, like oracle granularity): grade both
end-states against independently authored suites; the sharp causal readout is whether
arm A's defects sit at the spec locations arm B's review flagged.

## Kickoff

```sh
mkdir ~/repos/eaitl-nocode && cd ~/repos/eaitl-nocode && git init
cp ~/repos/eaitl/design-draft.md . && git add -A && git commit -m "seed"

python3 <outrigger>/docs/research/internal/longhorizon-value/nocode-trial/runner.py \
    --repo ~/repos/eaitl-nocode --plan design-draft.md --yes
```

**Conventions are the planner's job, not a manual pre-step.** The planning session
derives the project-wide conventions from the design doc and writes them to a root
CLAUDE.md — because that is the surface the built-in review/simplify passes enforce
against (their "Conventions" angle reads CLAUDE.md and flags violations by quotation; a
convention that lives only in a task spec is *requested* of the implementer but never
*enforced* by review). Whether the planner then chooses strict conventions — the design
doc pins none — is itself a trial finding. To force a floor instead, commit your own
CLAUDE.md in the seed step; the planner is told to write one only if absent.

Defaults: implement = Sonnet 5 @ xhigh, review/simplify/escalate/plan = Opus 4.8 @ xhigh
(per-session `--model` and `--effort` flags; auto-memory disabled so fresh means fresh).
Sessions run with `--dangerously-skip-permissions`: headless `-p` denies every
permission-gated tool by default *and still exits 0* (measured: the first live plan
session spent $1.65/533s and wrote nothing) — the disposable, operator-seeded trial repo
is the permission boundary here. Denials, if any still occur, are surfaced as a stderr
WARNING and a `permission_denials` count on the session's ledger record; control flow
stays git-state-only (a session that couldn't act halts via the no-commit and
missing-artifact guards).
**Per-session telemetry is first-class**: every session appends a ledger record with
model, effort, runner-measured wall_s, cost_usd, num_turns, api_s, and the four token
counts (best-effort parse — a stats hiccup never affects control flow); the full raw JSON
stays archived under `.runner/<ts>/`. Completion (and any halt) prints a spend rollup:
totals plus a per-`model@effort` split. Ledger also records per-task escalation and
simplify-revert flags.

Estimated spend at eaitl scale (~10 tasks the planner will likely choose): plan ~$3-5;
per task ~$5-12 (implement + 1-2 review passes with subagent fan-out + simplify);
closure review ~$5-10 → **~$60-130 total** (+~$3-8 once for a `--plan-review` arm).
Note plainly: review-heavy is not cheap —
the difference vs the gated harness is where the money goes (applied, validated fixes
vs hidden-test gates), not that it's free.

## Known fidelity gaps (accepted for this trial)

Spec admission is the planner's own judgment (no preflight, no ratification); no
independent end oracle (closure is a report-only whole-diff review); stop semantics are
halt-on-mechanical-signal only. If the trial's output warrants a real verdict, grade it
afterward against an independently authored spec-derived suite — that machinery exists
one directory up.
