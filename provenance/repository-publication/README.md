# Repository publication verification

The owner explicitly requested a new extractor repository and updates to the two
companion repositories after the initial local delivery. This publication adds
navigation and selected summary evidence. It does not change the extractor runtime,
AHIF 0.1.1, AHAS 1.0.4 or the existing Reddit CSV profiles.

## Checks

- [companion-checks.json](companion-checks.json) binds the three documentation-only
  companion edits and verifies every other tracked file against the reviewed
  starting commits. Existing reference checkouts and historical receipts remain
  untouched; the edits were prepared in separate clones.
- [extractor-checks.json](extractor-checks.json) records a fresh model-free delivery
  run from the allowlisted Git snapshot in an isolated Python 3.12 environment.
  It includes all command exit codes and the actual test output. The runtime,
  schemas, prompts, examples and tests are bound by relative-path hashes.

The repository omits local `qa/`, `private/`, environment/build directories, detailed
provider transcripts, resource identifiers, and session-approved live model configs.
Only disabled approval templates are distributed. Source and fixture scanning is
an accidental-disclosure check, not a claim that the prototype is a production
hostile-ingestion service.

[Initial delivery summary](../initial-delivery/README.md) retains the prior live
trial's successes, misses, failed reviewer arm, replay results and cost limitations.
No new paid inference, data collection or scientific pilot was run for publication.
No project license grant is inferred or added; see the
[publication scope](../../docs/PUBLICATION.md).
