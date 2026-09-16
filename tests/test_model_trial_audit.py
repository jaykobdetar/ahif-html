"""Trial-integrity checks using fake workers/transports; never live inference."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json

import pytest

from ahif_html.common import Failure, load_json, safe_read, sha, write_json
from ahif_html.planner import map_references
from ahif_html.provider import OllamaProvider, validate_config
from test_planner import configuration

ROOT = Path(__file__).resolve().parents[1]


def runner():
    spec = spec_from_file_location('ahif_html_trial_test_target', ROOT / 'scripts/run_model_trial.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def no_receipt_trial(tmp_path, monkeypatch):
    """An intentionally failed fake worker consumes a conservative reservation."""
    module = runner()
    cfg = configuration('live')
    cfg['data_approval']['capture_sha256'] = [
        sha(safe_read(ROOT / 'examples/fictional' / (name + '.html')))
        for name in ('reviews', 'forum', 'comments')]
    cfg['data_approval']['declaration'] = 'Fictional test only; subprocess execution replaced by a fake.'
    config_path = tmp_path / 'model-config.json'; write_json(config_path, cfg)
    destination = tmp_path / 'trial'
    invoked = []
    class NoReceiptProcess:
        returncode = 1
        def __init__(self, command, **kwargs):
            invoked.append((command, kwargs))
        def poll(self):
            return self.returncode
    monkeypatch.setattr(module.subprocess, 'Popen', NoReceiptProcess)
    monkeypatch.setattr(module.sys, 'argv', ['run_model_trial.py', '--config', str(config_path),
                        '--out', str(destination), '--max-provider-calls', '1'])
    module.main()
    return load_json(destination / 'trial-report.json'), destination, invoked


def test_skipped_reviewer_keeps_registered_arm_and_denominator(tmp_path, monkeypatch):
    report, _, _ = no_receipt_trial(tmp_path, monkeypatch)
    reviewer = next(v for v in report['results'] if v['id'] == 'comments-reviewer')
    assert reviewer['status'] == 'not_run'
    assert reviewer.get('reviewer') is True
    arms = report['same_held_out_inventory_by_arm']
    expected = len(load_json(ROOT / 'examples/fictional/comments.gold.json')['contributions'])
    for name in ('planner', 'reviewer'):
        metric = arms[name]['contribution_recall']
        assert metric['numerator'] == 0
        assert metric['denominator'] == expected


def test_unreceipted_reservation_is_not_reported_as_actual_calls(tmp_path, monkeypatch):
    report, _, _ = no_receipt_trial(tmp_path, monkeypatch)
    assert report['stop_reason'] == 'worker_no_receipt'
    assert report['actual_provider_calls'] is None
    assert report['actual_tool_calls'] is None
    assert report['actual_inspected_characters'] is None
    assert report['within_call_limit'] is True


def test_gold_not_in_worker_command_and_all_failed_jobs_are_scored(tmp_path, monkeypatch):
    report, destination, invoked = no_receipt_trial(tmp_path, monkeypatch)
    assert len(invoked) == 1
    command, kwargs = invoked[0]
    assert kwargs['cwd'] == destination / 'captures'
    assert not any('.gold.json' in str(v) or 'evaluator-only' in str(v) for v in command)
    assert len(report['results']) == 5
    for entry in report['results']:
        assert entry['metrics']['contribution_recall']['denominator'] > 0
        assert entry['metrics']['contribution_recall']['numerator'] == 0


def test_incomplete_provider_reply_still_retains_returned_usage():
    def transport(endpoint, payload, timeout, limit):
        if endpoint.endswith('/api/show'):
            return b'{"details":{"format":"gguf"},"model_info":{"general.architecture":"test"}}'
        return json.dumps({'done': False, 'message': {'content': '{"action":"refuse","reason":"insufficient_evidence"}'},
                           'prompt_eval_count': 91, 'eval_count': 17}).encode()
    provider = OllamaProvider(configuration('live'), transport)
    with pytest.raises(Failure, match='provider_response_invalid'):
        provider.call([{'role': 'user', 'content': 'Synthetic.'}], 50, 3)
    assert provider.last_usage is not None
    assert provider.last_usage['input_tokens'] == 91
    assert provider.last_usage['output_tokens'] == 17


def test_reference_aliases_leave_literal_selector_predicates_unchanged():
    ref = 'sha256:' + 'a' * 64 + ':2'
    value = {'node_ref': 'n2', 'arguments': {'criteria': {'attribute': 'id', 'equals': 'n2'},
                                           'literal_query': 'n2'},
             'source': {'node': 'n2', 'kind': 'attribute', 'attribute': 'data-post-id'},
             'attrs': [{'name': 'parent', 'value': 'n2'}], 'text': 'n2'}
    translated = map_references(value, {'n2': ref})
    assert translated['node_ref'] == ref
    assert translated['source']['node'] == ref
    assert translated['arguments']['criteria']['equals'] == 'n2'
    assert translated['arguments']['literal_query'] == 'n2'
    assert translated['attrs'][0]['value'] == 'n2'
    assert translated['text'] == 'n2'


def test_remote_tunnel_still_refuses_nonloopback_gateway():
    cfg = configuration('live')
    cfg.update(provider_location='remote_tunnel', endpoint='http://example.invalid:11434',
        tunnel_declaration={'provider': 'runpod', 'resource_id': 'fictional-test-pod',
                            'authorization': 'No real provider invocation in this test.',
                            'max_hourly_cost_usd': '0.50', 'max_runtime_seconds': 60})
    with pytest.raises(Failure, match='provider_endpoint_not_loopback'):
        validate_config(cfg)


def test_trial_proposal_cannot_omit_structurally_known_quote_boundary(tmp_path):
    from test_executor import fixture
    from ahif_html.plans import validate_plan
    _, _, evidence, plan = fixture(tmp_path)
    selected = plan['contributions'][0]
    selected['parts'] = [selected['parts'][0]]
    selected['parts'][0]['exclude'] = [selected['excluded'][0]['node']]
    # The body selector now contains an actual blockquote. Grounding alone cannot
    # justify folding it into the selected actor's uninterrupted body passage.
    with pytest.raises(Failure, match='quote|boundary|structur'):
        validate_plan(evidence, plan)
