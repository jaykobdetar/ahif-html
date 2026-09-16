"""Model tests are recorded/mock unless a test explicitly names fake transport."""
import copy
import json
from pathlib import Path

import pytest

from ahif_html.common import C, Failure, load_json
from ahif_html.index import build
from ahif_html.planner import discover, Session, map_references
from ahif_html.provider import OllamaProvider, RecordedProvider, validate_config


def configuration(mode='mock'):
    return {'version': '1.0.0', 'mode': mode,
            'response_format': 'schema',
            'provider_location': 'workstation', 'tunnel_declaration': None,
            'endpoint': 'http://127.0.0.1:11434' if mode == 'live' else None,
            'model': 'explicit-test-model', 'responses_file': None if mode == 'live' else 'explicit-test-responses.json',
            'reviewer': False, 'num_ctx': 8192, 'min_available_memory_mib': 1024,
            'data_approval': {'approved': mode == 'live', 'data_classes': ['synthetic'],
                              'capture_sha256': ['a' * 64] if mode == 'live' else [],
                              'declaration': 'Synthetic test configuration; transport is mocked.'},
            'budgets': {'max_calls': 12, 'max_tool_calls': 20, 'max_input_token_charge': 1000000,
                        'max_input_tokens_total': 98304,
                        'max_output_tokens_per_call': 2048, 'max_output_tokens_total': 24576,
                        'max_response_bytes': 131072, 'max_recording_bytes': 1048576,
                        'max_inspected_characters': 40000, 'max_wall_seconds': 60,
                        'max_retries': 0, 'max_repairs': 2}}


def fixture(tmp_path):
    capture = tmp_path / 'fixture.html'
    capture.write_text('<!doctype html><article><p>Keep this &amp; that.</p></article>', encoding='utf8')
    idx = build(capture, {'data_class': 'synthetic'})
    container = next(v['ref'] for v in idx['nodes'] if v['tag'] == 'article')
    body = next(v['ref'] for v in idx['nodes'] if v['tag'] == 'p')
    contribution = {'container': container, 'kind': 'post', 'identity': None, 'author': None,
                    'created': None, 'updated': None,
                    'parts': [{'root': body, 'role': 'body', 'attribution': 'unknown',
                               'exclude': [], 'evidence': [body]}],
                    'excluded': [], 'relations': [], 'links': [], 'state': None,
                    'completeness': None, 'evidence': [container]}
    proposal = {'action': 'propose', 'proposal': {'contributions': [contribution], 'rejected': [], 'unresolved': []}}
    return capture, idx, proposal


def test_mock_positive_uses_ordinary_executor(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    out = tmp_path / 'run'
    result = discover(capture, configuration(), out, {'data_class': 'synthetic'},
                      provider=RecordedProvider([proposal], 'mock'))
    assert result['failure'] is None
    assert result['mode'] == 'mock'
    records = [json.loads(v) for v in (out / 'extraction/bundle/records.jsonl').read_text().splitlines()]
    assert records[0]['content']['parts'][0]['text'] == 'Keep this & that.'
    assert records[0]['actor'] is None
    assert result['operation']['actual_input_tokens'] is None
    assert result['operation']['monetary_cost'] is None
    assert load_json(out / 'finalized-plan.json')['origin']['kind'] == 'mock'


def test_structural_failure_repaired_and_attempt_retained(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    invalid = copy.deepcopy(proposal)
    invalid['proposal']['contributions'][0]['parts'][0]['root'] = 'invented-reference'
    result = discover(capture, configuration(), tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([invalid, proposal], 'mock'))
    assert result['failure'] is None
    attempts = [json.loads(v) for v in (tmp_path / 'run/attempts.jsonl').read_text().splitlines()]
    assert [v['validation']['status'] for v in attempts] == ['failed', 'passed']
    assert load_json(tmp_path / 'run/finalized-plan.json')['ancestry']


def test_tool_budget_preserves_failure_without_bundle(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    cfg = configuration()
    cfg['budgets']['max_tool_calls'] = 1  # Initial outline is also charged.
    tool = {'action': 'tool', 'name': 'page_outline', 'arguments': {}}
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([tool, proposal], 'mock'))
    assert result['status'] == 'resource_limit'
    assert result['failure'] == 'model_tool_limit'
    assert not (tmp_path / 'run/extraction').exists()
    assert (tmp_path / 'run/discovery/call-0001.json').exists()


@pytest.mark.parametrize('action', [
    {'action': 'tool', 'name': 'shell', 'arguments': {'cmd': 'anything'}},
    {'action': 'tool', 'name': 'fetch', 'arguments': {'url': 'https://example.invalid'}},
    {'action': 'propose', 'proposal': {'contributions': [], 'rejected': [], 'unresolved': [], 'text': 'invented'}},
])
def test_untrusted_model_actions_rejected(tmp_path, action):
    capture, _, _ = fixture(tmp_path)
    config = configuration()
    config['budgets']['max_repairs'] = 0
    result = discover(capture, config, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([action], 'mock'))
    assert result['failure'] == 'model_action_schema_invalid'
    assert not (tmp_path / 'run/extraction').exists()


def test_model_cannot_declare_human_review(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    proposal['proposal']['review'] = {'status': 'human_reviewed', 'reviewer': 'somebody'}
    config = configuration()
    config['budgets']['max_repairs'] = 0
    result = discover(capture, config, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([proposal], 'mock'))
    assert result['failure'] == 'model_action_schema_invalid'


def test_reviewer_inspects_before_receiving_plan(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    cfg = configuration()
    cfg['reviewer'] = True
    actions = [proposal, {'action': 'tool', 'name': 'inspect_node',
                         'arguments': {'node_ref': proposal['proposal']['contributions'][0]['container'],
                                       'depth': 3, 'max_characters': 2000}},
               {'action': 'ready_for_review'}, {'action': 'review', 'decision': 'approve', 'issues': []}]
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider(actions, 'mock'))
    assert result['failure'] is None
    independent = load_json(tmp_path / 'run/discovery/call-0002.json')
    assert '"plan":' not in C(independent['request']['messages']).decode()
    assert load_json(tmp_path / 'run/finalized-plan.json')['review']['status'] == 'agent_reviewed'


def test_reviewer_cannot_skip_independent_inspection(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    cfg = configuration()
    cfg['reviewer'] = True
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([proposal, {'action': 'ready_for_review'}], 'mock'))
    assert result['failure'] == 'reviewer_independent_inspection_missing'


def test_live_needs_exact_capture_approval_without_call(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    class Never:
        mode = 'live'
        def call(self, *args):
            raise AssertionError('unapproved data reached provider')
    result = discover(capture, configuration('live'), tmp_path / 'run', {'data_class': 'synthetic'}, provider=Never())
    assert result['failure'] == 'capture_not_approved_for_provider'
    assert result['operation'] is None


@pytest.mark.parametrize('endpoint', ['https://external.invalid', 'http://localhost@external.invalid',
                                      'http://127.0.0.1/path', 'http://127.0.0.1?token=secret', 'http://['])
def test_provider_endpoint_restriction(endpoint):
    cfg = configuration('live')
    cfg['endpoint'] = endpoint
    with pytest.raises(Failure):
        validate_config(cfg)


def test_real_adapter_fake_transport_contract_and_no_hidden_thinking():
    captured = {}
    action = {'action': 'refuse', 'reason': 'insufficient_evidence'}
    def transport(endpoint, payload, timeout, limit):
        if endpoint.endswith('/api/show'):
            return b'{"details":{"format":"gguf"},"model_info":{"general.architecture":"test"}}'
        captured.update(endpoint=endpoint, payload=json.loads(payload), timeout=timeout)
        return json.dumps({'done': True, 'message': {'content': json.dumps(action), 'thinking': 'not retained'},
                           'prompt_eval_count': 12, 'eval_count': 8}).encode()
    provider = OllamaProvider(configuration('live'), transport)
    reply = provider.call([{'role': 'user', 'content': 'Synthetic.'}], 50, 3)
    assert captured['endpoint'] == 'http://127.0.0.1:11434/api/chat'
    assert captured['payload']['model'] == 'explicit-test-model'
    assert captured['payload']['options']['num_predict'] == 50
    assert captured['payload']['options']['num_ctx'] == 8192
    assert captured['payload']['think'] is False
    assert isinstance(captured['payload']['format'], dict)
    assert reply.action == action
    assert reply.usage['input_tokens'] == 12
    assert 'not retained' not in C(provider.last_public_response).decode()


def test_refusal_retained_and_distinct_from_success(tmp_path):
    capture, _, _ = fixture(tmp_path)
    result = discover(capture, configuration(), tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([{'action': 'refuse', 'reason': 'insufficient_evidence'}], 'mock'))
    assert result['status'] == 'model_refused'
    assert result['operation']['calls'] == 1
    assert not (tmp_path / 'run/extraction').exists()


def test_response_schema_repair_retains_failed_call(tmp_path):
    capture, _, proposal = fixture(tmp_path)
    result = discover(capture, configuration(), tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([{'echoed_input': True}, proposal], 'mock'))
    assert result['failure'] is None
    assert result['operation']['repairs'] == 1
    assert load_json(tmp_path / 'run/discovery/call-0001.json')['error']['code'] == 'model_action_schema_invalid'


def test_context_token_reservation_prevents_a_call(tmp_path):
    capture, _, proposal = fixture(tmp_path)
    cfg = configuration()
    cfg['budgets']['max_input_tokens_total'] = 1
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([proposal], 'mock'))
    assert result['failure'] == 'model_input_token_limit'
    assert result['operation']['calls'] == 0


def test_fake_transport_invalid_content_still_retains_actual_usage():
    def transport(endpoint, payload, timeout, limit):
        if endpoint.endswith('/api/show'):
            return b'{"details":{"format":"gguf"},"model_info":{"general.architecture":"test"}}'
        return b'{"done":true,"message":{"content":"not JSON"},"prompt_eval_count":12,"eval_count":8}'
    provider = OllamaProvider(configuration('live'), transport)
    with pytest.raises(Failure, match='provider_response_invalid'):
        provider.call([{'role': 'user', 'content': 'Synthetic.'}], 50, 3)
    assert provider.last_usage['input_tokens'] == 12
    assert provider.last_public_response['content'] == 'not JSON'


def test_fake_transport_context_overflow_refused():
    def transport(endpoint, payload, timeout, limit):
        if endpoint.endswith('/api/show'):
            return b'{"details":{"format":"gguf"},"model_info":{"general.architecture":"test"}}'
        return json.dumps({'done': True, 'message': {'content': '{"action":"refuse","reason":"insufficient_evidence"}'},
                           'prompt_eval_count': 8190, 'eval_count': 8}).encode()
    provider = OllamaProvider(configuration('live'), transport)
    with pytest.raises(Failure, match='provider_context_limit'):
        provider.call([{'role': 'user', 'content': 'Synthetic.'}], 50, 3)
    assert provider.last_usage['input_tokens'] == 8190


def test_remote_ollama_model_rejected_before_chat():
    requests = []
    def transport(endpoint, payload, timeout, limit):
        requests.append(endpoint)
        return b'{"remote_host":"https://remote.invalid","remote_model":"remote"}'
    provider = OllamaProvider(configuration('live'), transport)
    with pytest.raises(Failure, match='provider_local_model_not_verified'):
        provider.call([{'role': 'user', 'content': 'Synthetic.'}], 50, 3)
    assert requests == ['http://127.0.0.1:11434/api/show']


def test_fake_transport_schema_failure_usage_is_charged(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    cfg = configuration('live')
    cfg['data_approval']['capture_sha256'] = [idx['capture']['sha256']]
    responses = iter([{'wrong_action': True}, proposal])
    def transport(endpoint, payload, timeout, limit):
        if endpoint.endswith('/api/show'):
            return b'{"details":{"format":"gguf"},"model_info":{"general.architecture":"test"}}'
        return json.dumps({'done': True, 'message': {'content': json.dumps(next(responses))},
                           'prompt_eval_count': 100, 'eval_count': 30}).encode()
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=OllamaProvider(cfg, transport))
    assert result['failure'] is None
    assert result['operation']['actual_input_tokens'] == 200
    assert result['operation']['actual_output_tokens'] == 60
    assert result['operation']['calls'] == 2


def test_model_aliases_expand_to_same_executor_plan(tmp_path):
    capture, idx, proposal = fixture(tmp_path)
    aliases = {node['ref']: 'n' + str(node['order']) for node in idx['nodes']}
    compact = map_references(proposal, aliases)
    result = discover(capture, configuration(), tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider([compact], 'mock'))
    assert result['failure'] is None
    plan = load_json(tmp_path / 'run/finalized-plan.json')
    assert plan['contributions'] == proposal['proposal']['contributions']
    audit = load_json(tmp_path / 'run/discovery/node-aliases.json')
    assert audit['index_id'] == idx['index_id']


def test_aliases_never_rewrite_source_text_or_attribute_values():
    value = {'ref': 'full-ref', 'text': 'full-ref', 'attrs': [{'name': 'href', 'value': 'full-ref'}],
             'children': ['full-ref']}
    mapped = map_references(value, {'full-ref': 'n1'})
    assert mapped == {'ref': 'n1', 'text': 'full-ref', 'attrs': [{'name': 'href', 'value': 'full-ref'}],
                      'children': ['n1']}


def test_reviewer_discarded_tool_view_is_not_independent_inspection(tmp_path, monkeypatch):
    from ahif_html.index import Inspector
    original = Inspector.call
    def discarded(self, name, arguments):
        if name == 'inspect_node':
            return {'truncated': True, 'reason': 'tool_result_character_limit'}
        return original(self, name, arguments)
    monkeypatch.setattr(Inspector, 'call', discarded)
    capture, _, proposal = fixture(tmp_path)
    cfg = configuration()
    cfg['reviewer'] = True
    actions = [proposal, {'action': 'tool', 'name': 'inspect_node',
                         'arguments': {'node_ref': proposal['proposal']['contributions'][0]['container']}},
               {'action': 'ready_for_review'}, {'action': 'review', 'decision': 'approve', 'issues': []}]
    result = discover(capture, cfg, tmp_path / 'run', {'data_class': 'synthetic'},
                      provider=RecordedProvider(actions, 'mock'))
    assert result['failure'] == 'reviewer_independent_inspection_missing'
    assert not (tmp_path / 'run/extraction').exists()


def test_remote_tunnel_requires_explicit_declaration():
    cfg = configuration('live')
    cfg['provider_location'] = 'remote_tunnel'
    with pytest.raises(Failure, match='provider_tunnel_declaration_missing'):
        validate_config(cfg)


def test_invalid_config_type_retains_typed_receipt(tmp_path):
    capture, _, _ = fixture(tmp_path)
    result = discover(capture, [], tmp_path / 'run', {'data_class': 'synthetic'})
    assert result['status'] == 'invalid_input'
    assert result['failure'] == 'model-config_schema_invalid'
