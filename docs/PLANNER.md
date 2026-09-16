# Bounded planner and explicit provider, discovery version 1.1.0

The planner proposes source references. Accepted proposals go through
`plans.validate_plan` and the same `executor.execute_index` used by explicit
plans. It never has a second writer or a fixture-specific extraction branch.
The model supplies `contributions`, `rejected`, and `unresolved`; the host supplies
the capture/index bindings, version, origin, review declaration and ancestry.
Neither an unknown time nor an unknown author prevents supported text extraction.

## Modes and actual evidence

`live` means requests were sent to the explicitly configured Ollama model. `recorded`
replays an explicitly supplied response JSON file. `mock` is a separately labeled
test mode. Neither recorded nor mock is inference. Ordinary tests are model-free;
the adapter transport test is a fake HTTP response test, not a live model test.
Discovery never reads gold annotations, hand-authored plans, expected-output
files, or capture filenames as extraction rules.

Historical discovery-1.0.0 live development evidence is retained under `qa/live-discovery-*`, with
registration, approved frozen capture bytes, config, model digest, memory
monitoring, every attempted response and final failure/success status. Consult
those receipts for actual outcomes; an implemented adapter alone is not evidence
that discovery succeeded. Real saved-page evaluation and independent human
annotations are separate from these synthetic development runs.

The initial local Qwen3 4B runs are summarized in
`qa/live-discovery-summary.json`: nine provider attempts, no accepted model plan.
The small model copied evidence objects or exhausted its bounded workflow. Three
JSON-schema API attempts were rejected by the installed server's model-vocabulary
loader. These are retained failures, not mock successes. Early token-accounting
limitations have a separate audit; missing counts remain unknown.

The subsequent authorized Runpod Qwen3 32B trial used 18 actual calls. It emitted
three verified runs across two synthetic families (one was a fresh repeat), with
one of two reference contributions found on each accepted page. The forum and
reviewer arm failed safely. See `qa/remote-trial-01/ANALYSIS.md` and the raw
`trial-report.json`; all three accepted saved plans passed isolated model-free
replay. These partial successes do not establish real-site coverage or successful
live reviewer approval.

## Local Ollama contract

The adapter follows the official [chat API](https://docs.ollama.com/api/chat),
[structured JSON output](https://docs.ollama.com/capabilities/structured-outputs),
and [model metadata API](https://docs.ollama.com/api-reference/show-model-details),
checked on 2026-09-15. The concrete exercised server/model are recorded in each
live registration; no current flagship or paid provider is assumed.

Only explicit HTTP loopback destinations are accepted. `localhost` is mapped to
numeric `127.0.0.1`; environment proxies and redirects are disabled. The adapter
first uses metadata-only `/api/show`, requiring an installed GGUF model with model
information and refusing remote model/host declarations. It refuses cloud model
tags, never downloads models, and never falls back to another model/provider.
The Ollama daemon remains a trusted component: this check is not an
operating-system proof about what an arbitrarily modified server might do.

Config explicitly distinguishes `provider_location:"workstation"` from
`provider_location:"remote_tunnel"`. The latter requires a supplied SSH tunnel
and a Runpod declaration naming the resource, authorization, hourly cap below
USD 1, and maximum runtime of at most one hour. A loopback socket alone is not
proof that inference stays on this workstation. The adapter neither establishes
tunnels nor provisions/terminates pods; the external operator must enforce the
declared billing/runtime limit. Exact capture approval applies to either location.
No public arbitrary endpoint or automatic cloud fallback has been added.

Chat requests use explicit model, `stream:false`, explicit `response_format`
(`json` or phase-specific JSON schema), `think:false`,
configured `num_ctx`, `num_predict`, and temperature zero. This configuration
does **not** make new discovery deterministic. Replaying a finalized plan uses
neither Ollama nor the planner. A five-minute keep-alive avoids reloading between
bounded turns. The retained workstation batches unloaded their model afterward;
remote resource termination is recorded by the external resource controller.

The receipt records actual `prompt_eval_count` and `eval_count` when returned.
Absent usage and billing remain null. Saved provider content excludes separate
hidden-thinking fields; malformed outer envelopes retain their digest and byte
length, not arbitrary server internals. Returned content, including invalid JSON
content, remains retained privately. No credentials are accepted in endpoint
URLs or read from environment variables by this adapter.

## Explicit data boundary and resource settings

The config schema is `schemas/model-config.schema.json`. Live processing requires
an affirmative declaration, an allowed data class, and the exact capture SHA-256.
Authorization of one capture is not authorization of another revision. Unknown
or private data needs its own explicit approval. The shipped live example has
approval disabled; the development configs approve only particular synthetic
bytes. There is no inferred permission to transmit real private captures.

Inspector views exclude comments, unsupported/hidden subtrees, form values,
script/hydration bodies, arbitrary attributes, and unsafe/query-bearing URL values.
Only allowed text and structural attributes reach the model. This is a declared
data-minimization policy, **not** perfect redaction: an ordinary visible body can
contain private information. Review the approved capture scope accordingly.

Limits are cumulative across a discovery run: provider calls, inspection calls,
inspected characters, input message bytes, reserved input tokens, reserved output
tokens, response bytes, retries and elapsed time. Each call conservatively
reserves the configured context length against `max_input_tokens_total` and the
full configured output ceiling against `max_output_tokens_total`; retries also
consume reservations. `max_input_token_charge` is an additional **UTF-8 serialized
message-byte cap**, not a measurement of tokenizer output. Actual token usage is
reported separately and checked when the provider supplies it. Chat-template and
tokenizer behavior remains provider-owned; semantic success is not assumed when
the model loses context or fails the JSON protocol.

The shipped workstation context is 8192; explicitly configured remote runs may
use up to 16384. Returned prompt-plus-output counts exceeding the selected
context are refused. Unknown tokenizer preflight behavior is not silently treated
as proof that instructions survived context truncation. There are finite per-call output ceilings and bounded
repairs (at most two). `/proc/meminfo` admission checks protect available memory
before each call. The exercised batch additionally samples RAM every second,
requires 4 GiB available before starting, interrupts and unloads below 1.5 GiB,
and used a shared batch budget. Metadata gateway requests are counted
separately from inference calls. No concurrent model ensemble is implemented.

Failure, exhaustion, refusal and cancellation produce a retained receipt and no
accepted bundle when the complete run fits the output budget. The total publication
cap includes transcripts, sidecars and extraction output. A run exceeding that cap
is not published; the CLI can retain a separate bounded failure diagnostic. Already returned proposals remain in attempt/call logs. This
version does not try to publish independently valid records from an otherwise
invalid proposal. Batch-level cost registration is the caller's responsibility;
the single-page API cannot silently impose or infer a larger shared budget.

## Tools and review

The host exposes only `page_outline`, `inspect_node`, `inspect_neighbors`,
`read_attribute`, `search_text`, `find_structural_candidates`, `preview_plan`,
`candidate_inventory`, and `inspect_candidate`.
All refer to the current immutable index. Unexpected action keys, arbitrary tools,
bad references, unknown transformations, literal source fields and cardinality
errors fail host checks. Model context retains explicit node references and
truncation labels. The exposure audit records indexed, exposed, inspected and
unreviewed structural candidates; it is not proof of complete contribution recall.

Model-facing references use compact aliases (`n5`, for example), scoped to the
current capture/index. `discovery/node-aliases.json` records their full bindings.
Only named reference fields are expanded; text-node code points and attribute
values are never rewritten. Finalized plans and source maps contain the full
capture-bound references and need no model alias resolution during replay.

Set `reviewer:true` to request the evidence-focused workflow. A fresh reviewer
context initially receives evidence without the planner proposal or explanation.
It must independently inspect every inventoried candidate and return source-linked
observations before seeing the plan. Candidate roots alone do not suffice: nonempty
regions also require actual retained text evidence. Failed, withheld, or truncated
text views do not satisfy this check. After the plan is revealed, a separate check
for every candidate covers boundaries, authors, roles, times, and omissions. Every
selected value, retained body text node, and boundary must have been inspected.
Exclusions need visible structure, not disclosure of hidden/private text. Selected
attributes require the actual complete policy-permitted value; an element view
with a masked URL or shortened attribute does not make that value readable. Agreement marks
an **agent** review, never human review or guaranteed semantic correctness.

One reviewer pass is supported. A requested revision can produce a bounded repair
attempt, but its semantic issue remains unresolved until a later explicit review
or correction. The host does not pretend structural validity proves that a
wrong-author criticism was resolved. Such a run emits no accepted extraction.
Planner-only structural failures can be repaired automatically within the stated
limit, and every failed proposal/repair retains its validation outcome and ancestry.

## Discovery gate 1.1.0 and supported accounting

Runtime prompts are `prompts/1.1.0`; the response schema is
`schemas/planner-response-1.1.0.schema.json`. Prompts and response schema 1.0.0
remain byte-identical historical inputs. Model config and plan syntax remain
1.0.0. A baseline comparison must run the archived baseline implementation;
selecting a different model does not restore the old acceptance rules. Historical
receipts above are not new executions of discovery 1.1.0.

`candidates.py` enumerates a finite, deterministic inventory bound to the immutable
index. Signals are visible `article`, `li`, `blockquote`, `section`, `tr`, and `dd`
elements, documented native-ID attributes, a small declared set of exact semantic
class hints, and article/listitem/comment roles. These broad signals deliberately
include wrappers, navigation, and quotations that may need rejection. Unsupported
subtrees are counted separately. No website name, fixture ID, expected answer or
gold annotation selects a mapping. Unrecognized layouts may have additional
contributions outside this inventory; omitted unsupported patterns remain a
semantic limitation. Neither inventory traversal nor complete accounting proves
page or account completeness.

The inventory ceiling is the configured `candidates` limit (default 5,000). An
overflow refuses discovery before inference, preserving a capped inventory and
explicit total/truncation status. Candidate pagination uses ordinal offsets:

```json
{"action":"tool","name":"candidate_inventory","arguments":{"start":0,"limit":10}}
```

To inspect a candidate, page its subtree while repeating bounded parent/header
context. Node boundaries, source refs and truncation flags remain visible:

```json
{"action":"tool","name":"inspect_candidate","arguments":{"candidate_ref":"n12","start":0,"limit":12,"max_characters":300}}
```

Follow `next_start`. Each call shares the ordinary Inspector call/character/time
budgets. Oversized serialized views return an explicit discarded-view result and
do not count as evidence inspected. Context is a bounded preview; it is not a
claim to have exposed every header field or visual layout.

A final proposal must give every inventory candidate exactly one disposition:

- **Include:** its exact node is a selected contribution container.
- **Reject:** its exact node appears in `rejected` with a declared enum reason.
- **Unresolved:** its exact node appears in `unresolved` with a declared reason.

A parent disposition does not dispose of nested candidates. A quote can be
rejected as an event while separately retained as a quote content part. The
planner can select additional grounded containers outside the inventory. The
sidecars `discovery/candidate-inventory.json` and `candidate-accounting.json`
record these distinctions, missing/conflicting decisions, inventory and plan
bindings, and `not_completeness_proof:true`. An unresolved region permits an
otherwise valid **partial** extraction; it never becomes an invented event.

Reference repairs receive exact failing JSON paths, bounded unknown-reference
examples, and valid tool argument names. The host does not guess a replacement
node or source value. Failed attempts and costs remain retained.

Reviewer `ready_for_review` now requires `observations` for all candidates, with
`node`, `interpretation` (possible_contribution/non_contribution/uncertain), and
inspected `evidence` refs. Final `review` requires `checks` for the inventory and
additional selected containers. Each check gives `node`, `decision`
(supported/issue/unresolved), all five `aspects` (boundary/author/roles/time/omissions),
and actual `evidence`. Approval requires supported checks, no issues, and fully
readable selected evidence. Schema and source-exposure checks still cannot prove
the reviewer thought carefully or interpreted the page correctly. Evidence too
large for current full-text views, withheld selected attributes, and exhausted
budgets produce explicit abstention rather than automatic approval.

Offline construction/mock tests exercise positive partial extraction, omitted
candidates, navigation rejection, pagination/context, malformed references,
resource limits, reviewer coverage, excluded hidden/UI/signature regions, and
unreadable selected attributes. These tests demonstrate host mechanics, not live
model recall. New evaluation results belong to a separately frozen run.

## Running

After installing the project, the library entry point is:

```python
from pathlib import Path
from ahif_html.common import load_json
from ahif_html.planner import discover

result = discover(
    Path("capture.html"), load_json("approved-model-config.json"),
    Path("new-discovery-run"), load_json("capture-metadata.json"),
)
```

The CLI exposes the same operation as `ahif-html discover`; `--help` gives the
exact argument contract. The destination must be new. For recorded mode, config
`responses_file` is an explicit host-selected JSON array of response actions; the
model cannot choose it. For model-free replay, use `extract` with the saved
finalized plan, then `verify` against the accepted capture/plan/profile artifacts.

The current eight-page paired evaluation uses `scripts/run_discovery_v2.py`;
see [its registered design and commands](DISCOVERY-V2-EVALUATION.md). It freezes
implementation, prompts, inputs and budgets, retains every registered job and
reports fixed repeats separately.

The older `scripts/run_model_trial.py` registers a smaller synthetic inventory before calls:
two development families, both planner/reviewer arms on the same reserved comment
family, and a fresh development repeat. It freezes capture/metadata bytes, keeps
construction annotations in an evaluator-only directory, passes no annotation
path or content to inference, charges a shared call/wall budget, and scores all
outcomes afterward. A missing extraction scores the full reference inventory as
missed. `same_held_out_inventory_by_arm` is the arm comparison; development and
repeat outcomes remain separately labeled. The runner provisions no resource and
has no authority to widen an approved data or spending scope.

Requests/responses and model annotations are operational evidence, not source
facts. A grounded-but-wrong author association remains a possible semantic error.
Prompt-injection content can still mislead classification, despite the absence of
shell, arbitrary file access or model-selected HTTP tools. Measure that behavior;
do not equate mechanical integrity with semantic accuracy.
