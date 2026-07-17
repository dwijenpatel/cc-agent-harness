# Plugin-corpus survey — the user-level plugin fleet, superpowers deep-read

**Date:** 2026-07-17. **Companion to** [claude-code-artifacts.md](claude-code-artifacts.md)
(which covers the binary built-ins and the Anthropic plugins read from the pinned
`~/repos/claude-code` clone @c39cb0f). This file adds: the two-plugin-systems finding, the
installed user-level fleet, and a deep read of **superpowers v6.1.1** (3rd-party, obra) —
the strongest external corpus we've seen for long-horizon agent coding practice.

**Decay warning:** superpowers pinned at v6.1.1 / git d884ae04; the official-marketplace
Anthropic plugins verified content-identical to the surveyed clone at install time
(2026-07-17). Re-verify per version bump before relying on any detail.

## 1. Two separate plugin systems (the "where did my plugins go" answer)

- **Desktop-app / claude.ai plugins** (the app's plugin browser — "Engineering",
  "product manager", etc.): account-side installs. The app materializes their skills into
  its own sessions under `~/Library/Application Support/Claude/local-agent-mode-sessions/`
  — they never touch `~/.claude/settings.json` and never appear in `claude plugin list`.
  They follow the account, not the machine.
- **CLI plugins** (`~/.claude/plugins/` + `enabledPlugins` in `~/.claude/settings.json`,
  scope `user`): what terminal `claude` sessions load in any repo. Marketplace:
  `claude-plugins-official` (github anthropics/claude-plugins-official, 256 plugins,
  48 Anthropic-authored).
- `superpowers` is the one plugin that exists in **both** directories, which is why it was
  the only one visible in settings.json after the app installs.
- No "Engineering" / "product manager" plugin exists in the CLI marketplace — those are
  app-directory-only. Their content is surveyable only after an app session materializes
  them (or from a public source repo if one is named in the app UI).

**Installed user-level fleet (2026-07-17):** superpowers 6.1.1, feature-dev, code-review,
pr-review-toolkit, code-simplifier, ralph-loop, commit-commands, claude-md-management —
all `@claude-plugins-official`, scope user, enabled in `~/.claude/settings.json`.

## 2. Superpowers: the pipeline

A complete brainstorm→plan→execute→finish pipeline, distributed as skills plus a
SessionStart hook (startup|clear|compact) that injects its routing guidance every session.

- **brainstorming** — the interview stage. One question at a time; multiple-choice
  preferred; propose 2–3 approaches with a recommendation; present the design in sections
  with per-section approval; HARD-GATE: no implementation action before an approved
  design, "no project is too simple"; scope check FIRST (multi-subsystem request → decompose
  into sub-projects, each getting its own spec→plan→build cycle); writes a dated design doc;
  **spec self-review** incl. an ambiguity check ("could any requirement be interpreted two
  different ways? pick one and make it explicit"); explicit user review gate on the written
  spec.
- **writing-plans** — plans written for an implementer with "zero context and questionable
  taste": exact file paths, **complete code in every step** (test code AND implementation),
  bite-sized 2–5-minute steps, TDD cycle per task, a **Global Constraints** header with
  exact values copied verbatim from the spec, and per-task **Interfaces: Consumes/Produces**
  blocks ("a task's implementer sees only their own task; this block is how they learn the
  names and types neighboring tasks use"). A **No Placeholders** section names plan-failures:
  "TBD", "add appropriate error handling", "similar to Task N". Self-review checklist: spec
  coverage / placeholder scan / type consistency across tasks.
- **subagent-driven-development** — the execution harness. Fresh implementer subagent per
  task; **two-verdict task review** after each (spec compliance: Missing / Extra /
  Misunderstood — AND code quality: Critical/Important/Minor); fix subagents; **final
  whole-branch review** on the most capable model; **pre-flight plan review** (one scan for
  plan-internal contradictions before task 1, findings batched to the human); worker
  **status contract** DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED with distinct
  controller responses; **model tiering** ("turn count beats token price" — cheapest tier
  only when the plan text contains the complete code, mid-tier floor for prose-spec
  implementers); **durable progress ledger** (`.superpowers/sdd/progress.md` — "controllers
  that lost their place re-dispatched entire completed task sequences — the single most
  expensive failure observed"; explicitly notes `git clean -fdx` destroys it); **file
  handoffs** (task-brief and review-package scripts; "a real session's dispatch hit 42k
  chars of which 99% was pasted history"); fix-wave economics (final review findings → ONE
  fix subagent with the whole list; "a real session's final-review fix wave cost more than
  all its tasks combined").
- **task-reviewer template** — "Do Not Trust the Report": the implementer's report is
  unverified claims; rationales in it are "the implementer grading their own work"; a
  **⚠️ Cannot-verify-from-diff** channel for requirements spanning tasks (controller
  resolves them — it holds cross-task context); **anti-pre-judging** rule for dispatchers
  (never "do not flag X" in a reviewer prompt); plan-mandated defects are still findings —
  "the plan's authorship does not grade its own work; the human decides."
- **verification-before-completion** — the iron law: "NO COMPLETION CLAIMS WITHOUT FRESH
  VERIFICATION EVIDENCE"; the failure table includes "Agent completed → requires: VCS diff
  shows changes; NOT sufficient: agent reports success."
- Supporting: test-driven-development, requesting/receiving-code-review,
  systematic-debugging, using-git-worktrees, dispatching-parallel-agents,
  finishing-a-development-branch, writing-skills.

## 3. Independent convergence with our measured findings

Superpowers is practitioner-derived (no citations), yet it lands on the same mechanisms our
experiments measured — convergent evolution is evidence the mechanisms are load-bearing:

| Ours (measured) | Theirs (practice-derived) |
|---|---|
| exec-loop / nocode runner: fresh session per task + per-task review + closure review | fresh subagent per task + task review + final whole-branch review |
| `.runner/ledger.jsonl` resume; the `git clean` ledger bug we fixed live | progress ledger; "git clean -fdx will destroy the ledger"; re-dispatch = most expensive failure |
| consumed-interface restatement (the T9 lesson; planner prompt; plan-review seam finder) | Consumes/Produces blocks, exact signatures, per task |
| under-determination = defect class (plan-review finder; `<64-hex digest>` trap) | "No Placeholders" named plan-failures at authoring time |
| plan-review (adversarial, pre-implementation) | pre-flight plan review (self-scan, batched to human) — same slot, weaker instrument |
| completion granted never claimed (D3); earned banners; silent-no-op guards | verification-before-completion iron law; "agent reports success" insufficient |
| Sonnet 2/2 review-churn escalations from prose specs | "mid-tier floor for implementers working from prose"; cheapest tier ONLY for code-complete plans |
| file contracts / bundles, not pasted context | task-brief + review-package file handoffs |
| spec-interview: consolidated early questions, PM-boundary | brainstorming: one-at-a-time, multiple-choice, per-section approval |
| the unattended planner's 15-task all-at-once (no appetite question) | scope check first: decompose multi-subsystem work into sub-projects |

## 4. Ideas worth pulling (ranked)

1. **Code-complete plans as a determinacy tier.** Their plans embed the actual code;
   implementation becomes transcription+testing at the cheapest model tier. This is a third
   point on the spec-determinacy spectrum (contracts-only → contracts+worked-examples →
   full code) and plausibly kills the divergent-readings defect class outright by leaving
   nothing to interpret — at the cost of much heavier planning. Directly testable as a
   future nocode arm: same design doc, superpowers-style code-complete plan, cheapest-tier
   implementers. Prediction from their own tiering rule: our Sonnet churn disappears.
2. **Two-verdict task review (spec compliance + quality).** Our review stage (/code-review)
   checks correctness/conventions but never spec fidelity — "validations inert end-to-end"
   shipped as-specified and was caught only at the closure review. A per-task reviewer
   handed the task's spec, reporting Missing/Extra/Misunderstood separately from quality,
   closes that gap. Cheap to add to the nocode runner's review prompt.
3. **Worker status contract** (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED) with
   distinct controller responses — richer than our exit-code-only contract; as a file
   contract it stays within the runner's no-prose-parsing rule.
4. **Fix-wave economics**: one fixer with the complete findings list, never one per finding.
5. **⚠️ Cannot-verify-from-diff** reviewer channel — scope honesty instead of silent ✅.
6. **Anti-pre-judging rule** for review dispatchers. Note the genuine tension with the
   vendor FP-blocklist pattern: blocklists suppress *known-noise classes* inside the
   reviewer's own instructions; pre-judging suppresses *specific findings* from outside.
   Both corpora are right: class-level suppression in the instrument, never
   instance-level suppression in the dispatch.
7. **Ambiguity self-check at authoring time** (brainstorming's "two readings → pick one")
   — the free complement to adversarial plan-review; belongs in any planner prompt.

## 5. PRD-first pipeline (operator proposal, assessed)

Proposal: PM-plugin → PRD → technical planning → build. The evidence supports the shape:
each instrument then owns a disjoint defect class — **PRD/interview closes operator-intent
gaps** (the class plan-review measurably missed: status/rationale), **plan-review closes
spec incoherence** (the class interviews can't see: the unreachable worked-oracle),
**per-task review closes implementation defects**, and superpowers' brainstorming is
independent precedent for gating all creative work behind an approved product artifact.
The app-side "product manager" plugin itself is not yet surveyable (account-side; no CLI
sibling); the nearest readable analogues are brainstorming (above) and feature-dev's
clarify phase. The eaitl-nocode-interactive experiment is the first live cell of exactly
this pipeline.

## 6. Not yet surveyable / next steps

- **App-directory plugins** ("Engineering" by Anthropic, "product manager", anything else
  installed via the desktop app): content materializes only in app sessions. To survey:
  open one desktop-app session with the plugin active, then read
  `~/Library/Application Support/Claude/local-agent-mode-sessions/…/skills/`, or name the
  plugin's public repo.
- Superpowers' remaining skills (systematic-debugging, dispatching-parallel-agents,
  writing-skills, receiving-code-review) read at skim depth only — deepen on demand.
- The debugging/worktree/finishing skills likely carry more operational gems (the skim
  showed the same evidence-first voice); budget a second pass if we adopt tier-1 or tier-2.
