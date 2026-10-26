# Replay validation and dedup-refit summary (2026-10-25)

## Validation gate

The estimator re-implementation in `dedup_replay.py` (weights `w = S·r − 1`,
unique-plurality first update with all-rows fallback, zero-observation
reliability 0, first-encounter ties, top-four and all-source readouts, frozen
alias EM) reproduces **all 36 frozen cells exactly**: R0 EM, all-source
expected EM, iteration count, first-update row count, and fallback flag all
match `../evidence/learned/summary_36.json` (zero mismatches).

## Exact-dedup refit (A_exact, four byte-identical copies collapsed to one; panel 47 → 44)

R0 EM on the 34-event test set:

| model | cal | method | clean | attacked (frozen) | **dedup refit** | R2 (dedup) |
|---|---|---|---|---|---|---|
| qwen35 | 13 | SourceFit | 0.9412 | 0.0000 | **0.9412** | 0.9412 |
| qwen35 | 26 | SourceFit | 0.9412 | 0.0000 | **0.9412** | 0.9412 |
| ministral3 | 13 | SourceFit | 0.9118 | 0.0000 | **0.8235** | 0.8235 |
| ministral3 | 26 | SourceFit | 0.9118 | 0.0000 | **0.8529** | 0.8529 |
| gemma3_4b | 13 | SourceFit | 0.6176 | 0.0000 | **0.5588** | 0.5441 |
| gemma3_4b | 26 | SourceFit | 0.6471 | 0.0000 | **0.6471** | 0.6176 |
| qwen35 | 13 | F1S1 | 0.7941 | 0.0000 | **0.6765** | 0.6765 |
| qwen35 | 26 | F1S1 | 0.7941 | 0.0000 | **0.6765** | 0.6765 |
| ministral3 | 13 | F1S1 | 0.7353 | 0.0000 | **0.6176** | 0.6176 |
| ministral3 | 26 | F1S1 | 0.7353 | 0.0000 | **0.6471** | 0.6471 |
| gemma3_4b | 13 | F1S1 | 0.4706 | 0.0000 | **0.3824** | 0.3824 |
| gemma3_4b | 26 | F1S1 | 0.4706 | 0.0000 | **0.4118** | 0.4118 |

Reading: collapsing the copies to one slot removes the learned collapse —
SourceFit returns to 90–100% of its clean score (100% for qwen35 at both
sizes) and the joint-module variant to 81–88%. After dedup the single copy's
terminal weight is −1 (zero-coverage) for qwen35 and only +2.4 to +21 for the
other fits, versus the near-unanimous r = 1.00 that all four copies receive in
the frozen attacked fits: one wrong voice cannot flip the provisional answers
that drive the estimator, so the damage is vote multiplicity, not content.
Paraphrased repetition, which survives byte-identical deduplication, is the
case the aggregation branch measures.
