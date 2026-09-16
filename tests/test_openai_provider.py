"""Offline Responses fixtures only. No test uses a real key or hosted request."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import io
import json
import multiprocessing
import os
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from ahif_html.common import C, Failure, load_json
from ahif_html import openai_provider as gateway
from ahif_html.executor import verify
from ahif_html.planner import discover
from ahif_html.provider import OllamaProvider
from test_planner import configuration, fixture


KEY = 'fictional-test-value-not-a-real-api-key'
ACTION = {'action': 'refuse', 'reason': 'insufficient_evidence'}


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', KEY)


def config(tmp_path, cap='3.00', *, version='1.1.0'):
    ledger = tmp_path / 'spending.jsonl'
    gateway.initialize_ledger(ledger, cap)
    cfg = configuration('live')
    cfg.update(version=version, provider_location='hosted', endpoint=gateway.ENDPOINT,
               model=gateway.MODEL, num_ctx=16384, response_format='schema',
               openai={'reasoning_effort': 'medium', 'api_key_env': 'OPENAI_API_KEY', 'budget_ledger': str(ledger)})
    if version == '1.1.1':
        cfg['openai']['wire_mode'] = 'result_or_action'
    cfg['budgets']['max_output_tokens_per_call'] = 8192
    return cfg


def envelope(*, status='completed', text=None, usage=None):
    return {'id': 'resp_fictional', 'model': gateway.MODEL, 'status': status,
            'service_tier': 'default', 'error': None,
            'usage': usage if usage is not None else {'input_tokens': 100, 'output_tokens': 50,
                'input_tokens_details': {'cached_tokens': 90, 'cache_write_tokens': 10},
                'output_tokens_details': {'reasoning_tokens': 20}, 'total_tokens': 150},
            'output': [{'type': 'reasoning', 'summary': [{'text': 'PRIVATE_REASONING_MUST_NOT_BE_RETAINED'}],
                        'encrypted_content': 'PRIVATE_ENCRYPTED_REASONING'},
                       {'type': 'message', 'role': 'assistant', 'status': status,
                        'content': [{'type': 'output_text', 'text': json.dumps({'result': ACTION}) if text is None else text}]}]}


def transport(value):
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    return lambda *args: raw


def call(provider, maximum=8192):
    return provider.call([{'role': 'user', 'content': 'Fictional bounded source evidence.'}], maximum, 3)


def snapshot(cfg):
    return gateway.ledger_snapshot(cfg['openai']['budget_ledger'])


def test_positive_response_request_contract_usage_and_upper_price(tmp_path):
    cfg = config(tmp_path); captured = {}
    def fake(endpoint, payload, timeout, limit):
        captured.update(endpoint=endpoint, payload=json.loads(payload), timeout=timeout, limit=limit)
        during = snapshot(cfg)
        assert during['pending_requests'] == 1
        assert during['outstanding_nanodollars'] == 539745600
        return json.dumps(envelope()).encode()
    provider = gateway.OpenAIProvider(cfg, fake)
    result = call(provider)
    assert result.action == ACTION
    request = captured['payload']
    assert captured['endpoint'] == gateway.ENDPOINT
    assert request['reasoning'] == {'effort': 'medium'}
    assert request['store'] is False and request['service_tier'] == 'default'
    assert request['truncation'] == 'disabled'
    assert not set(request) & {'tools', 'temperature', 'seed', 'previous_response_id', 'conversation'}
    assert request['text']['format']['type'] == 'json_schema'
    assert request['text']['format']['strict'] is False
    assert request['text']['format']['schema']['type'] == 'object'
    assert request['text']['format']['schema']['required'] == ['result']
    assert request['text']['format']['schema']['additionalProperties'] is False
    assert set(request['text']['format']['schema']['properties']) == {'result'}
    assert 'oneOf' not in request['text']['format']['schema']
    assert result.usage['input_tokens'] == 100 and result.usage['output_tokens'] == 50
    assert result.usage['reasoning_tokens'] == 20
    assert result.usage['monetary_cost'] is None
    assert result.usage['cost_upper_bound_nanodollars'] == 100 * 250 + 50 * 1200
    assert snapshot(cfg)['committed_nanodollars'] == 85000
    assert snapshot(cfg)['pending_requests'] == 0
    assert provider.gateway_requests == 1
    assert json.loads(provider.last_public_response['content']) == {'result': ACTION}
    recorded = C([provider.last_public_request, provider.last_public_response, snapshot(cfg)]).decode()
    assert KEY not in recorded and 'PRIVATE_REASONING' not in recorded and 'PRIVATE_ENCRYPTED' not in recorded
    assert KEY not in Path(cfg['openai']['budget_ledger']).read_text()


@pytest.mark.parametrize('phase', ['planner', 'repair', 'reviewer_observe', 'reviewer_decide'])
def test_schema_parity_with_existing_ollama_actions(tmp_path, phase):
    captured = {}
    def fake(endpoint, payload, timeout, limit):
        if endpoint.endswith('/api/show'):
            return b'{"details":{"format":"gguf"},"model_info":{"general.architecture":"fictional"}}'
        captured['grammar'] = json.loads(payload)['format']
        return json.dumps({'done': True, 'message': {'content': json.dumps(ACTION)}, 'prompt_eval_count': 10, 'eval_count': 10}).encode()
    ollama = OllamaProvider(configuration('live'), fake); ollama.phase = phase
    ollama.call([{'role': 'user', 'content': 'Fictional.'}], 100, 3)
    expected = captured['grammar']; expected['type'] = 'object'
    assert gateway.action_grammar(phase) == expected
    assert gateway.wire_schema(phase) == {'type': 'object', 'properties': {'result': expected},
                                           'required': ['result'], 'additionalProperties': False}


@pytest.mark.parametrize('wire', [ACTION, {'result': ACTION, 'extra': None}, {'result': []}, {}, None])
def test_wire_envelope_requires_exact_single_result_key_without_fallback(tmp_path, wire):
    cfg = config(tmp_path)
    provider = gateway.OpenAIProvider(cfg, transport(envelope(text=json.dumps(wire))))
    with pytest.raises(Failure, match='provider_response_invalid'):
        call(provider)
    assert snapshot(cfg)['settled_requests'] == 1
    assert provider.last_public_response['content'] == json.dumps(wire)


@pytest.mark.parametrize('shape', ['direct_action', 'result_envelope'])
def test_versioned_decoder_accepts_only_declared_wire_shapes(tmp_path, shape):
    cfg = config(tmp_path, version='1.1.1')
    wire = ACTION if shape == 'direct_action' else {'result': ACTION}
    provider = gateway.OpenAIProvider(cfg, transport(envelope(text=json.dumps(wire))))
    assert call(provider).action == ACTION
    assert provider.last_public_response['decoder_version'] == '1.0.1'
    assert provider.last_public_response['wire_shape'] == shape
    assert json.loads(provider.last_public_response['content']) == wire
    assert provider.last_public_request['text']['format']['schema'] == gateway.wire_schema('planner')


@pytest.mark.parametrize('wire', [
    {'action': 'refuse', 'reason': 'insufficient_evidence', 'result': ACTION},
    {'result': ACTION, 'extra': None}, {'result': []}, {}, None,
])
def test_versioned_decoder_rejects_ambiguous_or_unsupported_shapes(tmp_path, wire):
    cfg = config(tmp_path, version='1.1.1')
    provider = gateway.OpenAIProvider(cfg, transport(envelope(text=json.dumps(wire))))
    with pytest.raises(Failure, match='provider_response_invalid'):
        call(provider)
    assert provider.last_public_response['decoder_version'] == '1.0.1'
    assert provider.last_public_response['wire_shape'] is None
    assert snapshot(cfg)['settled_requests'] == 1


@pytest.mark.parametrize('shape', ['direct_action', 'result_envelope'])
def test_new_decoder_fake_http_discovery_extracts_and_fully_replays(tmp_path, shape):
    capture, idx, proposal = fixture(tmp_path)
    cfg = config(tmp_path, version='1.1.1')
    cfg['data_approval']['capture_sha256'] = [idx['capture']['sha256']]
    sent = []
    wire = proposal if shape == 'direct_action' else {'result': proposal}
    def fake_http(endpoint, payload, timeout, limit):
        assert endpoint == gateway.ENDPOINT
        sent.append(json.loads(payload))
        return json.dumps(envelope(text=json.dumps(wire))).encode()
    provider = gateway.OpenAIProvider(cfg, fake_http)
    output = tmp_path / 'run'
    result = discover(capture, cfg, output, {'data_class': 'synthetic'}, provider=provider)
    assert result['failure'] is None
    assert result['operation']['calls'] == 1 and len(sent) == 1
    records = [json.loads(line) for line in (output / 'extraction/bundle/records.jsonl').read_text().splitlines()]
    assert len(records) == 1
    assert records[0]['actor'] is None
    assert [(part['role'], part['text']) for part in records[0]['content']['parts']] == [('body', 'Keep this & that.')]
    retained = load_json(output / 'discovery/call-0001.json')
    assert retained['provider_response']['decoder_version'] == '1.0.1'
    assert retained['provider_response']['wire_shape'] == shape
    assert json.loads(retained['provider_response']['content']) == wire
    assert retained['response'] == proposal
    replay = verify(capture, output / 'finalized-plan.json', output / 'extraction')
    assert replay['status'] == 'passed'
    assert replay['canonical_files_compared'] == 8 and replay['model_calls'] == 0
    assert replay['source_map_characters'] == len('Keep this & that.')
    assert len(sent) == 1  # Replay never returns to the fake HTTP gateway.


@pytest.mark.parametrize('shape', ['direct_action', 'result_envelope'])
def test_new_decoder_cannot_bypass_unchanged_host_action_validation(tmp_path, shape):
    capture, idx, _ = fixture(tmp_path)
    cfg = config(tmp_path, version='1.1.1')
    cfg['data_approval']['capture_sha256'] = [idx['capture']['sha256']]
    cfg['budgets']['max_repairs'] = 0
    invalid = {'action': 'tool', 'name': 'shell', 'arguments': {'command': 'forbidden'}}
    wire = invalid if shape == 'direct_action' else {'result': invalid}
    provider = gateway.OpenAIProvider(cfg, transport(envelope(text=json.dumps(wire))))
    output = tmp_path / 'run'
    result = discover(capture, cfg, output, {'data_class': 'synthetic'}, provider=provider)
    assert result['failure'] == 'model_action_schema_invalid'
    assert not (output / 'extraction').exists()
    assert load_json(output / 'discovery/call-0001.json')['provider_response']['wire_shape'] == shape


@pytest.mark.parametrize('cap', ['3.01', '0', '-1', 'NaN', 'Infinity', '0.0000000001', 3.0])
def test_ledger_cap_invalid_without_file_creation(tmp_path, cap):
    with pytest.raises(Failure, match='openai_ledger_cap_invalid'):
        gateway.initialize_ledger(tmp_path / 'ledger', cap)
    assert not (tmp_path / 'ledger').exists()


def test_initialization_cannot_reset_existing_readiness_spend(tmp_path):
    cfg = config(tmp_path)
    call(gateway.OpenAIProvider(cfg, transport(envelope())))
    before = snapshot(cfg)
    with pytest.raises(Failure, match='openai_ledger_already_exists'):
        gateway.initialize_ledger(cfg['openai']['budget_ledger'])
    assert snapshot(cfg) == before
    assert before['reservations'] == 1 and before['committed_nanodollars'] > 0


def test_atomic_shared_reservations_respect_exact_budget_boundary(tmp_path):
    amount = gateway.reservation_nanodollars(8192)
    ledger = tmp_path / 'ledger'
    gateway.initialize_ledger(ledger, gateway._usd(amount * 2))
    def reserve(_):
        try:
            return gateway._reserve(ledger, b'fictional request', 8192)
        except Failure as exc:
            assert exc.code == 'provider_dollar_budget_exhausted'
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(reserve, range(8)))
    assert sum(value is not None for value in outcomes) == 2
    result = gateway.ledger_snapshot(ledger)
    assert result['available_nanodollars'] == 0
    assert result['pending_requests'] == 2


def test_insufficient_worst_case_reservation_blocks_before_transport(tmp_path):
    cfg = config(tmp_path, '0.01')
    def never(*args):
        pytest.fail('budget-exhausted call reached transport')
    provider = gateway.OpenAIProvider(cfg, never)
    with pytest.raises(Failure, match='provider_dollar_budget_exhausted'):
        call(provider)
    assert provider.gateway_requests == 0 and snapshot(cfg)['reservations'] == 0


@pytest.mark.parametrize('raw', [b'not JSON', b'{', b'[]', b'{"usage":{},"usage":{}}', b'{"unused":NaN}'])
def test_malformed_envelope_never_refunds_reservation(tmp_path, raw):
    cfg = config(tmp_path); provider = gateway.OpenAIProvider(cfg, transport(raw))
    with pytest.raises(Failure, match='provider_budget_usage_unknown'):
        call(provider)
    result = snapshot(cfg)
    assert result['outstanding_nanodollars'] == gateway.reservation_nanodollars(8192)
    assert result['settled_requests'] == 0


@pytest.mark.parametrize('usage', [None, {}, {'input_tokens': 10}, {'input_tokens': True, 'output_tokens': 1},
                                  {'input_tokens': 10, 'output_tokens': -1},
                                  {'input_tokens': 10, 'output_tokens': 8193},
                                  {'input_tokens': 10, 'output_tokens': 2, 'total_tokens': 13},
                                  {'input_tokens': 10, 'output_tokens': 2, 'input_tokens_details': {'cached_tokens': 11}}])
def test_missing_or_malformed_usage_is_not_reconciled(tmp_path, usage):
    cfg = config(tmp_path); value = envelope(); value['usage'] = usage
    provider = gateway.OpenAIProvider(cfg, transport(value))
    with pytest.raises(Failure, match='provider_budget_usage_unknown'):
        call(provider)
    assert snapshot(cfg)['pending_requests'] == 1
    assert provider.last_usage is None


@pytest.mark.parametrize('status', ['queued', 'in_progress'])
def test_nonterminal_usage_never_releases_reservation(tmp_path, status):
    cfg = config(tmp_path)
    provider = gateway.OpenAIProvider(cfg, transport(envelope(status=status, usage={'input_tokens': 0, 'output_tokens': 0})))
    with pytest.raises(Failure, match='provider_response_nonterminal') as error:
        call(provider)
    assert error.value.status == 'model_unavailable'
    assert snapshot(cfg)['pending_requests'] == 1
    assert snapshot(cfg)['committed_nanodollars'] == 0
    assert snapshot(cfg)['outstanding_nanodollars'] == gateway.reservation_nanodollars(8192)
    assert provider.last_public_response['status'] == status
    assert provider.last_usage is None


@pytest.mark.parametrize('field,value', [('id', 'malformed'), ('status', 'invented')])
def test_invalid_response_identity_is_unknown_charge_infrastructure_failure(tmp_path, field, value):
    cfg = config(tmp_path); reply = envelope(); reply[field] = value
    provider = gateway.OpenAIProvider(cfg, transport(reply))
    with pytest.raises(Failure, match='provider_budget_usage_unknown') as error:
        call(provider)
    assert error.value.status == 'model_unavailable'
    assert snapshot(cfg)['pending_requests'] == 1


def test_model_mismatch_retains_observed_model_and_full_reservation(tmp_path):
    cfg = config(tmp_path); reply = envelope(); reply['model'] = 'gpt-fictional-other-model'
    provider = gateway.OpenAIProvider(cfg, transport(reply))
    with pytest.raises(Failure, match='provider_model_mismatch'):
        call(provider)
    assert provider.last_public_response['model'] == 'gpt-fictional-other-model'
    assert snapshot(cfg)['pending_requests'] == 1


def test_missing_cache_breakdown_uses_conservative_price(tmp_path):
    cfg = config(tmp_path)
    reply = call(gateway.OpenAIProvider(cfg, transport(envelope(usage={'input_tokens': 100, 'output_tokens': 10}))))
    assert reply.usage['cached_tokens'] is None and reply.usage['reasoning_tokens'] is None
    assert snapshot(cfg)['committed_nanodollars'] == 100 * 250 + 10 * 1200


def test_long_context_price_applies_before_local_context_refusal(tmp_path):
    cfg = config(tmp_path)
    provider = gateway.OpenAIProvider(cfg, transport(envelope(usage={'input_tokens': 272001, 'output_tokens': 10})))
    with pytest.raises(Failure, match='provider_context_limit'):
        call(provider)
    assert snapshot(cfg)['committed_nanodollars'] == 272001 * 500 + 10 * 1800
    assert provider.last_usage['input_tokens'] == 272001


@pytest.mark.parametrize('kind', ['incomplete', 'refusal', 'invalid_action', 'failed'])
def test_failed_content_retains_usage_without_hidden_reasoning(tmp_path, kind):
    cfg = config(tmp_path); value = envelope(status=kind if kind in ('incomplete', 'failed') else 'completed')
    expected = {'incomplete': 'provider_output_incomplete', 'failed': 'provider_response_not_completed',
                'refusal': 'provider_refused', 'invalid_action': 'provider_response_invalid'}[kind]
    if kind == 'refusal':
        value['output'][1]['content'] = [{'type': 'refusal', 'refusal': 'Fictional policy refusal'}]
    elif kind == 'invalid_action':
        value['output'][1]['content'][0]['text'] = 'This is not JSON.'
    provider = gateway.OpenAIProvider(cfg, transport(value))
    with pytest.raises(Failure, match=expected):
        call(provider)
    assert snapshot(cfg)['settled_requests'] == 1
    assert provider.last_usage['output_tokens'] == 50
    assert 'PRIVATE_REASONING' not in C(provider.last_public_response).decode()


def test_transport_error_is_sanitized_and_never_refunded(tmp_path):
    cfg = config(tmp_path)
    def broken(*args):
        raise URLError('fictional transport error containing ' + KEY)
    provider = gateway.OpenAIProvider(cfg, broken)
    with pytest.raises(Failure, match='provider_transport_error') as error:
        call(provider)
    assert KEY not in str(error.value)
    assert snapshot(cfg)['pending_requests'] == 1


def test_killed_process_leaves_durable_full_reservation(tmp_path):
    cfg = config(tmp_path)
    def child():
        def killed(*args):
            os._exit(0)
        call(gateway.OpenAIProvider(cfg, killed))
    process = multiprocessing.get_context('fork').Process(target=child)
    process.start(); process.join(5)
    assert process.exitcode == 0
    result = snapshot(cfg)
    assert result['pending_requests'] == 1
    assert result['outstanding_nanodollars'] == gateway.reservation_nanodollars(8192)


@pytest.mark.parametrize('field,value', [('endpoint', 'https://api.openai.com.evil.invalid/v1/responses'),
                                        ('endpoint', 'http://api.openai.com/v1/responses'),
                                        ('endpoint', gateway.ENDPOINT + '?secret=fictional'),
                                        ('model', 'some-other-model')])
def test_endpoint_and_model_never_fallback(tmp_path, field, value):
    cfg = config(tmp_path); cfg[field] = value
    with pytest.raises(Failure):
        gateway.OpenAIProvider(cfg, transport(envelope()))
    assert snapshot(cfg)['reservations'] == 0


def test_missing_key_and_unsafe_ledger_fail_before_request(tmp_path, monkeypatch):
    cfg = config(tmp_path); provider = gateway.OpenAIProvider(cfg, transport(envelope()))
    monkeypatch.delenv('OPENAI_API_KEY')
    with pytest.raises(Failure, match='provider_api_key_missing'):
        call(provider)
    assert snapshot(cfg)['reservations'] == 0
    link = tmp_path / 'symlink'; link.symlink_to(cfg['openai']['budget_ledger'])
    with pytest.raises(Failure, match='symlink'):
        gateway.ledger_snapshot(link)
    with pytest.raises(Failure, match='absolute'):
        gateway.initialize_ledger('relative-ledger')


def test_torn_ledger_is_fail_closed(tmp_path):
    cfg = config(tmp_path); path = Path(cfg['openai']['budget_ledger'])
    path.write_bytes(path.read_bytes() + b'{"operation":')
    with pytest.raises(Failure, match='openai_ledger_invalid'):
        gateway.ledger_snapshot(path)


def test_https_transport_disables_proxies_refuses_redirects_and_hides_error_body(tmp_path, monkeypatch):
    cfg = config(tmp_path); provider = gateway.OpenAIProvider(cfg)
    captured = {}
    class Opener:
        def open(self, request, timeout):
            captured['request'] = request
            raise HTTPError(gateway.ENDPOINT, 401, 'Unauthorized', {}, io.BytesIO(('secret echo ' + KEY).encode()))
    def fake_opener(*handlers):
        captured['handlers'] = handlers
        return Opener()
    monkeypatch.setattr(gateway, 'build_opener', fake_opener)
    with pytest.raises(Failure, match='provider_http_error') as error:
        call(provider)
    assert captured['handlers'][0].proxies == {}
    assert isinstance(captured['handlers'][1], gateway._NoRedirect)
    assert captured['request'].get_header('Authorization') == 'Bearer ' + KEY
    assert error.value.http_details == {'status_code': 401, 'body_retained': False}
    assert KEY not in str(error.value) and KEY not in C(error.value.http_details).decode()
    with pytest.raises(Failure, match='provider_redirect_refused'):
        captured['handlers'][1].redirect_request(None, None, 302, '', {}, 'https://fictional.invalid')


def test_http_error_retains_only_bounded_machine_identifiers(tmp_path, monkeypatch):
    cfg = config(tmp_path); provider = gateway.OpenAIProvider(cfg)
    class Opener:
        def open(self, request, timeout):
            body = {'error': {'type': 'invalid_request_error', 'code': 'invalid_json_schema',
                              'param': 'text.format.schema', 'message': 'Secret echo: ' + KEY,
                              'request': {'Authorization': KEY}}}
            raise HTTPError(gateway.ENDPOINT, 400, KEY, {'X-Secret': KEY}, io.BytesIO(json.dumps(body).encode()))
    monkeypatch.setattr(gateway, 'build_opener', lambda *handlers: Opener())
    with pytest.raises(Failure, match='provider_http_error') as error:
        call(provider)
    assert error.value.http_details == {'status_code': 400, 'body_retained': False, 'error_identifiers': {
        'type': 'invalid_request_error', 'code': 'invalid_json_schema', 'param': 'text.format.schema'}}
    assert KEY not in C(error.value.http_details).decode()
    assert snapshot(cfg)['pending_requests'] == 1


def test_response_byte_limit_keeps_full_reservation(tmp_path):
    cfg = config(tmp_path); cfg['budgets']['max_response_bytes'] = 1024
    provider = gateway.OpenAIProvider(cfg, transport(b'x' * 1025))
    with pytest.raises(Failure, match='provider_response_byte_limit'):
        call(provider)
    assert snapshot(cfg)['pending_requests'] == 1


def test_request_byte_limit_has_no_gateway_request(tmp_path):
    cfg = config(tmp_path); cfg['budgets']['max_input_token_charge'] = 1
    provider = gateway.OpenAIProvider(cfg, transport(envelope()))
    with pytest.raises(Failure, match='provider_request_byte_limit'):
        call(provider)
    assert provider.gateway_requests == 0 and snapshot(cfg)['reservations'] == 0
