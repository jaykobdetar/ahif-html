"""Discovery 1.1.0 engineering invariants; every provider here is an explicit mock."""
import copy
import json
from pathlib import Path

import pytest

from ahif_html.candidates import Candidates, CandidateInspector
from ahif_html.common import Failure, load_json, sha
from ahif_html.index import build, Inspector
from ahif_html.planner import discover, Session
from ahif_html.provider import RecordedProvider
from test_planner import configuration, fixture, review_responses


def capture_index(tmp_path, text):
    capture = tmp_path / 'page.html'
    capture.write_text(text, encoding='utf8')
    return capture, build(capture, {'data_class': 'synthetic'})


def contribution(idx, container, body):
    return {'container': container, 'kind': 'post', 'identity': None, 'author': None,
            'created': None, 'updated': None, 'parts': [{'root': body, 'role': 'body',
            'attribution': 'unknown', 'exclude': [], 'evidence': [body]}], 'excluded': [],
            'relations': [], 'links': [], 'state': None, 'completeness': None,
            'evidence': [container]}


def two_posts(tmp_path):
    capture, idx = capture_index(tmp_path, '<article><p>First source.</p></article><article><p>Second source.</p></article>')
    roots = [n['ref'] for n in idx['nodes'] if n['tag'] == 'article']
    bodies = [n['ref'] for n in idx['nodes'] if n['tag'] == 'p']
    proposal = {'action': 'propose', 'proposal': {'contributions': [contribution(idx, roots[0], bodies[0])],
                                               'rejected': [], 'unresolved': []}}
    return capture, idx, roots, proposal


def test_inventory_signals_are_finite_deterministic_hints(tmp_path):
    capture, idx = capture_index(tmp_path, '<nav><ul><li>Home</li></ul></nav><table><tr><td>Text</td></tr></table><dl><dd>Another text</dd></dl><article hidden>Hidden</article>')
    inventory = Candidates(idx)
    assert [item['tag'] for item in inventory.items] == ['li', 'tr', 'dd']
    assert inventory.manifest['unsupported_candidates'] == 1
    assert inventory.manifest['not_completeness_proof'] is True
    moved = tmp_path / 'relocated.html'; moved.write_bytes(capture.read_bytes())
    assert Candidates(build(moved, {'data_class': 'synthetic'})).manifest == inventory.manifest
    assert all(item['signals'] == ['structural_tag'] for item in inventory.items)


def test_candidate_pages_repeat_parent_header_and_keep_node_boundaries(tmp_path):
    _, idx = capture_index(tmp_path, '<main><article><header><span>Author label</span></header><p>First.</p><p>Second.</p></article></main>')
    inventory = Candidates(idx); inspector = Inspector(idx)
    gateway = CandidateInspector(inventory, inspector)
    ref = inventory.items[0]['node']
    first = gateway.call('inspect_candidate', {'candidate_ref': ref, 'limit': 4})
    second = gateway.call('inspect_candidate', {'candidate_ref': ref, 'start': first['next_start'], 'limit': 4})
    assert first['context'] == second['context']
    assert any(n['tag'] == 'header' for n in first['context'])
    assert any(n['tag'] == 'main' for n in first['context'])
    assert first['nodes'][0]['ref'] == ref
    assert {n['ref'] for n in first['nodes']}.isdisjoint(n['ref'] for n in second['nodes'])
    assert any(n.get('text') == 'First.' for n in second['nodes'])
    assert inspector.calls == 2 and inspector.characters > 0


def test_inventory_pagination_never_implicitly_disposes_later_candidates(tmp_path):
    _, idx = capture_index(tmp_path, ''.join('<article><p>Text.</p></article>' for _ in range(13)))
    inventory = Candidates(idx); gateway = CandidateInspector(inventory, Inspector(idx))
    first = gateway.call('candidate_inventory', {'limit': 10})
    later = gateway.call('candidate_inventory', {'start': first['next_start'], 'limit': 10})
    assert len(first['candidates']) == 10 and len(later['candidates']) == 3
    assert first['next_start'] == 10 and later['next_start'] is None
    report = inventory.accounting({'contributions': [], 'rejected': [], 'unresolved': []})
    assert len(report['missing']) == 13 and report['accounted'] is False


def test_unaccounted_second_post_cannot_be_accepted(tmp_path):
    capture, idx, roots, proposal = two_posts(tmp_path)
    cfg = configuration(); cfg['budgets']['max_repairs'] = 0
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([proposal], 'mock'))
    assert result['failure'] == 'candidate_accounting_incomplete'
    assert not (tmp_path / 'run/extraction').exists()
    report = load_json(tmp_path / 'run/candidate-accounting.json')
    assert report['missing'] == [roots[1]]
    assert report['accounted'] is False


def test_repair_can_abstain_on_second_post_while_preserving_first(tmp_path):
    capture, idx, roots, proposal = two_posts(tmp_path)
    repaired = copy.deepcopy(proposal)
    repaired['proposal']['unresolved'] = [{'node': roots[1], 'reason': 'needs_review'}]
    result = discover(capture, configuration(), tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([proposal, repaired], 'mock'))
    assert result['failure'] is None and result['status'] == 'partial_execution'
    records = [json.loads(v) for v in (tmp_path / 'run/extraction/bundle/records.jsonl').read_text().splitlines()]
    assert len(records) == 1 and records[0]['content']['parts'][0]['text'] == 'First source.'
    accounting = load_json(tmp_path / 'run/candidate-accounting.json')
    assert [v['decision'] for v in accounting['decisions']] == ['include', 'unresolved']
    assert accounting['accounted'] and accounting['not_completeness_proof']
    call = load_json(tmp_path / 'run/discovery/call-0002.json')
    assert 'remaining_missing' in call['request']['messages'][-1]['content']


def test_navigation_list_item_is_rejected_without_inventing_an_event(tmp_path):
    capture, idx = capture_index(tmp_path, '<nav><ul><li>Home</li></ul></nav><article><p>Useful text.</p></article>')
    root = next(n['ref'] for n in idx['nodes'] if n['tag'] == 'article')
    nav = next(n['ref'] for n in idx['nodes'] if n['tag'] == 'li')
    body = next(n['ref'] for n in idx['nodes'] if n['tag'] == 'p')
    proposal = {'action': 'propose', 'proposal': {'contributions': [contribution(idx, root, body)],
                   'rejected': [{'node': nav, 'reason': 'not_contribution'}], 'unresolved': []}}
    result = discover(capture, configuration(), tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([proposal], 'mock'))
    assert result['failure'] is None
    assert [v['decision'] for v in result['operation']['candidate_accounting']['decisions']] == ['reject', 'include']
    assert len((tmp_path / 'run/extraction/bundle/records.jsonl').read_text().splitlines()) == 1


def test_candidate_inventory_limit_is_explicit_before_inference(tmp_path):
    capture, idx, roots, proposal = two_posts(tmp_path)
    result = discover(capture, configuration(), tmp_path / 'run', {'data_class': 'synthetic'},
                      limits={'candidates': 1}, provider=RecordedProvider([proposal], 'mock'))
    assert result['failure'] == 'candidate_inventory_limit' and result['operation']['calls'] == 0
    inventory = load_json(tmp_path / 'run/discovery/candidate-inventory.json')
    assert inventory['inventory_truncated'] and inventory['total_supported_candidates'] == 2
    assert not (tmp_path / 'run/extraction').exists()


def test_conflicting_candidate_dispositions_fail(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    proposal['proposal']['rejected'] = [{'node': proposal['proposal']['contributions'][0]['container'], 'reason': 'not_contribution'}]
    cfg = configuration(); cfg['budgets']['max_repairs'] = 0
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([proposal], 'mock'))
    assert result['failure'] is not None
    assert not (tmp_path / 'run/extraction').exists()


def test_reference_and_argument_repairs_have_actionable_bounded_feedback(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    actions = [{'action': 'tool', 'name': 'inspect_candidate', 'arguments': {'candidate_ref': 'n999'}}, proposal]
    result = discover(capture, configuration(), tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider(actions, 'mock'))
    assert result['failure'] is None and result['operation']['repairs'] == 1
    message = load_json(tmp_path / 'run/discovery/call-0002.json')['request']['messages'][-1]['content']
    assert 'allowed_arguments' in message and 'candidate_ref' in message and 'unknown_reference' in message
    assert 'Do not guess' in message


def test_reviewer_root_only_inspection_is_not_meaningful(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    ready, approval = review_responses(idx, proposal)
    ready['observations'][0]['evidence'] = [proposal['proposal']['contributions'][0]['container']]
    cfg = configuration(); cfg['reviewer'] = True
    actions = [proposal, {'action': 'tool', 'name': 'inspect_node', 'arguments': {
                'node_ref': proposal['proposal']['contributions'][0]['container'], 'depth': 0}}, ready, approval]
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider(actions, 'mock'))
    assert result['failure'] == 'reviewer_independent_inspection_missing'
    assert load_json(tmp_path / 'run/review-observations.json')['validation'] == 'failed'


def test_reviewer_cannot_omit_an_accounted_unresolved_candidate(tmp_path):
    capture, idx, roots, proposal = two_posts(tmp_path)
    proposal['proposal']['unresolved'] = [{'node': roots[1], 'reason': 'needs_review'}]
    ready, approval = review_responses(idx, proposal)
    cfg = configuration(); cfg['reviewer'] = True
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'}, provider=RecordedProvider([
        proposal, {'action': 'tool', 'name': 'inspect_candidate', 'arguments': {'candidate_ref': roots[0]}},
        ready, approval], 'mock'))
    assert result['failure'] == 'reviewer_independent_inspection_missing'
    assert not (tmp_path / 'run/extraction').exists()


def test_reviewer_cannot_approve_uninspected_body_text(tmp_path):
    capture, idx = capture_index(tmp_path, '<article><header>Header.</header><div><p>Actual body.</p></div></article>')
    root = next(n['ref'] for n in idx['nodes'] if n['tag'] == 'article')
    body = next(n['ref'] for n in idx['nodes'] if n['tag'] == 'p')
    headertext = next(n['ref'] for n in idx['nodes'] if n['text'] == 'Header.')
    proposal = {'action': 'propose', 'proposal': {'contributions': [contribution(idx, root, body)], 'rejected': [], 'unresolved': []}}
    ready, approval = review_responses(idx, proposal)
    cfg = configuration(); cfg['reviewer'] = True
    # The independent inspection sees structure/header but no body text.
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'}, provider=RecordedProvider([
        proposal, {'action': 'tool', 'name': 'inspect_candidate', 'arguments': {'candidate_ref': root, 'limit': 5}},
        ready, approval], 'mock'))
    assert result['failure'] == 'reviewer_selected_evidence_not_inspected'


def test_new_candidate_tools_share_inspection_limits_and_rollback_discarded_views(tmp_path):
    _, idx = capture_index(tmp_path, '<article><p>Text.</p></article>')
    candidates = Candidates(idx); inspector = Inspector(idx, {'tool_characters': 150})
    result = CandidateInspector(candidates, inspector).call('inspect_candidate', {'candidate_ref': candidates.items[0]['node']})
    assert result['truncated'] and not inspector.exposed and not inspector.inspected
    assert inspector.calls == 1


def test_total_discovery_output_limit_prevents_publication(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    with pytest.raises(Failure, match='output_total_byte_limit'):
        discover(capture, configuration(), tmp_path / 'run', {'data_class': 'synthetic'},
                 limits={'output_bytes': 100}, provider=RecordedProvider([proposal], 'mock'))
    assert not (tmp_path / 'run').exists()


def reviewed_run(tmp_path, html, configure, view_arguments=None):
    capture, idx = capture_index(tmp_path, html)
    root = next(n['ref'] for n in idx['nodes'] if n['tag'] == 'article')
    body = next(n['ref'] for n in idx['nodes'] if n['tag'] == 'p')
    c = contribution(idx, root, body)
    configure(idx, c)
    proposal = {'action': 'propose', 'proposal': {'contributions': [c], 'rejected': [], 'unresolved': []}}
    ready, approval = review_responses(idx, proposal)
    cfg = configuration(); cfg['reviewer'] = True
    return discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'}, provider=RecordedProvider([
        proposal, {'action': 'tool', 'name': 'inspect_candidate', 'arguments': {
            'candidate_ref': root, **(view_arguments or {})}}, ready, approval], 'mock'))


def test_reviewer_sees_hidden_and_ui_exclusion_structure_without_private_text(tmp_path):
    def configure(idx, c):
        c['parts'][0]['root'] = c['container']
        c['excluded'] = [{'node': n['ref'], 'reason': 'hidden' if n['tag'] == 'footer' else 'interface'}
                         for n in idx['nodes'] if n['tag'] in ('footer', 'button')]
    result = reviewed_run(tmp_path, '<article><p>OK.</p><footer hidden>Private signature.</footer><button>UI label.</button></article>', configure)
    assert result['failure'] is None
    transcript = (tmp_path / 'run/discovery/call-0003.json').read_text()
    assert 'Private signature.' not in transcript and 'UI label.' not in transcript


def test_reviewer_does_not_require_globally_excluded_signature_text(tmp_path):
    def configure(idx, c):
        c['parts'][0]['root'] = c['container']
        c['excluded'] = [{'node': next(n['ref'] for n in idx['nodes'] if n['tag'] == 'footer'), 'reason': 'signature'}]
    result = reviewed_run(tmp_path, '<article><p>OK.</p><footer>' + 'Excluded signature. ' * 200 + '</footer></article>',
                          configure, {'max_characters': 10})
    assert result['failure'] is None
    records = [json.loads(v) for v in (tmp_path / 'run/extraction/bundle/records.jsonl').read_text().splitlines()]
    assert records[0]['content']['parts'][0]['text'] == 'OK.'


def test_reviewer_selected_query_url_cannot_pass_as_readable_attribute(tmp_path):
    def configure(idx, c):
        anchor = next(n['ref'] for n in idx['nodes'] if n['tag'] == 'a')
        label = next(n['ref'] for n in idx['nodes'] if n['text'] == 'Writer')
        c['author'] = {'identity': {'kind': 'uri', 'source': {'node': anchor, 'kind': 'attribute', 'attribute': 'href'},
                                  'basis': 'identity_link'}, 'label': {'node': label, 'kind': 'text'}, 'evidence': [anchor]}
    result = reviewed_run(tmp_path, '<article><a href="https://profiles.invalid/u/writer?token=private">Writer</a><p>OK.</p></article>', configure)
    assert result['failure'] == 'reviewer_selected_attribute_not_readable'
    assert 'token=private' not in (tmp_path / 'run/discovery/call-0003.json').read_text()


def test_reviewer_selected_truncated_attribute_cannot_pass(tmp_path):
    def configure(idx, c):
        c['created'] = {'node': next(n['ref'] for n in idx['nodes'] if n['tag'] == 'time'), 'kind': 'attribute', 'attribute': 'datetime'}
    result = reviewed_run(tmp_path, '<article><p>OK.</p><time datetime="' + '2' * 1100 + '">Date</time></article>', configure)
    assert result['failure'] == 'reviewer_selected_attribute_not_readable'
