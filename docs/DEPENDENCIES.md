# Dependency provenance

This project uses its own Python 3.12 environment. The AHAS environment and its
pins were not changed. The local historical `qa/dependency-inventory-02.json`
records the actual installed versions, package metadata hashes, and hashes of
installed license/notice files. The `qa/` tree is not published; selected safe
provenance appears in the [initial-delivery summary](../provenance/initial-delivery/README.md).
The inventory reads local distribution metadata; no license is inferred from a
package name or from the fact that a repository is public.

## Locked inputs

| File | SHA-256 |
|---|---|
| `uv.lock` | `a5b2175ecf4eb155c206f16541af02fe6dea980b351efb7287f0d337bfe799b4` |
| `pyproject.toml` | `112885f6349a98f9205ee24853204a864f3b2a61ce587b1b2599a4b6abebb597` |

The lock records source archive/wheel hashes and the resolved runtime/test dependency
graph. `uv sync --frozen --python 3.12` uses that graph. The declared build backend is
`hatchling==1.27.0`; it runs in an isolated build environment and is not installed in
the measured application environment. Its transient build dependencies are not
represented as installed application packages in this inventory.

## Actual installed third-party packages

The following declarations come from the installed metadata, except that
webencodings identifies its exact BSD variant in its installed `LICENSE` text.
The machine-readable receipt retains the original declaration fields and file hashes.

| Package | Installed version | License declaration | Role |
|---|---|---|---|
| html5lib | 1.1 | MIT | Sole HTML parser |
| jsonschema | 4.26.0 | MIT | Sidecar/schema validation |
| referencing | 0.37.0 | MIT | Schema references |
| attrs | 26.1.0 | MIT | Validation dependency |
| jsonschema-specifications | 2025.9.1 | MIT | Validation vocabularies |
| rpds-py | 2026.6.3 | MIT | Persistent collections dependency |
| six | 1.17.0 | MIT | Parser dependency |
| typing_extensions | 4.16.0 | PSF-2.0 | Typing dependency |
| webencodings | 0.6.1 | BSD 3-Clause | Parser encoding dependency |
| pytest | 9.0.2 | MIT | Tests |
| iniconfig | 2.3.0 | MIT | Test configuration |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | Test dependency |
| pluggy | 1.6.0 | MIT | Test hooks |
| Pygments | 2.21.0 | BSD-2-Clause | Test output formatting |

The lock also contains `colorama==0.4.6`, a platform-conditional test dependency.
It is not installed in the measured Linux environment. Its license was not asserted
from absent installed metadata. Python's standard library and the host's libseccomp
are separate environment components; this receipt does not pretend to be a full
operating-system software bill of materials.

The editable `ahif-html==0.1.0` distribution has no declared license expression.
No license grant for the new project is invented here. The owner can choose its
publication license separately. Third-party notices remain in their installed
distributions; packaged reference code provenance is described below and in
`REFERENCE-PROVENANCE.md`.

## AHIF reference code

The local project vendors the exact reviewed AHIF 0.1.1 checker and schema bytes
from commit `7629dbe63521978f0b99319a373dfea42b8e6b81`. The pinned AHIF tracked
inventory contains no project `LICENSE`, `COPYING`, or `NOTICE` file. Its license
therefore remains **unspecified**. The owner's assignment authorizes this local
implementation and reuse. A later explicit owner request authorizes publishing
this extractor repository, but no general project license has been selected or
invented. Public repository visibility is not treated as a license grant. See
[PUBLICATION.md](PUBLICATION.md) for the current publication boundary.

The initial `qa/dependency-inventory.json` remains historical. The second receipt
was freshly executed after final source-distribution metadata was added; the
dependency lock and installed package set remained unchanged.
