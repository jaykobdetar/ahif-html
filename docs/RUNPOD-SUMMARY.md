# Synthetic model trial: public infrastructure summary

This summarizes one completed, owner-authorized engineering trial on fictional
captures. The detailed deployment record and operational receipts remain local.
Resource, timer, key, host and account identifiers are omitted from this summary.
No real/private capture or gold annotation was an inference input.

## Exercised configuration

| Item | Observed value |
|---|---|
| Compute | One NVIDIA A40, Secure Cloud; 60 GB disposable container disk |
| Persistent storage | No persistent or network volume allocated |
| Provider | Ollama 0.34.1 through an operator-established loopback SSH tunnel |
| Model | `qwen3:32b-q4_K_M` |
| Model manifest digest | `030ee887880fc378860c2dd35101da424377520441ae4bfe7be6deff8ade7840` |
| Runtime settings | 16,384-token context; 4,096 output tokens per call; schema output; `think:false` |
| Registered trial ceilings | 40 provider calls and 1,200 seconds; separate per-job budgets |
| Payload | Bounded index evidence from three fictional layout families; runtime prompts and schema descriptions |
| Comparison | Planner/reviewer arms on the same reserved synthetic comments; separate development repeat |

The hardware and model size are execution facts, not evidence of extraction
reliability. New discovery is not promised deterministic, including at temperature
zero. Accepted finalized plans use the same deterministic executor and can replay
without the model.

## All registered outcomes

| Run | Calls | Found / reference | Usable / reference | Result |
|---|---:|---:|---:|---|
| Reviews, development | 4 | 1/2 | 1/2 | Accepted; missed a contribution and had a kind error |
| Forum, development | 3 | 0/2 | 0/2 | Invalid source reference; no accepted bundle |
| Comments, planner | 3 | 1/2 | 1/2 | Accepted partial page; missed a contribution |
| Same comments, planner + reviewer | 4 | 0/2 | 0/2 | Independent reviewer inspection requirement failed |
| Reviews, fresh repeat | 4 | 1/2 | 1/2 | Repeated measured outcome under equal registered budget |

Usable means matched contribution, exact ordered text/roles and correct attribution
under the registered construction truth. All accepted observations had unknown
actors: this trial does not demonstrate known-account attribution. The annotations
were authored with the fictional fixtures, not independently reviewed by humans.
Every failed run remains in the denominators; empty-output precision is undefined.

The trial used 18 calls, with 35,432 input tokens and 934 output tokens reported by
the provider. A separate readiness check used one call, 36 input tokens and 10
output tokens. The model trial lasted approximately 72 seconds. All three accepted
runs subsequently passed model-free verification of eight canonical artifacts per
run under the deterministic CLI's OS network/exec denial.

See [EVALUATION.md](EVALUATION.md), [ADOPTION-REPORT.md](ADOPTION-REPORT.md) and the
[selected evidence summary](../provenance/initial-delivery/README.md) for metrics,
registration limits and source-receipt identities. A synthetic trial does not fill
the missing real-capture or independent-annotation evaluation.

## Cost and teardown

The observed GPU quote was US$0.49/hour. A conservative disposable-disk allowance
brought the estimate to US$0.4983/hour, below the owner's US$1/hour ceiling.
Creation request through verified absence took approximately 11 minutes 58 seconds,
for an elapsed-rate estimate of US$0.0994. Actual billing remains unknown; token
counts and a missing billing record are not substituted for a reconciled charge.

A separate 50-minute deletion safeguard was armed before creation. After results
were retrieved, the pod was deleted and a fresh independent inventory confirmed its
absence. The local tunnel and timer were then removed. No persistent or network
volume was left allocated. The original deployment, usage and cleanup receipts
remain unchanged locally.

This repository's provider adapter does not create resources, establish tunnels,
or enforce a provider's billing policy. Any future paid or remote run needs its own
explicit scope, budget and lifecycle controls; this historical authorization does
not carry over to a new deployment.
