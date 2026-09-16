# Internal prototype interfaces (1.0.0)

The library separates indexing/plans, execution/review, planning/providers,
recipes/corrections and evaluation. All modules live in this separate project.

## Common

`common`: C(value), sha(bytes), bound(domain,value) -> sha256-prefixed ID;
`ahif` pinned checker; `Failure(code,status='invalid_input')`; `safe_read(path,limit)`;
`load_json(path,limit=...)`; `write_json(path,value)`; `fresh(destination)` staging
context manager; `schema(name)` and `validate(name,value)` package schemas;
`DEFAULT_LIMITS` dict; `PROFILE` and `PROFILE_SHA` frozen extraction rules.
Sidecars use AHIF restricted JSON, no float values. Elapsed/cost values use decimal
strings or null. All source strings in exceptions must stay private/inert.

## Index

`index.build(capture:Path, metadata:dict|None=None, limits:dict|None=None) -> dict`
`index.by_ref(index)`, `index.descendants(index,ref,include_self=True) -> list[dict]`
`index.read_value(index, value_ref) -> str`; `index.select(index,scope,selector) -> list[str]`
`index.text_segments(index, root_ref, excluded:list[str]) -> list[dict]`.
`index.Inspector(index,limits=None).call(name,args) -> dict` and `.audit()`.

Index contains index_version, index_id, capture{sha256,byte_length,metadata,decoding},
parser, nodes, indicators. Nodes: ref, kind(document/element/text/comment), tag
(nullable), attrs list[{name,value}], text(nullable), parent(nullable), children,
order, depth, flags. Unique refs are bound to capture bytes/parser/index profile;
HTML id values are not unique keys. Attribute names are data, never JSON keys.
No raw file paths in canonical index. Metadata fully expanded by build includes
capture_kind(html_response/rendered_dom), source_url nullable, captured_at nullable,
provenance nullable, data_class(synthetic/public/private/unknown), access and
redistribution declarations; unknown defaults. Root processes decoding/parser.

ValueRef is {node:<ref>,kind:'text'|'attribute',attribute?:<name>,start?:int,end?:int}.
Text reads only actual text nodes. Slices require both start/end and half-open
Unicode code-point positions. No literal source value in a plan. Selectors are
restricted objects {tag?:str,attribute?:str,equals?:str,class_token?:str}; optional
match strings are selector predicates, not output values. select includes scope.

text_segments returns contiguous pieces separated at excluded subregions and
forbidden script/style/template/form-like/hidden subtrees. Each piece is
{text:str,mappings:[{output_start,output_end,source:{node,kind,attribute?,start,end}} |
 {output_start,output_end,insertion:{operation:'block_boundary'|'line_break'|'table_cell',node}}]}.
Do not join pieces across exclusion boundaries. Preserve parsed text codepoints;
block/line separators explicitly map to structural insertions. Leading/trailing
insertion-only separators can be suppressed; source whitespace never stripped.

## Finalized plan (plans.py owns schema)

Required: plan_version='1.0.0', capture_sha256, index_id,
profile='html-structural-text/1.0.0', ancestry:list[digest],
origin:{kind:'manual'|'model'|'recorded'|'mock'|'recipe'|'correction',producer:str},
review:{status:'unreviewed'|'agent_reviewed'|'human_reviewed'|'unresolved',reviewer:str|null},
contributions:list[Contribution], rejected:list[{node,reason}], unresolved:list[{node,reason}].
Reason enums provided in schema; no arbitrary persuasive model rationale.

Contribution required keys:
container:<element ref>, kind:'post'|'reply'|'quote_post'|'repost'|'review'|'article'|'unknown',
identity:null|{kind:'native'|'uri',source:ValueRef,basis:'documented_native'|'identity_link',evidence:[refs]},
author:null|{identity:null|{kind:'native'|'uri'|'handle',source:ValueRef,basis:'documented_native'|'identity_link'|'source_label'},label:ValueRef|null,evidence:[refs]},
created:ValueRef|null, updated:ValueRef|null,
parts:[{root:ref,role:AHIF role,attribution:'record_actor'|'other'|'unknown'|'system',exclude:[refs],evidence:[refs]}],
excluded:[{node:ref,reason:enum}],
relations:[{type:'reply_to'|'quotes'|'reposts',target:ValueRef|null,kind:'uri'|'native'|'unknown',evidence:[refs]}],
links:[{source:ValueRef,role:'inline'|'native_destination'|'attachment'|'profile'|'other'}],
state:null|{value:'removed'|'deleted'|'restricted',evidence:[refs]},
completeness:null|{value:'partial'|'truncated'|'redacted',evidence:[refs]},
evidence:[refs].
No complete/visible/not_edited assertion provided in this first extraction profile.
No arbitrary native namespace: host derives source origin or capture-local intake.
Native IDs require source URL plus documented_native evidence; DOM id alone is
not sufficient (host requires meaningful data-post-id/data-comment-id/data-review-id
or an explicit supported identity-link URI). Uncertain identity uses source_local.
Shared guest/deleted/anonymous author labels yield actor null.

`plans.validate_plan(index,plan) -> dict` raises Failure or returns the validated
plan without changing its values.
`plans.plan_id(plan)` -> bound ID. Index/schema/capture/cardinality/ownership checks
must run in every executor path. Nested contributions require explicit exclusion
from outer parts; duplicate/overlapping selected text source ranges rejected.
Metadata sources/evidence lie within contribution container. Part roots may
nest only if descendants are explicitly excluded from outer roots. An excluded
signature need not be emitted; emitted quote is separately attributed. References
are concrete, selectors appear only in recipes, not finalized plans.

## Executor

`executor.extract(capture, plan, destination, metadata=None, limits=None) -> dict`
`executor.execute_index(index,plan,destination,limits=None) -> dict` useful shared
entry for planner, must call same validate_plan. `executor.verify(capture,plan,run,
metadata=None,limits=None) -> dict` full re-execution compares canonical accepted
files, never trusts replaced receipts alone. `executor.review(run,destination)`
safe escaped HTML and correction template through review.py.
Canonical files: bundle manifest/records; evidence/index.json, finalized-plan.json,
source-map.jsonl, decisions.jsonl, interpretation.json; plus capture-manifest.json.
Receipts, clocks, discovery transcripts, validation logs and review HTML separate.
Metadata can be recovered from evidence/index.json for verify but must revalidate.
No need include raw capture inside bundle; descriptor binds external supplied bytes.
Return typed dict status/record counts/canonical digest. Capture source mode
synthetic only metadata.data_class synthetic; otherwise web_capture.
Use fidelity transformed for structural extraction, language und. Exact time parser
only timezone-qualified ISO seconds with supported UTC conversion or date-only;
relative/ambiguous/missing zone unknown. Fields and every part map to refs.

## Planner/provider

`planner.discover(capture, config:dict, destination, metadata=None,limits=None) -> dict`;
real Ollama `/api/chat` provider, recorded and mock distinctly marked; explicit
workstation or approved Runpod SSH-tunnel configuration. Model identity, endpoint,
data approval and finite budgets are supplied; no implicit default model. Official
Ollama docs were checked during implementation; live execution receipts are in qa/.
Use Inspector tools plus strict plan validation, execute accepted plan through
executor.execute_index. Save all attempts and safe requests/responses (no hidden
thinking). config explicit model/destination/data approval/scope and cumulative
calls/input/output/turn/tool/wall caps; no model ID default. Optional reviewer
inspect evidence before seeing plan and no persuasive rationale; max2 repairs.
Each provider output JSON is either tool action or proposal/review decision.
Never read gold/fixture filenames in discovery; recorded responses explicit test
inputs only. See provider.py, planner.py, runtime prompts, model configuration
schema, model tests and provider documentation.

## Evaluation (separate agent owns)

Agent owns evaluate.py, evaluation/dataset schemas, examples with3+fictional layout
families and independent construction-truth annotations, focused evaluation tests.
Coordinate plan generation against above concrete references (build indexes to
resolve manually authored fixture selection; don't put fixture lookup in planner).
`evaluate.evaluate(dataset_path,config_path,destination) -> dict`; pre-run manifest,
family/thread/lineage split leak rejection, all reference items in denominators,
fixed one-to-one container-ref matching, all metrics raw counts/null denominators,
actor/text/role/metadata grounding vs correctness separate. Document missingreal
captures/human annotations/liveaccess; synthetic evaluation nevercalledrealpilot.
Run model-free planned extraction initially; recorded arms distinctlymock only.
