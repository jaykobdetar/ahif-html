# Evaluation contract 1.0.0

The `evaluate` CLI is a **fictional construction-truth evaluation of finalized
manual extraction plans**. It measures the common executor and evaluator without
model calls. A separately registered live remote-model trial is reported below.
Neither is a real-layout pilot or independent human annotation. The model worker
never receives the gold inventory; the parent scorer reads construction truth only
after every inference job finishes.

## Inventory, registration and split

`examples/fictional/dataset.json` (`fictional-construction-v2`) registers five captures and four layout families:

| Family | Pages | Reference appearances | Split |
|---|---:|---:|---|
| Forum thread | 2 | 4 | development |
| Review cards | 1 | 2 | development |
| Micro feed | 1 | 5 | development |
| Article comments | 1 | 2 | held_out |

The two forum captures are one thread and capture lineage, including a harmless
wrapper/header/sidebar variation. Both remain in one split. The held-out family is
a reserved synthetic fixture family; its labels were constructed by the implementation
agent and are not evidence of unfamiliar live-model generalization.

The first fixture draft used an underspecified native parent attribute. Before the
retained evaluation registration, v2 made fictional post/comment/review identity
collections and parent/quote/repost target collections explicit. The initial test
executions were temporary development checks; no retained evaluation result was
overwritten.

The examples-only `build_fixtures.py` resolves explicit construction selectors to
capture-bound node references. All expected wording, roles, actors, event IDs,
dates, and prohibited body fragments are independently written constants in that
file. It never calls the production executor to manufacture expected text. It is
not used by discovery. Ordinary runs use the already finalized plans and gold files.

Before any extraction, `evaluate` validates paths, annotation provenance and hashes,
rejects family/thread/lineage/exact-capture leakage across splits, and writes
`registration.json` with the complete input hashes, split, configuration and matching
rule. These are frozen inputs for that execution. Changes to construction truth or
fixes motivated by failures require a new evaluation designation for comparative
performance claims; old receipts remain historical.

## Executable commands

From the project root, using its isolated Python 3.12 environment:

```sh
.venv/bin/python -m ahif_html.cli evaluate --dataset examples/fictional/dataset.json --config examples/fictional/evaluation-config.json --out /tmp/ahif-html-evaluation-unique
.venv/bin/python -m pytest tests/test_evaluation.py -q
```

Destinations must be fresh. There is no network/model requirement. The configured
shared limits cover page count, cumulative input/output bytes and elapsed time. A Unix
real-time alarm interrupts in-progress extraction/reverification at the remaining
shared deadline. Evaluation therefore runs on the main thread. A nested enclosing worker timer
uses the smaller remaining allowance and is restored after subtracting elapsed
time; the prior signal handler is restored. The CLI worker’s 60-second cap can be
stricter than the configured batch allowance. Exhaustion stops further extraction,
while the evaluator records unexecuted pages in the reference denominators.
Individual extraction additionally enforces the standard worker limits. Elapsed
measurements and process RSS are operational data, outside canonical extraction
identity. The process RSS is an explicitly labeled high-water mark, not invented
per-page incremental usage.

## Metrics and denominators

- **Contribution precision/recall:** fixed one-to-one equality of immutable
  capture-bound contribution-container references. Gold includes every constructed
  contribution, not only candidates proposed by a plan. Additional observations at
  a matched container count as unmatched emissions. Zero emitted records has null
  precision with `no_emitted_contributions`, never a useful 100% score.
- **Attribution:** correct known account assignments, wrong known assignments,
  abstentions where a reference account is known, correct unknown attribution,
  unsupported known assignments to unknown reference authors, and missed records
  are separate counts. Source-grounded presence of a name alone cannot make its
  assignment semantically correct.
- **End-to-end usable recall:** reference contributions matched with both correct
  attribution (including correctly preserved unknown attribution) and exact ordered
  parts, roles and part-attribution relations. Its denominator includes missed
  reference contributions. This is evidence utility, not account-specific analysis
  eligibility.
- **Body/title fidelity:** exact ordered per-role text lists, counts of records with
  reference or emitted text for that role, and missing/extra/transformed Unicode
  code points. Deterministic `SequenceMatcher` character alignment is an engineering
  diff metric, not a raw-byte or visual-layout fidelity claim. Empty/empty text does
  not inflate these text denominators. Part order/roles/attribution are additionally
  checked as a whole, so false joins cannot hide behind identical concatenated text.
- **Quote/signature/interface contamination:** exact construction-truth forbidden
  fragments found inside emitted body parts, with occurrences, affected records,
  and number of annotated forbidden fragments. This is bounded fixture annotation,
  not a universal quotation detector.
- **Metadata:** separate correct/error/abstention counts for identity, kind, creation
  time with precision, edit time with precision, relations and context. An expected
  source-local key tests that identity remains source-local; it does not prescribe a
  fabricated native ID. Context is deliberately unknown/empty in these fixtures.
- **Grounding and replay:** actual full capture+plan re-execution through the common
  verifier. A valid source map is not semantic correctness. This evaluator's replay
  runs in the same process; separate QA covers fresh-process, relocated, hash-seed
  and offline replay claims.
- **Coverage/cost:** page failures, partial statuses, unresolved regions, zero manual
  execution provider calls, observed elapsed time and process high-water RSS.
  Monetary cost and unavailable token usage remain null. Indicators are not an
  account-completeness percentage.

Each page and layout retains raw numerators/denominators and outcomes. No composite
score combines mechanical validity, semantic agreement and replay. Tests explicitly
show a grounded but deliberately wrong author passing extraction verification while
failing attribution and usable-recall metrics. Other tests ensure missed records,
contamination, duplicated matches, leakage and empty outputs cannot earn false credit.

## Missing real evaluation

No approved real saved-capture corpus or independent human annotation inventory
was supplied. The approximately-20-page real pilot remains **not_run**. The manual
CLI report also marks its model arms not run because that configuration makes no
inference calls. The separate registered synthetic trial below did execute the
planner/reviewer comparison and a fresh repeat. Those executions do not fill the
missing real-capture or human-annotation requirements. Mock/recorded provider
checks remain separate and are never counted as live model evaluation.

## Retained execution evidence

The `qa/` paths below name local historical receipts and are excluded from this
repository. The published [initial-delivery summary](../provenance/initial-delivery/README.md)
provides selected safe outcomes and source-receipt hashes. Full model transcripts,
operational logs and host paths remain local; readers can run the shipped fictional
examples to create their own fresh receipts.

`qa/fictional-evaluation-03/evaluation.json` records the current retained evaluation:
13/13 appearances found with exact ordered text/roles/attribution, including 8 known
account assignments and 5 correctly unknown authors; body fidelity is 12/12 and
title fidelity 1/1. Three pages remain `partial_execution` because of observed
incomplete-capture indicators. Five micro-feed appearances represent four logical
events. These favorable fixture results are expected for hand-authored plans and
are not an estimate of model accuracy. Unknown expected metadata is counted as
correctly preserved uncertainty, not as newly established facts.

`qa/evaluation-tests-03` retains the actual command, environment, code hashes,
exit code and 16-test log. The current evaluation used the actual CLI under its
Linux seccomp/worker limits. Earlier `*-01` and `*-02` executions remain historical;
the third execution verifies nested shared/enclosing deadlines and the CLI path. `dataset.schema.json` validates the inventory and embeds
the annotation contract; `evaluation.schema.json` validates configuration;
`evaluation-result.schema.json` describes result structure. Result-schema validation
is an additional shape check, not a substitute for metrics or replay.

## Live remote-model trial: actual partial and failed outcomes

`qa/remote-trial-01/registration.json` was written before inference, with capture,
annotation, runtime-prompt and implementation hashes, all five jobs, family splits,
and per-arm/shared budgets. `trial-report.json` scores every reference contribution,
including page failures as empty output. Construction truth is implementation-agent
annotation, not independent human review. The reserved comments family was held out
from the trial's development jobs; fixture authors still knew its constructed content.
No model or code tuning followed scored outcomes in this designation.

The actual provider was Ollama 0.34.1 serving `qwen3:32b-q4_K_M` on a Runpod A40
through a loopback SSH tunnel. The trial used explicit schema output, no provider
fallback, 16,384-token context, and 4,096 output tokens per call. Its shared ceilings
were 40 provider calls and 1,200 seconds. It consumed 18 calls, 19 evidence-tool calls,
46,585 inspected characters, 35,432 reported input tokens and 934 output tokens in
72.032 seconds. A separate service-health call used 36 input and 10 output tokens:
19 actual calls across readiness plus trial, with those purposes kept distinct.

| Registered job | Outcome | Found/reference | Usable/reference | Calls |
|---|---|---:|---:|---:|
| Reviews development | Accepted; missed the second review; emitted record has a kind error | 1/2 | 1/2 | 4 |
| Forum development | Failed: `unknown_node_reference` | 0/2 | 0/2 | 3 |
| Comments planner | Partial; missed the second comment | 1/2 | 1/2 | 3 |
| Comments planner + reviewer | Unresolved: `reviewer_independent_inspection_missing` | 0/2 | 0/2 | 4 |
| Reviews fresh repeat | Same extraction as first review discovery; second review still missed | 1/2 | 1/2 | 4 |

Each emitted contribution matched its registered container and exact ordered text,
and retained correctly unknown attribution. This does **not** demonstrate correct
known-account assignment: the live accepted records exercised unknown authors.
The review kind error remains a separate metadata error; usable recall here measures
text and attribution, as defined above. Failed/empty runs have undefined precision,
not a perfect score. Forum quote/signature handling is demonstrated by manual fixture
execution; this live forum plan failed and does not establish successful discovery
of those boundaries.

On the same two held-out synthetic comments, review decreased usable recall from
1/2 to 0/2 and increased calls from three to four. The reviewer did not satisfy its
independent-inspection requirement; no critical-error reduction was demonstrated.
The repeated reviews discovery happened to match the first accepted result. A
single repeat is a retained variation observation, not a determinism guarantee.
All attempts remain available, including both failed jobs; none was replaced by a
better attempt. Three accepted runs were handed to the ordinary executor, with
separate offline extraction/replay checks under `offline-verification/`.

The paid resource was deleted after the trial and independently confirmed absent.
Its rate/time estimate is about US$0.09936 for the entire provisioning/readiness/trial
period; actual billing reconciliation remains unavailable. Deployment, model digest,
cleanup and billing-read evidence remain local under `qa/runpod-pilot-01/` and
in the excluded detailed deployment record. The public [Runpod summary](RUNPOD-SUMMARY.md)
retains the aggregate outcome without resource or access identifiers.
No model agreement, source-map validity or small synthetic sample establishes general
semantic reliability. The useful observed next targets are missed contributions,
plan-reference errors, and the reviewer inspection protocol.
