# Corrections ledger

## 2026-07-17 — the "confirm-nesting defect in all three arms" was a MIS-ATTRIBUTION

**Wrong claim** (arm-N root-cause report, three-arm verdict, PROBE.md, commits 8168bb5 /
9a6b0aa / d144507 / 7a82561): all three arms nest the whole freeze return under
stages.confirm.version, violating T11's pinned shape.

**Truth (direction-proof by reading the code on both sides):** all three arms are
spec-CORRECT — N `pipeline.py:67`, H `pipeline.py:51`, F `pipeline.py:116` all record
`{"version": <extracted hex str>}`. The nested value in the assertion diff was the
slice-2 TEST's own expectation: `test_composition.py:61` constructs
`{"version": confirm_mapping(ir)}`, wrapping the full `{"version", "ir"}` return — the
test author fell into the spec's wrap-vs-extract trap; the implementers did not. The
error chain then extended one link further: the grading analyst (Claude, session of
2026-07-16/17) read the assertEqual diff with the sides swapped and reported the arms
defective. Cell 2 of the review probe, which declared the pipeline "verbatim-correct",
was RIGHT on this point and was wrongly reported as a false verification.

**Corrected tallies:**
- Genuine shared defects across arms: **ONE** — the T2 registry-seam KeyError (crash
  inside each arm's own validate.py on a registry-grown op; direction-unambiguous).
  Three-arm tie stands (1 = 1 = 1); all cost/wall numbers unchanged.
- Slice-2 oracle defects: **+1** (confirm over-wrap joins the e2e record["version"]
  class and the two message over-pins; slice-2 t11/t12 author family: 6 defective tests).
- Review probe: cell 2 true-verified T11; both cells still missed the one real defect
  ("t2 → match spec"); cell findings on TS parity stand (requireInt arbitrated by direct
  execution, direction-safe). The probe's conclusion (review and test-authored oracle are
  complementary; neither alone suffices) survives with the false-verification example
  removed and a true-verification example added.
- The "four independent wrong readings of one sentence" headline is corrected to: ONE of
  five independent readers misread the sentence (the test author), and a sixth reader
  (the analyst) mis-attributed the resulting diff. The sentence remains the root cause of
  both errors — a ~20% single-reading trap at a wrap/extract boundary — but it is not a
  universal trap, and implementation was never wrong.

Everything else in the run records was re-checked for the same argument-order hazard:
the registry-seam (a traceback, not an assertion), the e2e KeyErrors (crash in the suite
helper), the message over-pins (literal-vs-arm-value, direction explicit), the T6
docstring and T7 quoted-key adjudications (message content, not order) — all stand.
