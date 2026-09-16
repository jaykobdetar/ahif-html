#!/usr/bin/env python3
"""Preregister and run a bounded synthetic trial; never provision paid resources.

The operator supplies an already configured model gateway. Only this script's
fixed fictional development/held-out inventory is approved; no real/private input
path is accepted by this trial runner. Gold is scored in the parent after workers
finish and is never passed to the model or worker arguments.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from ahif_html.common import C, Failure, check_path, load_json, safe_read, sha, write_json
from ahif_html.provider import validate_config

ROOT = Path(__file__).resolve().parents[1]
JOBS = (
    ('reviews-development', 'reviews', 'development', False, 6),
    ('forum-development', 'forum', 'development', False, 8),
    ('comments-planner', 'comments', 'held_out', False, 8),
    ('comments-reviewer', 'comments', 'held_out', True, 12),
    ('reviews-repeat', 'reviews', 'development_repeat', False, 6),
)


def available_memory_mib():
    path = Path('/proc/meminfo')
    if not path.exists():
        return None
    return next(int(line.split()[1]) // 1024 for line in path.read_text().splitlines()
                if line.startswith('MemAvailable:'))


def observed_total(entries, path):
    """Separate reported counts from reservations when a worker left no receipt."""
    known = 0
    incomplete = []
    for entry in entries:
        if entry['status'] == 'not_run':
            continue
        receipt = entry.get('receipt')
        if receipt is None:
            incomplete.append(entry['id'])
            continue
        value = receipt.get('operation')
        if value is None:
            # A retained discovery receipt with no Session means no provider/tool call.
            continue
        for name in path:
            value = value.get(name) if isinstance(value, dict) else None
        if type(value) is not int:
            incomplete.append(entry['id'])
        else:
            known += value
    return {'value': None if incomplete else known, 'known_lower_bound': known,
            'incomplete_jobs': incomplete}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--max-wall-seconds', type=int, default=1200)
    parser.add_argument('--max-provider-calls', type=int, default=40)
    args = parser.parse_args()
    if not 1 <= args.max_wall_seconds <= 1800 or not 1 <= args.max_provider_calls <= 40:
        raise Failure('trial_budget_invalid')
    base = validate_config(load_json(args.config))
    # Load the declared scorer before outcomes exist. Gold remains unread until
    # the independent parent scoring phase after all model workers have exited.
    from ahif_html.evaluate import score_records, _load_records, _aggregate
    if base['mode'] != 'live' or not base['data_approval']['approved']:
        raise Failure('trial_requires_explicit_live_synthetic_approval')
    if base['data_approval']['data_classes'] != ['synthetic']:
        raise Failure('trial_synthetic_only')
    destination = check_path(args.out)
    if destination.exists():
        raise Failure('trial_destination_must_be_fresh')
    destination.mkdir(parents=True, mode=0o700)
    (destination / 'captures').mkdir()
    (destination / 'evaluator-only').mkdir(mode=0o700)
    captures = {}
    for name in ('reviews', 'forum', 'comments'):
        capture = ROOT / 'examples/fictional' / (name + '.html')
        raw = safe_read(capture)
        # Explicit base scope must preapprove the actual source bytes. The worker
        # then receives only its one approved capture, not unrelated approvals.
        if sha(raw) not in base['data_approval']['capture_sha256']:
            raise Failure('trial_capture_not_preapproved')
        (destination / 'captures' / (name + '.html')).write_bytes(raw)
        (destination / 'captures' / (name + '.metadata.json')).write_bytes(
            safe_read(ROOT / 'examples/fictional' / (name + '.metadata.json')))
        (destination / 'evaluator-only' / (name + '.gold.json')).write_bytes(
            safe_read(ROOT / 'examples/fictional' / (name + '.gold.json')))
        captures[name] = {'capture_sha256': sha(raw),
                          'metadata_sha256': sha((destination / 'captures' / (name + '.metadata.json')).read_bytes()),
                          'annotation_sha256': sha((destination / 'evaluator-only' / (name + '.gold.json')).read_bytes())}
    registration = {'version': '1.0.0', 'designation': 'synthetic-model-trial-v1',
                    'model': base['model'], 'mode': 'live', 'provider_location': base['provider_location'],
                    'tunnel_declaration': base['tunnel_declaration'], 'response_format': base['response_format'],
                    'capture_inventory': captures, 'annotation_provenance': 'agent_authored_construction_truth',
                    'human_reviewed': False, 'real_capture_pilot': 'not_run',
                    'metric_definition': 'ahif_html.evaluate.score_records; exact container one-to-one match; all gold items in denominator; page failures score empty outputs',
                    'jobs': [{'id': job, 'capture': name, 'split': split, 'reviewer': reviewer, 'max_calls': cap,
                              'budgets': {'max_calls': cap, 'max_wall_seconds': min(300, args.max_wall_seconds),
                                          'max_input_tokens_reserved': cap * base['num_ctx'],
                                          'max_output_tokens_reserved': cap * base['budgets']['max_output_tokens_per_call'],
                                          'max_tool_calls': base['budgets']['max_tool_calls'],
                                          'max_inspected_characters': base['budgets']['max_inspected_characters']}}
                             for job, name, split, reviewer, cap in JOBS],
                    'budget': {'max_provider_calls': args.max_provider_calls,
                               'max_wall_seconds': args.max_wall_seconds,
                               'max_tool_calls': len(JOBS) * base['budgets']['max_tool_calls'],
                               'max_inspected_characters': len(JOBS) * base['budgets']['max_inspected_characters'],
                               'max_reserved_input_tokens': args.max_provider_calls * base['num_ctx'],
                               'max_reserved_output_tokens': args.max_provider_calls * base['budgets']['max_output_tokens_per_call']},
                    'runtime_prompt_sha256': {name: sha((ROOT / 'src/ahif_html/prompts/1.0.0' / (name + '.txt')).read_bytes())
                                              for name in ('planner', 'reviewer')},
                    'implementation_sha256': {name: sha((ROOT / 'src/ahif_html' / (name + '.py')).read_bytes())
                                              for name in ('provider', 'planner', 'index', 'plans', 'executor', 'common', 'evaluate')},
                    'schema_sha256': {str(path.relative_to(ROOT)): sha(safe_read(path))
                                      for path in sorted((ROOT / 'src/ahif_html/schemas').glob('*.json'))},
                    'pinned_ahif_sha256': {str(path.relative_to(ROOT)): sha(safe_read(path))
                                          for path in sorted((ROOT / 'src/ahif_html/vendor/ahif_011').rglob('*'))
                                          if path.is_file() and path.suffix in ('.py', '.json')},
                    'dependency_lock_sha256': sha(safe_read(ROOT / 'uv.lock')),
                    'runner_sha256': sha(safe_read(Path(__file__))),
                    'base_configuration_sha256': sha(safe_read(args.config)),
                    'limits': ['Synthetic construction truth is not independent human ground truth.',
                               'Held-out means model discovery on the reserved family; fixture authors knew constructed content.',
                               'No best-attempt selection; fresh repeat is retained separately.',
                               'Pod shutdown and price enforcement belong to the registered external operator controller.']}
    write_json(destination / 'registration.json', registration)
    started = time.monotonic()
    calls = 0
    results = []
    stop_reason = None
    for job, name, split, reviewer, cap in JOBS:
        remaining = int(args.max_wall_seconds - (time.monotonic() - started))
        if stop_reason or remaining <= 0 or calls >= args.max_provider_calls:
            results.append({'id': job, 'capture': name, 'split': split, 'status': 'not_run',
                            'reviewer': reviewer, 'reason': stop_reason or 'shared_budget_exhausted',
                            'provider_call_budget_charge': 0})
            continue
        cfg = json.loads(json.dumps(base))
        cap = min(cap, args.max_provider_calls - calls)
        cfg['reviewer'] = reviewer
        cfg['data_approval']['capture_sha256'] = [captures[name]['capture_sha256']]
        cfg['budgets'].update(max_calls=cap, max_input_tokens_total=cap * cfg['num_ctx'],
                              max_output_tokens_total=cap * cfg['budgets']['max_output_tokens_per_call'],
                              max_wall_seconds=min(300, remaining), max_retries=0, max_repairs=2)
        validate_config(cfg)
        config_path = destination / (job + '.config.json')
        write_json(config_path, cfg)
        run_path = destination / job
        code = ('import json,sys\nfrom ahif_html.common import load_json\nfrom ahif_html.planner import discover\n'
                'print(json.dumps(discover(sys.argv[1],load_json(sys.argv[2]),sys.argv[3],load_json(sys.argv[4])),sort_keys=True))\n')
        command = [sys.executable, '-c', code, str(destination / 'captures' / (name + '.html')),
                   str(config_path), str(run_path), str(destination / 'captures' / (name + '.metadata.json'))]
        samples = []
        with (destination / (job + '.process.log')).open('w') as stream:
            process = subprocess.Popen(command, cwd=destination / 'captures', stdout=stream, stderr=subprocess.STDOUT)
            while process.poll() is None:
                memory = available_memory_mib()
                samples.append({'elapsed_seconds': format(time.monotonic() - started, '.3f'), 'available_mib': memory})
                if ((memory is not None and memory < 1536) or time.monotonic() - started >= args.max_wall_seconds):
                    stop_reason = 'workstation_memory_limit' if memory is not None and memory < 1536 else 'shared_wall_limit'
                    process.send_signal(signal.SIGINT)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    break
                time.sleep(1)
        write_json(destination / (job + '.memory.json'), samples)
        receipt_path = run_path / 'discovery-receipt.json'
        receipt = load_json(receipt_path) if receipt_path.exists() else None
        if receipt is None:
            # Pending unreceipted requests cannot safely be assumed free.
            calls += cap
            charge = cap
            stop_reason = stop_reason or 'worker_no_receipt'
        else:
            charge = (receipt.get('operation') or {}).get('calls', 0)
            calls += charge
            if receipt['failure'] in ('provider_http_error', 'provider_transport_error', 'provider_local_model_not_verified'):
                stop_reason = 'provider_infrastructure_unavailable'
        entry = {'id': job, 'capture': name, 'split': split, 'reviewer': reviewer,
                 'exit_code': process.returncode, 'status': receipt['status'] if receipt else 'processing_failure',
                 'receipt': receipt, 'provider_call_budget_charge': charge}
        results.append(entry)
        print(json.dumps({'job': job, 'status': entry['status'], 'failure': receipt and receipt['failure'],
                          'cumulative_call_budget_charge': calls}), flush=True)
    # This independent process phase can read gold; no inference call follows it.
    scored = []
    for entry in results:
        name = entry['capture']
        path = destination / entry['id'] / 'extraction/bundle/records.jsonl'
        records = _load_records(path) if path.exists() else []
        entry['metrics'] = score_records(load_json(destination / 'evaluator-only' / (name + '.gold.json')), records)
        scored.append(entry)
    observed = {'provider_calls': observed_total(scored, ['calls']),
                'tool_calls': observed_total(scored, ['tool_calls']),
                'inspected_characters': observed_total(scored, ['inspection', 'inspected_characters']),
                'input_tokens': observed_total(scored, ['actual_input_tokens']),
                'output_tokens': observed_total(scored, ['actual_output_tokens'])}
    summary = {'version': '1.0.0', 'mode': 'live', 'provider_location': base['provider_location'],
               'results': scored, 'provider_call_budget_charge': calls,
               'actual_provider_calls': observed['provider_calls']['value'], 'max_provider_calls': args.max_provider_calls,
               'actual_tool_calls': observed['tool_calls']['value'],
               'actual_inspected_characters': observed['inspected_characters']['value'], 'observed_counts': observed,
               'within_call_limit': calls <= args.max_provider_calls,
               'elapsed_seconds': format(time.monotonic() - started, '.3f'), 'stop_reason': stop_reason,
               'human_reviewed': False, 'real_capture_pilot': 'not_run', 'monetary_cost': None,
               'aggregate_by_arm': {arm: _aggregate([entry for entry in scored if ('reviewer' if entry.get('reviewer') else 'planner') == arm])
                                    for arm in ('planner', 'reviewer')},
               'same_held_out_inventory_by_arm': {arm: _aggregate([entry for entry in scored
                    if entry['split'] == 'held_out' and ('reviewer' if entry.get('reviewer') else 'planner') == arm])
                    for arm in ('planner', 'reviewer')}}
    write_json(destination / 'trial-report.json', summary)
    print(json.dumps({'trial_complete': True, 'actual_calls': observed['provider_calls']['value'],
                      'call_budget_charge': calls, 'report': str(destination / 'trial-report.json')}))


if __name__ == '__main__':
    main()
