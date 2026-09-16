"""Independent bounded engineering audit of host-controlled boundaries.

Expected failures here describe the contract, not xfailed acceptance criteria.
Only fictional source strings are used.
"""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from ahif_html import index
from ahif_html.common import C, Failure, fresh, load_json, safe_read, write_json
from ahif_html.plans import validate_plan
from ahif_html.executor import materialize
from test_executor import fixture, only, contribution


def html_index(tmp_path, html, metadata=None):
    path = tmp_path / 'audit.html'; path.write_text(html, encoding='utf-8')
    return index.build(path, metadata)


def test_model_view_withholds_form_credentials_scripts_and_unsafe_href(tmp_path):
    evidence = html_index(tmp_path, '<!doctype html><article><p>Harmless prose.</p>'
        '<form><input name="password" value="FICTIONAL_FORM_SECRET"><textarea>FICTIONAL_DRAFT_SECRET</textarea></form>'
        '<script>FICTIONAL_SCRIPT_SECRET</script><!-- FICTIONAL_COMMENT_SECRET -->'
        '<a href="https://user:FICTIONAL_URL_PASSWORD@example.test/path?q=FICTIONAL_QUERY_SECRET">link</a>'
        '<a href="javascript:FICTIONAL_EXECUTION()">unsafe</a>'
        '<div hidden>FICTIONAL_HIDDEN_SECRET</div></article>')
    inspector = index.Inspector(evidence)
    output = inspector.call('page_outline', {'limit': 100, 'max_characters': 100})
    encoded = C(output).decode()
    for secret in ('FICTIONAL_FORM_SECRET', 'FICTIONAL_DRAFT_SECRET', 'FICTIONAL_SCRIPT_SECRET',
                   'FICTIONAL_COMMENT_SECRET', 'FICTIONAL_URL_PASSWORD', 'FICTIONAL_QUERY_SECRET',
                   'FICTIONAL_EXECUTION', 'FICTIONAL_HIDDEN_SECRET'):
        assert secret not in encoded


def test_model_gateway_rejects_arbitrary_actions_and_attributes(tmp_path):
    evidence = html_index(tmp_path, '<article data-secret="FICTIONAL_SECRET">words</article>')
    inspector = index.Inspector(evidence)
    article = only(evidence, tag='article')
    for tool, args in [('shell', {'cmd': 'touch unwanted'}), ('http', {'url': 'https://example.test'}),
                       ('read_attribute', {'node_ref': article, 'attribute': 'data-secret'})]:
        with pytest.raises(Failure):
            inspector.call(tool, args)


def test_read_and_destination_symlinks_refused(tmp_path):
    source = tmp_path / 'source'; source.write_text('fictional')
    alias = tmp_path / 'alias'; alias.symlink_to(source)
    with pytest.raises(Failure, match='symlink'):
        safe_read(alias)
    directory = tmp_path / 'real'; directory.mkdir()
    parent_link = tmp_path / 'linked'; parent_link.symlink_to(directory, target_is_directory=True)
    with pytest.raises(Failure, match='symlink'):
        with fresh(parent_link / 'out'):
            pass
    assert not (directory / 'out').exists()


def test_selector_budget_is_host_enforced(tmp_path):
    evidence = html_index(tmp_path, '<article><p>A</p><p>B</p></article>')
    inspector = index.Inspector(evidence, {'selector_work': 1})
    with pytest.raises(Failure, match='selector|budget|work'):
        inspector.call('find_structural_candidates', {'criteria': {'tag': 'article'}, 'limit': 1})


def test_native_identity_must_not_be_arbitrarily_sliced(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    plan['contributions'][0]['identity']['source'].update(start=0, end=1)
    with pytest.raises(Failure, match='identity|slice'):
        validate_plan(evidence, plan)


def test_semantically_invalid_capture_date_is_rejected_at_index(tmp_path):
    with pytest.raises(Failure, match='time|date|capture'):
        html_index(tmp_path, '<p>Useful evidence</p>', {'captured_at': {
            'status': 'known', 'value': '2026-02-30T12:00:00Z',
            'precision': 'second', 'basis': 'supplier_declared'}})


def test_global_exclusion_cannot_be_bypassed_by_descendant_part_root(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    selected = plan['contributions'][0]
    body = only(evidence, selected['container'], tag='div', attribute='class', value='body')
    signature = only(evidence, selected['container'], tag='aside')
    signature_text = next(n['ref'] for n in index.descendants(evidence, signature) if n['kind'] == 'text')
    selected['parts'] = [{'root': signature_text, 'role': 'body', 'attribution': 'record_actor',
                          'exclude': [], 'evidence': [signature]}]
    # Existing contribution exclusion names signature ancestor, not this text node.
    assert selected['excluded'] == [{'node': signature, 'reason': 'signature'}]
    with pytest.raises(Failure, match='exclu|part'):
        validate_plan(evidence, plan)


def test_nested_contribution_ownership_cannot_be_bypassed_below_container(tmp_path):
    evidence = html_index(tmp_path, '<!doctype html><article data-post-id="outer"><header><span class="author">Fictional Outer</span></header><time datetime="2026-09-15">date</time><div class="body">Outer prose.</div><article data-comment-id="inner"><header><span class="author">Fictional Inner</span></header><time datetime="2026-09-15">date</time><div class="body">Inner prose.</div></article></article>', {'source_url': 'https://example.test/thread'})
    outer = only(evidence, attribute='data-post-id', value='outer')
    inner = only(evidence, attribute='data-comment-id', value='inner')
    inner_contribution = contribution(evidence, inner, 'data-comment-id', kind='reply')
    outer_contribution = deepcopy(inner_contribution)
    outer_contribution.update(container=outer, kind='post', identity={'kind': 'native',
        'source': {'node': outer, 'kind': 'attribute', 'attribute': 'data-post-id'},
        'basis': 'documented_native', 'evidence': [outer]}, evidence=[outer],
        excluded=[{'node': inner, 'reason': 'nested_contribution'}])
    inner_contribution['parts'] = []
    # Outer steals a descendant body below the globally excluded inner container;
    # empty inner parts avoid relying on the separate overlapping-text check.
    plan = {'plan_version': '1.0.0', 'capture_sha256': evidence['capture']['sha256'],
            'index_id': evidence['index_id'], 'profile': 'html-structural-text/1.0.0', 'ancestry': [],
            'origin': {'kind': 'manual', 'producer': 'independent-boundary-audit'},
            'review': {'status': 'unreviewed', 'reviewer': None},
            'contributions': [outer_contribution, inner_contribution], 'rejected': [], 'unresolved': []}
    with pytest.raises(Failure, match='exclu|nested|part|ownership'):
        validate_plan(evidence, plan)


def test_overlap_duplicate_parts_is_rejected(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    selected = plan['contributions'][1]
    selected['parts'].append(deepcopy(selected['parts'][0]))
    with pytest.raises(Failure, match='overlapping'):
        validate_plan(evidence, plan)


def minimal_recipe():
    from ahif_html.common import PROFILE_SHA
    return {'recipe_version': '1.0.0', 'recipe_id': 'fictional-audit',
            'profile_sha256': PROFILE_SHA, 'assumptions': ['One article with one body region.'],
            'containers': {'selector': {'tag': 'article'}, 'minimum': 1, 'maximum': 1},
            'bindings': [{'name': '$body', 'selector': {'class_token': 'body'}, 'kind': 'element'}],
            'contribution_template': {'container': '$container', 'kind': 'post', 'identity': None,
                'author': None, 'created': None, 'updated': None,
                'parts': [{'root': '$body', 'role': 'body', 'attribution': 'unknown',
                           'exclude': [], 'evidence': ['$body']}],
                'excluded': [], 'relations': [], 'links': [], 'state': None, 'completeness': None,
                'evidence': ['$container']}}


def test_recipe_duplicate_binding_names_do_not_silently_overwrite(tmp_path):
    from ahif_html.recipes import instantiate
    evidence = html_index(tmp_path, '<!doctype html><article><p class="body">Body</p><aside class="signature">Signature</aside></article>')
    recipe = minimal_recipe()
    recipe['bindings'].append({'name': '$body', 'selector': {'class_token': 'signature'}, 'kind': 'element'})
    with pytest.raises(Failure, match='binding|duplicate'):
        instantiate(evidence, recipe)


def test_recipe_cannot_override_reserved_container_binding(tmp_path):
    from ahif_html.recipes import instantiate
    evidence = html_index(tmp_path, '<!doctype html><article><p class="body">Body</p></article>')
    recipe = minimal_recipe()
    recipe['bindings'].append({'name': '$container', 'selector': {'class_token': 'body'}, 'kind': 'element'})
    with pytest.raises(Failure, match='binding|reserved|container'):
        instantiate(evidence, recipe)


def test_scoped_relation_evidence_is_exposed_to_planner(tmp_path):
    evidence = html_index(tmp_path, '<article data-post-id="p2" data-parent-post-id="p1">Reply.</article>')
    article = only(evidence, tag='article')
    inspector = index.Inspector(evidence)
    output = inspector.call('read_attribute', {'node_ref': article, 'attribute': 'data-parent-post-id'})
    assert output['value']['value'] == 'p1'


def test_batch_total_output_budget_includes_required_sidecars(tmp_path):
    from ahif_html.cli import batch
    capture, metadata, evidence, plan = fixture(tmp_path)
    files, result, _ = materialize(evidence, plan)
    budget = sum(map(len, files.values())) + 100
    write_json(tmp_path / 'plan.json', plan)
    write_json(tmp_path / 'metadata.json', metadata)
    manifest = {'batch_version': '1.0.0',
                'pages': [{'id': 'one', 'capture': capture.name, 'plan': 'plan.json', 'metadata': 'metadata.json'}],
                'max_total_input_bytes': 1000000, 'max_total_output_bytes': budget, 'max_wall_seconds': 60}
    write_json(tmp_path / 'batch.json', manifest)
    result = batch(tmp_path / 'batch.json', tmp_path / 'batch-run')
    assert result['output_bytes'] <= budget
    assert result['status'] != 'complete_execution'


def test_batch_refuses_relative_traversal_before_reading(tmp_path):
    from ahif_html.cli import batch
    manifest = {'batch_version': '1.0.0',
                'pages': [{'id': 'one', 'capture': '../outside.html', 'plan': 'plan.json', 'metadata': None}],
                'max_total_input_bytes': 1000000, 'max_total_output_bytes': 1000000, 'max_wall_seconds': 60}
    write_json(tmp_path / 'batch.json', manifest)
    with pytest.raises(Failure, match='batch_path_invalid'):
        batch(tmp_path / 'batch.json', tmp_path / 'must-not-exist')
    assert not (tmp_path / 'must-not-exist').exists()


def test_discarded_tool_preview_does_not_count_as_exposed_evidence(tmp_path):
    evidence = html_index(tmp_path, '<article class="' + 'x' * 1000 + '">Tiny text.</article>')
    article = only(evidence, tag='article')
    inspector = index.Inspector(evidence, {'tool_characters': 300})
    output = inspector.call('inspect_node', {'node_ref': article, 'depth': 1, 'max_characters': 10})
    assert output['truncated'] is True
    assert 'nodes' not in output
    accounting = inspector.audit()
    assert article not in accounting['exposed']
    assert article not in accounting['inspected']
    assert article in accounting['unreviewed_candidates']


def test_custom_candidate_ceiling_is_not_ignored(tmp_path):
    capture, metadata, evidence, plan = fixture(tmp_path)
    try:
        _, result, _ = materialize(evidence, plan, {'candidates': 1})
    except Failure as exc:
        assert exc.status == 'resource_limit'
    else:
        assert result['record_observations'] <= 1
        assert result['status'] == 'partial_execution'


def test_recipe_custom_selector_ceiling_is_not_ignored(tmp_path):
    from ahif_html.recipes import apply_recipe
    capture = tmp_path / 'recipe.html'
    capture.write_text('<!doctype html><article><p class="body">Body</p></article>')
    with pytest.raises(Failure, match='selector|budget|work'):
        apply_recipe(capture, minimal_recipe(), tmp_path / 'recipe-run', limits={'selector_work': 1})
