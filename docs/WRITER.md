# Deterministic writer and replay — 1.0.0

The writer consumes the same finalized, validated concrete plan for manual,
recorded, mock, recipe and live discovery. It does not accept output text, user
names, native identifiers or timestamps as plan literals. Values are read from
the pinned index. The source capture, parser/index identity, profile and plan
are bound before observations; observation IDs are then bound in source maps.
There are no cyclic hash inputs.

## AHIF boundary

This is a new `html-structural-text/1.0.0` profile. AHIF 0.1.1 schemas, canonical
serialization, source/observation domains and full semantic checker are reused
unchanged from the vendored pinned reference. The new sidecar schemas are not
AHIF fields. No AHAS input, Reddit CSV profile or scientific inference is emitted.

A supplied unknown author remains null; a shared guest/deleted label cannot name
a common account. A non-generic observed label can form a handle key whose scope
is the AHIF source descriptor. A profile identity URI remains a source assertion,
not a person identity. All four key components participate; source-local records
use the full source ID plus a concrete capture-bound container reference.

Native event IDs require the plan validator's documented native source evidence
and an identified source origin. The native identity attributes data-post-id,
data-comment-id and data-review-id establish separate posts/comments/reviews
collections. Native relationships require the corresponding explicitly scoped
parent/quote/repost attribute; an ambiguous data-parent-id stays unresolved.
DOM IDs alone are not event identities. URI
identities are preserved as supplied when absolute, or resolved solely against
the explicitly supplied HTTP(S) source URL when relative. The original string
remains recoverable in the index/source mapping and permalink; no HTML `base`,
redirect, network lookup or canonical-site alias is used. Inert link destinations
remain verbatim and unresolved in AHIF's link fields. Different appearances of
the same supported identity remain observations, with distinct container
provenance; the checker separately counts observation rows and logical keys.
Identical text does not establish event identity or erase separate events.

Unknown lifecycle, capture time, language and original completeness allow actual
available text. A supported source-state declaration may retain removal,
restriction or redaction alongside retained text. Storage is evidence retention,
not an AHAS analytical-eligibility declaration. No unavailable body is invented
for a title. A textless identified action may be retained with content unavailable;
this first plan language does not claim that unknown text absence means empty.

## Text and fields

The index implements the declared parsed-codepoint structural text policy.
Inline formatting adds no spaces. Its registered block/line/table separators
carry structural insertion mappings. Excluded quotes, signatures, code, hidden
or unsupported subtrees split the surrounding body into independent parts.
Writer pieces are ordered by actual document order across all planned roles, so
body/quote/body never becomes one false contiguous prose part. Structural text
has AHIF fidelity `transformed`, plain format, and language `und`. It is not an
original lexical HTML field or a claim of CSS visual fidelity.

Creation and editing use only ISO calendar dates or timezone-qualified second
resolution with up to nine fractional digits. Offset conversion preserves the
supplied fraction and original raw spelling; date-only stays date-only.
Invalid dates, missing zones, minute-only and relative displays remain unknown
with raw evidence. A known update time implies edited; absence does not imply
not-edited. Capture time is the supplier's explicit time object and never comes
from file modification time or the execution clock.

Every emitted text code point must be reproduced from an immutable text-node
range or registered insertion. Source-map coordinates are zero-based half-open
Unicode code points in emitted part text; source coordinates are decoded node
or attribute code points. There are no fabricated raw-byte spans. The map
checker validates contiguity, characters, source references and bindings, then
independently re-runs that part's planned selection. Full verification rebuilds
the parser index from supplied capture bytes and compares all accepted artifacts.
Grounding does not establish that a plausible author header belongs to the body;
that remains a recorded structural interpretation and review/evaluation target.

## Artifact and operational boundary

The accepted canonical set is fixed:

- `bundle/manifest.json`, `bundle/records.jsonl`
- `evidence/capture-manifest.json`, `evidence/index.json`
- `evidence/finalized-plan.json`, `evidence/source-map.jsonl`
- `evidence/decisions.jsonl`, `evidence/interpretation.json`

Only the two AHIF files live under the bundle root. Original bytes remain in the
explicitly supplied file, described by actual hash and size and external raw
retention; the writer never copies a private capture by default. The index does
contain decoded evidence and must be treated with the capture's data boundary.
Review and discovery are separate private sidecars. Operational clocks, paths,
model cost and retry timing do not enter accepted extraction identity.

Verification re-derives the fixed inventory, canonical files, run receipt and
AHIF/source-map checks. A changed output plus changed checksum fails when the
unchanged capture and plan imply different output. A verifier cannot authenticate
a supplier's capture-time declaration: when explicit metadata is omitted, it
reuses the stored declaration and says so. Consumers requiring independent
metadata identity should supply the metadata again.

The static review escapes all captured text and attributes, embeds no source
HTML, uses no JavaScript, and applies `default-src 'none'` with a local inline
style allowance only. It presents actors, dates, roles, missing fields, excluded
regions, every contribution outcome and unclassified index regions. A successful
execution means the finalized plan ran; page/account/discovery completeness
remains `not_established`. Source-local duplication, inline semantic quotations,
CSS-only visibility and uncaptured shadow/frame contents remain limitations.

Invalid plans and global resource exhaustion raise stable failures before accepted
publication. Per-contribution AHIF field/part bounds and no-evidence proposals
remain explicit decisions, allowing other validated records in a partial bundle.
Fresh staging directories are mode 0700 and atomically renamed; existing outputs
and symlinks are refused. This bounded prototype is not a race-proof hostile
multi-user ingestion service. OS-level offline controls are documented and
exercised separately; pure Python execution itself is not an OS sandbox.
