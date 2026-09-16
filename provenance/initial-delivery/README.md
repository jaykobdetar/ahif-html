# Initial delivery evidence (selected summary)

[summary.json](summary.json) preserves selected results from the completed local
build and bounded synthetic model trial. It is a publication derivative, not a
new execution or a substitute for the original receipts. Original receipt hashes
bind the retained local evidence. Machine paths, credentials, model transcripts,
resource identifiers, and session-specific provider approvals are omitted.

- Deterministic extraction: 121 tests and 14 command checks passed; manual plans
  matched all 13 construction-reference appearances across five fictional pages.
- Real inference on synthetic captures: the first planner attempts found 2 of 6
  reference contributions. The repeat and failed reviewer arm remain separately
  represented. All three accepted plans passed full model-free replay.
- The Runpod instance was deleted and absence independently checked. The estimated
  elapsed-rate cost was about $0.10; actual billing is unknown.
- The original AHIF/AHAS inventories were unchanged at initial delivery. Later
  companion-repository cross-links are documentation-only changes.

Construction truth is agent-authored, not independent human annotation. No real
capture benchmark, known-account model-attribution success, universal extraction,
website completeness or authorship authenticity is established.

Reproduce model-free checks with Python 3.12 and the locked environment:

```bash
uv sync --frozen --python python3.12
.venv/bin/python scripts/verify_delivery.py --out local-runs/delivery-check
```

This writes fresh results. It does not rerun inference or rewrite old receipts.
[Publication checks](../repository-publication/README.md) cover the selected Git
snapshot and companion documentation changes.
