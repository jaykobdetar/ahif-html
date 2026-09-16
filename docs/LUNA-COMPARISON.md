# Luna comparison — development diagnostics

Experiment protocol 1.0.1, prepared 2026-09-16. This extends the provider boundary;
AHIF 0.1.1, AHAS 1.0.4, extractor evidence gates 1.1.0, text interpretation,
planner prompts 1.1.0, bounded tools, candidate accounting and scoring remain fixed.
Earlier receipts and the Qwen trial remain historical results.

## Registered question and inventory

Can `gpt-5.6-luna` produce more useful source-linked plans through the current
interface? Use all eight existing fictional discovery-v2 pages, four layout
families, 26 reference contributions (20 known account headers and six unknown).
Run planner-only three times per page in round-robin order. Retain every attempt;
report each round separately and all 78 reference appearances together. These
are eight unique pages, not 24 independent pages. The corpus and construction
annotations are agent-created development diagnostics, not human-reviewed or
untouched held-out confirmation. No real/private capture is authorized here.

The prior eight primary Qwen planner jobs provide a descriptive baseline. Their
reviewer arm and two repeated jobs are not pooled into that baseline. Matching
uses the existing exact-container policy, without post-hoc alternatives. Failure,
budget exhaustion, abstention and unstarted jobs retain their reference counts.

## Configuration and comparison limits

Use one model, `gpt-5.6-luna`, with explicit medium reasoning. Each job allows
12 provider calls, 300 seconds, two repairs, no transport retry, 64 bounded tool
calls and 120,000 inspected characters. Output allowance is 8,192 tokens per call,
including reasoning, compared with Qwen's 4,096 and disabled thinking. This is
a declared configuration difference, not an isolated causal model comparison.
The same 16,384-token context accounting ceiling remains; a hosted response that
exceeds it is recorded as a resource failure. The API does not receive a claim
that this smaller local accounting ceiling changes its server context window.

Responses transport uses the existing expanded action schema in non-strict
JSON-schema mode, inside a required `result` property. The adapter validates and
removes that transport envelope before the unchanged host action checks. Hosted
configuration 1.1.1 explicitly permits either that envelope or the original
direct action object, recording the observed wire shape. An ambiguous combination
is refused. It sends the same messages;
no new hints, examples, gold labels or source strings supplied by a model become
evidence. Strict structured output would require redesigning the existing open
tool argument objects and union, so it is not silently substituted. Compatibility
must pass a retained readiness call before scoring; no provider/model fallback.
OpenAI's non-strict schema mode and Ollama's grammar enforcement have different
provider-side guarantees; the host's action and extraction checks remain identical.
The first two readiness requests received HTTP 400; the diagnostic response
identified a forbidden top-level `oneOf`. Those receipts remain intact. Adding
the envelope is an explicit API compatibility change, not a new extraction rule.

### Preserved integration failure and new designation

The third readiness request passed, but scored designation 1 exposed a mismatch
between the unchanged prompt (which asks for a direct action) and the adapter's
required envelope. Sixteen jobs each returned direct actions and exhausted the
three-call response-repair allowance; job 17 was interrupted and seven jobs were
not started. All 24 jobs and their reference counts remain in that report, with
the original source bytes archived alongside it. This is transport integration
failure, not evidence of Luna's ability to extract contributions. No failed result
is retroactively marked accepted.

Designation 2 uses hosted configuration 1.1.1 and decoder 1.0.1 to accept both
explicit wire shapes. The host still validates the same action schema and source
references. No prompts, tool behavior, fixture labels, extraction or scoring rules
change. Both designations and readiness share the same original spending ledger;
the two HTTP errors and one cancelled request retain their full reservations.
The cancelled job's old Session token summary can omit the interrupted call's
unknown usage; its individual call log and ledger are authoritative for that gap.

API requests use `store:false`, default service tier, disabled automatic
truncation, and no provider-side tools. Request headers and the API key stay out
of logs. Returned visible JSON, usage, response identifiers and explicit errors
are retained; hidden reasoning is not requested or saved.

## Spending control

The owner authorized **$3 total**, including readiness. A durable, locked ledger
reserves a conservative maximum before every generation: the model's full
documented context at the higher long-context/cache-write input rate and the
configured output cap at the long-context output rate. This avoids relying on
a guessed tokenizer. Valid returned usage reconciles the reservation; missing
usage, timeout or process death leaves the full reservation charged. The next
request is refused if its reservation would exceed the remaining allowance.
This can stop early after uncertain failures. No retry or fresh designation
resets that spending ledger. Usage-based charges are estimates under the cited
price schedule, not an invoice or a reading of the account's remaining credits.

Official references checked before implementation:

- [Luna model and prices](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [Responses API](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)
- [Structured output limitations](https://developers.openai.com/api/docs/guides/structured-outputs)

## Execution evidence

Before inference, the runner freezes code, prompts, schemas, dependencies,
captures, metadata, annotations, matching policy, configuration, job list and
the old baseline report. Each accepted bundle must pass full AHIF/source-map
validation and model-free re-execution. Fresh discovery variation and identical
plan replay are reported separately. Final results will identify actual calls,
tokens (including reasoning/cache counts), elapsed time, estimated cost, all
errors and known/unknown account outcomes; format validity is not semantic
accuracy.

No result is claimed by this protocol document. See the new registration and
execution receipts for actual run status.

## Public checkout and new registrations

Publication interface **1.0.0** is a post-trial portability change to the runner.
It does not alter the evaluated prompts, gates, scoring, or historical receipts.
Offline tests and new registrations use the shipped provenance directories:

- `provenance/evaluation-20260916/qwen/` supplies the baseline.
- `provenance/evaluation-20260916/luna-01/` supplies the preserved integration-failure history.
- `provenance/evaluation-20260916/luna-02/` publishes the completed comparison.

Each directory contains `trial-report.json`, `registration.json`, and separate
`report-publication.json` and `registration-publication.json` manifests. The
registration is an explicit publication derivative: the disposed Qwen resource
identifier or local Luna budget-ledger path is replaced by a named marker. The
Qwen report also replaces its 18 repeated resource identifiers; the Luna reports
remain verbatim. Each manifest records the original SHA-256, published SHA-256,
and changed JSON pointers without retaining private values. Report metrics and
the original registration-hash binding are unchanged.
This records provenance; it is not a signature or a reconstruction of removed data.

The runner validates that binding and freezes both published artifacts and their
manifests in a new run. It refuses a missing manifest or a
mismatched published hash; it does not silently load ignored local `qa/` files.
Both provenance inputs can be chosen explicitly:

```sh
.venv/bin/python scripts/run_luna_trial.py prepare \
  --config /absolute/approved-config.json --out /absolute/fresh-trial \
  --baseline provenance/evaluation-20260916/qwen \
  --integration-history provenance/evaluation-20260916/luna-01
.venv/bin/python scripts/run_luna_trial.py check --run /absolute/fresh-trial
```

These two commands perform no inference. `prepare` creates or retains the
explicitly configured local spending ledger and freezes the supplied approval;
the published files do not grant approval or carry the original private ledger.
The default provenance arguments are the shipped directories above. Custom
directories must use the same manifest contract, including `mode:verbatim` with
equal original/published hashes and no changes for an unchanged registration.
Running `run` is a separate paid operation requiring approved data, budget, and
an API key. Ordinary tests mock providers and do not require private history or
network access.
