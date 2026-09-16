"""Expected wording is construction truth, not production extractor output."""
import copy
from pathlib import Path
import pytest

from ahif_html.common import Failure, load_json, write_json
from ahif_html.evaluate import evaluate, ratio, score_records, validate_splits

FIXTURES = Path(__file__).resolve().parents[1] / 'examples' / 'fictional'


def record(container='node-1', actor='author-a', body='Expected prose.', observation='obs-1'):
    return {'observation_id': observation, 'record_key': {'namespace': 'https://fictional.example', 'collection': 'contributions', 'id_type': 'native', 'id': 'event-1'}, 'kind': 'post', 'actor': None if actor is None else {'namespace': 'https://fictional.example', 'collection': 'accounts', 'id_type': 'uri', 'id': actor}, 'created_at': {'status': 'unknown'}, 'updated_at': {'status': 'unknown'}, 'content': {'parts': [{'role': 'body', 'text': body, 'attribution': {'relation': 'record_actor'}}]}, 'relations': [], 'extensions': {'org.ahif-html:extraction': {'container': container}}}


def gold():
    return {'contributions': [{'container': 'node-1', 'key_id': 'event-1', 'key_collection': 'contributions', 'key_namespace': 'https://fictional.example', 'kind': 'post', 'actor_id': 'author-a', 'created': {'status': 'unknown', 'value': None, 'precision': None}, 'updated': {'status': 'unknown', 'value': None, 'precision': None}, 'contexts': [], 'parts': [{'role': 'body', 'text': 'Expected prose.', 'attribution': 'record_actor'}], 'forbidden_body': [{'role': 'signature', 'text': 'SIGNATURE'}], 'relations': []}]}


def test_wrong_grounded_author_is_semantic_error():
    result = score_records(gold(), [record(actor='author-b')])
    assert result['contribution_recall']['numerator'] == 1
    assert result['ordered_parts_exact']['numerator'] == 1
    assert result['attribution']['wrong_account'] == 1
    assert result['end_to_end_usable_recall']['numerator'] == 0


def test_missed_contributions_stay_in_denominator():
    g = gold()
    g['contributions'].append({**copy.deepcopy(g['contributions'][0]), 'container': 'node-2'})
    result = score_records(g, [record()])
    assert result['contribution_recall'] == ratio(1, 2)
    assert result['attribution']['missed'] == 1
    assert result['fidelity']['body']['missing_characters'] == len('Expected prose.')


def test_empty_extraction_precision_is_undefined():
    result = score_records(gold(), [])
    assert result['contribution_precision']['value'] is None
    assert result['contribution_precision']['undefined_reason'] == 'no_emitted_contributions'
    assert result['contribution_recall']['numerator'] == 0


def test_matching_is_one_to_one_not_text_similarity():
    result = score_records(gold(), [record(), record(observation='obs-2'), record(container='wrong', observation='obs-3')])
    assert result['contribution_precision'] == ratio(1, 3)
    assert result['invented_observations'] == ['obs-2', 'obs-3']


def test_contamination_and_character_changes():
    result = score_records(gold(), [record(body='Expected prose. SIGNATURE')])
    assert result['contamination']['signature']['occurrences'] == 1
    assert result['contamination']['signature']['affected_records'] == 1
    assert result['fidelity']['body']['extra_characters'] == len(' SIGNATURE')
    assert result['end_to_end_usable_recall']['numerator'] == 0


def test_family_and_lineage_split_leakage_rejected():
    page = {'id': 'a', 'family': 'one', 'thread': 'thread-1', 'lineage': 'one-v1', 'split': 'development'}
    for field in ['family', 'thread', 'lineage']:
        other = {'id': 'b', 'family': 'two', 'thread': 'thread-2', 'lineage': 'two-v1', 'split': 'held_out'}
        other[field] = page[field]
        with pytest.raises(Failure, match='dataset_split_leakage'):
            validate_splits({'pages': [page, other]})


def test_fictional_dataset_extracts_every_reference(tmp_path):
    report = evaluate(FIXTURES / 'dataset.json', FIXTURES / 'evaluation-config.json', tmp_path / 'evaluation')
    assert report['status'] == 'complete'
    assert report['human_reviewed'] is False
    assert report['data_classes'] == ['synthetic']
    assert report['cost']['provider_calls'] == 0
    assert len(report['per_layout']) == 4
    assert report['aggregate']['contribution_recall'] == ratio(13, 13)
    assert report['aggregate']['ordered_parts_exact'] == ratio(13, 13)
    assert report['aggregate']['end_to_end_usable_recall'] == ratio(13, 13)
    assert all(p['grounding']['status'] == 'passed' for p in report['pages'])
    assert report['unexecuted'][0]['status'] == 'not_run'
    assert (tmp_path / 'evaluation' / 'registration.json').is_file()


def test_deliberately_wrong_author_passes_grounding_but_fails_semantics(tmp_path):
    from ahif_html import executor, index
    from importlib.util import spec_from_file_location, module_from_spec
    module_spec = spec_from_file_location('fictional_helper', FIXTURES / 'build_fixtures.py')
    helper = module_from_spec(module_spec)
    module_spec.loader.exec_module(helper)
    capture = FIXTURES / 'forum.html'
    metadata = load_json(FIXTURES / 'forum.metadata.json')
    ix = index.build(capture, metadata)
    plan = load_json(FIXTURES / 'forum.plan.json')
    wrong = helper.value(ix, 'f1-wrong-author', 'href')
    plan['contributions'][0]['author']['identity']['source'] = wrong
    plan['contributions'][0]['author']['label'] = helper.value(ix, 'f1-wrong-author')
    plan['contributions'][0]['author']['evidence'] = [helper.node(ix, 'f1-wrong-author')]
    executor.extract(capture, plan, tmp_path / 'wrong', metadata=metadata)
    verification = executor.verify(capture, plan, tmp_path / 'wrong', metadata=metadata)
    assert verification['status'] == 'passed'
    from ahif_html.evaluate import _load_records
    scored = score_records(load_json(FIXTURES / 'forum.gold.json'), _load_records(tmp_path / 'wrong' / 'bundle' / 'records.jsonl'))
    assert scored['attribution']['wrong_account'] == 1
    assert scored['end_to_end_usable_recall']['numerator'] == 1


def test_dataset_traversal_rejected(tmp_path):
    source = load_json(FIXTURES / 'dataset.json')
    source['pages'][0]['capture'] = '../outside.html'
    path = tmp_path / 'dataset.json'
    write_json(path, source)
    with pytest.raises(Failure, match='dataset_path_invalid'):
        evaluate(path, FIXTURES / 'evaluation-config.json', tmp_path / 'result')


def test_changed_wording_is_not_normalized_away():
    changed = score_records(gold(), [record(body='Expected Prose.')])
    assert changed['ordered_parts_exact']['numerator'] == 0
    assert changed['fidelity']['body']['transformed_characters'] == 1


def test_unknown_reference_does_not_reward_invented_identity():
    g = gold()
    g['contributions'][0]['actor_id'] = None
    scored = score_records(g, [record(actor='invented-person')])
    assert scored['attribution']['unsupported_assignment'] == 1
    assert scored['end_to_end_usable_recall']['numerator'] == 0


def test_metamorphic_variant_preserves_semantics_not_capture_identity(tmp_path):
    from ahif_html import executor
    from ahif_html.evaluate import _load_records
    outputs = []
    for name in ('forum', 'forum-variant'):
        run = tmp_path / name
        executor.extract(FIXTURES / (name + '.html'), load_json(FIXTURES / (name + '.plan.json')), run,
                         metadata=load_json(FIXTURES / (name + '.metadata.json')))
        outputs.append({r['record_key']['id']: r for r in _load_records(run / 'bundle' / 'records.jsonl')})
    assert set(outputs[0]) == set(outputs[1])
    for native_id in outputs[0]:
        before, after = outputs[0][native_id], outputs[1][native_id]
        assert before['actor'] == after['actor']
        assert before['relations'] == after['relations']
        assert [(p['role'], p['text'], p['attribution']) for p in before['content']['parts']] == [(p['role'], p['text'], p['attribution']) for p in after['content']['parts']]
        assert before['observation_id'] != after['observation_id']


def test_duplicate_appearances_do_not_become_extra_events(tmp_path):
    from ahif_html import executor
    from ahif_html.evaluate import _load_records
    run = tmp_path / 'micro'
    executor.extract(FIXTURES / 'micro.html', load_json(FIXTURES / 'micro.plan.json'), run,
                     metadata=load_json(FIXTURES / 'micro.metadata.json'))
    scored = score_records(load_json(FIXTURES / 'micro.gold.json'), _load_records(run / 'bundle' / 'records.jsonl'))
    assert scored['emitted_observations'] == 5
    assert scored['distinct_event_keys'] == 4


def test_source_map_swap_is_replay_failure(tmp_path):
    from ahif_html import executor
    run = tmp_path / 'forum'
    capture, plan, metadata = FIXTURES / 'forum.html', load_json(FIXTURES / 'forum.plan.json'), load_json(FIXTURES / 'forum.metadata.json')
    executor.extract(capture, plan, run, metadata=metadata)
    map_path = run / 'evidence' / 'source-map.jsonl'
    lines = map_path.read_bytes().splitlines(keepends=True)
    assert len(lines) == 2
    map_path.write_bytes(b''.join(reversed(lines)))
    with pytest.raises(Failure, match='canonical_reexecution_mismatch'):
        executor.verify(capture, plan, run, metadata=metadata)


def test_shared_deadline_interrupts_in_progress_work():
    import signal
    import time
    from ahif_html.evaluate import _deadline, _EvaluationDeadline
    original = signal.getsignal(signal.SIGALRM)
    with pytest.raises(_EvaluationDeadline):
        with _deadline(0.002):
            time.sleep(0.2)
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    assert signal.getsignal(signal.SIGALRM) == original


def test_nested_deadline_preserves_remaining_enclosing_budget():
    import signal
    import time
    from ahif_html.evaluate import _deadline
    original_handler = signal.getsignal(signal.SIGALRM)
    original_timer = signal.getitimer(signal.ITIMER_REAL)
    assert original_timer == (0.0, 0.0)
    signal.signal(signal.SIGALRM, lambda *_: None)
    signal.setitimer(signal.ITIMER_REAL, 0.5)
    try:
        with _deadline(1):
            selected, _ = signal.getitimer(signal.ITIMER_REAL)
            assert 0 < selected <= 0.5
            time.sleep(0.01)
        remaining, _ = signal.getitimer(signal.ITIMER_REAL)
        assert 0 < remaining < 0.495
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, original_handler)
