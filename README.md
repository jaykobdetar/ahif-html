# ahif-html — local prototype 0.1.0

Source-linked saved HTML → **AHIF 0.1.1**. A model may propose selections; ordinary
code retrieves every source string. A finalized plan replays without a model.
This is a separate project; [AHIF](https://github.com/jaykobdetar/ahif),
[AHAS 1.0.4](https://github.com/jaykobdetar/account-history-analyzer), the Reddit CSV
bridge and old studies remain unchanged. The owner authorized publication of this
extractor repository. See the [publication boundary](docs/PUBLICATION.md) and
[selected execution evidence](provenance/initial-delivery/README.md).

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
choose a new run name when repeating commands. Dependencies need network only
when not already cached; extraction/replay themselves deny network and exec through
Linux seccomp. The importable API does not sandbox its embedding process.

The fictional multi-author thread emits body/quote/code/body boundaries and a
nested reply, excludes a signature and UI, and retains unknown authorship/time.
The five-page fixture inventory covers four layout families. Agent-authored
construction truth is explicitly not independent human annotation.

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

The implemented provider is **Ollama**, on the workstation or through an explicitly
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

See [delivery report](docs/ADOPTION-REPORT.md) and the
[published evidence summary](provenance/initial-delivery/README.md) for executed
checks and live outcomes. References to `qa/` in historical documentation identify
local receipts omitted from this repository; full captures, transcripts and
operational controls are not published. The [changes/open issues](docs/CHANGELOG.md)
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
