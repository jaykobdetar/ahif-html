"""Preregistered, bounded deterministic-plan evaluation against explicit inventories.

This measures construction-truth fixtures or supplied annotations; it does not
turn agent labels into human ground truth, or replay into semantic validation.
"""
from __future__ import annotations
from collections import Counter
from contextlib import contextmanager
from difflib import SequenceMatcher
from pathlib import Path
import resource
import signal
import threading
import time

from .common import C, Failure, fresh, load_json, safe_read, schema, sha, validate, write_json
from jsonschema import Draft202012Validator

EXTENSION = 'org.ahif-html:extraction'


class _EvaluationDeadline(BaseException):
    """Avoid having record-level partial-success handlers swallow a shared deadline."""
    def __init__(self, reason='evaluation_shared_wall_limit'):
        self.reason = reason
        super().__init__(reason)


@contextmanager
def _deadline(seconds):
    if threading.current_thread() is not threading.main_thread():
        raise Failure('evaluation_deadline_requires_main_thread')
    previous_delay, previous_interval = signal.getitimer(signal.ITIMER_REAL)
    previous_handler = signal.getsignal(signal.SIGALRM)
    started = time.monotonic()
    local_delay = max(0.000001, seconds)
    outer_is_tighter = previous_delay > 0 and previous_delay <= local_delay
    selected_delay = min(previous_delay, local_delay) if previous_delay > 0 else local_delay
    def expired(_signum, _frame):
        raise _EvaluationDeadline('evaluation_enclosing_wall_limit' if outer_is_tighter else 'evaluation_shared_wall_limit')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, selected_delay)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_delay > 0:
            # Preserve an enclosing worker deadline; nesting must never restart its
            # full allowance. A consumed enclosing timer has no remaining interval.
            remaining = max(0.0, previous_delay - (time.monotonic() - started))
            signal.setitimer(signal.ITIMER_REAL, remaining, previous_interval if remaining else 0)


def ratio(numerator, denominator, reason='no_reference_items'):
    return {'numerator': numerator, 'denominator': denominator,
            'value': None if denominator == 0 else f'{numerator / denominator:.6f}',
            'undefined_reason': reason if denominator == 0 else None}


def _safe_member(root, name):
    if not isinstance(name, str) or not name or '\\' in name:
        raise Failure('dataset_path_invalid')
    part = Path(name)
    if part.is_absolute() or any(p in ('.', '..') for p in part.parts):
        raise Failure('dataset_path_invalid')
    path = root / part
    if not path.resolve().is_relative_to(root.resolve()):
        raise Failure('dataset_path_escape')
    safe_read(path)
    return path


def validate_splits(dataset):
    """Families, threads, lineages, and exact captures may occupy one split only."""
    seen = {}
    ids = set()
    for page in dataset['pages']:
        if page['id'] in ids:
            raise Failure('dataset_duplicate_page_id')
        ids.add(page['id'])
        for field in ('family', 'thread', 'lineage'):
            key = (field, page[field])
            previous = seen.setdefault(key, page['split'])
            if previous != page['split']:
                raise Failure('dataset_split_leakage')
    return True


def _parts(record):
    return [{'role': p['role'], 'text': p['text'], 'attribution': p['attribution']['relation']}
            for p in record['content']['parts']]


def _text_difference(expected, actual):
    missing = extra = transformed = 0
    for op, a, b, c, d in SequenceMatcher(a=expected, b=actual, autojunk=False).get_opcodes():
        if op == 'delete':
            missing += b - a
        elif op == 'insert':
            extra += d - c
        elif op == 'replace':
            transformed += min(b - a, d - c)
            missing += max(0, (b - a) - (d - c))
            extra += max(0, (d - c) - (b - a))
    return {'missing_characters': missing, 'extra_characters': extra, 'transformed_characters': transformed}


def score_records(gold, records):
    """Fixed 1:1 match is exact immutable container ref, never convenient text match."""
    references = gold['contributions']
    expected_by_ref = {g['container']: g for g in references}
    if len(expected_by_ref) != len(references):
        raise Failure('gold_duplicate_container')
    matched = {}
    invented = []
    for rec in records:
        container = rec.get('extensions', {}).get(EXTENSION, {}).get('container')
        if container in expected_by_ref and container not in matched:
            matched[container] = rec
        else:
            invented.append(rec['observation_id'])
    attribution = Counter(correct_known=0, wrong_account=0, unknown_abstained=0,
                          correct_unknown=0, unsupported_assignment=0, missed=0)
    fidelity = {role: Counter(exact=0, reference_records=0, missing_characters=0,
                             extra_characters=0, transformed_characters=0)
                for role in ('body', 'title')}
    metadata = {field: Counter(correct=0, errors=0, abstentions=0, reference=0)
                for field in ('identity', 'kind', 'created_at', 'updated_at', 'relations', 'contexts')}
    contamination = {role: Counter(occurrences=0, affected_records=0, reference_fragments=0)
                     for role in ('quote', 'signature', 'interface')}
    usable = 0
    exact_parts = 0
    items = []
    for g in references:
        rec = matched.get(g['container'])
        if rec is None:
            attribution['missed'] += 1
            actual_parts = []
            actor_ok = False
        else:
            actual_parts = _parts(rec)
            actor = rec['actor']['id'] if rec['actor'] else None
            actor_ok = actor == g['actor_id']
            if actor is not None:
                actor_ok = actor_ok and rec['actor'].get('namespace') == g['key_namespace'] and rec['actor'].get('collection') == 'accounts' and rec['actor'].get('id_type') == 'uri'
            if g['actor_id'] is None:
                attribution['correct_unknown' if actor is None else 'unsupported_assignment'] += 1
            elif actor is None:
                attribution['unknown_abstained'] += 1
            elif actor_ok:
                attribution['correct_known'] += 1
            else:
                attribution['wrong_account'] += 1
        parts_ok = actual_parts == g['parts']
        if parts_ok and rec is not None:
            exact_parts += 1
        if parts_ok and actor_ok and rec is not None:
            usable += 1
        for role in fidelity:
            expected = [p['text'] for p in g['parts'] if p['role'] == role]
            actual = [p['text'] for p in actual_parts if p['role'] == role]
            # Count every reference contribution; empty-title agreement is reported,
            # while nonempty text denominators below exclude empty/empty cases.
            if expected or actual:
                fidelity[role]['reference_records'] += 1
                fidelity[role]['exact'] += int(rec is not None and expected == actual)
                for i in range(max(len(expected), len(actual))):
                    fidelity[role].update(_text_difference(expected[i] if i < len(expected) else '',
                                                           actual[i] if i < len(actual) else ''))
        actual_bodies = [p['text'] for p in actual_parts if p['role'] == 'body']
        for role in contamination:
            forbidden = [f['text'] for f in g['forbidden_body'] if f['role'] == role]
            contamination[role]['reference_fragments'] += len(forbidden)
            count = sum(body.count(fragment) for fragment in forbidden for body in actual_bodies)
            contamination[role]['occurrences'] += count
            contamination[role]['affected_records'] += int(count > 0)
        for field in metadata:
            metadata[field]['reference'] += 1
            if rec is None:
                metadata[field]['abstentions'] += 1
                continue
            if field == 'identity':
                correct = (rec['record_key']['id'] == g['key_id'] and rec['record_key']['id_type'] == 'native') if g['key_id'] is not None else rec['record_key']['id_type'] == 'source_local'
                correct = correct and rec['record_key']['collection'] == g['key_collection'] and rec['record_key']['namespace'] == g['key_namespace']
                abstained = g['key_id'] is not None and rec['record_key']['id_type'] == 'source_local'
            elif field == 'kind':
                correct = rec['kind'] == g['kind']
                abstained = rec['kind'] == 'unknown' and g['kind'] != 'unknown'
            elif field in ('created_at', 'updated_at'):
                source_field = 'created' if field == 'created_at' else 'updated'
                actual_time = {'status': rec[field]['status'], 'value': rec[field].get('value'), 'precision': rec[field].get('precision')}
                correct = actual_time == g[source_field]
                abstained = actual_time['status'] == 'unknown' and g[source_field]['status'] != 'unknown'
            elif field == 'contexts':
                correct = rec.get('contexts', []) == g['contexts']
                abstained = bool(g['contexts']) and not rec.get('contexts')
            else:
                actual_rel = [{'type': r['type'], 'target_id': (r.get('target_key') or {}).get('id'), 'target_collection': (r.get('target_key') or {}).get('collection')} for r in rec.get('relations', [])]
                correct = actual_rel == g['relations']
                abstained = bool(g['relations']) and not actual_rel
            metadata[field]['correct' if correct else ('abstentions' if abstained else 'errors')] += 1
        items.append({'container': g['container'], 'matched': rec is not None,
                      'observation_id': rec['observation_id'] if rec else None,
                      'correct_attribution': actor_ok, 'exact_ordered_parts': parts_ok and rec is not None})
    return {'contribution_precision': ratio(len(matched), len(records), 'no_emitted_contributions'),
            'contribution_recall': ratio(len(matched), len(references)),
            'end_to_end_usable_recall': ratio(usable, len(references)),
            'ordered_parts_exact': ratio(exact_parts, len(references)),
            'attribution': dict(attribution), 'fidelity': {k: dict(v) for k, v in fidelity.items()},
            'contamination': {k: dict(v) for k, v in contamination.items()},
            'metadata': {k: dict(v) for k, v in metadata.items()},
            'invented_observations': invented, 'reference_outcomes': items,
            'distinct_event_keys': len({C(r['record_key']) for r in records}),
            'emitted_observations': len(records)}


def _load_records(path):
    from .common import ahif
    return [ahif.strict_loads(line) for line in safe_read(path, 64 * 1024 * 1024).splitlines() if line]


def _aggregate(pages):
    out = {}
    for metric in ('contribution_precision', 'contribution_recall', 'end_to_end_usable_recall', 'ordered_parts_exact'):
        out[metric] = ratio(sum(p['metrics'][metric]['numerator'] for p in pages),
                            sum(p['metrics'][metric]['denominator'] for p in pages),
                            'no_emitted_contributions' if metric == 'contribution_precision' else 'no_reference_items')
    for group in ('attribution',):
        total = Counter()
        for p in pages:
            total.update(p['metrics'][group])
        out[group] = dict(total)
    for group in ('fidelity', 'contamination', 'metadata'):
        total = {}
        for p in pages:
            for key, counts in p['metrics'][group].items():
                total.setdefault(key, Counter()).update(counts)
        out[group] = {key: dict(value) for key, value in total.items()}
    return out


def evaluate(dataset_path, config_path, destination):
    from . import executor
    dataset_path, config_path = Path(dataset_path), Path(config_path)
    dataset = load_json(dataset_path)
    config = load_json(config_path)
    validate('dataset', dataset)
    validate('evaluation', config)
    validate_splits(dataset)
    root = dataset_path.absolute().parent
    if len(dataset['pages']) > config['budgets']['max_pages']:
        raise Failure('evaluation_page_limit', 'resource_limit')
    inputs = []
    total_bytes = 0
    hash_splits = {}
    for page in dataset['pages']:
        files = {key: _safe_member(root, page[key]) for key in ('capture', 'metadata', 'plan', 'gold')}
        digest = sha(safe_read(files['capture']))
        previous = hash_splits.setdefault(digest, page['split'])
        if previous != page['split']:
            raise Failure('dataset_duplicate_capture_split_leakage')
        total_bytes += files['capture'].stat().st_size
        gold = load_json(files['gold'])
        try:
            Draft202012Validator(schema('dataset')['$defs']['annotation']).validate(gold)
        except Exception as exc:
            raise Failure('annotation_schema_invalid') from exc
        if gold.get('capture_sha256') != digest:
            raise Failure('gold_capture_binding_mismatch')
        if gold.get('human_reviewed') != dataset['human_reviewed'] or gold.get('provenance') != dataset['annotation_provenance']:
            raise Failure('annotation_provenance_mismatch')
        inputs.append((page, files, gold))
    if total_bytes > config['budgets']['max_total_capture_bytes']:
        raise Failure('evaluation_capture_byte_limit', 'resource_limit')
    registration = {'registration_version': '1.0.0', 'dataset': dataset, 'configuration': config,
                    'dataset_sha256': sha(safe_read(dataset_path)), 'config_sha256': sha(safe_read(config_path)),
                    'inputs': [{'id': page['id'], 'files': {key: sha(safe_read(path)) for key, path in files.items()}} for page, files, _ in inputs],
                    'matching_rule': 'exact_capture_bound_container_reference_one_to_one',
                    'registered_before_execution': True}
    with fresh(destination) as out:
        write_json(out / 'registration.json', registration)
        (out / 'pages').mkdir()
        results = []
        start = time.monotonic()
        output_bytes = 0
        deadline_exhausted = False
        for page, files, gold in inputs:
            exhausted = deadline_exhausted or time.monotonic() - start > config['budgets']['max_total_seconds'] or output_bytes >= config['budgets']['max_total_output_bytes']
            page_start = time.monotonic()
            record_path = out / 'pages' / page['id']
            result = None
            error = None
            grounding = {'status': 'not_run', 'reason': 'execution_not_completed'}
            replay = {'status': 'not_run', 'reason': 'execution_not_completed'}
            records = []
            if exhausted:
                error = 'evaluation_shared_budget_exhausted'
            else:
                try:
                    with _deadline(config['budgets']['max_total_seconds'] - (time.monotonic() - start)):
                        result = executor.extract(files['capture'], load_json(files['plan']), record_path,
                                                  metadata=load_json(files['metadata']),
                                                  limits={'output_bytes': min(67108864, config['budgets']['max_total_output_bytes'] - output_bytes)})
                        records = _load_records(record_path / 'bundle' / 'records.jsonl')
                        grounding = {'status': 'pending'}
                        # Full verification re-executes sources and plan; output checksums alone
                        # are intentionally insufficient evidence of source grounding.
                        verification = executor.verify(files['capture'], load_json(files['plan']), record_path,
                                                       metadata=load_json(files['metadata']))
                        grounding = {'status': 'passed', 'verification': verification}
                        replay = {'status': 'passed', 'mode': 'deterministic_reexecution_same_process'} if config['replay'] else {'status': 'not_run', 'reason': 'not_requested'}
                except _EvaluationDeadline as exc:
                    error = exc.reason
                    deadline_exhausted = True
                    if grounding['status'] == 'pending':
                        grounding = {'status': 'failed', 'reason': error}
                        replay = {'status': 'failed', 'reason': error}
                except Failure as exc:
                    error = exc.code
                    if grounding['status'] == 'pending':
                        grounding = {'status': 'failed', 'reason': error}
                        replay = {'status': 'failed', 'reason': error}
                except Exception as exc:
                    error = 'unexpected_execution_' + type(exc).__name__
                    if grounding['status'] == 'pending':
                        grounding = {'status': 'failed', 'reason': error}
                        replay = {'status': 'failed', 'reason': error}
            if record_path.exists():
                output_bytes += sum(p.stat().st_size for p in record_path.rglob('*') if p.is_file())
            metrics = score_records(gold, records)
            entry = {'id': page['id'], 'family': page['family'], 'split': page['split'],
                     'status': 'failed' if error else result.get('status', 'complete'), 'error': error,
                     'metrics': metrics, 'grounding': grounding, 'replay': replay,
                     'cost': {'mode': 'manual_finalized_plan', 'provider_calls': 0, 'cache_hits': 0, 'retries': 0,
                              'usage': None, 'monetary_cost': None, 'monetary_cost_reason': 'no_model_calls',
                              'elapsed_seconds': f'{time.monotonic() - page_start:.6f}'}}
            results.append(entry)
            write_json(out / (page['id'] + '.result.json'), entry)
        families = {f: _aggregate([p for p in results if p['family'] == f]) for f in sorted({p['family'] for p in results})}
        report = {'evaluation_version': '1.0.0', 'designation': dataset['designation'],
                  'status': 'failed' if any(p['error'] for p in results) else 'complete',
                  'registration_sha256': sha(C(registration)), 'data_classes': sorted({p['data_class'] for p in dataset['pages']}),
                  'annotation_provenance': dataset['annotation_provenance'], 'human_reviewed': dataset['human_reviewed'],
                  'mode': config['mode'], 'pages': results, 'aggregate': _aggregate(results), 'per_layout': families,
                  'coverage': {'pages': len(results), 'entire_page_failures': sum(bool(p['error']) for p in results),
                               'partial_pages': sum(p['status'] == 'partial_execution' for p in results),
                               'records_awaiting_review': sum(len(load_json(files['plan'])['unresolved']) for _, files, _ in inputs),
                               'unsupported_evidence': 'see each extraction interpretation and index indicators; not a completeness estimate'},
                  'cost': {'provider_calls': 0, 'usage': None, 'monetary_cost': None,
                           'elapsed_seconds': f'{time.monotonic() - start:.6f}',
                           'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                           'peak_resource_scope': 'whole evaluator process high-water mark, not per-page incremental memory'},
                  'unexecuted': [
                      {'path': 'real_layout_pilot', 'status': 'not_run', 'missing': ['approved real capture inventory', 'independent human annotations']},
                      {'path': 'planner_only_vs_reviewer', 'status': 'not_run', 'missing': ['registered inference arm and live per-arm budgets in this evaluation', 'eligible held-out real inventory']},
                      {'path': 'fresh_live_discovery_variation', 'status': 'not_run', 'missing': ['registered repeated-discovery configuration in this evaluation', 'eligible fixed real subset']}],
                  'limitations': ['Construction truth is agent-authored and is not independent human annotation.',
                                  'Semantic scores characterize these finalized manual plans, not planner discovery.',
                                  'Unknown reference attribution can correctly remain unknown in end-to-end usable recall.',
                                  'Source-map integrity does not establish correct semantic association.',
                                  'Coverage indicators and successful parsing do not establish capture or account completeness.',
                                  'No real-layout, live-model, or scientific authorship performance is claimed.']}
        validate('evaluation-result', report)
        write_json(out / 'evaluation.json', report)
    return report
