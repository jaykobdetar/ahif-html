# Discovery evaluation v2: registration and limits

This is a new synthetic engineering evaluation for discovery protocol/prompt 1.1.0
and normalizer 0.2.0. Historical 0.1.0 results and receipts remain unchanged. The
missing original independent review files were not recovered; new fixtures and
regression checks are agent-authored reconstruction, not the original review suite.

The eight-page inventory is `examples/discovery-v2/dataset.json`; its README records
construction provenance and splits. There are 26 reference appearances per primary
arm, including 20 known-account headers and six unknown authors. Every failed or
unstarted page remains in the denominator. Exact capture-bound container matching
and its wider/narrower-container limitation are frozen in `matching-policy.json`.

## Registered design

- Planner-only and planner-plus-reviewer each process all eight captures with the
  same per-job limits: initially 12 provider calls and 300 seconds, two repair
  rounds, no retries, explicit context/output/tool/inspection ceilings.
- Two fixed fresh planner repeats use `cards-a` and `table-a`, with the same budget.
  Repeat outcomes remain separate from the primary paired-arm aggregates.
- The default shared inference ceiling is 216 calls and 2,100 seconds. A later job
  is not started if its full equal-arm allowance cannot fit; it is scored as unrun.
  Budget exhaustion does not silently reduce the reviewer's comparison allowance.
- Every run uses the same selected model/provider settings. No specialist model,
  ensemble, fixture-specific discovery mapping or best-attempt selection is added.
- Gold and manual plans are copied to `evaluator-only/`. Workers are passed only a
  capture, metadata, model configuration and destination; the parent retains the registered construction truth in memory to protect its
  denominator from later file changes and scores only after all inference stops. This is argument/data separation,
  not a kernel filesystem jail for the evaluator's Python process.
- Each worker's complete discovery output has an 8 MiB limit. The runner reserves
  that allowance plus operational headroom against a 128 MiB shared output budget.

## Commands and freeze boundary

Run only after the mechanical gates pass and the operator authorizes the specific
provider, capture scope, total spending and cleanup arrangement. `prepare` performs
no model call or provisioning. The config must name an actual authorized gateway;
example approvals are disabled.

```sh
.venv/bin/python scripts/run_discovery_v2.py prepare --config APPROVED_CONFIG.json --out NEW_RUN
.venv/bin/python scripts/run_discovery_v2.py check --run NEW_RUN
.venv/bin/python scripts/run_discovery_v2.py run --run NEW_RUN
.venv/bin/python scripts/run_discovery_v2.py export --run NEW_RUN --out NEW_LOCAL_EXPORT
```

Before inference, registration binds the full source/prompt/schema/profile/checker
inventory, dependency lock, project metadata, runner and metric implementation,
captures, annotations, manual plans, matching policy and every per-job configuration.
The runner rechecks this freeze before each job. Changed frozen inputs stop later
jobs; their missing references remain scored. A started registration cannot restart.
A new evaluation designation is required for changes informed by scored outcomes.

A worker with no receipt consumes its full reserved call allowance for budget
accounting. Actual calls/usage remain unknown with a known lower bound, rather than
being invented from reservations. Returned usage, abstentions, errors, semantic
metrics and source grounding remain separate. Accepted artifacts receive independent
model-free CLI re-execution with its actual OS network/exec denial; a grounding
failure marks the evaluation failed regardless of semantic match counts.

## Evidence export and unavailable claims

The local export copies an explicit allowlist of fictional requests/responses,
actions, tools, finalized plans, source maps and AHIF artifacts verbatim. It records
original hashes for both copied and omitted artifacts. Configuration authorization,
resource identifiers, host keys, operational logs and known machine paths are not
included. Known-value scanning is scoped checking, not a universal secret detector.
The command never publishes, commits or pushes anything.

Real captures, independent human annotations, population-level attribution accuracy
and scientific authorship validation remain unavailable. Source-map correctness
cannot make a grounded wrong-author assignment correct. No successful model
outcome is claimed before the actual run report exists; mock worker tests only
exercise orchestration and denominators.

Attribution correctness and forbidden-fragment contamination metrics apply to exact-
container matches. Unmatched emissions have separate assigned/unknown-actor counts;
contamination on those extras is explicitly not assessed. Known and unknown reference
denominators and misses are reported separately (20 and six per primary arm). Malformed
or unverifiable output is excluded from usable evidence while its full reference
denominator remains; mechanical failure cannot become a semantic pass.
