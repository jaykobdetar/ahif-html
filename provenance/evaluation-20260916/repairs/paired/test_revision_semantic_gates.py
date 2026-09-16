"""Reconstructed probes for user-described HTML-REV-001/002, not lost reviewer tests.

Expected source wording and omission outcomes are construction truth. No model or
network is used; the mock route is explicitly recorded test discovery.
"""
import json

import pytest

from ahif_html import index
from ahif_html.common import C, Failure, PROFILE_SHA, ahif, load_json, write_json
from ahif_html.executor import extract, verify
from ahif_html.plans import plan_id, validate_plan


META = {'data_class': 'synthetic', 'source_url': 'https://fictional.example/thread'}


def setup(tmp_path, html):
    capture = tmp_path / 'fictional.html'
    capture.write_text('<!doctype html>' + html, encoding='utf8')
    evidence = index.build(capture, META)
    return capture, evidence


def element(evidence, label):
    matches = [n for n in evidence['nodes'] if index.attrs(n).get('id') == label]
    assert len(matches) == 1
    return matches[0]['ref']


def text_node(evidence, root):
    choices = [n for n in index.descendants(evidence, root) if n['kind'] == 'text']
    assert len(choices) == 1
    return choices[0]['ref']


def part(root, role='body'):
    return {'root': root, 'role': role, 'attribution': 'unknown',
            'exclude': [], 'evidence': [root]}


def contribution(root, parts=()):
    return {'container': root, 'kind': 'post', 'identity': None, 'author': None,
            'created': None, 'updated': None, 'parts': list(parts), 'excluded': [],
            'relations': [], 'links': [], 'state': None, 'completeness': None,
            'evidence': [root]}


def plan_for(evidence, contributions):
    return {'plan_version': '1.0.0', 'capture_sha256': evidence['capture']['sha256'],
            'index_id': evidence['index_id'], 'profile': 'html-structural-text/1.0.0',
            'ancestry': [], 'origin': {'kind': 'manual', 'producer': 'reconstructed-revision-probe'},
            'review': {'status': 'unreviewed', 'reviewer': None},
            'contributions': contributions, 'rejected': [], 'unresolved': []}


def run_serialized(tmp_path, capture, plan, metadata=META):
    plan_path = tmp_path / 'attempted-plan.json'
    write_json(plan_path, plan)
    run = tmp_path / 'run'
    result = extract(capture, plan_path, run, metadata)
    checks = verify(capture, plan_path, run, metadata)
    assert checks['status'] == 'passed'
    assert checks['canonical_files_compared'] == 8
    assert ahif.validate_bundle(run / 'bundle', require_canonical=True)['status'] == 'passed'
    assert load_json(run / 'verification/extraction-check.json')['status'] == 'passed'
    records = [json.loads(line) for line in (run / 'bundle/records.jsonl').read_text().splitlines()]
    return result, records, run


@pytest.mark.parametrize('tag', ['blockquote', 'pre', 'code'])
@pytest.mark.parametrize('role', ['body', 'title'])
@pytest.mark.parametrize('selection', ['element', 'text'])
@pytest.mark.parametrize('depth', [0, 3])
def test_protected_ancestor_cannot_be_relabeled_as_body_or_title(tmp_path, tag, role, selection, depth):
    content = '<span id="selected">Fictional quoted wording.</span>'
    for _ in range(depth):
        content = '<span>' + content + '</span>'
    capture, evidence = setup(tmp_path, '<article id="outer"><' + tag + '>' + content + '</' + tag + '></article>')
    root, chosen = element(evidence, 'outer'), element(evidence, 'selected')
    if selection == 'text':
        chosen = text_node(evidence, chosen)
    plan = plan_for(evidence, [contribution(root, [part(chosen, role)])])
    write_json(tmp_path / 'attempted-plan.json', plan)
    with pytest.raises(Failure, match='structural_quote_or_code_ancestor_forbids_body_title'):
        extract(capture, tmp_path / 'attempted-plan.json', tmp_path / 'must-not-exist', META)
    assert not (tmp_path / 'must-not-exist').exists()
    assert load_json(tmp_path / 'attempted-plan.json') == plan


@pytest.mark.parametrize('tag', ['blockquote', 'pre', 'code'])
def test_moving_contribution_container_inside_protected_region_does_not_bypass_gate(tmp_path, tag):
    capture, evidence = setup(tmp_path, '<' + tag + '><section id="inner"><span id="selected">Nested quotation.</span></section></' + tag + '>')
    plan = plan_for(evidence, [contribution(element(evidence, 'inner'), [part(element(evidence, 'selected'))])])
    with pytest.raises(Failure, match='structural_quote_or_code_ancestor_forbids_body_title'):
        validate_plan(evidence, plan)


@pytest.mark.parametrize('origin', ['manual', 'model', 'mock', 'recorded', 'recipe', 'correction'])
def test_plan_origin_never_bypasses_semantic_gate(tmp_path, origin):
    _, evidence = setup(tmp_path, '<article id="outer"><blockquote><span id="selected">Quote.</span></blockquote></article>')
    plan = plan_for(evidence, [contribution(element(evidence, 'outer'), [part(element(evidence, 'selected'))])])
    plan['origin']['kind'] = origin
    with pytest.raises(Failure, match='structural_quote_or_code_ancestor_forbids_body_title'):
        validate_plan(evidence, plan)


def test_quote_is_not_the_grounded_header_actors_own_body(tmp_path):
    capture, evidence = setup(tmp_path, '<article id="outer"><header><span id="author">Fictional Delta</span></header>'
                              '<blockquote><span id="selected">Another persons wording.</span></blockquote></article>')
    root, chosen, author = [element(evidence, name) for name in ('outer', 'selected', 'author')]
    selected = contribution(root, [part(chosen)])
    selected['parts'][0]['attribution'] = 'record_actor'
    selected['author'] = {'identity': None, 'label': {'node': text_node(evidence, author), 'kind': 'text'}, 'evidence': [author]}
    with pytest.raises(Failure, match='structural_quote_or_code_ancestor_forbids_body_title'):
        extract(capture, plan_for(evidence, [selected]), tmp_path / 'must-not-exist', META)


def test_valid_body_quote_code_body_and_nested_reply_replay(tmp_path):
    capture, evidence = setup(tmp_path, '<article id="outer"><div id="body"><p>Before.</p>'
                              '<blockquote id="quote"><span>Quoted voice.</span></blockquote>'
                              '<pre id="code"><code>literal()</code></pre><p>After.</p>'
                              '<article id="reply"><p id="reply-body">Separate reply.</p></article>'
                              '</div></article>')
    quote, code, reply = [element(evidence, x) for x in ('quote', 'code', 'reply')]
    body = part(element(evidence, 'body'))
    body['exclude'] = [quote, code, reply]
    quote_part = part(quote, 'quote'); quote_part['attribution'] = 'other'
    outer = contribution(element(evidence, 'outer'), [body, quote_part, part(code, 'code')])
    nested = contribution(reply, [part(element(evidence, 'reply-body'))]); nested['kind'] = 'reply'
    result, records, _ = run_serialized(tmp_path, capture, plan_for(evidence, [outer, nested]))
    assert result['record_observations'] == 2
    outer_record = next(r for r in records if r['kind'] == 'post')
    assert [(p['role'], p['text']) for p in outer_record['content']['parts']] == [
        ('body', 'Before.'), ('quote', 'Quoted voice.'), ('code', 'literal()'), ('body', 'After.')]
    assert next(r for r in records if r['kind'] == 'reply')['content']['parts'][0]['text'] == 'Separate reply.'


def empty_case(tmp_path, case):
    attributes = {'empty_native': 'data-post-id=""', 'blank_native': 'data-post-id=" "',
                  'state_marker': 'data-state="removed"'}.get(case, '')
    href = 'missing-relative' if case == 'unresolved_uri' else ''
    content = '<a id="link" href="' + href + '"></a>' if case in ('empty_uri', 'unresolved_uri') else ''
    capture, evidence = setup(tmp_path, '<div id="empty" ' + attributes + '>' + content + '</div>')
    root = element(evidence, 'empty'); selected = contribution(root)
    if case == 'unknown_relation':
        selected['relations'] = [{'type': 'reply_to', 'target': None, 'kind': 'unknown', 'evidence': [root]}]
    elif case in ('empty_native', 'blank_native'):
        selected['identity'] = {'kind': 'native', 'basis': 'documented_native', 'evidence': [root],
                                'source': {'node': root, 'kind': 'attribute', 'attribute': 'data-post-id'}}
    elif case in ('empty_uri', 'unresolved_uri'):
        selected['identity'] = {'kind': 'uri', 'basis': 'identity_link', 'evidence': [root],
                                'source': {'node': element(evidence, 'link'), 'kind': 'attribute', 'attribute': 'href'}}
    elif case in ('unfounded_state', 'state_marker'):
        selected['state'] = {'value': 'removed', 'evidence': [root]}
    return capture, evidence, plan_for(evidence, [selected])


@pytest.mark.parametrize('case', ['empty', 'unknown_relation', 'empty_native', 'blank_native', 'empty_uri', 'unfounded_state'])
def test_empty_container_requires_actual_positive_evidence(tmp_path, case):
    capture, _, plan = empty_case(tmp_path, case)
    result, records, run = run_serialized(tmp_path, capture, plan)
    assert result['record_observations'] == result['distinct_record_keys'] == 0
    assert result['unsupported_contributions'] == 1
    assert result['status'] != 'complete_execution'
    assert records == []
    assert load_json(run / 'evidence/finalized-plan.json') == plan
    decisions = [json.loads(v) for v in (run / 'evidence/decisions.jsonl').read_text().splitlines()]
    assert decisions[0]['status'] == 'no_evidence'
    assert decisions[0]['reasons'] == ['no_actual_contribution_evidence']


@pytest.mark.parametrize('support', ['native_id', 'identity_uri', 'native_relation', 'uri_relation', 'state_attribute', 'state_text'])
def test_grounded_textless_action_still_emits(tmp_path, support):
    capture, evidence = setup(tmp_path, '<article id="action" data-post-id="native-42" data-parent-post-id="parent-7" data-state="removed">'
                              '<a id="link" href="/posts/42"></a><span id="state">[removed]</span></article>')
    root, link, marker = [element(evidence, name) for name in ('action', 'link', 'state')]
    selected = contribution(root); selected['kind'] = 'repost'
    if support in ('native_id', 'identity_uri'):
        native = support == 'native_id'
        selected['identity'] = {'kind': 'native' if native else 'uri', 'basis': 'documented_native' if native else 'identity_link',
                                'source': {'node': root if native else link, 'kind': 'attribute', 'attribute': 'data-post-id' if native else 'href'},
                                'evidence': [root]}
    elif support in ('native_relation', 'uri_relation'):
        native = support == 'native_relation'
        selected['relations'] = [{'type': 'reposts', 'kind': 'native' if native else 'uri', 'evidence': [root],
                                  'target': {'node': root if native else link, 'kind': 'attribute', 'attribute': 'data-parent-post-id' if native else 'href'}}]
    else:
        selected['state'] = {'value': 'removed', 'evidence': [root if support == 'state_attribute' else text_node(evidence, marker)]}
    result, records, _ = run_serialized(tmp_path, capture, plan_for(evidence, [selected]))
    assert result['record_observations'] == 1
    assert records[0]['content']['parts'] == []
    assert records[0]['actor'] is None


@pytest.mark.parametrize('tag', ['blockquote', 'pre', 'code'])
def test_captured_state_inside_quoted_region_cannot_create_outer_event(tmp_path, tag):
    capture, evidence = setup(tmp_path, '<article id="outer"><' + tag + '><span id="state" data-state="removed">[removed]</span></' + tag + '></article>')
    selected = contribution(element(evidence, 'outer'))
    selected['state'] = {'value': 'removed', 'evidence': [element(evidence, 'state')]}
    result, records, _ = run_serialized(tmp_path, capture, plan_for(evidence, [selected]))
    assert result['record_observations'] == 0
    assert records == []


def test_positive_record_survives_independent_no_evidence_omission(tmp_path):
    capture, evidence = setup(tmp_path, '<div id="empty"></div><article id="real"><p id="body">Usable with unknown metadata.</p></article>')
    empty = contribution(element(evidence, 'empty'))
    empty['relations'] = [{'type': 'reply_to', 'target': None, 'kind': 'unknown', 'evidence': [empty['container']]}]
    real = contribution(element(evidence, 'real'), [part(element(evidence, 'body'))])
    result, records, run = run_serialized(tmp_path, capture, plan_for(evidence, [empty, real]))
    assert result['record_observations'] == result['unsupported_contributions'] == 1
    assert result['status'] == 'partial_execution'
    assert records[0]['content']['parts'][0]['text'] == 'Usable with unknown metadata.'
    assert len(load_json(run / 'evidence/finalized-plan.json')['contributions']) == 2


def test_recipe_and_correction_share_protected_ancestor_gate(tmp_path):
    from ahif_html.recipes import instantiate, correct
    capture, evidence = setup(tmp_path, '<article id="outer"><blockquote id="quote"><span id="selected">Quoted.</span></blockquote></article>')
    root, chosen = element(evidence, 'outer'), element(evidence, 'selected')
    template = contribution('$container', [part('$body')])
    recipe = {'recipe_version': '1.0.0', 'recipe_id': 'reconstructed-quote-probe', 'profile_sha256': PROFILE_SHA,
              'assumptions': ['One fictional article.'], 'containers': {'selector': {'tag': 'article'}, 'minimum': 1, 'maximum': 1},
              'bindings': [{'name': '$body', 'selector': {'tag': 'span'}, 'kind': 'element'}], 'contribution_template': template}
    with pytest.raises(Failure, match='structural_quote_or_code_ancestor_forbids_body_title'):
        instantiate(evidence, recipe)
    original = plan_for(evidence, [contribution(root, [part(chosen, 'quote')])])
    _, _, run = run_serialized(tmp_path, capture, original)
    edits = {'correction_version': '1.0.0', 'base_plan_id': plan_id(original), 'reviewer': {'kind': 'agent', 'name': 'reconstructed-probe'},
             'edits': [{'contribution': root, 'field': 'parts', 'value': [part(chosen)], 'reason': 'quote'}]}
    with pytest.raises(Failure, match='structural_quote_or_code_ancestor_forbids_body_title'):
        correct(capture, run, edits, tmp_path / 'correction', META)


def test_mock_discovery_uses_same_protected_ancestor_gate(tmp_path):
    from ahif_html.planner import discover
    from ahif_html.provider import RecordedProvider
    from test_planner import configuration
    capture, evidence = setup(tmp_path, '<article id="outer"><blockquote><span id="selected">Quoted.</span></blockquote></article>')
    selected = contribution(element(evidence, 'outer'), [part(element(evidence, 'selected'))])
    proposal = {'action': 'propose', 'proposal': {'contributions': [selected], 'rejected': [], 'unresolved': []}}
    cfg = configuration(); cfg['budgets']['max_repairs'] = 0
    result = discover(capture, cfg, tmp_path / 'discovery', META, provider=RecordedProvider([proposal], 'mock'))
    assert result['failure'] == 'structural_quote_or_code_ancestor_forbids_body_title'
    assert not (tmp_path / 'discovery/extraction').exists()
    assert (tmp_path / 'discovery/attempts.jsonl').exists()


def test_empty_or_fully_excluded_protected_regions_do_not_discard_unquoted_text(tmp_path):
    capture, evidence = setup(tmp_path, '<article id="outer"><div id="body">Before.'
                              '<blockquote></blockquote><code></code><pre></pre>After.</div></article>')
    chosen = contribution(element(evidence, 'outer'), [part(element(evidence, 'body'))])
    result, records, _ = run_serialized(tmp_path, capture, plan_for(evidence, [chosen]))
    assert result['record_observations'] == 1
    assert records[0]['content']['parts'][0]['text'] == 'Before.\nAfter.'


@pytest.mark.parametrize('attribute,value', [('data-parent-post-id', ''), ('data-parent-post-id', ' '), ('data-parent-id', 'unsupported-scope')])
def test_unresolved_native_relation_does_not_count_as_positive_evidence(tmp_path, attribute, value):
    capture, evidence = setup(tmp_path, '<article id="action" ' + attribute + '="' + value + '"></article>')
    root = element(evidence, 'action'); selected = contribution(root)
    selected['relations'] = [{'type': 'reply_to', 'kind': 'native', 'evidence': [root],
                              'target': {'node': root, 'kind': 'attribute', 'attribute': attribute}}]
    result, records, run = run_serialized(tmp_path, capture, plan_for(evidence, [selected]))
    assert result['record_observations'] == 0
    assert records == []
    assert json.loads((run / 'evidence/decisions.jsonl').read_text())['reasons'] == ['no_actual_contribution_evidence']


@pytest.mark.parametrize('field', ['identity', 'relation'])
def test_relative_identity_without_base_is_not_positive_textless_evidence(tmp_path, field):
    capture, _ = setup(tmp_path, '<article id="action"><a id="link" href="posts/7"></a></article>')
    metadata = {'data_class': 'synthetic'}
    evidence = index.build(capture, metadata)
    root = element(evidence, 'action'); selected = contribution(root)
    ref = {'node': element(evidence, 'link'), 'kind': 'attribute', 'attribute': 'href'}
    if field == 'identity':
        selected['identity'] = {'kind': 'uri', 'basis': 'identity_link', 'source': ref, 'evidence': [root]}
    else:
        selected['relations'] = [{'type': 'reposts', 'kind': 'uri', 'target': ref, 'evidence': [root]}]
    result, records, run = run_serialized(tmp_path, capture, plan_for(evidence, [selected]), metadata)
    assert result['record_observations'] == 0
    assert records == []
    assert json.loads((run / 'evidence/decisions.jsonl').read_text())['status'] == 'no_evidence'


@pytest.mark.parametrize('case', ['wrong_attribute', 'generic_prose', 'excluded', 'nested_owner'])
def test_unowned_or_unregistered_state_evidence_does_not_create_event(tmp_path, case):
    capture, evidence = setup(tmp_path, '<article id="outer"><section id="state" data-state="deleted">'
                              'Some discussion mentioning removed content.</section></article>')
    root, marker = element(evidence, 'outer'), element(evidence, 'state')
    selected = contribution(root)
    selected['state'] = {'value': 'removed', 'evidence': [marker]}
    contributions = [selected]
    if case == 'generic_prose':
        selected['state']['evidence'] = [text_node(evidence, marker)]
    elif case == 'excluded':
        selected['state']['value'] = 'deleted'
        selected['excluded'] = [{'node': marker, 'reason': 'interface'}]
    elif case == 'nested_owner':
        selected['state']['value'] = 'deleted'
        nested = contribution(marker)
        nested['state'] = {'value': 'deleted', 'evidence': [marker]}
        contributions.append(nested)
    result, records, run = run_serialized(tmp_path, capture, plan_for(evidence, contributions))
    assert result['record_observations'] == (1 if case == 'nested_owner' else 0)
    decisions = [json.loads(line) for line in (run / 'evidence/decisions.jsonl').read_text().splitlines()]
    assert decisions[0]['status'] == 'no_evidence'


def test_empty_identity_keeps_useful_text_without_invented_permalink(tmp_path):
    capture, evidence = setup(tmp_path, '<article id="outer"><a id="link" href=""></a><p id="body">Still useful.</p></article>')
    root = element(evidence, 'outer')
    selected = contribution(root, [part(element(evidence, 'body'))])
    selected['identity'] = {'kind': 'uri', 'basis': 'identity_link', 'evidence': [root],
                            'source': {'node': element(evidence, 'link'), 'kind': 'attribute', 'attribute': 'href'}}
    result, records, _ = run_serialized(tmp_path, capture, plan_for(evidence, [selected]))
    assert result['record_observations'] == 1
    assert records[0]['record_key']['id_type'] == 'source_local'
    assert 'permalink' not in records[0]
    assert records[0]['content']['parts'][0]['text'] == 'Still useful.'


def test_whitespace_only_parts_are_not_positive_contribution_evidence(tmp_path):
    capture, evidence = setup(tmp_path, '<article id="outer"><p id="body"> \n\t </p></article>')
    chosen = contribution(element(evidence, 'outer'), [part(element(evidence, 'body'))])
    result, records, run = run_serialized(tmp_path, capture, plan_for(evidence, [chosen]))
    assert result['record_observations'] == 0
    assert records == []
    assert json.loads((run / 'evidence/decisions.jsonl').read_text())['status'] == 'no_evidence'


def test_mock_and_recipe_unknown_relation_are_omitted_by_same_executor(tmp_path):
    from ahif_html.planner import discover
    from ahif_html.provider import RecordedProvider
    from ahif_html.recipes import apply_recipe
    from test_planner import configuration
    capture, evidence, plan = empty_case(tmp_path, 'unknown_relation')
    proposal = {'action': 'propose', 'proposal': {k: plan[k] for k in ('contributions', 'rejected', 'unresolved')}}
    result = discover(capture, configuration(), tmp_path / 'discovery', META, provider=RecordedProvider([proposal], 'mock'))
    assert result['failure'] is None
    assert (tmp_path / 'discovery/extraction/bundle/records.jsonl').read_bytes() == b''
    assert load_json(tmp_path / 'discovery/extraction/run-receipt.json')['unsupported_contributions'] == 1
    template = contribution('$container')
    template['relations'] = [{'type': 'reply_to', 'kind': 'unknown', 'target': None, 'evidence': ['$container']}]
    recipe = {'recipe_version': '1.0.0', 'recipe_id': 'reconstructed-empty-relation', 'profile_sha256': PROFILE_SHA,
              'assumptions': ['One fictional empty div.'], 'containers': {'selector': {'tag': 'div'}, 'minimum': 1, 'maximum': 1},
              'bindings': [], 'contribution_template': template}
    result = apply_recipe(capture, recipe, tmp_path / 'recipe', META)
    assert result['record_observations'] == 0
    assert (tmp_path / 'recipe/bundle/records.jsonl').read_bytes() == b''


def test_semantic_gate_is_bound_in_observation_and_interpretation(tmp_path):
    from ahif_html.common import GATE_CONTRACT, GATE_SHA
    capture, evidence = setup(tmp_path, '<article id="outer"><p id="body">Useful.</p></article>')
    selected = contribution(element(evidence, 'outer'), [part(element(evidence, 'body'))])
    _, records, run = run_serialized(tmp_path, capture, plan_for(evidence, [selected]))
    interpretation = load_json(run / 'evidence/interpretation.json')
    assert interpretation['interpretation_version'] == '1.1.0'
    assert interpretation['profile']['version'] == '1.0.0'
    assert interpretation['gate_contract'] == GATE_CONTRACT
    assert interpretation['gate_contract_sha256'] == GATE_SHA
    record = records[0]
    binding = record['extensions']['org.ahif-html:extraction']
    assert record['format_version'] == '0.1.1'
    assert record['provenance']['normalizer']['version'] == '0.2.0'
    assert binding['gate_contract_version'] == '1.1.0'
    assert binding['gate_contract_sha256'] == GATE_SHA
