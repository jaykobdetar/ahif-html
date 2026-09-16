#!/usr/bin/env python3
"""Separate, preregistered Luna development diagnostic: three rounds of eight pages.

No baseline file is edited. Only provider configuration/transport changes; all
source-linked execution and semantic scoring use the existing implementations.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
from ahif_html.common import Failure, check_path, fresh, load_json, safe_read, sha, write_json
from ahif_html.provider import validate_config
from ahif_html.evaluate import _aggregate, validate_splits

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('luna_baseline_runner', ROOT / 'scripts/run_discovery_v2.py')
old = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(old)
CORPUS = old.CORPUS
PAGES = old.PAGES
JOBS = tuple({'id': f'{page}-attempt-{attempt}', 'capture': page, 'arm': 'planner',
              'attempt': attempt, 'repeat': attempt > 1}
             for attempt in (1, 2, 3) for page in PAGES)
PUBLICATION_INTERFACE_VERSION = '1.0.0'
BASELINE = ROOT / 'provenance/evaluation-20260916/qwen'
INTEGRATION_HISTORY = ROOT / 'provenance/evaluation-20260916/luna-01'
CANONICAL_FILES = ('bundle/manifest.json', 'bundle/records.jsonl', 'evidence/capture-manifest.json',
                   'evidence/decisions.jsonl', 'evidence/finalized-plan.json', 'evidence/index.json',
                   'evidence/interpretation.json', 'evidence/source-map.jsonl')
terminate_owned = old.terminate_owned


def initialize_ledger(path):
    from ahif_html.openai_provider import initialize_ledger as initialize
    return initialize(path, cap_usd='3.00')


def ledger_snapshot(path):
    from ahif_html.openai_provider import ledger_snapshot as snapshot
    return snapshot(path)


def artifact_inventory():
    return {**old.artifact_inventory(),
            'scripts/run_luna_trial.py': sha(safe_read(Path(__file__)))}


def validate_trial_config(config):
    validate_config(config)
    if (config['version'] not in ('1.1.0', '1.1.1') or config['mode'] != 'live'
            or config['provider_location'] != 'hosted' or config['model'] != 'gpt-5.6-luna'
            or config['endpoint'] != 'https://api.openai.com/v1/responses'
            or config['reviewer'] or config['openai']['reasoning_effort'] != 'medium'
            or config['openai']['api_key_env'] != 'OPENAI_API_KEY'
            or not config['data_approval']['approved']
            or config['data_approval']['data_classes'] != ['synthetic']):
        raise Failure('luna_trial_configuration_mismatch')
    if config['version'] == '1.1.1' and config['openai'].get('wire_mode') != 'result_or_action':
        raise Failure('luna_trial_wire_mode_mismatch')
    return config


def published_artifact(directory, artifact):
    """Validate a published historical artifact and its original hash claim.

    This manifest is provenance, not a signature or a reconstruction of withheld
    values. The report retains its original registration-hash binding; new runs
    freeze both the published bytes and this manifest.
    """
    directory = check_path(directory)
    if artifact not in ('registration.json', 'trial-report.json'):
        raise Failure('publication_artifact_unsupported')
    manifest_name = 'registration-publication.json' if artifact == 'registration.json' else 'report-publication.json'
    raw = safe_read(directory / artifact)
    value = load_json(directory / artifact)
    manifest_raw = safe_read(directory / manifest_name)
    manifest = load_json(directory / manifest_name)
    fields = {'publication_version', 'artifact', 'mode', 'original_sha256', 'published_sha256', 'changes'}
    if (not isinstance(value, dict) or not isinstance(manifest, dict) or set(manifest) != fields
            or manifest['publication_version'] != PUBLICATION_INTERFACE_VERSION
            or manifest['artifact'] != artifact
            or manifest['published_sha256'] != sha(raw)
            or not isinstance(manifest['original_sha256'], str)
            or not re.fullmatch(r'[0-9a-f]{64}', manifest['original_sha256'])
            or not isinstance(manifest['changes'], list)):
        raise Failure('publication_registration_invalid')
    if manifest['mode'] == 'verbatim':
        if manifest['changes'] or manifest['original_sha256'] != sha(raw):
            raise Failure('publication_registration_invalid')
    elif manifest['mode'] == 'publication_derivative':
        allowed = {'/shared_budget/budget_ledger': 'publication-redacted:local-budget-ledger',
                   '/tunnel_declaration/resource_id': 'publication-redacted:disposed-resource'} if artifact == 'registration.json' else {}
        seen = set()
        for change in manifest['changes']:
            if not isinstance(change, dict) or set(change) != {'json_pointer', 'operation', 'replacement'}:
                raise Failure('publication_registration_invalid')
            pointer = change['json_pointer']
            if (artifact == 'trial-report.json' and isinstance(pointer, str)
                    and re.fullmatch(r'/results/[0-9]+/receipt/operation/tunnel_declaration/resource_id', pointer)):
                allowed[pointer] = 'publication-redacted:disposed-resource'
            if (not isinstance(pointer, str) or pointer not in allowed or pointer in seen
                    or change['operation'] != 'replace' or change['replacement'] != allowed[pointer]):
                raise Failure('publication_registration_invalid')
            selected = value
            try:
                for component in pointer.strip('/').split('/'):
                    selected = selected[int(component)] if isinstance(selected, list) else selected[component]
            except (KeyError, IndexError, TypeError, ValueError):
                raise Failure('publication_registration_invalid') from None
            if selected != change['replacement']:
                raise Failure('publication_registration_invalid')
            seen.add(pointer)
        if not seen or manifest['original_sha256'] == sha(raw):
            raise Failure('publication_registration_invalid')
    else:
        raise Failure('publication_registration_invalid')
    return value, raw, manifest, manifest_raw


def published_registration(directory):
    return published_artifact(directory, 'registration.json')


def prepare(config_path, destination, *, max_seconds=7200, baseline=None, integration_history=None):
    if type(max_seconds) is not int or not 1 <= max_seconds <= 7200:
        raise Failure('trial_budget_invalid')
    config = validate_trial_config(load_json(config_path))
    dataset = load_json(CORPUS / 'dataset.json'); validate_splits(dataset)
    by_id = {p['id']: p for p in dataset['pages']}
    if set(by_id) != set(PAGES): raise Failure('trial_inventory_mismatch')
    baseline = check_path(BASELINE if baseline is None else baseline)
    integration_history = check_path(INTEGRATION_HISTORY if integration_history is None else integration_history)
    baseline_registration, baseline_registration_raw, baseline_publication, baseline_publication_raw = published_registration(baseline)
    baseline_report, baseline_raw, baseline_report_publication, baseline_report_publication_raw = published_artifact(baseline, 'trial-report.json')
    if baseline_report['registration_sha256'] != baseline_publication['original_sha256']:
        raise Failure('baseline_registration_mismatch')
    if baseline_report['mechanical_integrity_failures']:
        raise Failure('baseline_integrity_failure')
    # Provider support is intentionally new. Corpus, prompts, tools, executor and
    # scorer must still match the scored Qwen source bytes, not just their labels.
    protected = {name: digest for name, digest in baseline_registration['implementation_and_input_sha256'].items()
                 if name.startswith(('src/ahif_html/', 'examples/discovery-v2/'))
                 and name not in ('src/ahif_html/provider.py', 'src/ahif_html/schemas/model-config.schema.json')}
    if any(sha(safe_read(ROOT / name)) != digest for name, digest in protected.items()):
        raise Failure('baseline_extraction_contract_changed')
    destination = check_path(destination)
    ledger_path = check_path(config['openai']['budget_ledger'])
    if ledger_path.is_relative_to(destination):
        raise Failure('ledger_must_be_outside_trial_destination')
    # A pre-existing ledger may include authorized readiness usage. Never reset it.
    if not ledger_path.exists(): initialize_ledger(ledger_path)
    ledger_initial = ledger_snapshot(ledger_path)
    if ledger_initial['cap_nanodollars'] != 3_000_000_000: raise Failure('trial_requires_registered_three_dollar_cap')
    ledger_raw = safe_read(ledger_path)
    history_raw = {}
    if config['version'] == '1.1.1':
        _, history_registration_raw, history_publication, history_publication_raw = published_registration(integration_history)
        history_report, history_report_raw, history_report_publication, history_report_publication_raw = published_artifact(integration_history, 'trial-report.json')
        history_raw = {'registration.json': history_registration_raw,
                       'registration-publication.json': history_publication_raw,
                       'trial-report.json': history_report_raw,
                       'report-publication.json': history_report_publication_raw}
        if history_report['registration_sha256'] != history_publication['original_sha256']:
            raise Failure('integration_history_registration_mismatch')
    with fresh(destination) as root:
        (root / 'captures').mkdir(); (root / 'evaluator-only').mkdir(mode=0o700)
        (root / 'evaluator-only/qwen-baseline.json').write_bytes(baseline_raw)
        (root / 'evaluator-only/qwen-registration.json').write_bytes(baseline_registration_raw)
        (root / 'evaluator-only/qwen-registration-publication.json').write_bytes(baseline_publication_raw)
        (root / 'evaluator-only/qwen-report-publication.json').write_bytes(baseline_report_publication_raw)
        history = []
        if history_raw:
            history_dir = root / 'evaluator-only/integration-history'; history_dir.mkdir()
            artifacts = {}
            for name, raw in history_raw.items():
                target = history_dir / ('trial-01-' + name); target.write_bytes(raw)
                artifacts[name] = {'path': target.relative_to(root).as_posix(), 'sha256': sha(raw)}
            history.append({'designation': 'luna-discovery-v2-development-1',
                            'role': 'transport_integration_failure_history_not_semantic_baseline',
                            'artifacts': artifacts, 'original_report_unchanged': history_report_publication['mode'] == 'verbatim',
                            'original_report_sha256': history_report_publication['original_sha256'],
                            'original_registration_sha256': history_publication['original_sha256'],
                            'registration_publication_mode': history_publication['mode'],
                            'reported_token_totals_interpretation': 'known_lower_bound_due_to_cancelled_inflight_request',
                            'usage_note': 'The original cancelled Session receipt retained a stale usage-known flag. Known call-log usage is a lower bound; the shared ledger retains the unknown request reservation.'})
        inventory = {}; configurations = {}
        for name in PAGES:
            page = by_id[name]; inventory[name] = {**page, 'evaluation_use': 'development_diagnostic', 'files': {}}
            for key in ('capture', 'metadata', 'gold', 'plan'):
                raw = safe_read(CORPUS / page[key])
                if key == 'capture' and sha(raw) not in config['data_approval']['capture_sha256']:
                    raise Failure('trial_capture_not_preapproved')
                previous = baseline_registration['capture_inventory'][name]['files'][key]['sha256']
                if sha(raw) != previous: raise Failure('trial_capture_differs_from_baseline')
                target = root / ('evaluator-only' if key in ('gold', 'plan') else 'captures') / page[key]
                target.write_bytes(raw)
                inventory[name]['files'][key] = {'path': target.relative_to(root).as_posix(), 'sha256': sha(raw)}
        for job in JOBS:
            cfg = json.loads(json.dumps(config)); cfg['reviewer'] = False; cfg['num_ctx'] = 16384
            cfg['data_approval']['capture_sha256'] = [inventory[job['capture']]['files']['capture']['sha256']]
            cfg['budgets'].update(max_calls=12, max_wall_seconds=300, max_tool_calls=64,
                                  max_inspected_characters=120000, max_output_tokens_per_call=8192,
                                  max_output_tokens_total=98304, max_input_tokens_total=196608,
                                  max_retries=0, max_repairs=2)
            validate_trial_config(cfg)
            path = root / (job['id'] + '.config.json'); write_json(path, cfg)
            configurations[job['id']] = sha(safe_read(path))
        registration = {'version': '1.0.0', 'designation': 'luna-discovery-v2-development-2' if config['version'] == '1.1.1' else 'luna-discovery-v2-development-1',
            'publication_interface_version': PUBLICATION_INTERFACE_VERSION,
            'model_configuration_version': config['version'],
            'wire_mode': config['openai'].get('wire_mode', 'wrapped_result'),
            'integration_failure_history': history,
            'mode': 'live', 'model': config['model'], 'provider_location': 'hosted',
            'endpoint': config['endpoint'], 'reasoning_effort': 'medium',
            'annotation_provenance': 'agent_authored_construction_truth', 'human_reviewed': False,
            'evaluation_use': 'development_diagnostic_all_pages', 'real_capture_pilot': 'not_run',
            'capture_inventory': inventory,
            'jobs': [{**j, 'family': by_id[j['capture']]['family'], 'split': 'development_diagnostic'} for j in JOBS],
            'per_job_budget': {'max_calls': 12, 'max_seconds': 300, 'max_output_tokens_per_call': 8192,
                               'num_ctx': 16384, 'max_tool_calls': 64, 'max_inspected_characters': 120000,
                               'max_extraction_output_bytes': 8388608},
            'shared_budget': {'max_calls': 288, 'max_seconds': max_seconds,
                              'max_trial_output_bytes': 268435456, 'cap_usd': '3.00',
                              'budget_ledger': str(ledger_path)},
            'ledger_at_registration': ledger_initial,
            'ledger_initial_prefix': {'byte_length': len(ledger_raw), 'sha256': sha(ledger_raw)},
            'implementation_and_input_sha256': artifact_inventory(),
            'baseline_protected_sha256': protected, 'configuration_sha256': configurations,
            'baseline': {'path': 'evaluator-only/qwen-baseline.json', 'sha256': sha(baseline_raw),
                         'original_report_sha256': baseline_report_publication['original_sha256'],
                         'report_publication_mode': baseline_report_publication['mode'],
                         'registration_sha256': baseline_publication['original_sha256'],
                         'published_registration': {'path': 'evaluator-only/qwen-registration.json', 'sha256': sha(baseline_registration_raw)},
                         'publication_manifest': {'path': 'evaluator-only/qwen-registration-publication.json', 'sha256': sha(baseline_publication_raw)},
                         'report_publication_manifest': {'path': 'evaluator-only/qwen-report-publication.json', 'sha256': sha(baseline_report_publication_raw)},
                         'selection': 'eight primary planner jobs only; original two repeats excluded'},
            'matching_policy': load_json(CORPUS / 'matching-policy.json'),
            'limitations': ['Three rounds reuse the same eight pages: pooled denominator 78 is repeated appearances, not 78 new contributions.',
                           'All pages are development diagnostics now; historical split labels are retained as provenance only.',
                           'Luna uses medium reasoning and 8192 output tokens/call; Qwen used thinking disabled and 4096. This is not an isolated causal model comparison.',
                           ('Version 1.1.1 explicitly accepts either one outer result wrapper or a direct original action, then applies unchanged host action validation; the request schema remains wrapped, json_schema strict:false. Ollama used direct server grammar.' if config['version'] == '1.1.1' else 'Luna uses json_schema strict:false transport and an outer required result wrapper, deterministically unwrapped before unchanged host action validation; Ollama used its direct server grammar.'),
                           'Existing unsettled readiness reservations remain charged in the shared ledger. A new unsettled trial request stops later jobs; no prior reservation is refunded or reset.',
                           'Hosted num_ctx 16384 is a returned-usage quota, not an API-side context setting; API requests are conservatively dollar-reserved against the documented full model context.',
                           'No gold, manual plan or baseline model output is passed to inference.',
                           'Every failure and budget-stopped job retains its full reference denominator. No best-of-three selection.']}
        write_json(root / 'registration.json', registration)
    return registration


def verify_frozen(destination, registration):
    if artifact_inventory() != registration['implementation_and_input_sha256']:
        raise Failure('trial_frozen_implementation_changed')
    for job, digest in registration['configuration_sha256'].items():
        if sha(safe_read(destination / (job + '.config.json'))) != digest:
            raise Failure('trial_frozen_configuration_changed')
    for page in registration['capture_inventory'].values():
        for item in page['files'].values():
            if sha(safe_read(destination / item['path'])) != item['sha256']:
                raise Failure('trial_frozen_capture_changed')
    if sha(safe_read(destination / registration['baseline']['path'])) != registration['baseline']['sha256']:
        raise Failure('trial_frozen_baseline_changed')
    for name in ('published_registration', 'publication_manifest', 'report_publication_manifest'):
        artifact = registration['baseline'].get(name)
        if artifact and sha(safe_read(destination / artifact['path'])) != artifact['sha256']:
            raise Failure('trial_frozen_baseline_provenance_changed')
    for history in registration.get('integration_failure_history', []):
        for artifact in history['artifacts'].values():
            if sha(safe_read(destination / artifact['path'])) != artifact['sha256']:
                raise Failure('trial_frozen_integration_history_changed')


def supplied_key(key_file=None):
    if key_file is None:
        key = os.environ.get('OPENAI_API_KEY', '')
    else:
        path = check_path(key_file); info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise Failure('api_key_file_invalid')
        # Explicitly supplied owner file is authorized even if its old mode is
        # broader than0600. Read only; never copy, chmod or log its path/content.
        try: key = safe_read(path, 16384).decode('utf8').strip()
        except (UnicodeError, OSError) as exc: raise Failure('api_key_file_invalid') from exc
    if not key or len(key) > 8192 or any(c.isspace() or ord(c) < 33 for c in key):
        raise Failure('api_key_missing_or_invalid', 'model_unavailable')
    return key


def score(destination, registration, entries, frozen_gold, baseline):
    old.score(destination, registration, entries, gold_override=frozen_gold)
    rounds = {str(n): _aggregate([e for e in entries if e['attempt'] == n]) for n in (1, 2, 3)}
    denominators = {str(n): {key: sum(e['attribution_denominators'][key] for e in entries if e['attempt'] == n)
                           for key in ('known_reference', 'unknown_reference', 'missed_known', 'missed_unknown', 'usable_known', 'usable_unknown')}
                    for n in (1, 2, 3)}
    prior = {e['capture']: e for e in baseline['results'] if e['arm'] == 'planner' and not e['repeat']}
    comparisons = []
    for entry in entries:
        base = prior[entry['capture']]
        comparisons.append({'job': entry['id'], 'capture': entry['capture'], 'attempt': entry['attempt'],
                            'qwen_job': base['id'], 'qwen_status': base['status'], 'luna_status': entry['status'],
                            'qwen_metrics': base['metrics'], 'luna_metrics': entry['metrics']})
    return {'rounds': rounds, 'attribution_denominators_by_round': denominators,
            'pooled_repeated_inventory': _aggregate(entries), 'pooled_reference_interpretation': '26 reference appearances repeated three times; 8 distinct fictional pages',
            'per_family_by_round': {str(n): {family: _aggregate([e for e in entries if e['attempt'] == n and e['family'] == family])
                                           for family in sorted({e['family'] for e in entries})} for n in (1, 2, 3)},
            'qwen_primary_baseline': baseline['same_inventory_by_arm']['planner'], 'per_page_baseline_comparisons': comparisons,
            'scoring_failures': [e['id'] for e in entries if e.get('scoring_error')]}


def verify_accepted(destination, registration, entry):
    accepted = destination / entry['id'] / 'extraction'
    if not (accepted / 'bundle/records.jsonl').exists(): return {'status': 'not_run', 'reason': 'no_accepted_bundle'}
    page = registration['capture_inventory'][entry['capture']]
    capture = destination / page['files']['capture']['path']
    metadata = destination / page['files']['metadata']['path']
    plan = accepted / 'evidence/finalized-plan.json'
    checks = []
    for label, seed in (('original_paths', '0'), ('relocated_paths', '117')):
        try:
            if label == 'relocated_paths':
                relocated = destination / 'replay-inputs' / entry['id']; relocated.mkdir(parents=True)
                for source, name in ((capture, 'capture.html'), (metadata, 'capture.metadata.json'), (plan, 'plan.json')):
                    (relocated / name).write_bytes(safe_read(source))
                capture, metadata, plan = relocated / 'capture.html', relocated / 'capture.metadata.json', relocated / 'plan.json'
            command = [sys.executable, '-m', 'ahif_html', 'verify', '--capture', str(capture),
                       '--metadata', str(metadata), '--plan', str(plan), '--run', str(accepted)]
            environment = dict(os.environ); environment.pop('OPENAI_API_KEY', None); environment['PYTHONHASHSEED'] = seed
            result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=70)
            (destination / (entry['id'] + '.' + label + '.verification.log')).write_text(result.stdout + result.stderr)
            try: value = json.loads(result.stdout)
            except json.JSONDecodeError: value = None
            if not isinstance(value, dict): value = {'status': 'verification_failure', 'reason': 'invalid_verifier_response'}
            checks.append({'status': 'passed' if result.returncode == 0 and value.get('status') == 'passed' else 'failed',
                           'exit_code': result.returncode, 'verification': value, 'input_paths': label,
                           'python_hash_seed': seed, 'model_calls': 0, 'api_key_environment_removed': True})
        except (Failure, OSError, subprocess.TimeoutExpired) as exc:
            checks.append({'status': 'failed', 'reason': 'verifier_unavailable_or_invalid_input',
                           'error_type': type(exc).__name__, 'input_paths': label, 'model_calls': 0})
        if checks[-1]['status'] != 'passed': break
    return {'status': 'passed' if len(checks) == 2 and all(x['status'] == 'passed' for x in checks) else 'failed',
            'checks': checks, 'model_calls': 0}


def run(destination, *, key_file=None):
    destination = check_path(destination); registration = load_json(destination / 'registration.json')
    digest = sha(safe_read(destination / 'registration.json'))
    if (destination / 'trial-started.json').exists(): raise Failure('trial_cannot_restart')
    verify_frozen(destination, registration)
    key = supplied_key(key_file)  # Missing key must not consume the fresh run.
    ledger = registration['shared_budget']['budget_ledger']; ledger_before = ledger_snapshot(ledger)
    prefix = registration['ledger_initial_prefix']; ledger_raw = safe_read(ledger)
    if sha(ledger_raw[:prefix['byte_length']]) != prefix['sha256']: raise Failure('budget_ledger_history_changed')
    if ledger_before['cap_nanodollars'] != 3_000_000_000: raise Failure('trial_requires_registered_three_dollar_cap')
    ledger_prefix = ledger_raw
    frozen_gold = {name: load_json(destination / page['files']['gold']['path']) for name, page in registration['capture_inventory'].items()}
    baseline = load_json(destination / registration['baseline']['path'])
    write_json(destination / 'trial-started.json', {'version': '1.0.0', 'registration_sha256': digest, 'mode': 'live', 'ledger_before': ledger_before})
    started = time.monotonic(); entries = []; charged = 0; stop_reason = None
    budget = registration['shared_budget']; cap = registration['per_job_budget']['max_calls']
    with old.cancellation_window() as cancellation:
        for job in registration['jobs']:
            if cancellation: stop_reason = stop_reason or 'host_cancelled'
            if budget['max_seconds'] - (time.monotonic() - started) < registration['per_job_budget']['max_seconds']:
                stop_reason = stop_reason or 'shared_wall_budget_insufficient_for_full_job'
            if charged + cap > budget['max_calls']: stop_reason = stop_reason or 'shared_call_budget_exhausted'
            if sum(p.stat().st_size for p in destination.rglob('*') if p.is_file()) + 12 * 1048576 > budget['max_trial_output_bytes']:
                stop_reason = stop_reason or 'shared_output_reservation_limit'
            if not stop_reason:
                try:
                    verify_frozen(destination, registration)
                    current_ledger = safe_read(ledger)
                    if not current_ledger.startswith(ledger_prefix): raise Failure('budget_ledger_history_changed')
                except (Failure, OSError, ValueError): stop_reason = 'trial_frozen_inputs_or_ledger_changed'
            if stop_reason:
                entries.append({**job, 'status': 'not_run', 'reason': stop_reason, 'worker_started': False, 'provider_call_budget_charge': 0}); continue
            page = registration['capture_inventory'][job['capture']]; run_path = destination / job['id']
            code = 'import json,sys\nfrom ahif_html.common import load_json\nfrom ahif_html.planner import discover\nresult=discover(sys.argv[1],load_json(sys.argv[2]),sys.argv[3],load_json(sys.argv[4]),limits={"output_bytes":8388608})\nprint(json.dumps({k:result.get(k) for k in ("status","failure")},sort_keys=True))\n'
            command = [sys.executable, '-c', code, str(destination / page['files']['capture']['path']), str(destination / (job['id'] + '.config.json')), str(run_path), str(destination / page['files']['metadata']['path'])]
            environment = dict(os.environ); environment['OPENAI_API_KEY'] = key
            began = time.monotonic(); process = None; termination = None; worker_error = None; cleanup = None; peak = None
            try:
                with (destination / (job['id'] + '.process.log')).open('w') as log:
                    process = subprocess.Popen(command, cwd=destination / 'captures', env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    while process.poll() is None:
                        try:
                            rss = next(int(line.split()[1]) for line in Path(f'/proc/{process.pid}/status').read_text().splitlines() if line.startswith('VmHWM:'))
                            peak = max(peak or 0, rss)
                        except (OSError, StopIteration): pass
                        if time.monotonic() - began > registration['per_job_budget']['max_seconds'] + 5: termination = 'host_job_wall_limit'
                        if time.monotonic() - started > budget['max_seconds']: termination = 'host_shared_wall_limit'
                        if cancellation: termination = 'host_cancelled'
                        if termination: cleanup = terminate_owned(process); break
                        time.sleep(.2)
            except OSError as exc:
                worker_error = {'reason': 'worker_launch_or_monitor_error', 'error_type': type(exc).__name__}
                if process is not None: cleanup = terminate_owned(process)
            receipt = None; receipt_error = None
            if process is not None:
                try:
                    receipt = load_json(run_path / 'discovery-receipt.json')
                    if not isinstance(receipt, dict) or not isinstance(receipt.get('status'), str): raise ValueError('receipt_shape')
                    op = receipt.get('operation')
                    if op is not None and (not isinstance(op, dict) or type(op.get('calls')) is not int or not 0 <= op['calls'] <= cap): raise ValueError('receipt_calls')
                except (Failure, OSError, ValueError): receipt = None; receipt_error = {'reason': 'worker_receipt_unavailable_or_invalid'}
            charge = 0 if process is None else cap if receipt is None else (receipt.get('operation') or {}).get('calls', 0)
            charged += charge
            failure = receipt and receipt.get('failure')
            if failure and ('budget' in failure or 'ledger' in failure): stop_reason = 'shared_api_budget_or_ledger_stop'
            if failure in ('provider_http_error', 'provider_transport_error', 'provider_api_key_missing', 'provider_model_mismatch', 'provider_redirect_refused', 'provider_service_tier_mismatch', 'provider_response_byte_limit', 'provider_response_nonterminal') or (receipt and receipt['status'] == 'model_unavailable'):
                stop_reason = stop_reason or 'provider_infrastructure_unavailable'
            op = receipt and receipt.get('operation')
            if op and op['calls'] and (op.get('actual_input_tokens') is None or op.get('actual_output_tokens') is None):
                stop_reason = stop_reason or 'provider_usage_unavailable'
            try:
                ledger_state = ledger_snapshot(ledger); current_ledger = safe_read(ledger)
                if not current_ledger.startswith(ledger_prefix): raise Failure('budget_ledger_history_changed')
                ledger_prefix = current_ledger
                if ledger_state['pending_requests'] > ledger_before['pending_requests']: stop_reason = stop_reason or 'provider_unsettled_request'
            except (Failure, OSError, ValueError): stop_reason = stop_reason or 'budget_ledger_unavailable_or_changed'
            if termination == 'host_cancelled': stop_reason = stop_reason or 'host_cancelled'
            if cleanup and cleanup['status'] == 'termination_unconfirmed': stop_reason = 'owned_worker_cleanup_required'
            if worker_error: stop_reason = stop_reason or 'worker_launch_or_monitor_error'
            if receipt_error: stop_reason = stop_reason or 'worker_receipt_unavailable_or_invalid'
            entry = {**job, 'status': receipt['status'] if receipt else 'processing_failure', 'receipt': receipt,
                     'worker_started': process is not None, 'worker_pid': process.pid if process else None,
                     'owned_process_cleanup': cleanup, 'worker_error': worker_error, 'receipt_error': receipt_error,
                     'exit_code': process.returncode if process else None, 'host_termination': termination,
                     'elapsed_seconds': f'{time.monotonic()-began:.3f}', 'peak_worker_rss_kib': peak,
                     'provider_call_budget_charge': charge}
            entries.append(entry)
            write_json(destination / 'progress.json', {'completed_jobs': len(entries), 'charged_calls': charged, 'results': entries})
            print(json.dumps({'job': job['id'], 'status': entry['status'], 'failure': failure, 'charged_calls': charged}), flush=True)
    cleanup_required = any((e.get('owned_process_cleanup') or {}).get('status') == 'termination_unconfirmed' for e in entries)
    write_json(destination / 'inference-finished.json', {'version': '1.0.0', 'jobs': len(entries), 'charged_calls': charged,
               'elapsed_seconds': f'{time.monotonic()-started:.3f}', 'no_more_provider_calls': not cleanup_required, 'cleanup_required': cleanup_required})
    integrity = []; checks = []
    def final_freeze(phase):
        try:
            verify_frozen(destination, registration)
            if sha(safe_read(destination / 'registration.json')) != digest: raise Failure('trial_registration_changed')
            checks.append({'phase': phase, 'status': 'passed'})
        except (Failure, OSError, ValueError):
            checks.append({'phase': phase, 'status': 'failed'}); integrity.append('frozen_inputs_changed')
    final_freeze('after_inference')
    for entry in entries:
        entry['grounding'] = verify_accepted(destination, registration, entry)
        if entry['grounding']['status'] == 'failed': integrity.append(entry['id'])
    comparisons = []
    for page in PAGES:
        selected = [e for e in entries if e['capture'] == page]
        for first, second in ((selected[0], selected[1]), (selected[0], selected[2]), (selected[1], selected[2])):
            comparison = {'capture': page, 'jobs': [first['id'], second['id']]}
            if all(e['grounding']['status'] == 'passed' for e in (first, second)):
                try:
                    hashes = {name: [sha(safe_read(destination / e['id'] / 'extraction' / name)) for e in (first, second)] for name in CANONICAL_FILES}
                    comparison.update(canonical_sha256=hashes, byte_identical=all(v[0] == v[1] for v in hashes.values()))
                except (Failure, OSError):
                    comparison.update(byte_identical=None, reason='accepted_artifact_unreadable'); integrity.append(first['id'])
            else: comparison.update(byte_identical=None, reason='both_attempts_not_accepted_and_verified')
            comparisons.append(comparison)
    final_freeze('before_scoring')
    scores = score(destination, registration, entries, frozen_gold, baseline)
    integrity.extend(scores['scoring_failures'])
    try:
        ledger_after = ledger_snapshot(ledger)
        if not safe_read(ledger).startswith(ledger_prefix): raise Failure('budget_ledger_history_changed')
    except (Failure, OSError, ValueError): ledger_after = None; integrity.append('budget_ledger_unavailable')
    final_freeze('before_report')
    result = {'version': '1.0.0', 'registration_sha256': digest, 'mode': 'live',
              'designation': registration['designation'], 'model_configuration_version': registration['model_configuration_version'],
              'wire_mode': registration['wire_mode'], 'integration_failure_history': registration['integration_failure_history'],
              'status': 'failed_integrity' if integrity else 'completed_with_all_outcomes_recorded',
              'mechanical_integrity_failures': sorted(set(integrity)), 'results': entries, **scores,
              'repeat_comparisons': comparisons, 'freeze_checks': checks, 'cleanup_required': cleanup_required,
              'provider_call_budget_charge': charged, 'within_call_limit': charged <= budget['max_calls'],
              'stop_reason': stop_reason, 'elapsed_seconds': f'{time.monotonic()-started:.3f}',
              'ledger_before': ledger_before, 'ledger_after': ledger_after,
              'observed_counts': {label: old.observed(entries, path) for label, path in
                  [('calls', ['calls']), ('input_tokens', ['actual_input_tokens']), ('output_tokens', ['actual_output_tokens']),
                   ('tool_calls', ['tool_calls']), ('inspected_characters', ['inspection', 'inspected_characters'])]},
              'human_reviewed': False, 'real_capture_pilot': 'not_run'}
    write_json(destination / 'trial-report.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--config', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--baseline', type=Path, default=BASELINE,
                   help='Published Qwen directory with registration, publication manifest, and report.')
    p.add_argument('--integration-history', type=Path, default=INTEGRATION_HISTORY,
                   help='Published Luna integration-history directory; required for configuration 1.1.1.')
    p = sub.add_parser('check'); p.add_argument('--run', type=Path, required=True)
    p = sub.add_parser('run'); p.add_argument('--run', type=Path, required=True); p.add_argument('--key-file', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            r = prepare(args.config, args.out, baseline=args.baseline, integration_history=args.integration_history)
            print(json.dumps({'status': 'registered_without_inference', 'jobs': len(r['jobs'])}))
        elif args.command == 'check':
            verify_frozen(args.run, load_json(args.run / 'registration.json')); print('{"status":"freeze_matches"}')
        else:
            r = run(args.run, key_file=args.key_file); print(json.dumps({'status': r['status'], 'calls': r['observed_counts']['calls']}))
    except (Failure, OSError) as exc:
        print(json.dumps({'status': 'not_started_or_invalid', 'reason': exc.code if isinstance(exc, Failure) else 'operational_io_error'})); raise SystemExit(2)


if __name__ == '__main__': main()
