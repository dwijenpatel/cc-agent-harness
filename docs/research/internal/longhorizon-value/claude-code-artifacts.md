# Claude Code's code-quality artifacts — survey, extraction, and measured behavior

**Surveyed 2026-07-16/17.** Sources: (a) the public `anthropics/claude-code` repo, local
clone `~/repos/claude-code` @ `c39cb0f`; (b) the **shipped binary** (`claude` 2.1.207 CLI;
strings extracted from the 229 MB executable — the built-in skills are compiled in, not on
disk); (c) live headless driving of the built-ins during the long-horizon experiment
(records under [runs/](runs/)). **Decay warning:** vendor artifacts are the
fastest-decaying dependency in this corpus — every claim here is pinned to the versions
above and must be re-checked per release before anything load-bearing reuses it.

Why this survey exists: the operator's revealed-preference argument — these artifacts
survived Anthropic's internal experimentation at a scale we can't run; what shipped (and
what conspicuously didn't) is evidence. Our own three-arm experiment independently
converged on the same shape (see [chain-design.md](chain-design.md) and
[runs/CORRECTIONS.md](runs/CORRECTIONS.md)).

---

## 1. Built-in `/code-review` (binary-extracted)

**Scope resolution (Phase 0):** reviews a diff — `git diff @{upstream}...HEAD`, falling
back to `main...HEAD` / `HEAD~1`, plus uncommitted changes; **or an explicit target
argument** (PR number, branch, file path, range). Everything after the effort level in the
invocation is passed through as target/instructions.

**Effort cells** (one skeleton, parameterized; verbatim structure from the binary):

| Level | Structure | Cap |
|---|---|---|
| low | 1 inline diff pass, hunk-only, no subagents, no verify; test/fixture hunks skipped | ≤4 findings |
| low (Sonnet-5 variant) | same, but targets `min(files_changed, 4)` findings with a second pass if under | ≥min(files,4) |
| medium | 8 finder subagents (3 correctness + reuse/simplification/efficiency + altitude + CLAUDE.md-conventions), ≤6 candidates each → 1-vote verify, **precision-biased** | ≤8 |
| high | same 8 angles, verify **recall-biased** | ≤10 |
| xhigh / max | **10 angles** (adds language-pitfall + wrapper/proxy) × 8 candidates → recall verify → fresh-eyes **gap sweep** (+8) | ≤15 |

**The five correctness angles** (shared string constants, also used by the workflow/ultra
variant): A line-by-line diff scan (read the enclosing function of every hunk; bugs in
unchanged lines of touched functions are in scope); B removed-behavior auditor (for every
deleted line, name the invariant it enforced and find where it's re-established); C
cross-file tracer (callers/callees of changed functions); D language-pitfall specialist
(falsy-zero, `==` coercion, mutable default args, nil-map writes, SQL injection, TZ/DST,
float equality); E wrapper/proxy correctness (delegation routing, method forwarding).

**Verify pass:** dedup by location, then **one verifier per (file,line) location group**
(the binary's comment: cuts verifier count by the ~40% cross-finder collision rate).
Three-state ladder: CONFIRMED (name the triggering inputs, quote the line) / PLAUSIBLE
(mechanism real, trigger uncertain) / REFUTED (only when constructible from the code —
quote the guard). Recall mode adds explicit anti-over-refute rules: "PLAUSIBLE by default"
for realistic-state candidates (races, rare-path nil, falsy-zero, lost regex anchors).

**Output:** the typed `ReportFindings` tool when available ({level, findings[]} with
file/line/summary/failure_scenario/category/verdict); JSON-array fallback otherwise.
Cleanup findings use the same shape with the cost in `failure_scenario`; "correctness
always outranks cleanup when the cap forces a cut."

**Flags:** `--fix` = after the findings list, apply each one (skip anything
behavior-changing, out-of-scope, or judged false-positive — note skips rather than argue);
`--comment` = inline PR comments via the GitHub MCP tool or `gh api` fallback; `ultra` =
routes to the cloud multi-agent workflow (user-triggered, billed; falls back to a local
max-effort review when unavailable).

**Routing layer (notable engineering):** per-model prompt cells exist (`o48-*-v1`
Opus-4.8-tuned variants of every tier; a `low-sonnet5` cell) — prompts are model-tuned,
not one-size; a **finder-budget hint scales with diff size** (`git diff --numstat` total
lines / 150, clamped 2–8 subagents) — difficulty-adaptive fan-out already shipped;
workflow routing behind a feature gate; full telemetry on every routing decision. The
whole git invocation for sizing is hardened (`core.hooksPath=/dev/null`, no lazy fetch,
no terminal prompts).

## 2. Built-in `/simplify` (binary-extracted)

Same Phase-0 scoping. **4 cleanup agents in parallel** — Reuse ("name the existing helper
to call instead"), Simplification (redundant/derivable state, copy-paste variation, dead
code — "name the simpler form"), Efficiency (wasted work, sequential independents,
closure-capture lifetime leaks), Altitude (right-depth check: "special cases layered on
shared infrastructure are a sign the fix isn't deep enough") — **then it applies the
fixes itself** (dedup → fix → skip behavior-changing/out-of-scope/false-positive with
notes). No verify pass. Quality-only by contract: "do not look for correctness bugs —
that is what /code-review is for." The four angle texts are the **same string constants**
code-review's cleanup angles use — one source of truth with an explicit precedence rule.

## 3. Published plugins (`~/repos/claude-code/plugins/`)

**`code-review` plugin** — the built-in's published ancestor and the most rigorous
pipeline in the repo (`plugins/code-review/commands/code-review.md`): haiku gatekeeper
(skip closed/draft/trivial/already-reviewed) → haiku CLAUDE.md-file locator → sonnet
change summarizer → **4 parallel finders** (2 sonnet CLAUDE.md-compliance; **2 Opus bug
agents with deliberately different framings**) → **one validation subagent per issue**
(Opus for bugs, sonnet for compliance: "validate that the stated issue is truly an
issue") → filter unvalidated → high-signal output. Carries an explicit **do-not-flag
blocklist**: pre-existing issues; correct-looking-but-actually-fine; "pedantic nitpicks a
senior engineer would not flag"; anything a linter catches; general quality concerns
unless CLAUDE.md-required; rules explicitly silenced in code. "If you are not certain an
issue is real, do not flag it. False positives erode trust." One comment per unique
issue; committable suggestions only when they fix the issue entirely.

**`pr-review-toolkit`** — six specialist agents (`plugins/pr-review-toolkit/agents/`),
each a narrow zealot persona with structured output:
- `code-reviewer` (**model: opus**): CLAUDE.md compliance + bugs, anchored 0–100
  confidence rubric, **report only ≥80**.
- `code-simplifier` (**model: opus**): preserve-functionality clarity pass; explicit
  anti-over-simplification rules (no nested ternaries, clarity over brevity, keep helpful
  abstractions).
- `silent-failure-hunter`: zero-tolerance error-handling audit — empty catches forbidden,
  "list every error type this catch could hide," fallbacks must be explicit/justified,
  mocks never in production paths; severity CRITICAL/HIGH/MEDIUM.
- `type-design-analyzer`: invariants identified, then **four 1–10 ratings**
  (encapsulation / invariant expression / usefulness / enforcement); "make illegal states
  unrepresentable"; anti-patterns list (anemic models, doc-only invariants).
- `pr-test-analyzer`: behavioral-not-line coverage; criticality-rated gaps (1–10 with
  the concrete regression each test would catch); flags tests coupled to implementation
  rather than behavior — "good tests fail when behavior changes unexpectedly, not when
  implementation details change."
- `comment-analyzer`: comment-rot guardian; verify every claim against code; advisory-only
  (explicitly must not edit).

Orchestrated by `review-pr` with **conditional activation** (types agent only if new
types; silent-failure only if error handling changed; simplifier only after review
passes) and sequential-vs-parallel modes.

**`feature-dev`** (`plugins/feature-dev/`) — the creation pipeline, 7 phases: discovery →
**2–3 parallel `code-explorer` agents (model: sonnet)** each returning 5–10 key files →
the orchestrator **reads those files itself** ("read files identified by agents" — never
act on summaries alone) → **Phase 3 marked "CRITICAL — DO NOT SKIP": clarifying
questions, wait for answers** ("if the user says 'whatever you think is best', provide
your recommendation and get explicit confirmation") → **3 parallel `code-architect`
agents (sonnet) with different value functions** (minimal-change / clean-architecture /
pragmatic), orchestrator recommends, **user picks** → approval-gated implementation → 3
parallel reviewers with different lenses → summary. Architects are told: "make confident
architectural choices rather than presenting multiple options" (divergence happens at the
panel level, not inside one agent).

**`ralph-wiggum`** — the published long-horizon loop: a Stop-hook re-feeds the SAME
prompt each iteration; work persists in files/git; `--completion-promise` (exact-match
string — their README flags you cannot encode SUCCESS-vs-BLOCKED dual outcomes) and
`--max-iterations` as the real safety rail. Scoping guidance verbatim-in-spirit: good for
"tasks with automatic verification (tests, linters)"; bad for "unclear success criteria."
Philosophy: iteration > perfection; failures are data; **operator skill (prompt/spec
quality) matters**; persistence wins. The command file adds: never output a false
completion promise to escape the loop.

**Others, briefly:** `security-guidance` (PreToolUse hook watching 9 patterns);
`commit-commands`; `hookify` (conversation-analyzer → custom guard hooks); `plugin-dev`
(meta-toolkit); `agent-sdk-dev`; output-style plugins. The separately-extracted built-in
**security-review** skill: diff-scoped, high-confidence-only (>80%), explicit exclusions
(DoS, secrets-on-disk, rate limits), two-phase (context research → comparative analysis).

## 4. Cross-cutting design patterns (what the corpus teaches)

1. **Find → adversarially validate → filter, everywhere.** No serious pipeline trusts a
   single pass; validation runs at equal-or-higher tier than finding.
2. **False positives are treated as THE product risk** — anchored confidence rubrics,
   ≥80 thresholds, do-not-flag blocklists, precision/recall as an explicit dial.
3. **Model tiering is shape-based, not difficulty-estimated**: haiku gates, sonnet
   breadth (explore/architect/compliance), opus judgment (bugs/validation/simplify) —
   plus diff-size-scaled fan-out. Cheap, static, no estimator.
4. **Specialization by defect class with conditional activation** — narrow zealot
   personas + an aggregator beat one generalist; agents activate only when the diff
   contains their prey.
5. **Quality is first-class but staged strictly after correctness**, with
   preserve-functionality as an invariant and anti-overreach rules.
6. **Ambiguity is resolved by forced human interaction at plan time** (feature-dev's
   DO-NOT-SKIP phase) — but the discipline is *conversational*, not notational: nowhere
   in the corpus is there an executable-pins rule, negative-example discipline, or any
   spec-notation guidance (see §6).
7. **Anti-telephone-game rule**: subagents return pointers (file lists); the orchestrator
   re-reads primary sources before acting.
8. **Negative space:** no hidden-test authorship, no test secrecy, no seals, no
   adversarial-implementer threat model anywhere in the dev workflow. The threat model is
   honest-but-fallible throughout. Published long-horizon guidance (ralph) presupposes an
   oracle ("automatic verification") but never says who writes it.

## 5. Operational facts from driving the built-ins headless (hard-won)

- Slash commands **work as `claude -p` prompts** (the skill expands; subagent fan-out
  runs headless). BUT our exec-loop launcher passes `--disable-slash-commands` by design
  — workers can't invoke skills through it; call `claude` directly for review/simplify
  stages (discovered live: sessions returned "Unknown command: /code-review", exit 0,
  0 turns, $0).
- `--effort <level>` is a real per-session CLI flag (launcher-verified on 2.1.207); the
  `CLAUDE_CODE_EFFORT_LEVEL` env var also exists (binary strings show it overriding
  sessions) but the flag is the verified path.
- Headless `-p` sessions **deny every permission-gated tool by default** (Write/Edit/
  Bash/Skill) and still **exit 0** — measured live 2026-07-16: the first nocode-trial
  plan session ran 533s/$1.65/16 turns, produced *zero files*, and ended "grant write
  access and I'll create all 15 files". Same silent-no-op class as the unknown-command
  failure: success signals lie; only artifact-existence checks tell the truth. Denial
  evidence is structured — `permission_denials` in the result JSON. Write-capable
  automation must pass `--dangerously-skip-permissions` (or configure explicit allows);
  read-only review sessions get by without it, which is why the probe never hit this.
- Headless `-p` sessions may run **static-only** — in our probe the sandbox blocked
  execution, so the review hand-traced instead of running anything. A review that "ran
  clean" may never have executed a test; read the transcript's own caveats.
- `ReportFindings` may not fire headless; findings arrive as JSON/text in `.result`.
- The conventions angle reads **CLAUDE.md only** ("if no CLAUDE.md applies, return
  nothing") — a convention living in a task spec is *requested* of the implementer but
  never *enforced* by review. Conventions must be routed into CLAUDE.md to arm the
  reviewers (this reshaped the nocode-trial planner prompt).
- Cost/latency measured on a ~5.5k-line whole-chain diff at xhigh (Opus): spec-blind
  $4.11 / 12.3 min / 8 findings; spec-fed $7.00 / 25.2 min / 4 findings.

## 6. Measured behavior (the probe, corrected)

Full record: [runs/review-probe/PROBE.md](runs/review-probe/PROBE.md) and
[runs/CORRECTIONS.md](runs/CORRECTIONS.md). Headlines that should inform any reuse:
`/code-review xhigh` (both spec-blind and spec-fed) **missed the one genuine shared
defect** of the three-arm experiment (the cross-spec registry seam) while **correctly
verifying** a contract the independent test-oracle had flagged wrongly — i.e., review and
test-authored oracles erred in *opposite directions* on the same corpus. Review's unique
catches were real and disjoint: a confirmed TS-parity bug (`requireInt` accepting `2.0`
where the engine errors — arbitrated live), two plausible siblings (ASCII-only cast
regexes; `to_date` regex narrower than `fromisoformat` — flagged independently by both
cells), and product-design gaps (inert validations end-to-end; CSV magnitude footgun;
10-sample examples cap) that ~1,400 sealed tests never touched. Conclusion carried into
the design amendment: **review and independent test authorship are complementary
instruments over disjoint defect classes; neither substitutes for the other.**

## 7. What we ported / plan to port into outrigger's pipeline

Ported already: conventions-into-CLAUDE.md (nocode-trial planner prompt); `--effort`
flag + auto-memory-off + process-group kill in the trial runner; review-churn as a
mechanical escalation meter (`--fix` dirtying the tree); the four cleanup angles ran as a
real `/simplify` pass over our own runner (found genuine drift). Planned: the FP
blocklist + confidence rubric grafted into our review stage; pr-test-analyzer's
implementation-coupled-test lens added to the oracle-authoring role contract (it names
the over-pin class behind every suite adjudication we ran); shape-based routing defaults;
the paraphrase gate (ours — the corpus has no spec-notation discipline to borrow).
