# Threat model and exercised boundary

Captured HTML, links, embedded data, model responses and plans are untrusted data.
Threats include source execution/egress, prompt injection, path escapes, resource
exhaustion, invented references and semantic misassignment.

## Controls implemented

- html5lib parses supplied bytes without executing JavaScript, loading assets,
  frames, stylesheets or remote entities. The extraction language contains only
  concrete reads, roles and allowlisted interpretations, not executable expressions.
- Each deterministic CLI process installs Linux libseccomp rules denying socket,
  connection, send/receive and exec syscalls. It also applies 1 GiB address-space,
  60-second CPU/wall, 64 MiB per-file and 128-descriptor limits. The sandbox-check
  actually attempts network socket creation and exec and requires OS denial.
  No Python network monkeypatch is represented as isolation.
- There is no kernel filesystem jail. Application code reads explicit input/config
  paths; page/model values cannot choose files. Symlinks and traversal in manifests
  are refused, outputs must be fresh dedicated destinations and staging is atomic.
  Filesystem races from a concurrent malicious local writer are outside this
  prototype's threat model; it is not a production hostile multi-user service.
- Profile ceilings: 8 MiB capture, 100k nodes, depth256, 5k planned contributions,
  128 output parts per record, 64 MiB canonical/retained run output. Plans/schemas
  and tool results have bounds; limits may only be reduced. Parse allocation is
  guarded by OS memory limits in deterministic CLI runs. Library calls require
  caller isolation. Global batch/model budgets include cumulative work.
- Model evidence views omit script/comment/form contents and non-allowlisted
  attributes. Query-bearing or credential-bearing URLs are withheld. Arbitrary
  source prose can itself contain secrets: redaction is not claimed perfect.
- Only an explicitly approved loopback Ollama gateway is implemented. An explicitly declared remote_tunnel configuration can route that loopback connection through an operator-established SSH tunnel to an approved Runpod resource.
  Model/config/capture hashes and budget are explicit, cloud models/proxies/redirects
  are refused. No credential values are logged; private hidden reasoning is not
  requested or stored. A local model is still untrusted; every proposal is checked.
- The review is escaped static HTML with a restrictive CSP. No original active
  markup, remote images/CSS, source event handlers, frames, forms or clickable
  unsafe destinations are inserted. It is not a visual facsimile of the source.
- Full verification re-executes the fixed accepted artifact inventory, not just
  attacker-editable hashes. Output/map/receipt swaps and rehashed tampering fail.

## Limits of these controls

Seccomp rules are a narrow denylist, not a complete containment sandbox for native
parser vulnerabilities; CPU/RAM limits do not prove all denial-of-service risks are
solved. The live discovery process (including its parsing/executor calls) needs gateway networking and is not under the
network-denying deterministic-worker filter. Its host checks are not OS worker isolation; accepted plans are separately replayed in the isolated CLI. Tests establish no unauthorized
execution/egress for exercised paths, not semantic immunity to prompt injection.
A model can select a grounded but wrong author or omit a contribution. Independent
semantic evaluation and review remain necessary. Hashes prove byte integrity and
interpretation lineage, never authentic authorship or complete account history.
