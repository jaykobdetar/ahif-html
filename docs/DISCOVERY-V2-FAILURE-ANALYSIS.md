# Discovery v2: frozen trial failure analysis

This is a post-trial reading of retained evidence, not a new evaluation or a
rescored result. Runtime, corpus, annotations, registration, and receipts were
unchanged. The trial used live Qwen3 32B on eight fictional pages from four layout
families, two arms per page, and two additional fresh-discovery repeats. The
reference inventory is agent-authored construction truth; there are no real-page
or independently human-reviewed accuracy claims.

The authoritative totals are in [trial-report.json](../provenance/evaluation-20260916/qwen/trial-report.json).
The 18 jobs used 136 actual calls, 652,785 input tokens and 13,991 output tokens.
Primary planner jobs used 60 calls; reviewer-arm jobs used 62; repeats used 14.
The reviewer arm includes its own planning, not a review of a shared saved plan.

## What 13/26 and 0/20 mean

The primary planner emitted 13 observations, all matching the exact reference
container under the preregistered one-to-one rule. **None of this trial's misses
was an emitted alternative-container mismatch:** there were zero unmatched
emissions. Nine missed contributions belong to three wholly failed pages; four
more were rejected or left unresolved on accepted partial card pages.

All 11 matched known accounts were correct; two matched anonymous records remained
unknown. Nevertheless, **every emitted part for those 11 known accounts used
`attribution: unknown`**. The references assign their authored body/title parts
`record_actor`. Exact ordered-parts fidelity includes attribution, role, text,
segmentation, and order; therefore none passed known-account usable recall
(**0/20**, with nine known-account contributions also missed entirely).

This does not mean no correct prose was extracted. Seven matched known-account
records have the expected single body and exact wording, with part attribution as
the remaining ordered-parts disagreement. Four other known-account records also
have substantive missing or misassigned content. The two usable records are
anonymous (`table-a-3` and `catalog-a-3`), for which unknown attribution is correct.
They still have wrong record kinds, and the table reply loses its relation:
“usable” here means matched account plus exact ordered parts, not all metadata.
See the [table output](../provenance/evaluation-20260916/qwen/table-a-planner/extraction/bundle/records.jsonl)
and its [reference](../provenance/evaluation-20260916/qwen/evaluator-only/table-a.gold.json).

The matched-only forbidden-fragment checks report zero quote/signature/UI
contamination. That is narrower than “no semantic contamination”: `feed-a` emits
“Reposted” as body and `catalog-a` emits “Reviewer” as title, neither of which is
one of that record's registered forbidden fragments. The fixed score remains
unchanged. Character-difference totals also include missed records and use
SequenceMatcher; they are not a count of model-rewritten source characters.

## Primary planner cases

| Page | Matched/reference | Concrete cause and retained evidence |
|---|---:|---|
| `cards-a` | 1/4 | Selects only the first body before the quote; loses the separate quote and closing body. Marks the actual nested reply unresolved, and rejects two genuine separate posts as `quote`. The injection-like sentence remains ordinary source evidence; its rejection is a semantic miss, not evidence that the host obeyed it. [Final plan](../provenance/evaluation-20260916/qwen/cards-a-planner/finalized-plan.json). |
| `cards-b` | 3/4 | Again keeps only the opening body of the interrupted contribution. Rejects the anonymous post as `quote`. The nested reply's text/account are right, but kind is `post` and its parent relation is absent. [Final plan](../provenance/evaluation-20260916/qwen/cards-b-planner/finalized-plan.json). |
| `feed-a` | 3/3 | Two ordinary bodies are exact. The pure repost is emitted as a `post` whose body is “Reposted”; original quoted text is excluded and no repost relation is retained. This is event/role interpretation failure, not source-string invention. [Final plan](../provenance/evaluation-20260916/qwen/feed-a-planner/finalized-plan.json), [reference](../provenance/evaluation-20260916/qwen/evaluator-only/feed-a.gold.json). |
| `feed-b` | 0/3 | Both proposals emit a quote rooted at `n34` while globally excluding its ancestor `n31`. The shared executor refuses `part_root_globally_excluded`. A second inspection does not repair the contradictory selection. [Attempts](../provenance/evaluation-20260916/qwen/feed-b-planner/attempts.jsonl). |
| `table-a` | 3/3 | All three bodies are exact. Distinct native IDs preserve two genuinely separate identical-wording posts. Both known bodies retain unknown part attribution; the anonymous reply is mislabeled `post` and loses its parent link. Signature exclusion succeeds. [Output](../provenance/evaluation-20260916/qwen/table-a-planner/extraction/bundle/records.jsonl). |
| `table-b` | 0/3 | Three successive `inspect_node` requests include unsupported `limit:10`. The tool exists; its supported arguments are `node_ref`, `depth`, and `max_characters`. The model repeats the invalid argument after receiving that list, exhausting two repairs. This is an argument-contract failure, not an attempted forbidden tool or network operation. [Tools](../provenance/evaluation-20260916/qwen/table-b-planner/tools.jsonl), [feedback](../provenance/evaluation-20260916/qwen/table-b-planner/discovery/call-0002.json). |
| `catalog-a` | 3/3 | The first review's title is the field label “Reviewer”, and its body is the actual title “Useful small tool”; the real body is omitted. Remaining two bodies are exact. All three record kinds become `post` instead of `review`. Candidate accounting is complete despite these semantic errors. [Output](../provenance/evaluation-20260916/qwen/catalog-a-planner/extraction/bundle/records.jsonl), [reference](../provenance/evaluation-20260916/qwen/evaluator-only/catalog-a.gold.json). |
| `catalog-b` | 0/3 | Broad definition-list candidates consume repeated inspection calls. A request for `n41` starting at offset 12 is invalid; the next call restarts that region. Twelve calls are exhausted with no proposal. [Calls](../provenance/evaluation-20260916/qwen/catalog-b-planner/discovery/), [receipt](../provenance/evaluation-20260916/qwen/catalog-b-planner/discovery-receipt.json). |

A further provenance error is visible in `cards-a`: its creation-time source is
`data-post-id`, with raw value `cards-a-1`. The deterministic time parser leaves
time unknown, which agrees with the reference's unknown value; the field-source
interpretation is nevertheless wrong. Correct normalized unknown metadata does
not establish that the chosen raw evidence was appropriate.

## Reviewer failure is a protocol result, not demonstrated semantic benefit

Five reviewer jobs reach `reviewer_observe`: `cards-a`, `cards-b`, `feed-a`,
`table-a`, and `catalog-a`. **Each immediately returns `ready_for_review` without
making any independent inspection call.** Their observations cite inventory
nodes, guessed adjacent refs, or—in the table case—the literal example placeholder
`nTEXT`. The host refuses `reviewer_independent_inspection_missing` before exposing
the candidate plan. No final semantic review or reviewer approval occurred.

Exact examples: [table reviewer call 6](../provenance/evaluation-20260916/qwen/table-a-reviewer/discovery/call-0006.json),
[card reviewer call 8](../provenance/evaluation-20260916/qwen/cards-a-reviewer/discovery/call-0008.json),
and [catalog reviewer observations](../provenance/evaluation-20260916/qwen/catalog-a-reviewer/review-observations.json).
`feed-b`, `table-b`, and `catalog-b` fail in their planning phase for the causes
above; they never reach review. Thus reviewer recall is 0/26 and precision has
an undefined empty denominator. There is no evidence that review reduced wrong
attributions. The failure gate prevented uninspected approval, while the runtime
workflow failed to obtain a useful review.

## Repair feedback and fresh-discovery variation

Candidate-accounting feedback can identify exact missing candidates: the final
`catalog-a` planner call receives ten missing aliases and supplies dispositions,
after which accounting passes. That proves completion of a checklist, not the
correctness of those dispositions. [Repair request](../provenance/evaluation-20260916/qwen/catalog-a-planner/discovery/call-0010.json).

The scope/selection failures expose a narrower diagnostic weakness. The
`cards-a` repeat proposes a nested reply whose relation target reads parent `n7`
outside that reply's container `n20`, although `n20` itself carries the relevant
parent-ID attribute. It repeats the same invalid plan three times. Feedback says
`field_outside_container`, but `details:null` and `reference_errors:[]`: all node
refs exist, so the unknown-reference detector cannot locate the wrong field.
The global quote exclusion failure likewise receives a code without an exact
conflicting field path. [Repeat attempts](../provenance/evaluation-20260916/qwen/cards-a-repeat/attempts.jsonl),
[scope feedback](../provenance/evaluation-20260916/qwen/cards-a-repeat/discovery/call-0008.json),
[exclusion feedback](../provenance/evaluation-20260916/qwen/feed-b-planner/discovery/call-0008.json).

With equal registered budgets, `cards-a` changes from one accepted partial record
to an unaccepted four-contribution proposal in its fresh repeat. `table-a` repeats
all eight canonical accepted files byte-for-byte. Both outcomes are retained;
neither permits selecting only the better attempt or claiming deterministic new
model discovery. Saved-plan replay is a separate property: all six accepted runs
(five primary pages plus the table repeat) passed isolated, model-free replay.

## Prioritized next steps for a new version and evaluation

1. **Make legal actions depend on workflow state.** Give each tool a strict
   argument schema; expose reviewer readiness only after sufficient independent
   evidence is retained. Keep the evidence gate and finite budget. This addresses
   the repeated `limit` error and five immediate uninspected readiness responses
   without claiming an automatic review.
2. **Diagnose known-but-wrong references.** Return the exact failing field path,
   owning container, and conflicting exclusion ancestor. Do not silently substitute
   a source. Add bounded repair tests for the observed scope/exclusion cases.
3. **Require deliberate part attribution and field meaning.** Distinguish a known
   record actor from supported authorship of each body/title part, and clarify when
   unknown remains justified. Do not blanket-promote unknown parts or weaken exact
   scoring. Test metadata labels versus values and creation-time evidence bases.
4. **Account for content within selected events.** Check later body segments,
   separately represented quotes, repost action labels, and title/body field
   pairs; keep allowed exclusions explicit. A contribution-level checklist alone
   permits premature success with omitted text. Use compact candidate groups and
   paged inspection progress to reduce repeated definition-list work within the
   same finite resource envelope.
5. **Freeze again before measuring changes.** These pages are now diagnostic
   development evidence. Retain their original scores; use a separately registered
   evaluation, additional independent annotations when available, and real saved
   pages before making general-purpose or account-analysis readiness claims.

Publication note: links above target selected copies. Each registration has a
`registration-publication.json` manifest identifying its original hash and explicit
operational-field redactions. Historical outcomes and their original hashes are
unchanged. See [publication scope](../provenance/evaluation-20260916/README.md).
