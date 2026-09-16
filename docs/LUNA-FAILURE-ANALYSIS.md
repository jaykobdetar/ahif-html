# Luna discovery: observed successes and failures

This is a post-run analysis of the frozen [second Luna trial](../provenance/evaluation-20260916/luna-02/trial-report.json), not a new scoring run. All 24 planner-only jobs ran: three rounds on the same eight fictional pages. Reference annotations are agent-authored construction truth, not human-reviewed real captures. No runtime, prompt, annotation, or receipt was changed for this analysis.

## Results and their meaning

| Measurement | Qwen primary baseline | Luna round 1 | Luna round 2 | Luna round 3 |
|---|---:|---:|---:|---:|
| Matched contributions / reference inventory | 13/26 | 16/26 | 17/26 | 18/26 |
| Usable contributions / reference inventory | 2/26 | 16/26 | 16/26 | 16/26 |
| Known-account usable / known reference | 0/20 | 13/20 | 11/20 | 12/20 |
| Correct known actor assignments | 11 | 13 | 12 | 14 |
| Correct unknown actor assignments | 2 | 3 | 5 | 4 |
| Accepted pages / attempted pages | 5/8 | 5/8 | 5/8 | 6/8 |

The frozen matching rule requires the exact reference contribution container. All 51 emitted observations across Luna's three rounds matched a reference container; there were no unmatched extra events or observed wrong-account assignments. Nevertheless, 27/78 reference appearances were missed because eight page plans were refused. The pooled 78 denominator repeats 26 contributions three times; it is not 78 independent contributions.

**“Usable” means a matched contribution with correct actor assignment and exact ordered parts, including text, role, attribution relation, and segmentation. It does not require every metadata field to be correct.** Thus a record can score usable while its relationship is wrong. Luna has two relationship errors, two relationship abstentions among emitted records, and one kind error. The [unchanged scorer](../src/ahif_html/evaluate.py) reports these separately.

All 16 accepted runs passed both retained model-free verification checks: original paths and relocated inputs with a different Python hash seed. This establishes extraction replay and AHIF/source-map integrity for those artifacts; it does not establish semantic correctness. The trial used 162 provider calls with reported usage of 897,107 input and 57,860 output tokens. Earlier readiness and integration failures are separate retained history, not included in these trial-only counts.

The comparison is a development diagnostic. Luna used medium reasoning, an 8,192-token output ceiling, a Responses wire envelope/explicit decoder, and `strict:false`; Qwen used thinking disabled, a 4,096-token ceiling, and Ollama grammar transport. Prompt, inspection-tool, plan, executor, and scorer contracts were held fixed. These results do not isolate a causal model effect or estimate performance on unfamiliar real sites. See the [registration](../provenance/evaluation-20260916/luna-02/registration.json).

## Concrete positive demonstrations

- **Nested thread and quotation:** [cards-b round 1 records](../provenance/evaluation-20260916/luna-02/cards-b-attempt-1/extraction/bundle/records.jsonl) preserve Iona's `body / other-author quote / body`, Sora's separately attributed reply with its native parent key, a guest contribution with `actor:null`, and Malik's captured truncated text. The instruction-like guest prose remains source text. All four match the [reference inventory](../provenance/evaluation-20260916/luna-02/evaluator-only/cards-b.gold.json).
- **Repost semantics:** [feed-a round 1](../provenance/evaluation-20260916/luna-02/feed-a-attempt-1/extraction/bundle/records.jsonl) preserves an original short post, an exact timezone conversion, and a pure repost with a quote attributed to `other` and a native `reposts` target. The absent original is not invented as another contribution.
- **Table layout:** [table-a round 2](../provenance/evaluation-20260916/luna-02/table-a-attempt-2/extraction/bundle/records.jsonl) preserves separate native events with identical wording, excludes the signature, and keeps the guest reply anonymous. The relative timestamp “yesterday” remains unknown while its raw evidence is retained.
- **Definition-list reviews:** both catalog pages succeeded in all three rounds. For example, [catalog-a round 1](../provenance/evaluation-20260916/luna-02/catalog-a-attempt-1/extraction/bundle/records.jsonl) separates the actual title and body, preserves date-only precision, and uses review kinds. All six repeated title-bearing records were exact; Qwen's primary run had zero exact titles out of two.

## Accepted interpretations that were wrong or incomplete

1. **Native target interpreted as a URI.** [feed-b round 1](../provenance/evaluation-20260916/luna-02/feed-b-attempt-1/extraction/bundle/records.jsonl) correctly extracts quote commentary and its author, but interprets `uncaptured-feed-post` as a relative URI. The emitted target is `https://feed.example/discussion/uncaptured-feed-post` in collection `records`; the reference is the native `posts` key. This record still meets the narrower usable definition.
2. **Quote omitted without merging surrounding body passages.** [cards-a round 2](../provenance/evaluation-20260916/luna-02/cards-a-attempt-2/extraction/bundle/records.jsonl) finds all four contributions but excludes the first contribution's quote entirely. Its two authored passages remain separate body parts. Exact authored body text does not make the full ordered-part sequence complete.
3. **Unknown original author confused with unknown relation to the record actor.** In [feed-a round 3](../provenance/evaluation-20260916/luna-02/feed-a-attempt-3/extraction/bundle/records.jsonl) and [feed-b round 3](../provenance/evaluation-20260916/luna-02/feed-b-attempt-3/extraction/bundle/records.jsonl), the quote text is exact but attribution is `unknown` instead of `other`. The original person's identity can be unknown while the quoted text is still identifiable as somebody else's contribution.
4. **Relationship/type drift.** Feed-a round 3 emits `kind:repost` with a `quotes` relationship rather than `reposts`. Feed-b round 3 emits ordinary `post`, omits the quote relationship, and retains quote parts. [Cards-b round 2](../provenance/evaluation-20260916/luna-02/cards-b-attempt-2/extraction/bundle/records.jsonl) also omits the reply's otherwise available parent relationship.

The registered forbidden-fragment contamination checks found zero quote, signature, or UI contamination. That is a limited fragment-based observation, not proof that every semantic boundary or prompt-injection case is correct.

## Why eight pages produced no accepted bundle

| Final refusal | Jobs | Concrete cause |
|---|---|---|
| `part_exclusion_outside_root` | cards-a/1, feed-b/2 | Exclusions name nodes outside the selected part's root. |
| `part_root_globally_excluded` | cards-a/3, cards-b/3 | A quote is both globally excluded and selected as an output part. |
| `relation_target_kind_invalid` | table-b/1, table-b/2, feed-a/2 | A native relationship is proposed with `target:null`. |
| `tool_arguments_invalid` | table-a/1 | `inspect_candidate` requests an out-of-range `max_characters` after repair allowance was consumed. |

The retained logs contain 19 provider responses consisting of multiple concatenated top-level JSON values and six rejected `inspect_candidate` argument sets. These failures use the same two-repair budget as plan errors. In [cards-a round 1](../provenance/evaluation-20260916/luna-02/cards-a-attempt-1/attempts.jsonl), one concatenated response and one oversized tool request consumed both repairs before the first full proposal reached the outside-root exclusion check. [Table-b round 1](../provenance/evaluation-20260916/luna-02/table-b-attempt-1/attempts.jsonl) repaired the exclusion error but retained a native relation with no target; round 2 repeated that sequence. All source strings remain retrieved by the deterministic executor; refusing these plans did not publish their potentially useful subsets as accepted extraction.

## Variation and next work

Fresh discovery varied even on identical bytes: cards-a was refused, then accepted with a missing quote, then refused; table-b was refused twice and succeeded in round 3. Catalog extraction semantics were stable across all three rounds, but all ten comparable pairs of accepted fresh runs differed in canonical artifact bytes, including their plans/provenance. That does not contradict byte-stable replay of one finalized plan.

Priorities for a separately versioned follow-up are:

1. Improve the one-action response and bounded-tool protocol; report protocol repairs separately from semantic repairs without silently expanding the registered budget.
2. Make part-root and exclusion ownership easier to inspect and correct, retaining explicit quote boundaries and avoiding global exclusions of selected parts.
3. Target relation kind/native-versus-URI meaning and quote attribution in evidence-focused review. Grounding validates where a string came from, not what the selected relationship means.
4. Freeze a new evaluation before testing changes. Luna reviewer effectiveness, independent human annotations, and a real-layout pilot remain unmeasured here.

Publication note: links above target selected copies. Each registration has a
`registration-publication.json` manifest identifying its original hash and explicit
operational-field redactions. Historical outcomes and their original hashes are
unchanged. See [publication scope](../provenance/evaluation-20260916/README.md).
