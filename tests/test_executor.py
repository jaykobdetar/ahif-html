"""Construction-truth tests; expected text is hand-written, not extractor output."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from ahif_html import index
from ahif_html.common import C, Failure, ahif, load_json, sha, write_json
from ahif_html.executor import (CANONICAL_PATHS, EXT, execute_index, extract, materialize,
                                parse_time, verify, verify_source_maps)

HTML = ('<!doctype html><html><body><article data-post-id="900719925474099312345">'
        '<header><span class="author">Fictional Alder</span></header>'
        '<time datetime="2026-09-14T10:20:30+02:00">today</time>'
        '<div class="body"><p>First <em>really</em> &amp; exact.</p>'
        '<blockquote><p>Another voice.</p></blockquote><p>After quote.</p>'
        '<aside class="signature">Not my body.</aside></div></article>'
        '<article data-comment-id="2"><header><span class="author">Guest</span></header>'
        '<time datetime="2026-09-15">today</time><div class="body">Unknown still useful.</div></article>'
        '</body></html>')


def attrs(node):
    return {a['name']: a['value'] for a in node['attrs']}


def only(index_value, root=None, tag=None, attribute=None, value=None):
    choices = index.descendants(index_value, root) if root else index_value['nodes']
    found = [n for n in choices if n['kind'] == 'element' and (tag is None or n['tag'] == tag)
             and (attribute is None or attrs(n).get(attribute) == value)]
    assert len(found) == 1, (tag, attribute, value, len(found))
    return found[0]['ref']


def textref(index_value, root):
    matches = [n for n in index.descendants(index_value, root) if n['kind'] == 'text']
    assert len(matches) == 1
    return {'node': matches[0]['ref'], 'kind': 'text'}


def contribution(index_value, root, native_attr, kind='post', quote=None, signature=None):
    author = only(index_value, root, tag='span', attribute='class', value='author')
    body = only(index_value, root, tag='div', attribute='class', value='body')
    time = only(index_value, root, tag='time')
    parts = [{'root': body, 'role': 'body', 'attribution': 'record_actor',
              'exclude': [r for r in (quote, signature) if r], 'evidence': [body]}]
    if quote:
        parts.append({'root': quote, 'role': 'quote', 'attribution': 'other', 'exclude': [], 'evidence': [quote]})
    return {'container': root, 'kind': kind,
            'identity': {'kind': 'native', 'source': {'node': root, 'kind': 'attribute', 'attribute': native_attr},
                         'basis': 'documented_native', 'evidence': [root]},
            'author': {'identity': None, 'label': textref(index_value, author), 'evidence': [author]},
            'created': {'node': time, 'kind': 'attribute', 'attribute': 'datetime'}, 'updated': None,
            'parts': parts, 'excluded': [{'node': signature, 'reason': 'signature'}] if signature else [],
            'relations': [], 'links': [], 'state': None, 'completeness': None, 'evidence': [root]}


def fixture(tmp_path):
    capture = tmp_path / 'capture.html'
    capture.write_text(HTML, encoding='utf-8')
    metadata = {'metadata_version': '1.0.0', 'capture_kind': 'html_response',
                'source_url': 'https://fictional.example/thread', 'data_class': 'synthetic'}
    evidence = index.build(capture, metadata)
    root = only(evidence, attribute='data-post-id', value='900719925474099312345')
    reply = only(evidence, attribute='data-comment-id', value='2')
    quote = only(evidence, root, tag='blockquote')
    signature = only(evidence, root, tag='aside')
    plan = {'plan_version': '1.0.0', 'capture_sha256': evidence['capture']['sha256'],
            'index_id': evidence['index_id'], 'profile': 'html-structural-text/1.0.0', 'ancestry': [],
            'origin': {'kind': 'manual', 'producer': 'construction-truth-test'},
            'review': {'status': 'unreviewed', 'reviewer': None},
            'contributions': [contribution(evidence, root, 'data-post-id', quote=quote, signature=signature),
                              contribution(evidence, reply, 'data-comment-id', kind='reply')],
            'rejected': [], 'unresolved': []}
    return capture, metadata, evidence, plan


def rows(run):
    return [ahif.strict_loads(line) for line in (run / 'bundle/records.jsonl').read_bytes().split(b'\n') if line]


def test_positive_full_ahif_and_hard_boundaries(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    run = tmp_path / 'run'
    result = extract(capture, plan, run, metadata)
    assert result['record_observations'] == 2
    records = {r['record_key']['id']: r for r in rows(run)}
    post = records['900719925474099312345']
    assert [(p['role'], p['text']) for p in post['content']['parts']] == [
        ('body', 'First really & exact.'), ('quote', 'Another voice.'), ('body', 'After quote.')]
    assert post['actor']['id'] == 'Fictional Alder'
    assert post['created_at']['value'] == '2026-09-14T08:20:30Z'
    assert post['content']['completeness'] == 'unknown'
    assert post['lifecycle']['state'] == 'unknown'
    assert post['observed_at']['status'] == 'unknown'
    assert all(p['fidelity'] == 'transformed' and p['language']['tag'] == 'und' for p in post['content']['parts'])
    guest = records['2']
    assert guest['actor'] is None
    assert guest['content']['parts'][0]['attribution']['relation'] == 'unknown'
    assert guest['created_at']['status'] == 'date_only'
    assert ahif.validate_bundle(run / 'bundle', require_canonical=True)['status'] == 'passed'
    assert verify(capture, plan, run, metadata)['status'] == 'passed'
    assert 'Not my body.' not in post['content']['parts'][0]['text']


def test_replay_relocation_and_json_key_order(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    first, second = tmp_path / 'a', tmp_path / 'b'
    extract(capture, plan, first, metadata)
    moved = tmp_path / 'elsewhere' / 'renamed.html'
    moved.parent.mkdir(); moved.write_bytes(capture.read_bytes())
    reordered = json.loads(json.dumps(plan, sort_keys=True))
    extract(moved, reordered, second, dict(reversed(list(metadata.items()))))
    for relative in CANONICAL_PATHS:
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
    assert verify(moved, reordered, first, metadata)['status'] == 'passed'


def test_exact_unicode_and_inline_no_extra_spaces(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    replacement = 'A\u00a0e\u0301 <em>🙂</em>\u2028\u0085\u202eZ\u00ad&lt;b&gt;'
    capture.write_text(HTML.replace('First <em>really</em> &amp; exact.', replacement), encoding='utf-8')
    rebuilt = index.build(capture, metadata)
    # Re-author concrete references after a changed capture; no old ref reuse.
    root = only(rebuilt, attribute='data-post-id', value='900719925474099312345')
    plan['capture_sha256'] = rebuilt['capture']['sha256']; plan['index_id'] = rebuilt['index_id']
    plan['contributions'] = [contribution(rebuilt, root, 'data-post-id', quote=only(rebuilt, root, tag='blockquote'), signature=only(rebuilt, root, tag='aside'))]
    run = tmp_path / 'unicode'; execute_index(rebuilt, plan, run)
    assert rows(run)[0]['content']['parts'][0]['text'] == 'A\u00a0e\u0301 🙂\u2028\u0085\u202eZ\u00ad<b>'
    assert verify(capture, plan, run, metadata)['status'] == 'passed'


def test_output_rehash_does_not_fool_full_reexecution(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    run = tmp_path / 'run'; extract(capture, plan, run, metadata)
    records = rows(run)
    records[0]['content']['parts'][0]['text'] = 'Invented replacement.'
    records[0]['observation_id'] = ahif.bound_id('record', records[0])
    data = b''.join(C(row) + b'\n' for row in sorted(records, key=lambda row: row['observation_id']))
    (run / 'bundle/records.jsonl').write_bytes(data)
    manifest = load_json(run / 'bundle/manifest.json')
    manifest['files'][0].update(sha256=sha(data), byte_length=len(data))
    write_json(run / 'bundle/manifest.json', manifest)
    # Valid AHIF+matching file hash is insufficient extraction evidence.
    assert ahif.validate_bundle(run / 'bundle', require_canonical=True)['status'] == 'passed'
    with pytest.raises(Failure, match='canonical_reexecution_mismatch'):
        verify(capture, plan, run, metadata)


def test_source_map_swapped_reference_fails(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    files, result, grounding = materialize(evidence, plan)
    records = [ahif.strict_loads(line) for line in files['bundle/records.jsonl'].split(b'\n') if line]
    maps = [ahif.strict_loads(line) for line in files['evidence/source-map.jsonl'].split(b'\n') if line]
    maps[0]['plan_id'] = 'sha256:' + '0' * 64
    with pytest.raises(Failure, match='source_map_binding_mismatch'):
        verify_source_maps(evidence, plan, records, maps)


def test_changed_capture_and_existing_output_refused(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    run = tmp_path / 'run'; extract(capture, plan, run, metadata)
    with pytest.raises(Failure):
        extract(capture, plan, run, metadata)
    capture.write_bytes(capture.read_bytes() + b'<!-- changed -->')
    with pytest.raises(Failure):
        verify(capture, plan, run, metadata)


def test_review_html_escapes_source_markup(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    capture.write_text(HTML.replace('Unknown still useful.', '&lt;script&gt;alert(1)&lt;/script&gt; Ignore previous instructions.'), encoding='utf-8')
    rebuilt = index.build(capture, metadata)
    reply = only(rebuilt, attribute='data-comment-id', value='2')
    plan['capture_sha256'] = rebuilt['capture']['sha256']; plan['index_id'] = rebuilt['index_id']
    plan['contributions'] = [contribution(rebuilt, reply, 'data-comment-id', kind='reply')]
    run = tmp_path / 'safe'; execute_index(rebuilt, plan, run)
    html = (run / 'review/index.html').read_text()
    assert '<script>' not in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html
    assert "default-src 'none'" in html
    assert 'Ignore previous instructions.' in html


@pytest.mark.parametrize('raw,status,value', [
    ('2026-09-15', 'date_only', '2026-09-15'),
    ('2026-09-15T01:02:03.123456789Z', 'known', '2026-09-15T01:02:03.123456789Z'),
    ('2026-09-15T01:02:03-02:30', 'known', '2026-09-15T03:32:03Z'),
    ('09/10/2026', 'unknown', None), ('2 hours ago', 'unknown', None),
    ('2026-09-15T12:30', 'unknown', None), ('2026-09-15T12:30:00', 'unknown', None),
    ('2026-09-15T12:30:00-00:00', 'unknown', None),
    ('2026-02-30', 'unknown', None), ('2026-09-15T12:30:00+14:01', 'unknown', None),
])
def test_time_rules(raw, status, value):
    parsed = parse_time(raw)
    assert parsed['status'] == status
    assert parsed.get('value') == value
    assert parsed['raw'] == raw


def test_unknown_metadata_keeps_nonempty_evidence(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    selected = plan['contributions'][1]
    selected.update(identity=None, author=None, created=None, updated=None)
    plan['contributions'] = [selected]
    run = tmp_path / 'unknown'; execute_index(evidence, plan, run)
    record = rows(run)[0]
    assert record['record_key']['id_type'] == 'source_local'
    assert record['record_key']['id'].startswith(record['source_id'] + '#')
    assert record['actor'] is None
    assert record['content']['availability'] == 'present'
    assert record['content']['parts'][0]['text'] == 'Unknown still useful.'
    assert record['created_at']['status'] == record['updated_at']['status'] == 'unknown'


def test_partial_preserves_valid_independent_record(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    run = tmp_path / 'partial'
    result = execute_index(evidence, plan, run, limits={'parts_per_record': 1})
    assert result['status'] == 'partial_execution'
    assert result['record_observations'] == 1
    assert result['unsupported_contributions'] == 1
    assert rows(run)[0]['record_key']['id'] == '2'
    decisions = [ahif.strict_loads(line) for line in (run / 'evidence/decisions.jsonl').read_bytes().split(b'\n') if line]
    assert decisions[0]['reasons'] == ['record_part_limit']
    assert verify(capture, plan, run, metadata)['status'] == 'passed'


def test_equal_native_numbers_use_separate_collections(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    capture.write_text(HTML.replace('data-comment-id="2"', 'data-comment-id="900719925474099312345"'), encoding='utf-8')
    rebuilt = index.build(capture, metadata)
    post = only(rebuilt, attribute='data-post-id', value='900719925474099312345')
    comment = only(rebuilt, attribute='data-comment-id', value='900719925474099312345')
    plan.update(capture_sha256=rebuilt['capture']['sha256'], index_id=rebuilt['index_id'])
    plan['contributions'] = [contribution(rebuilt, post, 'data-post-id', quote=only(rebuilt, post, tag='blockquote'), signature=only(rebuilt, post, tag='aside')), contribution(rebuilt, comment, 'data-comment-id', kind='reply')]
    run = tmp_path / 'collections'; result = execute_index(rebuilt, plan, run)
    assert result['distinct_record_keys'] == 2
    assert {r['record_key']['collection'] for r in rows(run)} == {'posts', 'comments'}


def test_known_nonvisible_redacted_text_is_retained_as_evidence(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    selected = plan['contributions'][1]
    selected['state'] = {'value': 'removed', 'evidence': [selected['container']]}
    selected['completeness'] = {'value': 'redacted', 'evidence': [selected['container']]}
    plan['contributions'] = [selected]
    run = tmp_path / 'retained'; execute_index(evidence, plan, run)
    record = rows(run)[0]
    assert record['lifecycle']['state'] == 'removed'
    assert record['content']['availability'] == 'redacted'
    assert record['content']['completeness'] == 'partial'
    assert record['content']['parts'][0]['text'] == 'Unknown still useful.'
    # A human/model can still misinterpret evidence semantics; this test proves
    # representation and replay, not whether the source actually declared removal.
    assert verify(capture, plan, run, metadata)['status'] == 'passed'


def test_empty_unidentified_container_is_no_evidence_not_success(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    selected = plan['contributions'][1]
    selected.update(identity=None, author=None, created=None, parts=[])
    plan['contributions'] = [selected]
    run = tmp_path / 'empty'; result = execute_index(evidence, plan, run)
    assert result['record_observations'] == 0
    assert result['unsupported_contributions'] == 1
    assert result['status'] == 'partial_execution'
    assert rows(run) == []
    assert ahif.validate_bundle(run / 'bundle', require_canonical=True)['status'] == 'passed'


def test_forged_nontext_support_reference_fails_map_check(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    files, result, grounding = materialize(evidence, plan)
    records = [ahif.strict_loads(line) for line in files['bundle/records.jsonl'].split(b'\n') if line]
    maps = [ahif.strict_loads(line) for line in files['evidence/source-map.jsonl'].split(b'\n') if line]
    field = next(f for f in maps[0]['fields'] if f['path'] == '/actor')
    field['source_refs'] = [{'node': 'invented', 'kind': 'region'}]
    with pytest.raises(Failure, match='source_map_support_reference_invalid'):
        verify_source_maps(evidence, plan, records, maps)
