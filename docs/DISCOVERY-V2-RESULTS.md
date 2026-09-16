# Discovery v2: executed synthetic comparison

Executed 2026-09-16 with frozen `ahif-html` 0.2.0 runtime, discovery/gates/prompts 1.1.0, and unchanged AHIF 0.1.1 destination contract.

**Result:** planner-only matched 13/26 reference contributions and correctly assigned 11 known actors, but only 2/26 records matched the complete ordered text-part/attribution inventory. Neither was a known-actor record. The reviewer arm finalized no records. All six accepted bundles, including one repeat, passed full source-map re-execution and AHIF verification. Mechanical integrity passed; semantic discovery remains inadequate for unattended account-history extraction.

## Registration and evidence

- [Registered inventory, split, budgets and hashes](../provenance/evaluation-20260916/qwen/registration.json), SHA-256 `3a254c1a32f16fe7da0bd527d51354d8f958d5d77faebd8295b5b5bc4df47cdb`.
- [Runtime/corpus freeze](../provenance/evaluation-20260916/qwen/runtime-inventory.json): 79 artifacts; canonical inventory SHA-256 `6634acc19a20c1ca520762b760593f76217ecd61f15f80236fbaf7574ee1b52c`.
- [Complete machine-readable outcomes](../provenance/evaluation-20260916/qwen/trial-report.json), including every failure, abstention, per-field count, and repeat.
- [Local fictional evidence export](../provenance/evaluation-20260916/qwen/export-manifest.json): 260 allowlisted artifacts copied verbatim, zero omitted; requests, returned actions, inspected evidence, plans, maps, outputs and original hashes retained. These selected fictional files are now published; the original export was local.
- [Manual-plan positive executions](../provenance/evaluation-20260916/manual-construction-evaluation.json): all 26 reference appearances extracted with exact ordered parts/attribution across eight pages, independently of model discovery.

The reference is an **agent-authored construction inventory**, written before inference independently of model proposals. It is not human-reviewed or real-world ground truth. The corpus has eight fictional multi-contribution pages, four DOM families, 26 reference appearances (20 known actors and six unknowns). Related page variants share family/thread/capture-lineage groups. Cards/feed are development families; table/catalog were reserved synthetic families. Their construction by the implementation agent limits any holdout claim. Old scored fixtures remain development/regression material.

The registered one-to-one match requires the exact contribution-container reference. Plausible wider or narrower selections can therefore be scored as unmatched. No alternative matching rules, labels, prompts, source, or budgets were changed after scoring began. All missing and failed-job contributions remain in the denominator. Metadata is scored separately from the registered usable-text metric: usable means found, correctly attributed, and exact ordered parts (role, text, part attribution, order and boundaries), not that every metadata field is correct.

## Paired primary outcomes

| Measure | Planner only | Planner + reviewer |
|---|---:|---:|
| Matched / emitted (precision) | 13/13 | 0/0: undefined, no emissions |
| Matched / all reference contributions (recall) | 13/26 | 0/26 |
| Exact ordered parts and correct actor / all references | 2/26 | 0/26 |
| Correct known actor / known reference actors | 11/20 | 0/20 |
| Fully usable known-actor records / known references | 0/20 | 0/20 |
| Correct unknown attribution / unknown references | 2/6 | 0/6 |
| Fully usable unknown-actor records / unknown references | 2/6 | 0/6 |
| Missed known / missed unknown references | 9 / 4 | 20 / 6 |
| Wrong-account / unsupported assignments among matched records | 0 / 0 | 0 / 0 |
| Unmatched emissions: assigned / unknown actor | 0 / 0 | 0 / 0 |

A 13/13 container precision value does not establish semantic correctness. Zero wrong-account assignments among 13 matched emissions does not establish a zero population error rate. The reviewer arm had no accepted emissions; its zero contamination/wrong-account counts are not evidence of successful review.

## Per-page outcomes

Counts exclude repeats in this table. `P/R` means planner-only / planner-plus-reviewer. All jobs ran; failed finalization is not an executed empty successful extraction.

| Page | References | Matched P/R | Usable P/R | Calls P/R | Planner outcome | Reviewer outcome |
|---|---:|---:|---:|---:|---|---|
| cards-a | 4 | 1/0 | 0/0 | 7/8 | `partial_execution` | `reviewer_independent_inspection_missing` |
| cards-b | 4 | 3/0 | 0/0 | 7/8 | `partial_execution` | `reviewer_independent_inspection_missing` |
| catalog-a | 3 | 3/0 | 1/0 | 10/8 | `complete_execution` | `reviewer_independent_inspection_missing` |
| catalog-b | 3 | 0/0 | 0/0 | 12/12 | `model_call_limit` | `model_call_limit` |
| feed-a | 3 | 3/0 | 0/0 | 7/8 | `complete_execution` | `reviewer_independent_inspection_missing` |
| feed-b | 3 | 0/0 | 0/0 | 9/9 | `part_root_globally_excluded` | `part_root_globally_excluded` |
| table-a | 3 | 3/0 | 1/0 | 5/6 | `complete_execution` | `reviewer_independent_inspection_missing` |
| table-b | 3 | 0/0 | 0/0 | 3/3 | `tool_not_allowed` | `tool_not_allowed` |

## Per-family outcomes

| Family / split | Reference contributions | Planner matched / usable | Reviewer matched / usable |
|---|---:|---:|---:|
| cards / development | 8 | 4 / 0 | 0 / 0 |
| catalog / reserved synthetic | 6 | 3 / 1 | 0 / 0 |
| feed / development | 6 | 3 / 0 | 0 / 0 |
| table / reserved synthetic | 6 | 3 / 1 | 0 / 0 |

Development-family planner recall was 7/14, with 0/14 usable under the registered full-parts definition. Reserved-family planner recall was 6/12, with 2/12 usable. These compare constructed layouts, not generalization across real sites.

## Fidelity, metadata and useful partial evidence

Planner body-part text lists were exact for 9/26 body comparison records, with 510 missing, 13 extra and five transformed characters. The denominator is the union of expected or emitted bodies: 25 reference bodies plus one unexpected body on a textless repost. Titles were exact for 0/2, with 24 missing and seven transformed characters. The reviewer had no emitted text: 784 body and 32 title characters were missing. Character differences use the frozen aligned-part comparison; they are diagnostic edit counts, not probabilities.

| Planner metadata field | Correct / 26 | Errors / 26 | Abstentions or missing / 26 |
|---|---:|---:|---:|
| contexts | 13/26 | 0/26 | 13/26 |
| created_at | 13/26 | 0/26 | 13/26 |
| identity | 13/26 | 0/26 | 13/26 |
| kind | 7/26 | 6/26 | 13/26 |
| relations | 10/26 | 0/26 | 16/26 |
| updated_at | 13/26 | 0/26 | 13/26 |

The reviewer had 26/26 missing/abstained values for each metadata field. Correct unknown timestamps and empty supported relationship/context inventories count as correct where construction truth declares them unknown/empty; they are not invented known metadata.

Among matched planner records, the registered forbidden-fragment checks observed zero quote, signature or interface fragments inside body parts (four quote, two signature and two interface reference fragments in the full inventory). **These contamination checks assess exact-container matched emissions only.** Unmatched emissions would need separate semantic review; this run had none. Omitted contributions and unannotated contamination classes are not validated by zero observed contamination.

A concrete partial success is [`table-a-planner`](../provenance/evaluation-20260916/qwen/table-a-planner/extraction/bundle/records.jsonl): Iona and Malik remain distinct actors/events despite each saying “The hinges need oil.” Their actor links and body wording are correct. The proposed body-part attribution remains `unknown`, so neither meets the registered full-parts requirement. This is useful source evidence requiring correction, not a fully successful known-author extraction. The two records meeting the text/actor metric are the unknown-actor body in `table-a` and the unknown-actor Unicode body in `catalog-a`; metadata issues remain separately reported.

## Reviewer and fresh-discovery behavior

Five reviewer-arm attempts stopped because the model failed the independent-inspection prerequisite. `feed-b` could not repair a globally excluded selected part, `table-b` repeatedly supplied the unsupported `limit` argument to the allowed `inspect_node` tool, and `catalog-b` exhausted its 12-call cap. The same three latter failures affected planner-only attempts. A valid author/source pointer alone did not override these gates.

The [read-only transcript failure analysis](DISCOVERY-V2-FAILURE-ANALYSIS.md) traces the retained evidence without rescoring: all 11 known-actor emissions left part attribution unknown, including seven with otherwise exact single-body text. Five reviewer phases attempted readiness without independent inspection; other observed mistakes included a repost interface label as body and a review heading assigned the wrong text role.

The reviewer arm used 62 calls versus 60 planner-only calls on the same eight pages, finalized no output, and therefore did not demonstrate reduced critical semantic errors. It increased finalization abstention. This is a result for the configured protocol, model and equal-arm budgets; it does not establish that evidence review is ineffective in general.

- `cards-a` fresh repeat: initial partial extraction became `unresolved_plan` (`field_outside_container`). No accepted repeat bundle; canonical comparison is undefined.
- `table-a` fresh repeat: both attempts accepted and verified; all eight canonical artifact files were byte-identical. Each emitted 3/3 matched records and 1/3 usable by the text/actor metric.

Both fixed repeats are retained, not selected for their best outcome. Model rediscovery is not promised deterministic. Separately, all six accepted runs passed model-free full capture/plan re-execution, eight canonical artifact comparisons, source-map validation and AHIF checks. Verification ran with Linux libseccomp network/exec syscall denial, 60-second/1024-MiB worker limits, and validated explicit paths; it was not a kernel filesystem jail. All three final frozen-input checks passed, and there were no mechanical integrity failures.

## Operating record and cleanup

One Secure Cloud A40 48GB ran Ollama 0.34.1 and `qwen3:32b-q4_K_M`, digest `030ee887880fc378860c2dd35101da424377520441ae4bfe7be6deff8ade7840`. The model occupied 24,476,301,393 GPU bytes at context 16,384. Runtime model settings and limits were explicit: schema output, thinking disabled, temperature zero, 4,096 output tokens/call, 12 provider calls and 300 seconds/job; 216 calls and 2,100 seconds shared. There was no provider/model fallback, no retries, and at most two repair rounds. Only registered fictional captures crossed the private SSH loopback gateway.

| Scope | Calls | Returned input tokens | Returned output tokens | Sum of worker seconds |
|---|---:|---:|---:|---:|
| Planner primary | 60 | 307,118 | 5,558 | 425.427 |
| Reviewer primary | 62 | 281,304 | 5,902 | 448.659 |
| Fixed repeats | 14 | 64,363 | 2,531 | 161.962 |

Overall: 136/216 calls, 652,785 input tokens, 13,991 output tokens, 134 evidence-tool calls and 588,336 inspected characters. Inference took 1,036.480 seconds; verification/scoring brought total runner time to 1,038.026 seconds. No job was skipped, no shared budget stop occurred, and the largest observed worker RSS was 35,552 KiB (a worker-process measure, not total host memory). The separate synthetic readiness call added one call, 36 input/10 output tokens and 9.595 seconds; it contained no scored capture.

The pod was deleted at `2026-09-16T06:05:46.821742+00:00` immediately after the inference-finished marker. A fresh independent Runpod list returned zero matching pods; the cleanup timer/service were then removed and inactive, the dedicated SSH tunnel was absent, and no persistent/network volumes had been created. [Cleanup receipt](../provenance/evaluation-20260916/runpod-cleanup-summary.json) binds the readbacks.

GPU rate was $0.49/hour plus a conservative 60GB temporary-disk allowance, totaling about $0.498333/hour. Creation-request to deletion duration was 1427.956291 seconds: **estimated $0.197666** for this trial, or approximately $0.297026 including the earlier trial estimate. This stayed below the authorized $1/hour and $5 total limits. Actual invoiced cost is unknown: a fresh billing query returned zero records, which is not proof of zero charges. Setup, download and readiness time are included in the duration estimate; token counts are not converted into fabricated dollar charges.

The pre-armed 55-minute local systemd deletion timer survived agent/CLI process exit by design but depended on the local machine, user manager and network. A provider `terminateAfter` deadline was also requested atomically; its enforcement was not exposed by readback. Actual deletion was performed and independently confirmed rather than inferred from either timer.

## Supported conclusion and next work

- **Implemented and demonstrated:** deterministic source-linked extraction, immutable bounded inspection, candidate dispositions, live bounded planning, fail-closed review checks, raw attempt retention, exact replay, and safe local evidence export.
- **Evaluated:** eight agent-constructed pages with all 26 reference appearances in each primary-arm denominator; two fixed repeats reported separately. Manual plans establish the positive executor path; live discovery results above are the separate measured result.
- **Not demonstrated:** a fully correct known-actor contribution under the frozen live full-parts criterion; a successful independent-reviewer finalization; real-page or independent human-annotation performance; general-purpose unattended account-history extraction.
- **Next work suggested by these outcomes:** revise and test the planner/reviewer interaction in a new version/designation, especially part attribution, title/body selection, semantic kind/relationships, valid tool arguments and independent reviewer coverage. Preserve this scored run; do not tune and relabel it as a fresh holdout. Acquire appropriately authorized real captures and actual independent annotations before real-layout claims.

Publication note: links above target selected copies. Each registration has a
`registration-publication.json` manifest identifying its original hash and explicit
operational-field redactions. Historical outcomes and their original hashes are
unchanged. See [publication scope](../provenance/evaluation-20260916/README.md).
