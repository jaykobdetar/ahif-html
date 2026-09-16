# Repair and model-comparison evidence — 2026-09-16

This owner-authorized repository update publishes the extractor repairs and
selected **fictional** execution evidence. It does not perform new inference,
collect data or change AHIF/AHAS behavior. Captures and construction annotations
are agent-created; they are not independent human review or real-site evidence.

## Results and artifacts

- [Repair report](../../docs/REPAIR-0.2.0.md): three reproduced contracts repaired;
  [paired probes](repairs/paired/) retain captures, concrete node selections,
  before/after output and refusal reasons. [Inspection before](repairs/inspection-before/)
  and [after](repairs/inspection-after/) retain the output-limit reproduction.
- [Qwen results](../../docs/DISCOVERY-V2-RESULTS.md), [all outcomes](qwen/trial-report.json),
  and [visible model evidence](qwen/). The planner found 13/26 contributions;
  2/26 met exact text/attribution requirements. Reviewer outcomes remain failures.
- [Luna results](../../docs/LUNA-RESULTS.md), [all scored outcomes](luna-02/trial-report.json),
  and [visible model evidence](luna-02/). Three rounds each produced 16/26 usable
  text/attribution matches on the same eight pages. This metric does not require
  correct metadata. All 24 attempted jobs remain in their declared denominators.
- [First Luna integration failure](luna-01/trial-report.json) and its visible
  evidence remain separate from semantic scoring. No failed result was relabeled.
- [Positive four-contribution review](luna-02/cards-b-attempt-1/extraction/review/index.html)
  is inert HTML; open a local copy for the review view.
- [Usage/cost analysis](luna-02/analysis-summary.json): reported-token estimate
  $0.126120; conservative ledger charge/reservations $1.9350069 under the $3 cap.
  Actual invoice remains unknown. This update makes no paid requests.
- [Historical test receipt](historical-luna-tests.json): 323 tests passed at the
  Luna checkpoint. Fresh publication checks are separate below.
- [Historical reference checks](luna-02/preservation-check.json) and
  [companion documentation checks](../repository-publication/companion-update-20260916.json)
  distinguish preserved engine/contracts from later documentation edits.

## Copy integrity and omissions

[publication-files.json](publication-files.json) lists each selected source and
published hash. Canonical extraction files, fictional source captures and visible
model messages are copied verbatim. Command receipts with machine paths are
explicitly marked derivatives. `registration-publication.json` beside each
registration identifies operational-field redactions and its original hash;
Luna trial reports still bind the original registration, not an invented historical
registration. The Qwen report removes resource identifiers under its separate
`report-publication.json` manifest; its metrics and all failed outcomes are retained. These manifests document copying, not new execution or authenticity.

[replay-publication-files.json](replay-publication-files.json) binds 66 additional
verbatim extraction receipts/checks, the selected inert review and model reviewer
observations, and one standalone discovery receipt with an explicitly
redacted operational resource identifier. Each source and published hash is
recorded; the original local evidence remains unchanged.

Private captures, exports, account mappings, credentials, approved model configs,
raw spending ledgers, SSH/resource controls and machine-specific preservation
inventories remain local. Model hidden reasoning and authentication headers were
never retained as source evidence. Selected visible requests/responses are
fictional but may contain prompt-injection examples: treat them as data.

Historical directories and receipts were not rewritten. The repository's current
Luna runner has a publication-only portability revision; the original evaluated
runner source remains in the local frozen snapshot. Re-running discovery requires
new authorization/configuration and a new designation; it cannot reproduce old
model choices by claiming temperature or seed determinism.

## Model-free verification

[The fresh public replay receipt](public-replay-check.json) records 22 successful
full replays from these published paths: six accepted Qwen outputs and sixteen
accepted Luna outputs, comparing 176 canonical files. Every command used the
ordinary network-denied CLI worker and made zero model calls. This checks
extraction and AHIF integrity; it does not improve the reported semantic results.

Use the locked Python 3.12 environment from the project root:

```sh
uv sync --frozen --python python3.12
.venv/bin/python scripts/verify_delivery.py --out local-runs/publication-check
.venv/bin/ahif-html verify \
  --capture provenance/evaluation-20260916/luna-02/captures/cards-b.html \
  --metadata provenance/evaluation-20260916/luna-02/captures/cards-b.metadata.json \
  --plan provenance/evaluation-20260916/luna-02/cards-b-attempt-1/extraction/evidence/finalized-plan.json \
  --run provenance/evaluation-20260916/luna-02/cards-b-attempt-1/extraction
```

Choose a fresh output directory for each delivery check. Saved-plan verification
makes no model calls and independently re-executes extraction/source maps plus
AHIF validation. It does not certify semantic author association or completeness.

## Fresh repository checks

[Publication checks](publication-checks.json) record **328 tests passed**, all
**13 model-free CLI checks**, and a successful source/wheel build from a new
locked Python 3.12.3 checkout without ignored inputs. [Command receipt](fresh-delivery-check.json)
and [test output](fresh-tests.txt) retain actual execution. An isolated installed
wheel passed 30 runner tests and full extraction/replay with the same eight
canonical files as the checkout. The source archive contains the portable baseline
inputs; credentials, operational directories and private data are absent.

Earlier publication-check failures remain recorded: a test-only ancestor-folder
assumption was fixed, dependency export was rerun with its explicit writable cache,
and a verification path containing unresolved `..` segments was refused. Use a
normalized absolute run path in that case. This path limitation was not changed
inside the pinned checker or extractor runtime for publication.
