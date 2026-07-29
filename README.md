# outrigger

**A lab for long-horizon coding agents.** outrigger is an experiment repo: a place to
build, measure, and discard ideas about what makes coding agents perform well on large,
ambitious, hours-long tasks — specs interrogated before code, verification the worker
cannot touch, completion granted on evidence rather than declared on confidence.

It began as a product thesis (the stabilizing float lashed to the hull — the agent does
the work, the harness keeps it upright). It is now, deliberately, the *lab* behind that
idea: mechanisms are built here, run against real work, and kept or demoted by what the
measurements say. **The ground moves fast** — models improve between experiments, and
several findings below revised our own earlier beliefs. Every conclusion in this repo
carries a date; read it as a snapshot, not gospel.

> **Where the active work lives now:** the current incarnation of the useful artifacts —
> a planning skill, an adversarial plan reviewer, and a gated execution runner — is the
> **one-punch** repo (`~/repos/one-punch`), installed as Claude Code plugin skills
> (`/one-punch:tech-plan`, `/one-punch:plan-review`). outrigger remains the evidence
> base and testbed those artifacts cite; behavior changes earn their numbers here first.

## What we've learned so far (dated, revisable)

The strongest findings from the experiments run in this repo, including the reversals:

1. **Spec ambiguity is the defect class that survives everything** (2026-07 series).
   Implementers, reviewers, and test authors all inherit the same misreading; end-state
   review cannot catch it because code consistent with its author's reading looks
   correct. The cheapest interception is before implementation: a planning interview
   that pins interfaces and worked examples, then an adversarial *plan* review. That
   reviewer caught a build-breaking spec defect pre-implementation, blind, in its first
   live firing (2026-07-17).
2. **The blind merge gate underperformed on well-specified work** (three-arm
   experiment, 2026-07-16: gated vs. diligent vs. frontier-solo). All three arms shipped
   the same single genuine defect — a spec seam — while the gate cost 5.9× the ungated
   arm. The gate is demoted to a profile for weak specs or high stakes. This reversed
   the repo's original centerpiece thesis, by its own measurement discipline.
3. **Frontier one-shot builds are strong; their residual defects cluster where two
   artifacts must agree** (pipeline vs. one-shot comparison, 2026-07-20). A single
   conversation-spec'd frontier build produced 2.6× the system at conversation speed —
   and its surviving defects were cross-artifact drift (data↔fixtures, spec↔code,
   docs↔defaults), exactly the class plan-pinning and independent verification target.
4. **Fresh adversarial eyes keep paying, on every artifact, regardless of method.**
   Both codebases in that comparison — including the pipeline-built one — yielded real
   findings only when reviewed by instruments that had no stake in them. Layered
   independent review is the one mechanism no experiment here has managed to demote.
5. **Error compounding over run length is real and not fixed by model size** (external
   evidence corpus). Short fresh-context links with gates between them remain the
   working structure; whether they beat one long well-resourced session is still this
   lab's central open bet, not a settled fact.
6. **Token economics are measurable and worth measuring** (2026-07-13, $17): cached
   reads weigh well under a fifth of fresh input against subscription windows — settled
   by a pre-registered two-arm experiment when vendor docs wouldn't answer.

## How the lab works

**Evidence discipline.** A mechanism enters the design only when graded evidence
licenses it; otherwise it is Provisional with a named promotion trigger, or TBD with a
named settling experiment. Changes to the machinery itself enter the same way:
pre-registered predictions, null arms where feasible, an append-only ledger, and
deletion criteria — a check that catches no errors gets removed, on the record (see
finding 2). The [design doc](docs/design/evidence-based-harness.md) records every
decision with its warrant; the [graded evidence base](docs/research/distilled/README.md)
shows the scoring method; the [full corpus](docs/research/README.md) holds raw material
and the corrections ledger.

**Everything is runnable.** Each tool is a standalone CLI connected by schema-validated
files and exit codes, and ships tests that drive the full pipeline against a scripted
mock worker — no tokens spent:

| Tool | One thing, done well |
|---|---|
| [spec-interview](.claude/skills/spec-interview/README.md) | Goal in, ratified machine-checkable plan out |
| [plan-preflight](tools/plan-preflight/README.md) | Refuses malformed or unratified plans |
| [heldout-suite](tools/heldout-suite/README.md) | Blind suite lifecycle: fails-on-base proof, tamper-evident seal |
| [merge-gate](tools/merge-gate/README.md) | Judges the merged tree in a clean worktree |
| [exec-loop](tools/exec-loop/README.md) | Walks a ratified plan unattended: author, seal, implement, gate, land |
| [run-ledger](tools/run-ledger/README.md) | Append-only measurement ledger: every prediction and null arm |
| [shadow-pilot](tools/shadow-pilot/README.md) | Harness-vs-null comparisons with a blind arbiter |

```sh
git clone https://github.com/dwijenpatel/outrigger.git && cd outrigger
python3 tools/exec-loop/test_exec_loop.py   # full mock pipeline, zero API spend
```

**Experiment records.** The long-horizon value chain (design, specs, arm ledgers, grade
records) lives under
[docs/research/internal/longhorizon-value/](docs/research/internal/longhorizon-value/chain-design.md).
v1's conclusions live in [docs/attic/](docs/attic/README.md) — prior art to argue
against, never a source of defaults; the continuity record is
[docs/reincarnation-plan.md](docs/reincarnation-plan.md). The capstone that graduated
into one-punch is
[docs/design/one-liner-to-code-complete.md](docs/design/one-liner-to-code-complete.md)
(frozen here; living copy in one-punch).

## License

MIT. See [LICENSE](LICENSE).
