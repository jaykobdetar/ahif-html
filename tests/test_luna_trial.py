from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import pytest
from ahif_html.common import Failure, load_json, sha, write_json

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('luna_trial_tests', ROOT / 'scripts/run_luna_trial.py')
runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)


def config(tmp_path, version='1.1.0'):
    value = load_json(ROOT / 'examples/model-config.remote-tunnel.example.json')
    value.update(version=version, endpoint='https://api.openai.com/v1/responses', model='gpt-5.6-luna',
                 provider_location='hosted', tunnel_declaration=None, reviewer=False, response_format='schema',
                 openai={'reasoning_effort': 'medium', 'api_key_env': 'OPENAI_API_KEY',
                         'budget_ledger': str(tmp_path / 'ledger.jsonl')})
    if version == '1.1.1': value['openai']['wire_mode'] = 'result_or_action'
    value['data_approval'].update(approved=True, capture_sha256=[sha((runner.CORPUS / (p + '.html')).read_bytes()) for p in runner.PAGES],
                                 declaration='Offline runner tests only; no inference or actual credentials.')
    path = tmp_path / 'config.json'; write_json(path, value); return path


@pytest.fixture
def trial(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'artifact_inventory', lambda: {'offline-test-frozen-source': 'fixed'})
    runner.prepare(config(tmp_path), tmp_path / 'trial')
    monkeypatch.setenv('OPENAI_API_KEY', 'fictional-not-an-api-key')
    return tmp_path / 'trial'


class FakeProcess:
    returncode = 0
    pid = 999999999
    def poll(self): return 0


def mock_worker(command, **kwargs):
    compile(command[2], '<offline-worker-check>', 'exec')
    assert all('evaluator-only' not in Path(arg).parts and not Path(arg).name.endswith('.gold.json') for arg in command[3:])
    assert kwargs['env']['OPENAI_API_KEY'] == 'fictional-not-an-api-key'
    target = Path(command[5]); target.mkdir()
    write_json(target / 'discovery-receipt.json', {'status': 'unresolved_plan', 'failure': 'offline_mock_only',
               'operation': {'calls': 1, 'actual_input_tokens': 0, 'actual_output_tokens': 0,
                             'tool_calls': 0, 'inspection': {'inspected_characters': 0}}})
    return FakeProcess()


def test_prepare_registers_24_round_robin_jobs_exact_fictional_inventory_and_baseline(trial):
    r = load_json(trial / 'registration.json')
    assert len(r['jobs']) == 24
    assert [j['capture'] for j in r['jobs'][:8]] == list(runner.PAGES)
    assert [j['attempt'] for j in r['jobs']] == [1] * 8 + [2] * 8 + [3] * 8
    assert r['shared_budget']['max_calls'] == 288 and r['shared_budget']['cap_usd'] == '3.00'
    assert len(r['capture_inventory']) == 8 and r['evaluation_use'] == 'development_diagnostic_all_pages'
    assert r['baseline']['sha256'] == sha((runner.BASELINE / 'trial-report.json').read_bytes())
    for job in r['jobs']:
        cfg = load_json(trial / (job['id'] + '.config.json'))
        assert cfg['reviewer'] is False and cfg['budgets']['max_calls'] == 12
        assert cfg['budgets']['max_output_tokens_per_call'] == 8192
        assert cfg['budgets']['max_output_tokens_total'] == 98304
    assert not (trial / 'trial-started.json').exists()
    runner.verify_frozen(trial, r)


def test_prepare_preserves_preexisting_ledger_readiness_usage(tmp_path, monkeypatch):
    path = config(tmp_path); ledger = tmp_path / 'ledger.jsonl'
    runner.initialize_ledger(ledger); original = ledger.read_bytes()
    monkeypatch.setattr(runner, 'initialize_ledger', lambda path: pytest.fail('must not initialize existing ledger'))
    runner.prepare(path, tmp_path / 'trial')
    assert ledger.read_bytes() == original


def test_missing_key_does_not_consume_fresh_destination(trial, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY')
    with pytest.raises(Failure, match='api_key_missing_or_invalid'): runner.run(trial)
    assert not (trial / 'trial-started.json').exists()


def test_explicit_key_file_is_read_only_and_never_in_public_artifacts(trial, tmp_path, monkeypatch):
    key = tmp_path / 'explicit-owner-key.txt'; key.write_text('fictional-not-an-api-key\n'); key.chmod(0o664)
    before = key.stat().st_mode
    monkeypatch.delenv('OPENAI_API_KEY'); monkeypatch.setattr(runner.subprocess, 'Popen', mock_worker)
    result = runner.run(trial, key_file=key)
    assert len(result['results']) == 24 and key.stat().st_mode == before
    for path in trial.rglob('*'):
        if path.is_file():
            assert b'fictional-not-an-api-key' not in path.read_bytes()
            assert str(key).encode() not in path.read_bytes()


def test_key_symlink_and_multi_line_values_refused(tmp_path):
    key = tmp_path / 'key'; key.write_text('fictional-one\nfictional-two')
    with pytest.raises(Failure, match='api_key_missing_or_invalid'): runner.supplied_key(key)
    link = tmp_path / 'link'; link.symlink_to(key)
    with pytest.raises(Failure, match='symlink_path_refused'): runner.supplied_key(link)


def test_mocked_run_retains_every_round_and_pooled_repeated_denominators(trial, monkeypatch):
    monkeypatch.setattr(runner.subprocess, 'Popen', mock_worker)
    r = runner.run(trial)
    assert len(r['results']) == 24 and r['observed_counts']['calls']['value'] == 24
    assert r['pooled_repeated_inventory']['contribution_recall']['denominator'] == 78
    for number in ('1', '2', '3'):
        assert r['rounds'][number]['contribution_recall']['denominator'] == 26
        assert r['rounds'][number]['contribution_precision']['value'] is None
        assert r['attribution_denominators_by_round'][number]['known_reference'] == 20
        assert r['attribution_denominators_by_round'][number]['unknown_reference'] == 6
    assert len(r['repeat_comparisons']) == 24 and len(r['per_page_baseline_comparisons']) == 24
    assert r['qwen_primary_baseline']['contribution_recall']['numerator'] == 13
    with pytest.raises(Failure, match='trial_cannot_restart'): runner.run(trial)


def test_dollar_budget_stop_preserves_all_remaining_attempts(trial, monkeypatch):
    def worker(command, **kw):
        result = mock_worker(command, **kw)
        write_json(Path(command[5]) / 'discovery-receipt.json', {'status': 'resource_limit',
                   'failure': 'provider_dollar_budget_exhausted', 'operation': {'calls': 1}})
        return result
    monkeypatch.setattr(runner.subprocess, 'Popen', worker)
    r = runner.run(trial)
    assert r['stop_reason'] == 'shared_api_budget_or_ledger_stop'
    assert sum(e['status'] == 'not_run' for e in r['results']) == 23
    assert r['pooled_repeated_inventory']['contribution_recall']['denominator'] == 78
    assert r['ledger_before'] == r['ledger_after']


def test_launch_failure_is_zero_calls_without_loss_of_reference_inventory(trial, monkeypatch):
    def failed(*args, **kwargs): raise OSError('offline launch failure')
    monkeypatch.setattr(runner.subprocess, 'Popen', failed)
    r = runner.run(trial)
    assert r['provider_call_budget_charge'] == 0 and r['observed_counts']['calls']['value'] == 0
    assert r['pooled_repeated_inventory']['contribution_recall']['denominator'] == 78


def test_missing_worker_receipt_keeps_unknown_usage_and_full_reserved_call_charge(trial, monkeypatch):
    monkeypatch.setattr(runner.subprocess, 'Popen', lambda *args, **kw: FakeProcess())
    r = runner.run(trial)
    assert r['provider_call_budget_charge'] == 12
    assert r['observed_counts']['calls']['value'] is None
    assert len(r['results']) == 24 and r['results'][1]['status'] == 'not_run'


@pytest.mark.parametrize('kind', ['timeout', 'oserror', 'scalar', 'malformed_output'])
def test_verifier_failures_remain_in_report_and_never_count_corrupt_output(trial, monkeypatch, kind):
    count = []
    def worker(command, **kw):
        p = mock_worker(command, **kw); count.append(command)
        if len(count) == 1:
            target = Path(command[5]) / 'extraction/bundle'; target.mkdir(parents=True)
            (target / 'records.jsonl').write_text('{invalid JSON\n')
        return p
    def verify(*args, **kw):
        if kind == 'timeout': raise subprocess.TimeoutExpired('offline test', 70)
        if kind == 'oserror': raise OSError('offline test')
        return subprocess.CompletedProcess([], 0, '[]' if kind == 'scalar' else '{"status":"failed"}', '')
    monkeypatch.setattr(runner.subprocess, 'Popen', worker); monkeypatch.setattr(runner.subprocess, 'run', verify)
    r = runner.run(trial)
    assert r['status'] == 'failed_integrity' and len(r['results']) == 24
    assert r['results'][0]['metrics']['end_to_end_usable_recall']['numerator'] == 0
    assert r['pooled_repeated_inventory']['contribution_recall']['denominator'] == 78


def test_registration_and_gold_tamper_after_last_job_keeps_original_denominators(trial, monkeypatch):
    count = []; digest = sha((trial / 'registration.json').read_bytes())
    def worker(command, **kw):
        result = mock_worker(command, **kw); count.append(command)
        if len(count) == 24:
            p = trial / 'registration.json'; p.write_text(p.read_text() + '\n')
            p = trial / 'evaluator-only/cards-a.gold.json'; g = load_json(p); g['contributions'] = []; write_json(p, g)
        return result
    monkeypatch.setattr(runner.subprocess, 'Popen', worker)
    r = runner.run(trial)
    assert r['status'] == 'failed_integrity' and r['registration_sha256'] == digest
    assert r['pooled_repeated_inventory']['contribution_recall']['denominator'] == 78


def test_unconfirmed_owned_worker_cleanup_blocks_further_jobs_and_truthfully_marks_finish(trial, monkeypatch):
    class BadProcess:
        returncode = None; pid = 999999999
        def poll(self): raise OSError('offline monitor failure')
    monkeypatch.setattr(runner.subprocess, 'Popen', lambda *args, **kw: BadProcess())
    monkeypatch.setattr(runner, 'terminate_owned', lambda process: {'status': 'termination_unconfirmed'})
    r = runner.run(trial)
    assert r['cleanup_required'] and r['stop_reason'] == 'owned_worker_cleanup_required'
    assert load_json(trial / 'inference-finished.json')['no_more_provider_calls'] is False
    assert len(r['results']) == 24


def test_frozen_baseline_and_configs_are_independently_bound(trial):
    registration = load_json(trial / 'registration.json')
    p = trial / registration['baseline']['path']; p.write_text(p.read_text() + '\n')
    with pytest.raises(Failure, match='trial_frozen_baseline_changed'): runner.verify_frozen(trial, registration)


def test_stricter_existing_ledger_is_not_mislabeled_three_dollars(tmp_path):
    from ahif_html.openai_provider import initialize_ledger
    path = config(tmp_path); initialize_ledger(tmp_path / 'ledger.jsonl', cap_usd='2.00')
    with pytest.raises(Failure, match='trial_requires_registered_three_dollar_cap'):
        runner.prepare(path, tmp_path / 'trial')
    assert not (tmp_path / 'trial').exists()


def test_preexisting_unsettled_readiness_charge_is_preserved_without_reset(trial, monkeypatch):
    from ahif_html.openai_provider import _reserve
    registration = load_json(trial / 'registration.json')
    _reserve(registration['shared_budget']['budget_ledger'], b'{"fictional":"readiness"}', 64)
    monkeypatch.setattr(runner.subprocess, 'Popen', mock_worker)
    result = runner.run(trial)
    assert len(result['results']) == 24 and result['stop_reason'] is None
    assert result['ledger_before'] == result['ledger_after']
    assert result['ledger_after']['pending_requests'] == 1
    assert result['ledger_after']['outstanding_nanodollars'] > 0


@pytest.mark.parametrize('failure,status,reason', [
    ('provider_response_invalid', 'unresolved_plan', 'provider_usage_unavailable'),
    ('provider_budget_usage_unknown', 'model_unavailable', 'shared_api_budget_or_ledger_stop'),
    ('provider_response_nonterminal', 'model_unavailable', 'provider_infrastructure_unavailable')])
def test_unknown_usage_stops_later_jobs_without_making_unknown_cost_zero(trial, monkeypatch, failure, status, reason):
    def worker(command, **kw):
        process = mock_worker(command, **kw)
        write_json(Path(command[5]) / 'discovery-receipt.json', {'status': status,
                   'failure': failure, 'operation': {'calls': 1, 'actual_input_tokens': None, 'actual_output_tokens': None}})
        return process
    monkeypatch.setattr(runner.subprocess, 'Popen', worker)
    result = runner.run(trial)
    assert result['stop_reason'] == reason
    assert result['observed_counts']['input_tokens']['value'] is None
    assert len(result['results']) == 24 and result['results'][1]['status'] == 'not_run'


def test_new_pending_reservation_stops_remaining_jobs_and_is_not_refunded(trial, monkeypatch):
    from ahif_html.openai_provider import _reserve
    registration = load_json(trial / 'registration.json')
    def worker(command, **kw):
        process = mock_worker(command, **kw)
        _reserve(registration['shared_budget']['budget_ledger'], b'{"fictional":"unknown-response"}', 8192)
        return process
    monkeypatch.setattr(runner.subprocess, 'Popen', worker)
    result = runner.run(trial)
    assert result['stop_reason'] == 'provider_unsettled_request'
    assert result['ledger_after']['pending_requests'] == 1
    assert result['ledger_after']['outstanding_nanodollars'] > 0
    assert result['results'][1]['status'] == 'not_run'


def test_accepted_verification_relocates_inputs_varies_hash_seed_and_removes_key(trial, monkeypatch):
    from ahif_html.executor import extract
    registration = load_json(trial / 'registration.json'); job = registration['jobs'][0]
    page = registration['capture_inventory'][job['capture']]
    destination = trial / job['id'] / 'extraction'
    extract(trial / page['files']['capture']['path'], trial / page['files']['plan']['path'], destination,
            metadata=load_json(trial / page['files']['metadata']['path']))
    commands = []
    def verify(command, **kw):
        commands.append((command, kw))
        assert 'OPENAI_API_KEY' not in kw['env']
        return subprocess.CompletedProcess([], 0, '{"status":"passed","canonical_files_compared":8}', '')
    monkeypatch.setattr(runner.subprocess, 'run', verify)
    checked = runner.verify_accepted(trial, registration, job)
    assert checked['status'] == 'passed' and len(commands) == 2
    assert [kw['env']['PYTHONHASHSEED'] for _, kw in commands] == ['0', '117']
    assert 'replay-inputs' in commands[1][0][5] and 'replay-inputs' not in commands[0][0][5]
    assert Path(commands[0][0][5]).read_bytes() == Path(commands[1][0][5]).read_bytes()


def test_new_wire_designation_binds_original_failure_history_and_keeps_qwen_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'artifact_inventory', lambda: {'offline-test-frozen-source': 'fixed'})
    original_history = {name: (runner.INTEGRATION_HISTORY / name).read_bytes() for name in ('registration.json', 'trial-report.json')}
    path = config(tmp_path, version='1.1.1'); trial = tmp_path / 'trial'
    registration = runner.prepare(path, trial)
    assert registration['designation'] == 'luna-discovery-v2-development-2'
    assert registration['model_configuration_version'] == '1.1.1'
    assert registration['wire_mode'] == 'result_or_action'
    assert len(registration['jobs']) == 24
    history = registration['integration_failure_history'][0]
    assert history['role'] == 'transport_integration_failure_history_not_semantic_baseline'
    assert history['reported_token_totals_interpretation'] == 'known_lower_bound_due_to_cancelled_inflight_request'
    for name, data in original_history.items():
        artifact = history['artifacts'][name]
        assert artifact['sha256'] == sha(data) and (trial / artifact['path']).read_bytes() == data
        assert (runner.INTEGRATION_HISTORY / name).read_bytes() == data
    assert registration['baseline']['sha256'] == sha((runner.BASELINE / 'trial-report.json').read_bytes())
    runner.verify_frozen(trial, registration)
    artifact = trial / history['artifacts']['trial-report.json']['path']
    artifact.write_bytes(artifact.read_bytes() + b'\n')
    with pytest.raises(Failure, match='trial_frozen_integration_history_changed'):
        runner.verify_frozen(trial, registration)


def test_old_wire_designation_stays_distinct_without_new_history(trial):
    registration = load_json(trial / 'registration.json')
    assert registration['designation'] == 'luna-discovery-v2-development-1'
    assert registration['wire_mode'] == 'wrapped_result'
    assert registration['integration_failure_history'] == []


def test_publication_defaults_are_shipped_and_bind_original_registration_hashes():
    for directory in (runner.BASELINE, runner.INTEGRATION_HISTORY):
        assert directory.is_relative_to(ROOT / 'provenance')
        value, raw, manifest, _ = runner.published_registration(directory)
        report = load_json(directory / 'trial-report.json')
        assert manifest['mode'] == 'publication_derivative'
        assert manifest['published_sha256'] == sha(raw)
        assert report['registration_sha256'] == manifest['original_sha256']
        assert manifest['original_sha256'] != sha(raw)
        assert '/home/' not in raw.decode()
        assert value
        report, report_raw, report_manifest, _ = runner.published_artifact(directory, 'trial-report.json')
        assert report_manifest['published_sha256'] == sha(report_raw)
        assert report_manifest['mode'] == ('publication_derivative' if directory == runner.BASELINE else 'verbatim')
        assert report['registration_sha256'] == manifest['original_sha256']


def test_explicit_published_provenance_works_without_private_qa_or_default_paths(tmp_path, monkeypatch):
    baseline = tmp_path / 'published-qwen'; history = tmp_path / 'published-history'
    for source, destination in ((runner.BASELINE, baseline), (runner.INTEGRATION_HISTORY, history)):
        destination.mkdir()
        for name in ('registration.json', 'registration-publication.json', 'trial-report.json', 'report-publication.json'):
            shutil.copyfile(source / name, destination / name)
    monkeypatch.setattr(runner, 'BASELINE', tmp_path / 'missing-default-baseline')
    monkeypatch.setattr(runner, 'INTEGRATION_HISTORY', tmp_path / 'missing-default-history')
    monkeypatch.setattr(runner, 'artifact_inventory', lambda: {'offline-test-frozen-source': 'fixed'})
    read = runner.safe_read
    def no_private_read(path, *args, **kwargs):
        assert not Path(path).is_relative_to(runner.ROOT / 'qa')
        assert not Path(path).is_relative_to(runner.ROOT / 'private')
        return read(path, *args, **kwargs)
    monkeypatch.setattr(runner, 'safe_read', no_private_read)
    destination = tmp_path / 'trial'
    registration = runner.prepare(config(tmp_path, '1.1.1'), destination,
                                  baseline=baseline, integration_history=history)
    assert registration['publication_interface_version'] == '1.0.0'
    runner.verify_frozen(destination, registration)
    artifact = registration['baseline']['publication_manifest']
    (destination / artifact['path']).write_bytes(b'{}\n')
    with pytest.raises(Failure, match='trial_frozen_baseline_provenance_changed'):
        runner.verify_frozen(destination, registration)


def test_publication_manifest_is_required_and_cannot_silently_rebind_history(tmp_path):
    directory = tmp_path / 'baseline'; directory.mkdir()
    for name in ('registration.json', 'registration-publication.json', 'trial-report.json', 'report-publication.json'):
        shutil.copyfile(runner.BASELINE / name, directory / name)
    manifest_path = directory / 'registration-publication.json'
    manifest = load_json(manifest_path); manifest['original_sha256'] = '0' * 64
    write_json(manifest_path, manifest)
    with pytest.raises(Failure, match='baseline_registration_mismatch'):
        runner.prepare(config(tmp_path), tmp_path / 'trial', baseline=directory)
    assert not (tmp_path / 'ledger.jsonl').exists()
    manifest_path.unlink()
    with pytest.raises(Failure):
        runner.published_registration(directory)


def test_changed_published_registration_is_refused_before_trial_creation(tmp_path):
    directory = tmp_path / 'baseline'; directory.mkdir()
    for name in ('registration.json', 'registration-publication.json', 'trial-report.json', 'report-publication.json'):
        shutil.copyfile(runner.BASELINE / name, directory / name)
    path = directory / 'registration.json'; path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(Failure, match='publication_registration_invalid'):
        runner.prepare(config(tmp_path), tmp_path / 'trial', baseline=directory)
    assert not (tmp_path / 'trial').exists()


def test_published_report_manifest_is_bound_without_changing_baseline_scores(trial):
    registration = load_json(trial / 'registration.json')
    baseline = registration['baseline']
    manifest = load_json(runner.BASELINE / 'report-publication.json')
    assert baseline['report_publication_mode'] == 'publication_derivative'
    assert baseline['original_report_sha256'] == manifest['original_sha256']
    assert len(manifest['changes']) == 18
    report = load_json(trial / baseline['path'])
    assert report['same_inventory_by_arm']['planner']['contribution_recall']['numerator'] == 13
    artifact = baseline['report_publication_manifest']
    (trial / artifact['path']).write_bytes(b'{}\n')
    with pytest.raises(Failure, match='trial_frozen_baseline_provenance_changed'):
        runner.verify_frozen(trial, registration)
