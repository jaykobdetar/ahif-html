# ahif-html — extraction prototype 0.2.0

This revision repairs the deterministic evidence gates and adds discovery
contract/prompt version 1.1.0. See the [repair and evaluation report](docs/REPAIR-0.2.0.md).
The uploaded 0.1.0 baseline and its initial trial results remain historical;
the [publication evidence](provenance/evaluation-20260916/README.md) retains the later repair and model-comparison outcomes.

Source-linked saved HTML → **AHIF 0.1.1**. A model may propose selections; ordinary
code retrieves every source string. A finalized plan replays without a model.
This is a separate project; [AHIF](https://github.com/jaykobdetar/ahif),
[AHAS 1.0.4](https://github.com/jaykobdetar/account-history-analyzer), the Reddit CSV
bridge and old studies remain unchanged. See the [publication boundary](docs/PUBLICATION.md),
[current execution evidence](provenance/evaluation-20260916/README.md), and
[historical initial-delivery summary](provenance/initial-delivery/README.md).

## Model-free quickstart

Use Linux with Python **3.12**, uv, and `libseccomp.so.2` (the tested CLI boundary).
From this directory:

```bash
uv sync --frozen --python python3.12
.venv/bin/ahif-html extract \
  --capture examples/fictional/forum.html \
  --metadata examples/fictional/forum.metadata.json \
  --plan examples/fictional/forum.plan.json --out local-runs/forum
.venv/bin/ahif-html verify \
  --capture examples/fictional/forum.html \
  --plan examples/fictional/forum.plan.json --run local-runs/forum
.venv/bin/python -m pytest -q
```

Open `local-runs/forum/review/index.html` locally. Its escaped static source view
contains no active source HTML or remote resources. Destinations must be **new**;
choose a new run name when repeating commands. Use run paths without unresolved
`..` segments; normalize such paths before verification. Dependencies need network only
when not already cached; extraction/replay themselves deny network and exec through
Linux seccomp. The importable API does not sandbox its embedding process.

The fictional multi-author thread emits body/quote/code/body boundaries and a
nested reply, excludes a signature and UI, and retains unknown authorship/time.
The original five-page fixture inventory covers four layout families. The new
[discovery evaluation inventory](examples/discovery-v2/README.md) adds eight
multi-contribution pages and a frozen matching policy. Agent-authored construction
truth is explicitly not independent human annotation.

## Inspect, discover, review, correct, reuse, evaluate

```bash
.venv/bin/ahif-html inspect --capture examples/fictional/reviews.html --out local-runs/index
.venv/bin/ahif-html apply-recipe \
  --capture examples/recipes/thread-b.html --metadata examples/recipes/metadata.json \
  --recipe examples/recipes/thread.recipe.json --out local-runs/recipe
.venv/bin/ahif-html review --run local-runs/forum --out local-runs/review
.venv/bin/ahif-html evaluate \
  --dataset examples/fictional/dataset.json \
  --config examples/fictional/evaluation-config.json --out local-runs/evaluation
.venv/bin/python scripts/verify_delivery.py --out local-runs/delivery-check
```

`correct --capture FILE --run RUN --corrections FILE --out NEW` validates a
source-selecting correction with base-plan hash and declared reviewer. It writes
`NEW/run` plus the preserved correction. Empty review correction templates are
intentionally not executable. The delivery-check command above generates a
working correction example; its contract is
`src/ahif_html/schemas/correction.schema.json`. No correction can supply replacement prose.

`batch --manifest FILE --out NEW` accepts explicit relative capture/metadata/plan
paths and cumulative byte/time ceilings. `--limits FILE` on single-capture commands
can lower the documented profile ceilings. `--help` exposes exact syntax.
Exit zero can mean partial execution: inspect JSON status, reasons and coverage.
A successful DOM traversal is never an account-completeness claim.

### Live discovery — separate from replay

The original provider is **Ollama**, on the workstation or through an explicitly
approved SSH tunnel to a Runpod instance. Explicit model ID, loopback endpoint,
context/output/call budgets and per-capture data approval are required. No hosted
API credentials or paid dependency are required. An already installed model can
be selected; the prototype never silently downloads/falls back during discovery.

Both `examples/model-config.live.example.json` and
`examples/model-config.remote-tunnel.example.json` have approval disabled.
Review your input, bind its actual SHA-256 and allowed data class, declare approval,
and select an installed local model before running:

```bash
.venv/bin/ahif-html discover --capture capture.html --metadata capture.metadata.json \
  --model-config approved-local-model.json --out local-runs/discovery
```

No real/private captures should be approved by copying a synthetic approval.
Model requests/returned content and index sidecars can contain supplied source
text; keep them private when needed. Only safe bounded index tools are exposed.
`mock` and `recorded` modes are test/replay modes, visibly distinct from live calls.
Reviewer selection and repair budgets are explicit. New discovery is not promised
deterministic, even at temperature zero. See [planner details](docs/PLANNER.md).

## What a minimal incoming record needs

A saved byte file, a concrete contribution region and at least one useful source
selection are enough. Unknown source URL, author, original time, language,
lifecycle and completeness remain valid. Without dependable event identity the
host creates a source-local appearance key. A bare empty container is not a
successful evidence target. Capture metadata, links, titles, quoted material,
known IDs, parent references and dates are optional when unsupported by the source.

The output bundle contains only declared AHIF files. Capture/index/plan/source-map/
interpretation and operational evidence sit outside the bundle. Original supplied
bytes stay in their external location, bound by hash; the user retains them for
replay. No credentials, real account exports or account mappings ship as examples.

## Supported limits and evidence

See the current [repair report](docs/REPAIR-0.2.0.md) and
[discovery evaluation design](docs/DISCOVERY-V2-EVALUATION.md). The historical
[delivery report](docs/ADOPTION-REPORT.md) and the
[published evidence summary](provenance/initial-delivery/README.md) for executed
checks and live outcomes. References to `qa/` in historical documentation identify
local receipts omitted from this repository. Selected fictional captures, visible
model actions, outputs and failures now ship in the versioned publication evidence;
private operational controls remain excluded. The [changes/open issues](docs/CHANGELOG.md)
record implemented, demonstrated, evaluated, failed and not-run work. Important boundaries:

- Saved HTML and explicitly declared rendered DOM; pinned HTML5 parser and strict
  decoding; concrete plans, bounded local planning/review, corrections, recipes.
- Roles and hard boundaries, exact source maps, scoped identities, explicit unknowns,
  full pinned AHIF validation, canonical model-free re-execution and inert review.
- No crawler/login/browser extension, CSS visual reconstruction, OCR, hydration JS
  interpreter, language inference, identity-continuity service or generic AHAS
  projection. Arbitrary websites are not universally supported.
- No real-layout or independent human-annotated benchmark is claimed. The local
  model's actual successes and failures are reported separately from manual plans.

References: [architecture](docs/ARCHITECTURE.md), [text policy](docs/TEXT-POLICY.md),
[threat model](docs/THREAT-MODEL.md), [writer](docs/WRITER.md),
[evaluation](docs/EVALUATION.md), [AHAS boundary](docs/DOWNSTREAM.md),
[reference provenance](docs/REFERENCE-PROVENANCE.md),
[dependencies/licenses](docs/DEPENDENCIES.md).

## Optional Luna comparison

The [executed results](docs/LUNA-RESULTS.md) report three live rounds, all failures,
usage and source-linked replay checks. [Failure analysis](docs/LUNA-FAILURE-ANALYSIS.md)
separates remaining interpretation errors from mechanical validation.

The separate [Luna experiment protocol](docs/LUNA-COMPARISON.md) describes a
planner-only comparison on the existing eight fictional development pages.
Hosted model configuration 1.1.1 explicitly selects OpenAI Responses and
`gpt-5.6-luna`; the older local Ollama configuration stays version 1.0.0.
Cloud access requires explicit synthetic capture hashes and a shared spending
ledger capped at $3. Supply the API key through `OPENAI_API_KEY` or the runner's
private key-file option; never put it in model JSON, source files or receipts.
The protocol is not itself an executed result. Original trials remain available
under their original designations.

See [the unapproved configuration template](examples/model-config.openai.example.json).
For the shipped fictional corpus and published historical baseline:

```sh
.venv/bin/python scripts/run_luna_trial.py prepare --config /absolute/approved-config.json --out /absolute/fresh-trial
.venv/bin/python scripts/run_luna_trial.py check --run /absolute/fresh-trial
.venv/bin/python scripts/run_luna_trial.py run --run /absolute/fresh-trial --key-file /absolute/private-key-file
```

Preparation uses the published Qwen baseline and first Luna integration-failure
history under `provenance/evaluation-20260916/`. Explicit `--baseline` and
`--integration-history` directories can select other retained copies. Publication
redactions have separate manifests and never replace original receipt hashes.
No model calls occur during preparation or ordinary tests.
