# Changes and open issues

## New extractor prototype 0.1.0; sidecars/profile 1.0.0

AHIF destination **0.1.1** and its reviewed schemas/checker are unchanged. There
is no reinterpretation of frozen AHIF 0.1.0/0.1.1 examples and no change to AHAS,
the Reddit bridge or historical scientific evidence.

| New implementation / revision during this build | Reason |
|---|---|
| Pinned html5lib DOM, strict decoding, capture-bound nodes, restricted JSON | Preserve source structure and reproducible parsed evidence. |
| Concrete reference-only plans and shared executor | Model output cannot invent source wording or use a second writer. |
| Hard exclusions plus independent overlap/ownership checks | Tests exposed descendant selections bypassing signature/nested-reply exclusions; now refused. |
| Mandatory known quote/code boundaries for body/title | Structural grounding alone could previously include blockquote prose as actor body. |
| Whole native/URI identity reads; posts/comments/reviews scopes | Slices and equal numeric IDs from different collections must not merge events. |
| Captured timestamp semantic validation | Schema syntax alone accepted impossible calendar dates. |
| Exact text mappings and full accepted-artifact replay | Rehashing modified output or swapping maps must not pass verification. |
| Exposure audit rollback for discarded model previews | Unseen evidence must not count as inspected. |
| Enforced custom candidate/selector ceilings and total output admission | Tests found overrides or required sidecars omitted from accounting. |
| Shared batch/evaluation deadlines, including nested worker timers | Per-page limits cannot restart the batch allowance. |
| Recipe duplicate/reserved binding refusal | A recipe cannot overwrite its host-selected contribution container. |
| Optional reviewer, bounded repair, explicit alias map and response format | Smaller source-linked model views; failed attempts and API incompatibilities remain visible. |
| Explicit workstation vs approved remote SSH-tunnel configuration | A loopback address alone does not establish that inference stays on the workstation. |
| Preserve usage from incomplete provider responses | Operational token accounting must retain available counts even when the response is rejected. The regression test passed after the live trial; historical attempts remain unchanged. |
| Fuller implementation inventory for future model trials | The first remote trial registered five implementation files; additional hashes were collected afterward and explicitly labeled supplemental. Future registrations include the scorer, schemas, runner and full configuration. |
| Normalizer version aligned to actual package 0.1.0 | Earlier development writer used the sidecar version 1.0.0 as software version; final writer records the installed extractor version. Earlier development receipts remain historical. |
| CLI generated-review success status fixed | First delivery harness found a valid review incorrectly returned exit2. Failed attempt is recorded; the next harness ran successfully. |
| Source/wheel packaging excludes private and operational evidence | Credentials, captured data and transcripts are not runtime package inputs. |

## Supported contracts

- One saved HTML response or explicitly declared rendered DOM serialization;
  optional supplier metadata; explicit batch manifest with cumulative limits.
- Versioned concrete page plans, source-linked metadata/parts/relationships/links,
  unknown outcomes, bounded indexing/inspection and same-executor model proposals.
- Native IDs from declared supported attributes, identity links, source-local
  appearances; unknown/shared guests; handle scope remains source-bound.
- Date-only/zoned ISO timestamps and unresolved raw time strings; language `und`.
- Ordered text roles, titles, quotes, signatures/code exclusions, removed/redacted
  retained evidence; textless identified actions can be retained with unavailable
  text. Empty selected regions do not assert known absence of original prose.
- AHIF schema + semantic validation, exact source maps, re-execution, inert review,
  source-selecting corrections, explicit structural recipes and visible mismatch.
- Live Ollama, recorded responses and mocks with distinct provenance; optional
  reviewer inspects actual returned evidence before seeing the proposal.

## Not supported / unresolved

1. No real website captures or independent human annotation inventory was supplied
   for the approximately20-page real-layout pilot. Synthetic construction truth
   and development model runs cannot fill that gap.
2. No universal layout success, authentic authorship, cross-capture handle
   continuity, account completeness, or calibrated model confidence is established.
3. CSS visual fidelity, screenshot/OCR text, media transcription, alt-text parts,
   hydration JavaScript interpretation, iframe/shadow traversal, relative-time
   reconstruction, arbitrary selectors/regex/transforms and source-specific live
   collection are not implemented. Structural metadata outside a chosen
   contribution container needs a new supported ownership rule.
4. Recipes are supplied declarative mappings. Automatic recipe learning and proof
   of semantic layout compatibility are not implemented. A structurally matching
   but meaning-changed layout can still require human review.
5. Deterministic CLI workers have tested OS network/exec denial and rlimits.
   The live gateway process and direct library calls do not inherit that sandbox;
   accepted live plans are separately replayed under it. No complete hostile
   ingestion service or kernel filesystem jail is claimed.
6. A reviewer-requested semantic repair remains unresolved until explicitly
   reviewed/corrected; the host does not pretend structural checks prove the
   criticism resolved. Invalid proposals do not publish accepted bundles.
7. Provider behavior and new discovery vary. The local4B failures are retained;
   stronger GPU results are reported in the adoption report, without selecting only
   a best attempt. Unknown token usage/billing remains unknown.
8. No generic HTML→AHAS projection. Unknown lifecycle, language, disjoint body parts
   and richer roles need a separately reviewed narrow mapping and loss/refusal
   ledger. See DOWNSTREAM.md.
9. AHIF upstream and this new project have no explicit project license selected.
   The owner has now authorized publishing the extractor repository. This does not
   invent a license grant, capture consent or third-party redistribution permission.

All paths under `qa/*-01`, `*-02`, etc. are execution/designation history. The
adoption report identifies current final evidence. Older receipts are not silently
replaced or counted as new final executions.


## Publication preparation after the initial local delivery

- The owner explicitly authorized creation/publication of the separate `ahif-html`
  repository. Earlier statements that the build remained local describe that
  previous delivery checkpoint.
- `qa/`, private controls/transcripts, built distributions, local environments,
  historical approved live configs and the detailed Runpod deployment record stay
  out of Git. Public live configuration templates keep approval disabled.
- The public [Runpod summary](RUNPOD-SUMMARY.md) retains model/cost/outcome facts
  without pod, timer, access or machine identifiers. Selected safe execution
  provenance is published under `provenance/initial-delivery/`; its summaries do
  not replace or rewrite the historical receipts.
- The original versions of changed delivery documents were preserved under local
  `qa/publication-preparation/original-docs/` before editing. Runtime code, tests,
  source fixtures, the dependency lock and pinned reference bytes are unchanged
  by this documentation/exclusion preparation.
