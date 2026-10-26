R2 anonymous CPU recomputation package — 2026-10-25

Requires Python 3.9 or newer; standard library only. No installation, network, model weights, GPU or API key.

Unzip, open a terminal in R2_ANONYMOUS_REPRO, and run:
    python3 reproduce.py
Optional saved output outside the sealed folder:
    python3 reproduce.py --out ../R2_recomputed.json

A successful run prints PASS and the primary comparison, review counts and qualified costs. It checks hashes, the exact 48-topic/4608-cell/768-normalization coverage, frozen input gold, question/answer-card mappings, A/B/D merge, all four model scores, 10000-draw stratified paired bootstrap intervals, exact discordant-pair tests, process gates and physical allocation sums. About a few seconds on a laptop. No new judgments are generated.

Interpretation:
- Only Qwen-27B H_SQ minus SQ is the prespecified confirmatory comparison. Replica and process results are descriptive.
- C process scoring requires a faithful normalization and correct final label; H_C gates only its actual C branch. Failed/unresolved outputs remain in planned denominators.
- Nine-card scope stress is hypothetical and selected. Actual human labels are retained; it is neither a new human review nor an exhaustive uncertainty interval.
- 15.3731 card-hours are supervisor allocations. About 15.42 adds reported/estimated overhead, before other unquantified transitions; it is not an exact all-inclusive bill.
- The immutable protocol is the historical pre-execution plan. Its planning-phase status fields are deliberately not rewritten.
- These materials reproduce R2 from exported records. The raw execution archive and earlier R1/revision studies remain in the author evidence archive; this package does not independently authenticate hardware execution.
- Source excerpts retain their original provenance. No new license over third-party source text is asserted.

The manuscript PDF is submitted separately as one file. This local ZIP is a prepared companion artifact; use only a venue-permitted anonymous sharing mechanism after the responsible author's review.
