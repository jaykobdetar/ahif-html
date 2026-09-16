# Fictional discovery evaluation, construction revision 1

Eight synthetic pages contain 26 independently enumerated contribution appearances:
20 have source-linked account headers and six have unknown authors. Four DOM families
have two related pages each. No page is a real capture, and no annotation is human-
reviewed. The authoring agent wrote both fictional sources and construction truth.

| Family | DOM structure | Pages | Reference appearances | Model-evaluation split |
|---|---|---:|---:|---|
| Cards | Section headers, separate prose, nested reply | 2 | 8 | development |
| Feed | Ordered list, post/repost/quote commentary | 2 | 6 | development |
| Table | Row containers with header author cells | 2 | 6 | reserved synthetic family |
| Catalogue | Definition lists with labeled fields | 2 | 6 | reserved synthetic family |

Related pages remain in the same family/thread/lineage group. Existing scored
fixtures remain development/regression evidence. Table/catalogue cases have not
been used for live discovery or prompt tuning before the registered run. Their
manual executor checks do not make them independently authored holdouts. The agent
can see the full corpus; the inference worker receives only the source capture,
metadata, configured prompts and bounded evidence tools.

`build_fixtures.py` is an examples-only authoring helper. It resolves opaque `id`
anchors into concrete index references for explicit manual plans. It does not call
the planner or executor to obtain expected wording. Native `data-post-id`,
`data-comment-id` and `data-review-id` fields are deliberately supported fictional
source declarations; arbitrary DOM `id` values never become native event identity.
The code is not imported by production discovery.

The gold inventory names exact container references. A plausible broader/narrower
container still fails that fixed matching rule; no alternatives are registered.
Do not add alternatives after seeing outcomes. Reposts retain quoted original
material without treating it as the reposting account's own words. Two identical
sentences at different table-post IDs remain separate events. Unknown parents do
not require fabricated parent records.

## Model-free positive checks

```sh
.venv/bin/ahif-html evaluate --dataset examples/discovery-v2/dataset.json --config examples/discovery-v2/evaluation-config.json --out local-runs/discovery-v2-manual
.venv/bin/python -m pytest tests/test_discovery_v2.py -q
```

`qa/discovery-v2-construction-02/evaluation.json` is an actual manual-plan execution:
26/26 exact ordered parts and correct known-or-unknown attribution; all metadata
comparisons and full re-executions passed. Two pages retain incomplete-capture
indicators. These results establish executable construction expectations, not model
accuracy. The first preflight used an invalid `day` precision annotation; it was
corrected to AHIF's `date_only` status with null separate precision before the
retained run. Source wording and expected text were not changed to fit the executor.
