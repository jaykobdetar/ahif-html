# Extractor 0.2.0 — deterministic repairs and discovery revision

## Scope and versions

This records the local repair checkpoint on uploaded baseline
`70e3a07cc7bfaf0e42f93cd99cd2c40f73d2177a`. Publication was not authorized at that checkpoint. The owner subsequently
authorized repository updates; see the [publication evidence](../provenance/evaluation-20260916/README.md). The downloaded baseline archive was compared with all 100
tracked Git files; all bytes matched. Old execution receipts remain unchanged.

- Extractor software: **0.2.0**.
- Deterministic evidence gates: **1.1.0**, bound by version/hash in observation
  provenance and the interpretation sidecar (**1.1.0**).
- Discovery/candidate accounting and new runtime prompts: **1.1.0**. Prompt 1.0.0
  remains preserved verbatim.
- Existing source-linked plan syntax, parser/index contract and text profile stay
  **1.0.0**. A syntactically valid old plan still faces the repaired gates when
  executed by 0.2.0. There is no legacy bypass for invalid selections.
- AHIF **0.1.1**, AHAS **1.0.4**, all existing bridge profiles and third-party
  dependency pins remain unchanged. The lock changes only this project's version.

New accepted observations differ from baseline observations because software and
gate identities are explicit. Compare canonical replay within the same version.
Use baseline code to replay old receipts; a fresh baseline replay verified all eight
original canonical files. The current executor must not reinterpret a historical
receipt as though it had originally passed the repaired gates.

## Reconstruction and environment

The independent review, probes and eight original failing assertions were lost.
The owner instructed this implementation to proceed without them. New tests are
**reconstructed from the three findings in the owner's message**, not the lost
reviewer's files. Parametrized assertions cover the three contracts; they are not
presented as dozens of independent findings.

The supported environment is locked **Python 3.12.3 / html5lib 1.1**. The unchanged
baseline passed its existing 121 tests here. All three reported behaviors were
then reproduced in this environment, so their reproduction does not depend on
the reviewer's unsupported Python 3.13.5 environment. That reviewer's exact
environment and missing test files were not recreated.

## Deterministic repairs

### HTML-REV-001 — effective role follows selected source ancestors

Every retained text range selected as body/title is checked through its full
ancestor chain, including ancestors above the contribution container. Moving the
container or selecting a descendant element/text node cannot erase quote/code
ownership. Excluded and empty regions contribute no selected ranges. Genuine
quote/code parts and ordered body/quote/body boundaries remain supported.

The same plan gate applies to manual, model, recipe and correction execution.
Checks retain the existing overlapping-range and nested-contribution boundaries.
Grounding is still separate from semantic author association.

One retained fictional probe contains this exact source:

```html
<!doctype html><article id="outer"><header><span id="author">Fictional Delta</span></header><blockquote><span id="selected">Another persons wording.</span></blockquote></article>
```

The baseline accepted the selected span as Fictional Delta's `body` with
`record_actor` attribution and passed full replay. The repaired execution refuses
that same plan with `structural_quote_or_code_ancestor_forbids_body_title`.
The raw capture, concrete node references and both executions are retained in the
`quote_known_actor` paired-probe directories. A separate positive probe retains
the actual quote role and body/quote/body sequence successfully.

### HTML-REV-002 — positive evidence for textless actions

An annotation object/list is not evidence by itself. A candidate needs substantive
retained text, a nonblank resolved native/URI event identity, a grounded resolved
relationship, or a narrowly supported captured state marker. Empty identifiers,
empty hrefs, unknown relationships, whitespace alone and unsupported state
assertions do not create events. Empty hrefs do not become the page URL.

Supported textless state evidence is an exact `data-state` value or an explicitly
referenced direct text marker such as `[deleted]`, with contribution ownership,
quote/code ancestry and exclusions respected. This records a captured assertion;
it does not verify the source's claim. Omitted candidates keep their attempted
plan and `no_actual_contribution_evidence` decision for review. Independent usable
records remain extractable.

### HTML-REV-003 — bound all accepted inspection files

The baseline published **22,275 bytes** for a 100-byte `inspect` allowance and
returned success. The repaired atomic publisher counts every file before rename.
An exact allowance succeeds; one byte below fails with `output_total_byte_limit`,
and no accepted index is published. `inspect`, standalone review, correction
wrappers, discovery and evaluation now count their outer sidecars too. Existing
extraction and batch checks already counted their accepted output sets.

A failed CLI attempt may publish only a diagnostic receipt under a separate
**4,096-byte** ceiling. This never increases the accepted artifact allowance.
This is a publication-size guarantee, not a new filesystem sandbox or a promise
that temporary computation/disk allocation cannot exceed the final allowance.

## Evidence locations and current status

Local receipts and source snippets are preserved under `qa/revisions/html-rev-001-002/`
and `qa/repair-20260916/`. They include serialized plans, actual output, stable error
codes, and separate AHIF/source-map checks where extraction is accepted. The new
discovery corpus, fixed matching policy and reference inventory are in
`examples/discovery-v2/`. The executed outcomes below keep mechanical checks,
manual construction evaluation and actual live discovery separate.

## Executed mechanical evidence

| Boundary | Frozen baseline | Repaired execution |
|---|---|---|
| Reconstructed quote/code and textless-event regressions | 59 failed, 8 passed | 67 passed |
| Twelve serialized fictional probes | 2 met the intended invariants | 12 met the intended invariants |
| Original small-cap inspection | Exit 0; 22,275 accepted bytes under a 100-byte allowance | Exit 2; `resource_limit`; bounded failure receipt only |
| Inspection exact/over-limit regression subset | 2 failed, 1 passed | Passing within the seven publication-limit tests |
| Full suite at delivery checkpoint 01 | Historical baseline: 121 passed | 221 passed, no failed/skipped tests |
| Model-free delivery checkpoint 01 | Separate historical replay passed | All 13 CLI checks passed, plus pytest |
| Final mechanical checkpoint 02, including runner failure accounting | Not part of the old baseline | 231 tests passed; all 13 CLI checks passed, plus pytest |

The 59 failures cover parametrized assertions for two findings, including the
versioned gate binding; they do not imply 59 independent defects. Full paired
commands, source selections, snippets, exact output and stable refusal codes are
under `qa/revisions/html-rev-001-002/final-paired-stable-order/`. Refused malicious
plans have no accepted AHIF bundle; their AHIF/source-map checks are correctly
`not_run`, not claimed as passes. Accepted positives and no-evidence omission
bundles passed the separate AHIF and extraction-source-map boundaries.

`qa/repair-20260916/delivery-01/` and the final
`qa/repair-20260916/delivery-02/` record the real commands and exit codes for
inspection, extraction, verification, recipe success/mismatch, a source-selecting
correction, safe review, evaluation and batch execution. The replay changed process,
working directory, capture path/mtime, elapsed clock, `PYTHONHASHSEED`, timezone and
JSON property order. All eight canonical files remained byte-identical, with no
inference. The canonical set hash was
`e522a3deb2dc63ad4f535d755be873f1a8ffde1d085697a3e13a31f26ea30d51`.

Reproduce with new output directories:

```sh
uv sync --frozen --python python3.12
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q tests/test_revision_semantic_gates.py tests/test_output_publication_limits.py
.venv/bin/python scripts/verify_delivery.py --out local-runs/repair-delivery
```

For a failing-before comparison, place baseline commit
`70e3a07cc7bfaf0e42f93cd99cd2c40f73d2177a` in a separate checkout and set
`PYTHONPATH` to that checkout's `src` while running the current reconstructed test
file. The retained paired receipt records the actual separate checkout and
environment used here. The uploaded archive and existing working trees were not
reset or overwritten.

Checkpoint 02 used Python 3.12.3, html5lib 1.1, jsonschema 4.26.0, referencing
0.37.0 and pytest 9.0.2. The full suite took 10.28 seconds; the complete delivery
harness took 14.67 seconds. Its 14 recorded commands comprise pytest and 13 CLI
checks (the earlier progress count incorrectly called all 14 CLI checks).

## Preserved references and history

`qa/repair-20260916/preservation-after.json` passed against the initial inventory:

- All **1,106 historical evidence files** retained their exact bytes.
- All **4,756 tracked files** across the current AHIF/AHAS checkouts and the two
  reviewed reference checkouts retained their bytes; all four Git revisions match.
- **53 protected extractor files** match the uploaded baseline, including vendored
  AHIF, original schemas/prompts, parser/index code, original fictional fixtures,
  recipe fixtures and reference documentation.
- The uploaded archive hash remains
  `892e8f35ea4ea7468738f6fb139174f7b1c4b6b8cb51a1ded1f213e39ae97226`.
- At the repair checkpoint extractor HEAD remained the uploaded baseline commit. That execution made no commit,
  push, release, pull request or publication.

The original AHIF reviewed revision remains
`7629dbe63521978f0b99319a373dfea42b8e6b81`; the original AHAS reviewed revision remains
`070213f0520d01529556e4aa7f4fa9270c22c6aa`. Preservation does not authenticate source
authorship; it establishes which file bytes were retained.

## New live discovery evaluation

See [the full results](DISCOVERY-V2-RESULTS.md),
[transcript-based failure analysis](DISCOVERY-V2-FAILURE-ANALYSIS.md), and
`qa/discovery-v2-model-01/trial-report.json`. This was real inference using pinned
Ollama 0.34.1 and `qwen3:32b-q4_K_M` on one authorized Runpod A40. It used eight
fictional pages across four layout families, with agent-authored construction
annotations prepared separately from model proposals. It is not independent human
annotation or a real-website benchmark.

All 18 registered jobs ran: eight pages in each arm plus two fixed repeats. No
failed page disappeared from the denominator. There was no source/prompt/config
tuning during scoring, no budget stop and no integrity failure. Both arms had the
same per-job allowance of 12 calls and 300 seconds, under shared ceilings of 216
calls and 2,100 seconds. Source/corpus freeze:
`6634acc19a20c1ca520762b760593f76217ecd61f15f80236fbaf7574ee1b52c`.
Registration hash:
`3a254c1a32f16fe7da0bd527d51354d8f958d5d77faebd8295b5b5bc4df47cdb`.

| Primary-arm outcome | Planner only | Planner plus reviewer |
|---|---:|---:|
| Contributions found / reference inventory | 13 / 26 | 0 / 26 |
| Exact-container matched / emitted | 13 / 13 | 0 / 0; precision undefined |
| Correct known account-header assignments / known references | 11 / 20 | 0 / 20 |
| Correct unknown assignments / unknown references | 2 / 6 | 0 / 6 |
| Fully correct ordered parts and attribution / all references | 2 / 26 | 0 / 26 |
| End-to-end usable known-account contributions / known references | 0 / 20 | 0 / 20 |

The eleven correct account keys are a useful field-level demonstration, but none
of those known-account records had fully correct ordered parts and attribution.
The two fully correct records had unknown authors. The reviewer did not produce
an accepted reviewed extraction; this run demonstrates added abstention/cost,
not a semantic-review improvement. Successful schema, source-map and replay
checks do not rescue semantic errors or missing contributions.

Five primary planner outputs and one fixed-repeat output were accepted. All six
passed independent model-free verification. The first cards repeat became
unresolved after its primary attempt had emitted a partial result; the table
repeat again found 3/3 with 1/3 fully correct parts. Neither repeat replaced an
earlier outcome or counted as a new page. Exact-container matching limitations
and the matched-record scope of contamination checks are disclosed in the results.

The run made **136 model calls**, with returned usage of **652,785 input tokens**
and **13,991 output tokens**, over **1,036.48 seconds** of inference orchestration.
A separate readiness call used 36 input / 10 output tokens and no scored page.
The actual fictional requests, actions, plans, mappings and failures are retained;
`qa/discovery-v2-model-01-safe/` copies 260 allowlisted artifacts verbatim. Provider
configuration, resource/control identifiers, operational logs and machine paths
remain outside that export. That export was local at execution time; selected fictional copies are now published.

The paid pod was deleted immediately after inference, and both the evaluator and
root independently confirmed its absence. Timer/service and tunnel cleanup are
recorded. The combined quoted rate was **$0.498333/hour**; rate times the measured
23m47.956s resource duration estimates **$0.197666** for this run. Provider billing
returned no records, so the actual invoice amount remains **unknown**, not zero.
No persistent or network volume was created. The lifecycle receipt is
`qa/runpod-discovery-v2-01/cleanup-receipt.json`; the root's independent empty-list
check is `qa/repair-20260916/independent-runpod-deletion-check.json`.

## Acceptance and remaining limits

- **Implemented and demonstrated:** all three deterministic repairs, bounded
  candidate accounting, contextual inspection, reference-error feedback, the
  stricter reviewer gate, safe review/correction, recipe success/mismatch and
  model-free replay. A demonstrated refusal is not a successful model review.
- **Evaluated:** 26/26 manual-plan construction cases with exact expected parts and
  attribution (`qa/discovery-v2-construction-02/evaluation.json`), plus the live
  paired trial above. The manual-plan result evaluates the executor, not discovery.
- **Failed/unresolved live outcomes:** retained in the trial report, including
  missed contributions, incomplete/wrong part interpretations, invalid tool
  arguments, incompatible exclusions, review gating and call exhaustion.
- **Not run/unavailable:** the lost original review files, that reviewer's Python
  3.13.5 environment, authorized real captures with human annotations, a generic
  HTML-to-AHAS projection and production hostile-ingestion certification.

The next work follows the observed failures in the linked analysis. Improvements
informed by this trial require a new version/designation and another frozen
evaluation; these results must not be silently rewritten.

## Published repair evidence

The [paired fictional probes](../provenance/evaluation-20260916/repairs/paired/)
retain raw captures, concrete selections, exact output and refusal codes.
[Inspection before](../provenance/evaluation-20260916/repairs/inspection-before/)
and [after](../provenance/evaluation-20260916/repairs/inspection-after/) retain the
output-cap checks. Machine paths in command receipts are explicitly redacted
publication derivatives; canonical extraction files are verbatim copies.
