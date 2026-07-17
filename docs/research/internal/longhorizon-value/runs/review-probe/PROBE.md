# Review-arm probe — can Opus-as-reviewer catch what Opus-as-implementer missed?

Target: arm N's product diff `a129bad...d393126`. Two cells, `/code-review xhigh`
(inline 10-angle fan-out + verify), Opus 4.8, report-only, headless (static-only —
execution was sandbox-blocked; noted as a condition):
- **cell 1, spec-blind**: pure product tree, no specs present. $4.11, 12.3 min, 8 findings.
- **cell 2, spec-fed**: the eleven ratified spec renders in docs-specs/ (outside the
  reviewed range), review instructed to verify against pinned contracts. $7.00, 25.2 min,
  4 findings.

## Result on the two known spec-trap defects (ground truth from slice-2)

**Caught: 0/2 in both cells.** Worse: cell 2 hand-traced the pipeline and freeze flows and
declared them "verbatim-correct" / "unusually faithful" — a FALSE VERIFICATION of the
confirm-shape defect. That is the fourth independent wrong reading of the same spec
sentence (N's implementer, H's implementer, F's implementer, and now a spec-armed
reviewer), across two model tiers and two roles. The only instrument that ever caught it
was the slice-2 author's EXECUTABLE expectation (assertEqual on the pinned shape). The
registry-seam defect was likewise missed by both cells ("t2 → match spec").

## What review DID find (complementary classes, cheap)

Arbitrated so far: **one confirmed new real parity bug** — generated TS `requireInt` uses
Number.isInteger (accepts 2.0) where the engine's _require_int errors; verified live
(engine errors, N's TS slices silently). Plus 2 more plausible TS-parity gaps (ASCII-only
cast regexes vs Python int() unicode digits; to_date DATE_RE narrower than fromisoformat —
flagged independently by BOTH cells), an inert-validations product gap (validate_output is
never executed by pipeline/CLI — as-specified, a design gap for the register), the CSV
magnitude footgun and the 10-sample examples cap (as-specified product-design findings),
a repr(inf) codegen edge, triple validate_ir traversal, and style nits. None of these were
touched by the experiment's ~1,400 sealed tests.

## Conclusion for the design

Review and oracle are DIFFERENT INSTRUMENTS for disjoint defect classes. Static review —
any tier, spec in hand or not — shares the implementers' misreadings (it false-verifies
them); executable test authorship from the spec is the only measured catcher of the
spec-trap class. Review is a cheap widener for parity/robustness/design-gap classes
(~$1/task at whole-chain scale). The pipeline needs BOTH: per-task review+fix, plus the
independently TEST-AUTHORED end oracle. "Implement + review" alone would have shipped
both spec-traps.

## CORRECTION (2026-07-17) — see ../CORRECTIONS.md

Cell 2's "verbatim-correct" on the pipeline confirm shape was a TRUE verification: all
three arms extract the version string correctly; the nested expectation belonged to the
slice-2 test itself, and the original PROBE verdict mis-attributed it. Cell 2's real miss
is unchanged (the registry-seam). The complementary-instruments conclusion stands, now
with review credited one true-verification the oracle got wrong.
