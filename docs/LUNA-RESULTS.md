# Luna comparison results — 2026-09-16

**Luna produced substantially more usable source-linked text and correct account
attribution in this fictional development diagnostic. It still produced unstable
plans and metadata errors.** This does not establish universal extraction or
real-site performance.

## Results

Eight fictional pages, four layout families, 26 contributions: three predeclared
planner-only rounds, retaining every outcome. An agent authored the construction
annotations; they are not independent human review. Matching is the frozen exact
contribution-container rule. Related pages are development data, including the
previously scored pages.

| Run | Found /26 | Usable text + attribution /26 | Known-author usable /20 |
|---|---:|---:|---:|
| Qwen primary baseline | 13 | 2 | 0 |
| Luna round 1 | 16 | 16 | 13 |
| Luna round 2 | 17 | 16 | 11 |
| Luna round 3 | 18 | 16 | 12 |

“Usable” is the existing scorer's combination of a matched contribution, correct
record actor, and exact ordered text parts/roles/part attribution. It does **not**
require every metadata field to be correct. There are eight unique pages, not 24
independent pages. Across the three repeated inventories: **51/78 found, 48/78
usable**, 39 correct known-account assignments and 12 correct unknowns. No wrong
account or extra contribution was observed among the51 emitted records; 27
reference appearances were missed through rejected pages. These denominators
include every failed job.

| Fictional page | Round 1 usable | Round 2 usable | Round 3 usable |
|---|---:|---:|---:|
| cards-a | 0/4 | 3/4 | 0/4 |
| cards-b | 4/4 | 4/4 | 0/4 |
| feed-a | 3/3 | 0/3 | 2/3 |
| feed-b | 3/3 | 0/3 | 2/3 |
| table-a | 0/3 | 3/3 | 3/3 |
| table-b | 0/3 | 0/3 | 3/3 |
| catalog-a | 3/3 | 3/3 | 3/3 |
| catalog-b | 3/3 | 3/3 | 3/3 |

## Failures and variation

**16/24 page attempts accepted** (13 complete execution, 3 partial); 8 refused:
2 outside-root exclusions,2 roots both selected and globally excluded,3 invalid
relationship targets, and1 invalid tool-argument case. The partial records retain
observed truncation or unresolved coverage; successful execution is not complete
website/account coverage.

Accepted plans also contained three ordered-part mismatches: one omitted quote
and two quote-attribution differences. Metadata scoring reports 1 event-kind
error, 2 relationship errors and 29 relationship abstentions across 78 repeated
references. Example: a native quoted-post target was interpreted as a URI. Unknown
metadata matching an unknown reference is counted separately from evidence of a
known timestamp or lifecycle. See the [source-linked failure analysis](LUNA-FAILURE-ANALYSIS.md).

Body fidelity: 49/75 exact comparisons, 867 missing characters, 0 extra/transformed
characters. Title fidelity: 6/6 exact. The scorer found 0 registered quote/signature/UI
contamination fragments in matched bodies; this finite fragment check is not a
universal contamination test. Exact ordered parts, including attribution, remain
the stricter 48/78 result.

Fresh discovery varied: none of 10 comparable accepted attempt-pairs had all eight
canonical files byte-identical. **Saved-plan replay passed 32/32 checks**, covering
16 accepted plans with original and relocated paths, Python hash seeds 0 and 117,
no model calls, and Linux seccomp network/exec denial. Each replay compares all
eight canonical extraction files, independently re-executes source mappings and
runs the pinned AHIF schema/semantic checker. There were 0 mechanical-integrity
failures. Filesystem containment remains validated paths, not a kernel filesystem
jail; this is not a production hostile-ingestion security claim.

## Configuration and preserved integration failure

Actual model: `gpt-5.6-luna`, medium reasoning; 12 calls/300 seconds per page,
8192 output tokens/call including reasoning, two repairs, no transport retries.
Qwen used thinking disabled and 4096 output tokens. OpenAI's non-strict schema,
explicit wire-envelope handling and post-response 16384-token accounting differ
from Ollama's transport/context behavior. These confounds prevent an isolated
causal model comparison. Prompts 1.1.0, bounded tools, candidate accounting,
extractor gates, source text interpretation and scoring remained byte-identical.
No reviewer was run in this new comparison.

Two HTTP 400 readiness failures identified a forbidden root schema union. A third
readiness request succeeded with a `result` wrapper. Designation 1 then exposed
that the unchanged prompt elicits direct actions: 16 jobs failed decoding, one
was cancelled and seven were not started. Its 49 calls, all 24 denominators and
original source snapshot remain intact. Designation 2 explicitly accepts either
direct action or exact wrapper under hosted configuration 1.1.1/decoder 1.0.1,
then applies the unchanged host action schema. No failed old result was relabeled.

## Execution and budget

The scored designation ran **162 provider calls**, 897,107 input tokens and 57,860
output tokens in 828.774 seconds (about 13.8 minutes). There were 132 bounded tool
calls and 767,809 inspected characters. Peak observed worker RSS was 33,828 KiB;
this excludes the remote provider. No Runpod resources were provisioned.

Across both designations and readiness: 214 POST attempts, 211 with settled usage,
1,036,554 known input tokens and 65,625 output tokens, including 28,038 reasoning
tokens. The known-input breakdown is 920,595 cached,115,326 cache-write and 633
ordinary tokens. These total-token counts are lower bounds because three requests
have no reconciled usage; the interrupted job's old Session summary also omits
its unknown call, so individual logs and the ledger are authoritative.

**Reported-token price estimate: $0.126120.** The ledger instead charges a
conservative $0.3378885 for all known usage and keeps $1.5971184 reserved for the two
HTTP errors and interrupted request: **$1.9350069 total conservative accounting,
below the authorized $3 cap**. No invoice/balance was obtained; do not interpret
reservations as actual charges. Prices include cached and cache-write rates from
[OpenAI's Luna page](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
The shared ledger was never reset or refunded between designations.

## Tests, preservation and retained evidence

- Locked Python 3.12.3: `.venv/bin/python -m pytest -q` → **323 passed**, exit 0.
  The earlier 310-test execution and all readiness failures remain separately recorded.
- Preparation/freeze check and the scored runner exited 0. All 24 jobs ran; no
  scored run was stopped by budget or infrastructure. Complete execution status
  means outcomes were retained, not that all pages passed.
- All 83 registered implementation/input artifacts stayed frozen during designation 2.
- **4,756 AHIF/AHAS reference files** across the current and reviewed checkouts,
  their revisions, and **3,560 prior QA files** are unchanged.
- Existing source-file edits for this task are limited to provider dispatch,
  README and change log; provider/schema/runner/tests/docs were added. At that execution checkpoint nothing had been
  committed, pushed or published; the later owner-authorized repository update
  publishes selected fictional evidence without rerunning inference. No private capture, account export, key or
  credential was sent as model evidence.

Published evidence copies (registration redactions are described in adjacent manifests):

- [Frozen registration](../provenance/evaluation-20260916/luna-02/registration.json)
- [All per-page/per-layout metrics, attempts and replay results](../provenance/evaluation-20260916/luna-02/trial-report.json)
- [Combined usage and cost analysis](../provenance/evaluation-20260916/luna-02/analysis-summary.json)
- [Actual test command and output](../provenance/evaluation-20260916/historical-luna-tests.json)
- [Reference/history preservation](../provenance/evaluation-20260916/luna-02/preservation-check.json)
- [Preserved first designation](../provenance/evaluation-20260916/luna-01/trial-report.json)
- [Positive four-contribution review](../provenance/evaluation-20260916/luna-02/cards-b-attempt-1/extraction/review/index.html)
- [Protocol and exact configuration differences](LUNA-COMPARISON.md)

The next practical work is reducing malformed actions and exclusion/relationship
mistakes while preserving the structural gates. A new held-out real-capture study
and independent annotations would be needed to assess real-world performance.

Publication note: links above target selected copies. Each registration has a
`registration-publication.json` manifest identifying its original hash and explicit
operational-field redactions. Historical outcomes and their original hashes are
unchanged. See [publication scope](../provenance/evaluation-20260916/README.md).
