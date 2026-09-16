# html-structural-text/1.0.0

**Fidelity is `transformed`, not `source_field`.** This policy preserves parsed
text-node Unicode code points and order; it does not promise browser visual text
or original lexical HTML. The input bytes remain a separate authoritative layer.

## Decode and parse

Explicit UTF-8/UTF-16/Windows-1252/ISO-8859-1 declarations are supported. A compatible
UTF BOM takes precedence and is recorded; otherwise UTF-8 strict is the default.
No charset guessing or parser retry occurs. `decode_errors: replace` is an explicit
supplier-selected mode, separately recorded, and never claims exact character
recovery. HTML charset markup is not an automatic decoding instruction.

html5lib 1.1 DOM tree builder runs once with scripting disabled. HTML parsing may
repair malformed markup, create nodes (e.g. tbody), decode entities and normalize
HTML line endings. The repair count and parser configuration are recorded. Node
refs bind capture hash + parser/index version + deterministic preorder ordinal.
No raw byte spans are claimed. Unsupported surrogate/restricted-JSON strings fail.

## Text assembly

- Text nodes retain spaces, tabs, NBSP, combining marks, emoji, U+2028, U+0085,
  bidi controls and soft hyphens. No NFC, case folding, punctuation fixes,
  translation, summarization or visual whitespace collapse is applied.
- Inline formatting contributes its child text with no added space.
- Paragraphs, headings, divisions, lists/list items, blockquotes, preformatted
  blocks, table rows and other documented block tags insert structural newlines.
  Adjacent structural block separators coalesce; captured whitespace does not.
- `br` inserts a newline. Subsequent cells in a table row insert tabs; the first
  cell does not. `pre` source indentation/newlines remain unchanged after HTML
  parser preprocessing.
- Leading/trailing *inserted* separators are removed; source whitespace is retained.
- Excluded quote/signature/code/reply regions and forbidden/hidden subtrees create
  hard part boundaries. Body text on both sides is emitted as separate parts.
  Separate quote/code selections can preserve their own roles and attribution.
  Plans that include structurally known blockquote/pre/code regions in body/title
  without excluding those subtrees are refused. Inline code also needs an explicit
  separate role/exclusion under this conservative profile.
- Script/style/template/noscript, frame/embed/object and form-like subtrees are
  excluded. `hidden` and `aria-hidden=true` subtrees are excluded by this declared
  policy, not asserted visually absent. CSS-dependent visibility is unknown.
- Comments are indexed but not body text or model evidence. `alt`, accessibility
  names, CSS content and screenshots do not manufacture authored words. Attribute
  text-part extraction is not supported yet. Links retain destination and display
  text separately; URL resolution uses only the supplied HTTP(S) source base.

## Source maps

Coordinates are zero-based, half-open Unicode code-point ranges in immutable
parsed text nodes or attributes. Output ranges are likewise Unicode code points.
Every output character maps either to a source range or to a named structural
insertion (`block_boundary`, `line_break`, `table_cell`) with an element ref.
Entity decoding and parser repair precede this coordinate space; these are not
raw-byte positions. Verification checks contiguous output coverage, reads the
source ranges, and re-executes the corresponding selection. Equal wording found
elsewhere cannot substitute for the selected source location.

Inline quotation without structural evidence remains semantically unresolved.
Structural grounding alone does not prove that an author header belongs to a body.
