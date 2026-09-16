# Adoption report — ahif-html prototype 0.1.0

## Outcome

A working source-linked extraction library/CLI now produces validated **AHIF 0.1.1**
from saved HTML. Manual plans, model proposals, recipes and corrections share one
executor. Source wording is retrieved from immutable evidence references; models
cannot supply final post text. AHIF/AHAS/the Reddit bridge and old studies remain
unchanged. The initial build was delivered locally without publication. The owner
subsequently authorized publication of this separate extractor repository; see
[the publication note](PUBLICATION.md). No license grant is inferred from that
publication request.

This is a usable engineering prototype with limited model discovery quality. It
is not ready to make unattended claims about full account histories.

## Actual evidence and acceptance distinctions

This report describes the retained initial executions. Their full `qa/` receipts
remain local and are excluded from Git. A deliberately selected, sanitized
[initial-delivery summary](../provenance/initial-delivery/README.md) is published
with the code; it identifies original evidence hashes and limitations. Publication
preparation does not turn an earlier result into a new test execution.

| Milestone | Status and retained evidence |
|---|---|
| M0 boundary/contracts | **Implemented and demonstrated.** Exact pinned AHIF schemas/checker vendored; reference hashes, strict sidecar contracts, isolated Python 3.12 environment and locked dependencies recorded. |
| M1 deterministic extraction | **Implemented, demonstrated and evaluated.** Five fictional pages/four layouts/13 reference appearances: 13/13 exact ordered parts and correct known-or-unknown attribution using hand-authored plans. Full AHIF validation and source-map replay pass. |
| M2 model discovery | **Implemented and demonstrated on synthetic inputs.** A live 32B model on Runpod produced three accepted runs over two distinct layouts, including a repeated discovery. All accepted plans use the same executor. Two other registered runs failed and remain in the results. |
| M3 review/repair/correction/recipes | **Implemented and tested.** Same-executor correction creates new traceable output; recipe transfers to a compatible wrapper variant and rejects a cardinality mismatch. Reviewer and bounded repair pass offline protocol tests. The live reviewer attempt **failed** its independent-evidence requirement; it was not labeled reviewed. |
| M4 evaluation | **Evaluated against agent-authored construction truth.** Manual-plan evaluation and the registered synthetic model trial are retained separately. The real 20-page/four-family evaluation and independent human annotations are **not run/unavailable**. |

The final model-free delivery run passed **121 tests** (zero failed or skipped)
and all **14 command checks**, including the expected exit 2 for a recipe mismatch.
The command/exit-code/source-hash receipt is `qa/delivery-final/delivery-receipt.json`.
This runs the test suite and model-free CLI operations, full pinned
AHIF validation, exact mappings, OS-denied network/exec checks, correction, recipe
transfer/mismatch and replay under relocation, mtime/clock/timezone/hash-seed/JSON
property-order changes. Earlier numbered delivery/evaluation/test receipts remain
historical and are not counted as fresh final runs.

All three accepted live plans also passed full model-free re-execution with OS
network/exec denial, comparing all eight canonical files per run; see
`qa/remote-trial-01/offline-verification/receipt.json`. Final protected-reference
inventory verification found all **155 AHIF and 2,223 AHAS tracked files unchanged**,
at the reviewed commits, with clean checkouts (`qa/reference-preservation-final.json`).

## Live model results — all registered runs

The Runpod A40 ran `qwen3:32b-q4_K_M`, digest
`030ee887880fc378860c2dd35101da424377520441ae4bfe7be6deff8ade7840`,
through Ollama 0.34.1 and a loopback-only SSH tunnel. These are actual inference
calls on fictional captures, not recorded/mock responses or real website evaluation.

| Registered run | Calls | Found / reference | Exact text + correct attribution / reference | Outcome |
|---|---:|---:|---:|---|
| Review layout, development | 4 | 1/2 | 1/2 | Accepted; missed one contribution and mislabeled emitted review as post. |
| Forum layout, development | 3 | 0/2 | 0/2 | Invalid source reference; no accepted bundle. |
| Held-out comments, planner | 3 | 1/2 | 1/2 | Accepted partial page; missed one contribution. |
| Same held-out comments, planner+reviewer | 4 | 0/2 | 0/2 | Required independent reviewer evidence inspection missing; no accepted bundle. |
| Review layout, fresh repeat | 4 | 1/2 | 1/2 | Same measured outcome under equal registered budget; not proof of deterministic rediscovery. |

Across planner runs, **3/8** reference appearances were found and had exact ordered
text plus correct unknown attribution. This denominator includes the repeated
review page; it is not eight unique real posts. All three emitted observations had
unknown actors, so this trial does **not** demonstrate known-account attribution.
There were two event-kind errors. No quote/signature/UI contamination was observed
in the three accepted outputs; many reference contributions were missed, so zero
observed contamination/wrong-account assignments is not a population guarantee.

On the same held-out inventory, the reviewer arm reduced accepted usable recall
from **1/2 to 0/2** and used one extra call. It did not demonstrate an improvement in
critical errors. Empty-output precision is null, not 100%. The full report retains
all field metrics, missing/extra characters, abstentions, per-run costs and failures:
`qa/remote-trial-01/trial-report.json`.

The trial made **18/40** permitted provider calls, with **35,432 input tokens and
934 output tokens reported by the provider**. A separate readiness call reported
36 input and 10 output tokens: **19 actual inference calls** including readiness.
The approximately 72-second model trial used only fictional evidence views. Original registration is preserved;
`supplemental-execution-inventory.json` explicitly labels additional hashes gathered
after trial completion rather than pretending they were preregistered. No held-out
labels were passed to inference. Later usage-accounting fixes were tested offline
and do not rewrite this trial's implementation or outcomes.

The initial workstation Qwen3 4B experiments had nine attempted calls and **no
accepted plan**. Protocol failures, schema-format incompatibility and call exhaustion
are retained in `qa/live-discovery-*` and their accounting audit. They are not
counted as successful live extraction.

## Cost and cleanup

The quoted GPU rate was $0.49/hour; a conservative temporary-disk allowance brought
the combined estimate to **$0.4983/hour**, below the owner's $1/hour cap. Creation
request to independently verified absence was about 11 minutes 58 seconds: estimated
elapsed-rate cost **$0.0994**. Actual billing is unknown, not fabricated from tokens.
The pod was deleted, a fresh Runpod inventory confirmed absence, and its independent
cleanup timer was disabled after deletion. No persistent/network volume was allocated.
The local receipt is `qa/runpod-pilot-01/cleanup.json`; the public
[Runpod summary](RUNPOD-SUMMARY.md) omits resource, timer and access identifiers.

## Minimal incoming normalized evidence

The host needs a supplied HTML byte artifact, a concrete contribution container and
at least one useful source-linked text selection or grounded textless action.
It supplies versioned keys/provenance and AHIF-required explicit unknowns. A URL,
author, original date, language, lifecycle/completeness declaration, title, link,
parent, screenshot or native ID is optional when the source does not reveal it.
A source-local appearance is valid; an all-unknown empty arbitrary container is not
counted as extracted contribution evidence. Raw bytes remain externally retained
by the caller for replay and are bound by actual hash.

## Next work, based on observed limits

1. Improve bounded candidate coverage: the model repeatedly stopped after the first
   useful record. Surface unexamined structural candidates and require explicit
   decisions while preserving partial success; do not advertise this as proof of
   complete discovery.
2. Improve reference/tool protocol handling and semantic kind selection, then use
   a new evaluation designation for any changes informed by these outcomes.
3. Make the reviewer complete actual independent inspection and measure whether it
   reduces errors instead of merely increasing abstention and cost.
4. Obtain explicitly approved saved real captures and independent annotations with
   family/thread/lineage splits. Missing inputs are registered in
   `qa/capture-availability.json`; no live collection was performed to fill the gap.
5. Define a separate narrow AHAS projection with per-field loss/refusal rules and
   tested disjoint-body representation. Unknown English, sample length or volume
   remains an ordinary downstream limitation. No numerical analysis was run here.

Supported/unsupported contracts and fixes are detailed in `CHANGELOG.md`;
identity, text, threat and downstream rules are in the adjacent documentation.
