# Anonymous output-level reproduction

Requires Python 3.9 or newer; standard library only. No installation, network, GPU, model weights or API keys are needed.

From this directory run:

```sh
python3 R2_ANONYMOUS_REPRO/reproduce.py
python3 NATURAL_QA/reproduce.py
```

Both commands must print `PASS`. Optional `--out` paths save the recomputed JSON outside the sealed data folders. Expected execution time is seconds to tens of seconds on a laptop.

`R2_ANONYMOUS_REPRO` is the unchanged original anonymous 48-topic package. Its original manifest checks 18 protected files; it reproduces exported prediction metrics, the fixed 10,000-replicate stratified paired bootstrap (seed 20261022), exact discordant-pair tests, existing fidelity review merges, and recorded resource summaries. Existing review labels are retained; no new annotation or inference is performed.

`NATURAL_QA` contains exactly 100 common public test inputs, reduced final gold, and 400 original output strings per deployment. StrongSQ choices remain A/B/A/B for Qwen27/Qwen9/Ministral/Gemma. Public inputs preserve the original seven fields and bytes. Gold retains only id, support_gold, answer_type and relevance_gold. Raw exports retain only id, method, raw_text, finish_reason, status and the SHA-256 of the corresponding original raw record. Output strings and failure status are unchanged.

Natural-QA replay copies the frozen contract and statistical core byte for byte and the original score_view function verbatim. It recomputes strict and LPC3 views of identical outputs, derives H_SQ within each view, retains all 100 items in every endpoint denominator, and reproduces paired counts, exact tests and 10,000-replicate source-group bootstrap intervals (seed 20261026). Every released aggregate is asserted equal to the accepted four-deployment report. Shared source groups and scoring views are not independent replication samples. Prompt selection is not repeated.

This release reproduces statistics from exported outputs. It does not rerun models, establish GPU execution authenticity, replay native runtime/hardware validation, independently re-review source truth, or reproduce all historical R1 and revision-control studies. The minimized raw records support parser replay; their source hashes document lineage but cannot alone authenticate omitted private runtime records.

Reviewer identities, review timestamps/notes, private machine paths and GPU identifiers are excluded. Factual named entities, public source URLs, original generated reasoning and corpus copyright attribution remain part of the source data. No new license over third-party source passages is asserted.

The natural-QA cohort comes from the official RAGTruth repository, commit `c103204b9ce28d6bbad859304bf30de72b8ed8fe`, at https://github.com/CodingLLM/RAGTruth . The original MIT license is retained as `NATURAL_QA/RAGTRUTH_LICENSE.txt`. Original questions, generated answers and evidence excerpts are preserved. Source hashes and release manifests permit byte checks without disclosing private source paths.
