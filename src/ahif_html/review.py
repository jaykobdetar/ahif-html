"""Static, escaped evidence review. Captured HTML is never embedded as markup."""
from __future__ import annotations
from html import escape
from pathlib import Path

from .common import C, Failure, check_path, fresh, load_json, safe_read, sha, write_json, ahif


def _jsonl(path):
    raw = safe_read(path, 64 * 1024 * 1024)
    return [ahif.strict_loads(line) for line in raw.split(b'\n') if line]


def _text(value):
    return escape(value if isinstance(value, str) else C(value).decode('utf-8'), quote=True)


def write_review(run, destination):
    """Internal writer to an absent review subdirectory, called after AHIF checks."""
    run = check_path(run)
    destination = check_path(destination)
    if destination.exists():
        raise Failure('review_output_must_be_fresh')
    receipt = load_json(run / 'run-receipt.json')
    plan = load_json(run / 'evidence/finalized-plan.json')
    index = load_json(run / 'evidence/index.json', 64 * 1024 * 1024)
    interpretation = load_json(run / 'evidence/interpretation.json', 64 * 1024 * 1024)
    records = _jsonl(run / 'bundle/records.jsonl')
    decisions = _jsonl(run / 'evidence/decisions.jsonl')
    nodes = {node['ref']: node for node in index['nodes']}
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'; frame-src \'none\'">',
           '<meta name="referrer" content="no-referrer"><title>AHIF HTML evidence review</title>',
           '<style>body{max-width:80rem;margin:2rem auto;padding:1rem;font:16px system-ui;line-height:1.5}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f4f4;padding:1rem}article{border:1px solid #999;margin:1rem 0;padding:1rem}dt{font-weight:bold}code{overflow-wrap:anywhere}.warning{border:2px solid #a70;padding:1rem}summary{cursor:pointer}blockquote{border-left:4px solid #999;padding-left:1rem}</style></head><body>',
           '<h1>AHIF HTML evidence review</h1>',
           '<p class="warning">Escaped structural evidence, not the original visual page. No source scripts, assets, links or forms run here. Source-map replay is authoritative for extraction integrity; it does not establish authorship or complete discovery.</p>',
           '<dl><dt>Execution status</dt><dd>' + _text(receipt['status']) + '</dd>',
           '<dt>Review declaration</dt><dd>' + _text(plan['review']) + '</dd>',
           '<dt>Capture / plan</dt><dd>' + _text(index['capture']['sha256']) + '<br>' + _text(receipt['plan_id']) + '</dd>',
           '<dt>Observed capture indicators</dt><dd>' + _text(index['indicators']) + '</dd></dl>',
           '<h2>Emitted observations</h2>']
    for record in records:
        extension = record['extensions']['org.ahif-html:extraction']
        out.extend(['<article><h3>' + _text(record['kind']) + ': ' + _text(record['record_key']['id']) + '</h3>',
                    '<dl><dt>Selected actor</dt><dd>' + _text(record['actor']) + '</dd>',
                    '<dt>Source author label</dt><dd>' + _text(extension['author_label']) + '</dd>',
                    '<dt>Creation time</dt><dd>' + _text(record['created_at']) + '</dd>',
                    '<dt>Update time</dt><dd>' + _text(record['updated_at']) + '</dd>',
                    '<dt>Lifecycle / content uncertainty</dt><dd>' + _text(record['lifecycle']) + '; ' + _text({k:v for k,v in record['content'].items() if k!='parts'}) + '</dd>',
                    '<dt>Container reference</dt><dd>' + _text(extension['container']) + '</dd>',
                    '<dt>Observation</dt><dd>' + _text(record['observation_id']) + '</dd></dl>'])
        for part in record['content']['parts']:
            out.extend(['<h4>' + _text(part['part_id']) + ' · ' + _text(part['role']) + ' · ' + _text(part['attribution']['relation']) + '</h4>',
                        '<pre>' + _text(part['text']) + '</pre><p>Source: <code>' + _text(part['locator']['value']) + '</code></p>'])
        planned = next(c for c in plan['contributions'] if c['container'] == extension['container'])
        out.extend(['<h4>Excluded regions</h4><pre>' + _text(planned['excluded']) + '</pre>',
                    '<h4>Relationships and inert destinations</h4><pre>' + _text({'relations': record['relations'], 'links': record['links']}) + '</pre></article>'])
    out.extend(['<h2>All planned contribution outcomes</h2><pre>' + _text(decisions) + '</pre>',
                '<h2>Rejected and unresolved regions</h2><pre>' + _text({'rejected': plan['rejected'], 'unresolved': plan['unresolved']}) + '</pre>',
                '<h2>Index regions not explicitly classified</h2>',
                '<p>These include ordinary child nodes and page furniture. They are exposed for review, not declared missed contributions. A successful DOM traversal does not establish contribution recall.</p>'])
    unclassified = interpretation['region_accounting']['not_explicitly_classified_nodes']
    for ref in unclassified:
        node = nodes[ref]
        if node['kind'] not in ('element', 'text'):
            continue
        preview = node.get('text') or ''
        out.append('<details><summary>' + _text(ref) + ' · ' + _text(node['kind']) + ' ' + _text(node.get('tag')) + '</summary><pre>' + _text({'text': preview[:2000], 'preview_truncated': len(preview) > 2000, 'attributes': node.get('attrs', []), 'parent': node.get('parent'), 'flags': node.get('flags', [])}) + '</pre></details>')
    out.append('<h2>Corrections</h2><p>Edit the companion correction-template.json using source references. No replacement wording is accepted. Agent-created changes are not human approval. Re-run the correct command to validate and regenerate traceable observations.</p></body></html>')
    data = '\n'.join(out).encode('utf-8')
    if len(data) > receipt['limits']['output_bytes']:
        raise Failure('review_output_byte_limit', 'resource_limit')
    destination.mkdir(mode=0o700, parents=True)
    (destination / 'index.html').write_bytes(data)
    template = {'correction_version': '1.0.0', 'base_plan_id': receipt['plan_id'],
                'reviewer': {'kind': 'agent', 'name': 'REPLACE_WITH_ACTUAL_REVIEWER'}, 'edits': []}
    write_json(destination / 'correction-template.json', template)
    result = {'review_version': '1.0.0', 'status': 'generated', 'plan_id': receipt['plan_id'],
              'html_sha256': sha(data), 'record_observations': len(records),
              'not_explicitly_classified_nodes': len(unclassified), 'source_content_execution': 'none'}
    write_json(destination / 'review-receipt.json', result)
    return result


def review(run, destination):
    with fresh(destination) as stage:
        result = write_review(run, stage / 'content')
        for child in (stage / 'content').iterdir():
            child.rename(stage / child.name)
        (stage / 'content').rmdir()
    return result
