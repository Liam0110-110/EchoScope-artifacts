# EchoScope Evaluation Artifacts (anonymous)

This package contains the frozen evaluation artifacts for the submission
*Repetition Is Not Corroboration: Diagnosing Source Dependence in RAG Aggregation*
(WWW 2027 research track, anonymous review). It supports every number in the
paper: per-source answer matrices, fitting trajectories, predictions,
independent recomputations, human-label receipts, and self-contained replays
of the frozen fits, the exact-dedup refit, and the stage-normalization control
reported in the paper. No external dependencies are needed beyond Python 3
(standard library only).

## Layout

| Path | Contents | Supports |
|---|---|---|
| `numeric_evidence.json` | Registry mapping paper numbers to evidence files | all tables |
| `evidence/learned/` | Learning branch: 24 fitting trajectories, 1,224 test predictions (both readouts), per-fit summaries, coverage and parity receipts | Table 9, Fig. 3, §6.2 |
| `evidence/fixed/` | Aggregation branch: 2,880 scored model–event–condition–method cells, contrasts, receipts | Table 7, §6.1 |
| `evidence/semantic_intake/` | Human short-answer review: cards, automatic scoring, dual-review receipts, consensus labels | Table 8 (semantic), §6.1 |
| `evidence/original_g7_audit/` | Independent audit of the frozen G7 return | §6 execution claims |
| `quality_gate_result.txt`, `new_table_numeric_checks.json`, `revision_checks.json`, `semantic_replay_check.json`, `c3_independent_receipt.json`, `baseline_numeric_tokens.json`, `g7_material_counts.json` | Gate receipts and numeric cross-checks | manuscript QA |
| `recompute_semantic.py` | Exact recompute of expected semantic accuracy | Table 8 (semantic column) |
| `data/learned_branch_rows.jsonl` | Frozen per-source answer matrices (3 models × 60 events × {N, W_exact}; raw and module-filtered answers; 47 slots for attacked rows) | replay input |
| `data/frozen_partition.json` | Frozen calibration (13 / 26) and test (34) event split | replay input |
| `data/g7_aliases.jsonl` | Frozen gold aliases and designated wrong entity per event | replay scoring |
| `replay/dedup_replay.py` | Self-contained replay (see below) | §6.2 dedup |
| `replay/dedup_replay_results.json`, `replay/dedup_replay_run.json` | Recorded replay outputs | §6.2 |
| `replay/VALIDATION.md` | Validation-gate and dedup-replay summary | §6.2 |
| `supplement/figure_data/supplement_summaries.jsonl` | Per-run summaries of the supplementary refits: E1 (wrong-paraphrase learning refits), E2 (fitting/vote stage-normalization 2×2), E4 (all-subset copy-count replay) | §6.2 and Table 15 |
| `supplement/confirmed_evidence.json` | Frozen evidence registry for the supplement: E2 stage means, E3 answer-pooling table, resolved human effects, E4 dose curves | §5.4, §6.2, Table 15 |
| `supplement/{verification,build_summary,evidence_source_hashes}.json` | Build verification chain for the supplement package | manuscript QA |
| `supplement/figure_data/{figure3_values,g7_human_effects}.json` | Frozen values behind Figure 3 panels | Fig. 3 |
| `supplement/gpu_aux/ELB_SUPPLEMENT_GPU_RETURN.zip` | Auxiliary-inference return backing the supplement: 187 support checks and 1,610 directional NLI pairs (sha256 355c8dd5...) | §6.2 supplement |
| `SHA256MANIFEST.json` | Hashes of all files in this package | integrity |

## Re-running the fits

```
cd replay
python dedup_replay.py
```

The script first refits all 36 frozen cells (SourceFit / F1S1 / GroupVote ×
{N, W_exact} × calibration size {13, 26} × 3 models) from the frozen answer
matrices and requires exact agreement with `evidence/learned/summary_36.json`
(R0 and all-source expected EM, iteration counts, first-update row counts;
exit code is nonzero on any mismatch). It then collapses the four
byte-identical copy slots into one slot (panel 47 → 44) in calibration and
test matrices, refits SourceFit and F1S1, and reports R0 / R2 EM next to the
frozen clean and attacked baselines. A typical run takes under a minute on a
laptop.

## Notes for reviewers

- The two formerly disputed human short-answer judgments are resolved by
  third-reviewer adjudication (both correct); the frozen label-assignment
  ranges are retained in `evidence/semantic_intake/` for auditability.
- Some reviewer-local filesystem paths in receipts were redacted
  (`[redacted]`) before packaging; no other content was altered.
  `SHA256MANIFEST.json` hashes the packaged (redacted) files.
