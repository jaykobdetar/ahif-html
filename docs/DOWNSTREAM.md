# AHAS compatibility assessment — no HTML projection implemented

Inspected production `src/account_history_analyzer/contracts/record.schema.json`
and `snapshot.schema.json` at AHAS commit
`070213f0520d01529556e4aa7f4fa9270c22c6aa`. They require schema version 1.0.0,
one selected account, `comment|submission`, a scalar text field, and different
status/time semantics. AHIF 0.1.1 JSONL does **not** work as direct AHAS input.
The existing `reddit-export-observation` profile remains limited to its declared
Reddit CSV source; relabeling this extractor's output would violate that contract.

## Future narrow projection contract (proposal, not code)

| AHAS field | Possible source | Required loss/refusal rule |
|---|---|---|
| `schema_version` | Fixed `1.0.0` | Only after a new projection validates the existing production schemas. |
| `id` | All four AHIF record-key components | Deterministic collision-safe encoding ≤256; keep external key/observation map. Never text deduplication; select observations explicitly and preserve conflicts. |
| `account_id` | Explicitly selected actor key and source scope | Unknown actor cannot enter an account-specific stream. Handle continuity needs separate evidence; no automatic cross-capture grouping. |
| `kind` | Reviewed event semantics | Only a supported post/reply mapping to submission/comment. Refuse generic review/article/repost coercion until separately specified. |
| `text` | Ordered actor-attributed body parts | Single supported contiguous body can map exactly. **Refuse body/quote/body flattening** until a tested boundary-preserving representation is specified. Do not split one event into invented events or concatenate records to satisfy sample guards. |
| `title` | Distinct title part | Submission only, ≤20,000 code points. Do not prepend to body. Multiple/ambiguous titles require a loss declaration or refusal. |
| `status` | Evidence lifecycle plus availability | AHAS `present` requires string text; deleted/removed/unavailable require null. Retained prose with unknown/removed lifecycle has no automatic faithful scalar mapping. Require an explicit observation policy; no hidden erasure or invented visibility. |
| `created_utc`, `edited_utc` | Known zoned times | Date-only/uncertain/relative → null with sidecar evidence. Nanosecond precision cannot silently truncate to six digits; require explicit loss or refusal. No capture/mtime substitution. |
| `edit_state` | Documented edit observation | Unknown stays unknown. A timestamp only maps when the source establishes editing; do not infer never-edited from its absence. |
| `language` | Supported contribution language declaration | `und`/null with retained basis; no English claim from UI language or model impression. English/sample guards remain normal downstream limitations. |
| `subreddit` | Actual supported Reddit community | Forum sections/review sites never become subreddits; null elsewhere. |
| `parent_id`, `thread_id`, `parent_created_utc` | Grounded relation/context/parent time | Unknown or absent targets remain null; no parent record/time invention or visual-adjacency inference. Preserve scoped mapping externally. |
| `permalink` | Supported native contribution link | Bound length and preserve original/resolution evidence; no redirects or safety/ownership verification claim. |
| Snapshot source/coverage | Supplier declarations and selected scope | `synthetic` only for constructed inputs; otherwise appropriate supplied category. Coverage unknown, no calculated completeness from page traversal or source totals. |
| `text_format`, `default_language` | New projection rules | Declare exact representation; do not label DOM-derived structure original Markdown. No invented default English. |
| `license_notes` | Explicit source/supplier declarations | Unknown/null if absent. Capture availability is not consent or a dataset license. |

AHAS does not carry all roles, field uncertainty, source maps, raw values or
observation conflicts. Any future projection must retain these in a linked loss
ledger outside its input schema and refuse unsupported cases explicitly.

A downstream demonstration is deferred because this delivery intentionally retains
`body / quote / body`, unknown lifecycle and unknown language. No faithful generic
flattening was established; no engine, settings, old profile or study was changed.
Next: choose a narrow eligible source-account scope, define its boundary-preserving
projection and independently prepare equivalent AHAS input; compare extraction
counts/features under unchanged numerical settings before scientific use.
