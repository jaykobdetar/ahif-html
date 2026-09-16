# Bounded planner and explicit provider, version 1.0.0

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

Fresh live development evidence is retained under `qa/live-discovery-*`, with
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
accepted bundle. Already returned proposals remain in attempt/call logs. This
version does not try to publish independently valid records from an otherwise
invalid proposal. Batch-level cost registration is the caller's responsibility;
the single-page API cannot silently impose or infer a larger shared budget.

## Tools and review

The host exposes only `page_outline`, `inspect_node`, `inspect_neighbors`,
`read_attribute`, `search_text`, `find_structural_candidates`, and `preview_plan`.
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
It must independently inspect a structural region before seeing the plan.
Only a returned, non-withheld structural view satisfies that preliminary check;
an error or wholly discarded oversized view does not. Only then can it return
short, source-referenced enum decisions. Agreement marks
an **agent** review, never human review or guaranteed semantic correctness.

One reviewer pass is supported. A requested revision can produce a bounded repair
attempt, but its semantic issue remains unresolved until a later explicit review
or correction. The host does not pretend structural validity proves that a
wrong-author criticism was resolved. Such a run emits no accepted extraction.
Planner-only structural failures can be repaired automatically within the stated
limit, and every failed proposal/repair retains its validation outcome and ancestry.

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

`scripts/run_model_trial.py` registers a fixed synthetic inventory before calls:
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
