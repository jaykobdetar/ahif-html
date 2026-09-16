# Reviewed references and preservation

The implementation used these exact reviewed commits from existing local checkouts:

| Reference | Revision | Tracked files checked |
|---|---|---:|
| [AHIF](https://github.com/jaykobdetar/ahif/tree/7629dbe63521978f0b99319a373dfea42b8e6b81) | `7629dbe63521978f0b99319a373dfea42b8e6b81` | 155 |
| [AHAS](https://github.com/jaykobdetar/account-history-analyzer/tree/070213f0520d01529556e4aa7f4fa9270c22c6aa) | `070213f0520d01529556e4aa7f4fa9270c22c6aa` | 2,223 |

`qa/reference-inventory-before.json` contains the pre-assignment tracked-file
SHA-256 inventory. `qa/reference-preservation.json` records a fresh full comparison:
both HEAD revisions match, the complete tracked-file sets match, every tracked
working-tree file has the same SHA-256, and both Git porcelain status checks are
clean. Optional Git locks were disabled for these read-only inspections. No previous
pilot, private account export, analysis engine, or numerical study was rerun by this
preservation check.

The referenced `qa/` inventories remain local historical evidence and are omitted
from Git. The public [initial-delivery summary](../provenance/initial-delivery/README.md)
retains selected safe verification facts and source-receipt hashes.

## Copied bytes

Nine local reference files were compared independently against the pinned inventory:

- `src/ahif_html/vendor/ahif_011/SPEC.md`
- `src/ahif_html/vendor/ahif_011/FIELDS.md`
- The four entry-point/schema files under
  `src/ahif_html/vendor/ahif_011/schemas/`
- `src/ahif_html/vendor/ahif_011/reference/validate_bundle.py`
- `reference/EXPORT_OBSERVATION_DECISION.md`
- `reference/EXPORT_OBSERVATION.md`

All nine matched. The receipt records each source path, local path, actual and
expected hash. These copies are the actual implementation references, not a
replacement format revision. Local parser/planner/executor contracts are separate
sidecars; AHIF still has `format_version: 0.1.1`.

The AHIF checker is reused for its restricted JSON serialization, hash domains,
manifest checks and semantic validation. Its original fixture-oriented limits remain
understood; the extractor adds bounded ingestion and source-map replay around it
without modifying the reference checker. The implemented Reddit CSV bridge remains
a distinct source contract. HTML output does not masquerade as that bridge and
cannot be submitted to its projector by changing source labels.

## Rights and evidence scope

The pinned AHIF inventory has no project license/notice file. The AHIF license is
unspecified, and no invented license text has been attached to its copies. The owner
explicitly requested this separate implementation and subsequently authorized
publication of its repository. The earlier local-only delivery status is historical;
publication authorization does not select a project license or assert third-party
capture redistribution rights. The pinned reference copies retain their exact bytes.
See [the publication boundary](PUBLICATION.md).

The shipped HTML examples are newly constructed fictional material and are labeled
synthetic. Their annotation provenance is implementation-agent construction truth,
not human review. Existing public repository files were read and hashed; private
Reddit exports, credentials and account mappings were not imported into this project.

A future supplied capture's access declaration, redistribution permission, authorship
and content license remain independent evidence claims. Unknown values remain
unknown; successful extraction, public visibility, a matching hash, or a local
model run does not supply consent or a dataset license. This prototype stores the
supplied declaration rather than manufacturing one.

## Final preservation read

`qa/reference-preservation-final.json` is the final fresh read after implementation
and packaging changes. Both protected checkouts retained the same commits, all
155 AHIF and 2,223 AHAS tracked file hashes matched the pre-assignment inventory,
and both were clean. All nine copied reference files still matched the pinned
bytes. The earlier preservation receipt remains unchanged as historical evidence.
