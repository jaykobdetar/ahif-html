# Architecture and decisions — prototype 0.1.0

## Boundary

This is a separate Python 3.12 library and CLI. The destination remains AHIF 0.1.1,
using the exact reviewed checker and schema bytes. AHAS 1.0.4 and the Reddit CSV
bridge are references, not runtime dependencies. No HTML-to-AHAS converter is
implemented. `REFERENCE-PROVENANCE.md` records actual reference revisions and byte
verification. The upstream AHIF package and this extractor have no explicit
project license selected. The owner authorized publication of this separate
repository after the initial local delivery; [PUBLICATION.md](PUBLICATION.md)
defines the included code/evidence boundary without inventing a license grant.

## Data flow

1. An explicit file and supplier metadata are bounded and decoded once.
2. html5lib 1.1 produces a DOM; deterministic preorder indexing retains elements,
   text, attributes, comments, parent/child links and document order. HTML IDs are
   ordinary attributes and may repeat. No page code is evaluated.
3. A manual plan, bounded model planner, or relative structural recipe selects
   concrete references. Every path calls the same plan validator and executor.
4. Host code retrieves strings, assigns scoped keys, applies registered text/time/
   URL rules and emits canonical AHIF. Every text character has a source-map entry.
5. The pinned AHIF checker and independent source-map reconstruction validate the
   artifact. `verify` re-executes from capture + externally supplied finalized plan
   and compares the fixed accepted artifact set, including maps and interpretation.
6. A static escaped review shows contributions and indexed/rejected/unreviewed
   regions. Corrections change source selections and enumerated interpretations,
   preserve base-plan ancestry, and create a new run; they cannot rewrite text.

## Stable internal contracts

All schemas are packaged under `src/ahif_html/schemas`, use JSON Schema 2020-12,
and are version 1.0.0. They are extractor sidecars, never additions to AHIF core.
`capture` describes supplier declarations. `plan` binds capture/index/profile,
contributions, references, exclusions, uncertainty and review declarations.
`source-map`, `run-status`, `recipe`, `correction`, `batch`, model configuration,
planner responses, evaluation dataset/configuration/results have separate schemas.
Runtime validation includes semantic constraints beyond schema syntax.

All serialized sidecars use the vendored restricted JCS-compatible implementation:
no floating JSON numbers, duplicate keys, invalid Unicode, or implicit ordinary
JSON fallback. The application uses decimal strings for timings and ratios.
Hashes use explicit `AHIF-HTML:<domain>:1.0.0\n` domains for internal identities;
AHIF uses its unchanged versioned hash domains. Input bytes/parser/index precede
plan/profile, which precede observations/files and receipts. No cyclic hash input.

## Identity and uncertainty

Native event IDs are exact whole strings from the supported declared attributes:
`data-post-id` → posts, `data-comment-id` → comments, `data-review-id` → reviews.
They require supplied source authority and a plan assertion with evidence.
This is a structural interpretation, not source authenticity verification.
An ordinary DOM `id` is not a native contribution ID. Meaningful captured identity
links can supply URI keys; otherwise source-local keys bind source ID + node ref.
Text equality never deduplicates events. Multiple appearances of one native event
have separate observation IDs; event counts use all four record-key components.
Source-local IDs do not establish cross-capture sameness. Handle labels must be
scoped by `(source_id, key)` as required by AHIF; no continuity resolver is provided.
Generic guest/deleted/anonymous labels become `actor: null`.

Unknown creation/edit/capture time, language (`und`), lifecycle, completeness,
parent and authorship remain valid. Zoned ISO timestamps and calendar dates are
parsed using one versioned rule; relative, zone-less and ambiguous dates remain
unknown with raw evidence. Capture time is never filesystem mtime. Source totals
and traversal success never become a completeness percentage. Indicators such as
pagination, loading, hidden frames and truncation remain indicators, not proof.

## Practical choices and limits

- No raw capture copies are required in the bundle. The caller retains original
  supplied bytes outside it; hashes bind them. Sidecars contain indexed source text
  and are equally sensitive. Unsupported decoding fails without modifying input.
- Namespace, source descriptor, profile and finalized plan are bound in observation
  provenance. Operational clocks, model requests, retry timing and money are outside
  canonical extraction identity.
- Pure repost, title-only, removed/redacted text and unknown actor observations are
  supported when concrete plan evidence exists. Arbitrary hydration JavaScript,
  OCR, CSS-generated words, inferred languages and relative-time reconstruction
  are not implemented. Embedded JSON is indexed as an excluded script region;
  semantic structured-data extraction is explicitly unsupported in this version.
- No extra ontology/module is required to store useful prose. Missing contexts,
  metrics, screenshots and metadata remain absent/unknown.
- Recipes validate cardinality and ownership; they do not prove that a reused
  class name retains meaning. Visible mismatch stops reuse; semantic review remains
  needed for deceptively compatible layout changes.
- The CLI uses Linux OS controls documented in `THREAT-MODEL.md`. An embedding
  application must apply its own process isolation for library calls.
