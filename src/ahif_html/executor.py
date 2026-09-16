"""Source-linked, model-free AHIF emission and independent extraction replay.

No source wording is accepted from plans. All output words come from the immutable
index; only registered structural separators may be inserted.
"""
from __future__ import annotations
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit

from .common import (C, PROFILE, PROFILE_SHA, GATE_CONTRACT, GATE_SHA, Failure, ahif, bound, check_path,
                     fresh, limits_for, load_json, safe_read, sha, validate, write_json)
from . import index as indexing
from . import __version__
from .plans import plan_id, validate_plan

EXT = 'org.ahif-html:extraction'
CANONICAL_PATHS = (
    'bundle/manifest.json', 'bundle/records.jsonl',
    'evidence/capture-manifest.json', 'evidence/index.json',
    'evidence/finalized-plan.json', 'evidence/source-map.jsonl',
    'evidence/decisions.jsonl', 'evidence/interpretation.json',
)
UNKNOWN_LABELS = {'guest', 'anonymous', 'unknown', 'deleted', '[deleted]', '[removed]'}
NATIVE_COLLECTIONS = {'data-post-id': 'posts', 'data-comment-id': 'comments', 'data-review-id': 'reviews'}
RELATION_COLLECTIONS = {'data-parent-post-id': 'posts', 'data-quote-post-id': 'posts',
                        'data-repost-post-id': 'posts', 'data-parent-comment-id': 'comments',
                        'data-parent-review-id': 'reviews'}


def unknown(reason='not_supplied', raw=None):
    value = {'status': 'unknown', 'reason': reason}
    if raw is not None and len(raw) <= 1024:
        value['raw'] = raw
    return value


def parse_time(raw, *, supplied=False):
    """Registered ISO date/seconds parser; never infer zones or rounded seconds."""
    if raw is None:
        return unknown()
    if not isinstance(raw, str) or len(raw) > 1024:
        return unknown('unsupported_time_representation')
    basis = 'supplier_declared' if supplied else 'source'
    if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', raw):
        try:
            date.fromisoformat(raw)
            return {'status': 'date_only', 'value': raw, 'utc_offset': None,
                    'basis': basis, 'raw': raw}
        except ValueError:
            return unknown('invalid_calendar_date', raw)
    match = re.fullmatch(r'([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-5][0-9])(?:\.([0-9]{1,9}))?(Z|[+-][0-9]{2}:[0-9]{2})', raw)
    if not match:
        return unknown('unsupported_or_ambiguous_time', raw)
    fraction, zone = match[2] or '', match[3]
    if zone == '-00:00':
        return unknown('timezone_not_available', raw)
    try:
        instant = datetime.fromisoformat(match[1])
        if zone != 'Z':
            hour, minute = int(zone[1:3]), int(zone[4:6])
            if hour > 14 or minute > 59 or (hour == 14 and minute):
                return unknown('unsupported_timezone_offset', raw)
            offset = timedelta(hours=hour, minutes=minute)
            instant = instant - offset if zone[0] == '+' else instant + offset
        text = instant.isoformat(timespec='seconds') + ('.' + fraction if fraction else '') + 'Z'
        result = {'status': 'known', 'value': text,
                  'precision': 'second' if not fraction else 'millisecond' if len(fraction) <= 3 else 'microsecond' if len(fraction) <= 6 else 'nanosecond',
                  'basis': basis if supplied or zone == 'Z' else 'source_documented_conversion', 'raw': raw}
        ahif.check_time(result)
        return result
    except (ValueError, OverflowError, ahif.Invalid):
        return unknown('invalid_calendar_time', raw)


def namespace(metadata):
    source = metadata.get('source_url')
    if source:
        try:
            parsed = urlsplit(source)
            origin = parsed.scheme + '://' + parsed.netloc
            if parsed.scheme in ('http', 'https') and parsed.netloc and not parsed.username and ahif.absolute_uri(origin):
                return origin
        except ValueError:
            pass
    return 'urn:ahif:source-local'


def resolved_uri(raw, metadata):
    """Only supplied HTTP(S) source URL is a base; no HTML base or redirects."""
    if not raw or not raw.strip():
        return None, 'empty_identity_value'
    if ahif.absolute_uri(raw):
        return raw, 'identity_uri_as_supplied'
    base = metadata.get('source_url')
    if base and namespace(metadata) != 'urn:ahif:source-local':
        result = urljoin(base, raw)
        if ahif.absolute_uri(result):
            return result, 'resolve_relative_against_supplied_source_url'
    return None, 'relative_identity_without_base'


def key(authority, collection, kind, value):
    return {'namespace': authority, 'collection': collection, 'id_type': kind, 'id': value}


def locator(index, ref):
    return {'kind': 'other', 'value': index['index_id'] + '#' + ref,
            'artifact_sha256': index['capture']['sha256']}


def source_descriptor(index):
    metadata = index['capture']['metadata']
    redistribution = metadata.get('redistribution') or {'status': 'unknown', 'basis': ''}
    if isinstance(redistribution, str):
        redistribution = {'status': redistribution, 'basis': ''}
    source = {'mode': 'synthetic' if metadata.get('data_class') == 'synthetic' else 'web_capture',
              'description': 'Supplied ' + metadata.get('capture_kind', 'html_response') + '; extraction is a structural interpretation, not source verification.',
              'acquired_at': unknown(),
              'content_as_of': metadata.get('captured_at') or unknown(),
              'origin': metadata.get('source_url'),
              'artifacts': [{'sha256': index['capture']['sha256'], 'byte_length': index['capture']['byte_length'],
                             'media_type': metadata.get('media_type') or 'text/html', 'label': 'supplied-capture', 'included_path': None}],
              'access': metadata.get('access') or 'unknown', 'redistribution': redistribution,
              'extensions': {EXT: {'capture_kind': metadata.get('capture_kind', 'html_response'),
                                   'capture_metadata': metadata, 'index_id': index['index_id'],
                                   'parser': index['parser'], 'profile_sha256': PROFILE_SHA}}}
    source['source_id'] = ahif.bound_id('source', source)
    return source


def _field(path, refs=(), *, outcome='grounded_uncertain', operation='source_reference', decision=None):
    return {'path': path, 'outcome': outcome, 'source_refs': list(refs),
            'operation': operation, 'decision': decision, 'mappings': None,
            'unit': None, 'coordinate_space': None}


def _sources(author):
    if not author:
        return []
    return [v for v in (author.get('label'), author.get('identity', {}).get('source') if author.get('identity') else None) if v]


def _captured_state_support(index, plan, contribution):
    """Narrow positive evidence for a textless lifecycle observation.

    The declared state enum and container existence alone are insufficient. This
    gate recognizes an exact data-state value or an explicitly referenced text
    node containing only that state marker. It does not infer arbitrary prose or
    establish that the source's state assertion is true.
    """
    state = contribution['state']
    if state is None:
        return False
    nodes = indexing.by_ref(index)
    blocked = {item['node'] for item in contribution['excluded']}
    blocked.update(ref for part in contribution['parts'] for ref in part['exclude'])
    own_scope = {node['ref'] for node in indexing.descendants(index, contribution['container'])}
    blocked.update(other['container'] for other in plan['contributions']
                   if other['container'] != contribution['container'] and other['container'] in own_scope)
    for ref in state['evidence']:
        node = nodes[ref]
        ancestor = node
        while ancestor is not None:
            if ancestor['ref'] in blocked or ancestor['flags'] or ancestor['tag'] in ('blockquote', 'pre', 'code'):
                break
            ancestor = nodes.get(ancestor['parent'])
        if ancestor is not None:
            continue
        if node['kind'] == 'element' and indexing.attrs(node).get('data-state') == state['value']:
            return True
        if node['kind'] == 'text' and node['text'].strip().casefold() in (state['value'], '[' + state['value'] + ']'):
            return True
    return False


def _one_record(index, plan, number, source, limits):
    contribution = plan['contributions'][number]
    container = contribution['container']
    pid = plan_id(plan)
    decision_root = '/contributions/' + str(number)
    metadata = index['capture']['metadata']
    authority = namespace(metadata)
    source_id = source['source_id']
    fields = []
    identity = contribution['identity']
    record_key = key(authority, 'records', 'source_local', source_id + '#' + container)
    identity_operation = 'capture_scoped_appearance'
    if identity:
        raw = indexing.read_value(index, identity['source'])
        if identity['kind'] == 'native':
            collection = NATIVE_COLLECTIONS.get(identity['source'].get('attribute'))
            if raw.strip() and collection and authority != 'urn:ahif:source-local':
                record_key = key(authority, collection, 'native', raw)
                identity_operation = 'documented_native_id'
            else:
                identity_operation = 'native_scope_unresolved_capture_local_fallback'
        else:
            uri, identity_operation = resolved_uri(raw, metadata)
            if uri:
                record_key = key(authority, 'records', 'uri', uri)
    fields.append(_field('/record_key', [identity['source']] if identity else [],
                         operation=identity_operation, decision=decision_root + '/identity'))
    actor = None
    author = contribution['author']
    label = indexing.read_value(index, author['label']) if author and author.get('label') else None
    actor_operation = 'unknown_author'
    if author and not (label is not None and label.strip().casefold() in UNKNOWN_LABELS):
        author_identity = author.get('identity')
        if author_identity:
            value = indexing.read_value(index, author_identity['source'])
            kind = author_identity['kind']
            if value.strip().casefold() not in UNKNOWN_LABELS:
                if kind == 'uri':
                    value, actor_operation = resolved_uri(value, metadata)
                else:
                    actor_operation = 'source_scoped_handle' if kind == 'handle' else 'documented_native_id'
                if value:
                    actor = key(authority, 'accounts', kind, value)
        elif label and label.strip():
            actor = key(authority, 'accounts', 'handle', label)
            actor_operation = 'source_scoped_handle'
    fields.append(_field('/actor', _sources(author), outcome='grounded_uncertain' if actor else 'missing_evidence',
                         operation=actor_operation, decision=decision_root + '/author'))
    times = {}
    for label_name, field_name in [('created', 'created_at'), ('updated', 'updated_at')]:
        ref = contribution[label_name]
        raw = indexing.read_value(index, ref) if ref else None
        times[field_name] = parse_time(raw)
        fields.append(_field('/' + field_name, [ref] if ref else [],
                             outcome='missing_evidence' if not ref else 'unresolved_assignment' if times[field_name]['status'] == 'unknown' else 'grounded_uncertain',
                             operation='iso_date_or_zoned_seconds/1.0.0', decision=decision_root + '/' + label_name))
    node_map = indexing.by_ref(index)
    pending_parts = []
    for part_number, planned in enumerate(contribution['parts']):
        exclusions = sorted(set(planned['exclude'] + [item['node'] for item in contribution['excluded']]))
        pieces = indexing.text_segments(index, planned['root'], exclusions)
        for piece_number, piece in enumerate(pieces):
            if not piece['text']:
                continue
            source_positions = [(node_map[m['source']['node']]['order'], m['source']['start'])
                                for m in piece['mappings'] if 'source' in m]
            if not source_positions:
                continue
            order = min(source_positions)
            pending_parts.append((order, part_number, piece_number, planned, piece))
    pending_parts.sort(key=lambda item: (item[0], item[1], item[2]))
    if len(pending_parts) > limits['parts_per_record']:
        raise Failure('record_part_limit', 'resource_limit')
    parts = []
    for _, part_number, piece_number, planned, piece in pending_parts:
        if len(piece['text']) > 2000000:
            raise Failure('ahif_part_character_limit', 'resource_limit')
        attribution = planned['attribution']
        if attribution == 'record_actor' and actor is None:
            attribution = 'unknown'
        part = {'part_id': 'part-' + str(len(parts) + 1), 'role': planned['role'],
                'attribution': {'relation': attribution, 'account_key': None},
                'format': 'plain', 'format_variant': None, 'text': piece['text'], 'fidelity': 'transformed',
                'language': {'tag': 'und', 'basis': 'unknown'}, 'locator': locator(index, planned['root'])}
        path = '/content/parts/' + str(len(parts)) + '/text'
        mapping = _field(path, [{'node': planned['root'], 'kind': 'region'}],
                         operation=PROFILE['text_policy'], decision=decision_root + '/parts/' + str(part_number))
        mapping.update({'mappings': piece['mappings'], 'unit': 'unicode_code_point',
                        'coordinate_space': 'emitted_part_text'})
        fields.append(mapping)
        fields.append(_field('/content/parts/' + str(len(parts)) + '/role',
                             [{'node': n, 'kind': 'region'} for n in planned['evidence']],
                             operation='structural_role_interpretation', decision=decision_root + '/parts/' + str(part_number)))
        fields.append(_field('/content/parts/' + str(len(parts)) + '/attribution',
                             _sources(author) + [{'node': n, 'kind': 'region'} for n in planned['evidence']],
                             operation='structural_ownership_interpretation', decision=decision_root + '/parts/' + str(part_number)))
        parts.append(part)
    state = contribution['state']['value'] if contribution['state'] else 'unknown'
    completeness = contribution['completeness']['value'] if contribution['completeness'] else 'unknown'
    if completeness == 'redacted':
        content = {'availability': 'redacted', 'completeness': 'partial' if parts else 'not_applicable',
                   'reason': 'source_region_declares_redaction', 'parts': parts}
    elif parts:
        content = {'availability': 'present', 'completeness': completeness, 'reason': None, 'parts': parts}
    else:
        content = {'availability': 'unavailable', 'completeness': 'not_applicable',
                   'reason': 'no_supported_nonempty_text_selection', 'parts': []}
    fields.append(_field('/content/completeness', [{'node': n, 'kind': 'region'} for n in contribution['completeness']['evidence']] if contribution['completeness'] else [],
                         outcome='grounded_uncertain' if contribution['completeness'] else 'missing_evidence', operation='source_state_interpretation', decision=decision_root + '/completeness'))
    fields.append(_field('/lifecycle/state', [{'node': n, 'kind': 'region'} for n in contribution['state']['evidence']] if contribution['state'] else [],
                         outcome='grounded_uncertain' if contribution['state'] else 'missing_evidence', operation='source_state_interpretation', decision=decision_root + '/state'))
    relations = []
    for relation_number, relation in enumerate(contribution['relations']):
        raw = indexing.read_value(index, relation['target']) if relation['target'] else None
        target_key, target_url, resolution = None, None, 'unknown'
        if raw and raw.strip():
            if relation['kind'] == 'native' and authority != 'urn:ahif:source-local':
                collection = RELATION_COLLECTIONS.get(relation['target'].get('attribute'))
                if collection:
                    target_key = key(authority, collection, 'native', raw)
                    resolution = 'known_identity'
            elif relation['kind'] == 'uri':
                target_key_value, _ = resolved_uri(raw, metadata)
                target_url = raw
                if target_key_value:
                    target_key = key(authority, 'records', 'uri', target_key_value)
                    resolution = 'known_identity'
                else:
                    resolution = 'locator_only'
        relations.append({'type': relation['type'], 'target_type': 'record', 'target_key': target_key,
                          'target_url': target_url, 'resolution': resolution})
        fields.append(_field('/relations/' + str(relation_number), [relation['target']] if relation['target'] else [],
                             operation='source_relation_interpretation', decision=decision_root + '/relations/' + str(relation_number)))
    links = []
    for link_number, planned_link in enumerate(contribution['links']):
        raw = indexing.read_value(index, planned_link['source'])
        if not raw:
            continue
        # Keep destinations verbatim and inert. URI identity resolution above is
        # separate; AHIF's link bases do not include this derived URL rule.
        links.append({'link_id': 'link-' + str(len(links) + 1), 'role': planned_link['role'],
                      'url_as_supplied': raw, 'resolved_url': None, 'resolution_basis': 'not_attempted'})
        fields.append(_field('/links/' + str(len(links) - 1) + '/url_as_supplied', [planned_link['source']],
                             outcome='grounded', decision=decision_root + '/links/' + str(link_number)))
    # Count supported values, not the presence of plan objects/lists. Unknown
    # relations, blank identity fields, and an ungrounded state enum cannot turn
    # an arbitrary empty container into a posting event. Whitespace is preserved
    # in emitted text but is not sufficient evidence by itself.
    positive_text = any(part['text'].strip() for part in parts)
    positive_identity = record_key['id_type'] in ('native', 'uri') and bool(record_key['id'].strip())
    positive_relation = any(relation['resolution'] == 'known_identity' and relation['target_key'] is not None
                            and relation['target_key']['id'].strip() for relation in relations)
    positive_state = _captured_state_support(index, plan, contribution)
    if not (positive_text or positive_identity or positive_relation or positive_state):
        raise Failure('no_actual_contribution_evidence', 'no_contributions_observed')
    normalizer_binding = {'profile_sha256': PROFILE_SHA, 'gate_contract_version': GATE_CONTRACT['version'],
                          'gate_contract_sha256': GATE_SHA, 'plan_id': pid, 'index_id': index['index_id']}
    record = {'format_version': '0.1.1', 'record_key': record_key, 'source_id': source_id,
              'observed_at': source['content_as_of'], 'actor': actor, 'kind': contribution['kind'],
              **times, 'lifecycle': {'state': state, 'edit_state': 'edited' if times['updated_at']['status'] != 'unknown' else 'unknown', 'native_revision_id': None},
              'visibility': 'unknown', 'content': content,
              'provenance': {'locator': locator(index, container),
                             'normalizer': {'name': 'ahif-html', 'version': __version__, 'configuration_sha256': sha(C(normalizer_binding))},
                             'transformations': [{'operation': PROFILE['text_policy'], 'version': '1.0.0',
                                                  'parameters': normalizer_binding, 'input_locator': locator(index, container)}],
                             'notes': 'Source-linked structural interpretation. Authorship, visibility, original completeness and CSS rendering are not established.'},
              'relations': relations, 'links': links,
              'extensions': {EXT: {**normalizer_binding, 'container': container, 'review': plan['review'],
                                   'author_label': label, 'association': 'structural_interpretation'}}}
    if record_key['id_type'] == 'uri':
        record['permalink'] = indexing.read_value(index, identity['source'])
    record['observation_id'] = ahif.bound_id('record', record)
    ahif.row_checks('record', record, {source_id: source})
    fields.extend([
        _field('/kind', [{'node': n, 'kind': 'region'} for n in contribution['evidence']], operation='contribution_kind_interpretation', decision=decision_root + '/kind'),
        _field('/observed_at', [], operation='supplier_capture_metadata', outcome='missing_evidence' if source['content_as_of']['status'] == 'unknown' else 'grounded_uncertain'),
        _field('/visibility', [], operation='unknown_not_inferred', outcome='missing_evidence'),
        _field('/lifecycle/edit_state', [contribution['updated']] if contribution['updated'] else [], operation='known_edit_time_or_unknown'),
        _field('/provenance', [], operation='host_configuration_binding', outcome='host_generated'),
    ])
    mapping = {'source_map_version': '1.0.0', 'capture_sha256': index['capture']['sha256'],
               'index_id': index['index_id'], 'plan_id': pid, 'observation_id': record['observation_id'],
               'record_key': record_key, 'container': container, 'fields': fields}
    validate('source-map', mapping)
    verify_source_maps(index, plan, [record], [mapping])
    return record, mapping


def _pointer(value, path):
    for item in path.split('/')[1:]:
        value = value[int(item)] if isinstance(value, list) else value[item]
    return value


def verify_source_maps(index, plan, records, maps):
    """Check maps against referenced characters AND independently re-run selection.

    Grounding proves provenance, not that a structurally plausible author is correct.
    """
    record_map = {r['observation_id']: r for r in records}
    if len(maps) != len(record_map) or {m['observation_id'] for m in maps} != set(record_map):
        raise Failure('source_map_observation_inventory_mismatch', 'verification_failure')
    nodes = indexing.by_ref(index)
    checked = 0
    for mapping in maps:
        validate('source-map', mapping)
        record = record_map[mapping['observation_id']]
        if mapping['capture_sha256'] != index['capture']['sha256'] or mapping['index_id'] != index['index_id'] or mapping['plan_id'] != plan_id(plan) or mapping['record_key'] != record['record_key'] or mapping['container'] != record['extensions'][EXT]['container']:
            raise Failure('source_map_binding_mismatch', 'verification_failure')
        mapped_paths = []
        for field in mapping['fields']:
            try:
                _pointer(record, field['path'])
                if field['decision'] is not None:
                    _pointer(plan, field['decision'])
                for support in field['source_refs']:
                    if support['node'] not in nodes:
                        raise Failure('source_map_support_reference_invalid', 'verification_failure')
                    if support['kind'] != 'region':
                        indexing.read_value(index, support)
            except (KeyError, IndexError, TypeError) as exc:
                raise Failure('source_map_field_or_decision_invalid', 'verification_failure') from exc
            if field['mappings'] is None:
                continue
            text = _pointer(record, field['path'])
            mapped_paths.append(field['path'])
            cursor = 0
            for segment in field['mappings']:
                begin, end = segment['output_start'], segment['output_end']
                if begin != cursor or end <= begin or end > len(text):
                    raise Failure('source_map_coordinate_gap_or_overlap', 'verification_failure')
                if 'source' in segment:
                    value = indexing.read_value(index, segment['source'])
                else:
                    insertion = segment['insertion']
                    if insertion['node'] not in nodes or nodes[insertion['node']]['kind'] != 'element':
                        raise Failure('source_map_insertion_reference_invalid', 'verification_failure')
                    value = {'block_boundary': '\n', 'line_break': '\n', 'table_cell': '\t'}.get(insertion['operation'])
                    if value is None:
                        raise Failure('source_map_insertion_unregistered', 'verification_failure')
                if text[begin:end] != value:
                    raise Failure('source_map_character_mismatch', 'verification_failure')
                cursor = end
            if cursor != len(text):
                raise Failure('source_map_unattributed_character', 'verification_failure')
            # Re-run the decision; a same-string occurrence elsewhere is insufficient.
            chosen = _pointer(plan, field['decision'])
            parent = _pointer(plan, field['decision'].split('/parts/')[0])
            exclusions = sorted(set(chosen['exclude'] + [e['node'] for e in parent['excluded']]))
            candidates = indexing.text_segments(index, chosen['root'], exclusions)
            if not any(piece['text'] == text and piece['mappings'] == field['mappings'] for piece in candidates):
                raise Failure('source_map_selection_replay_mismatch', 'verification_failure')
            checked += len(text)
        wanted = ['/content/parts/' + str(i) + '/text' for i in range(len(record['content']['parts']))]
        if sorted(mapped_paths) != sorted(wanted):
            raise Failure('source_map_part_inventory_mismatch', 'verification_failure')
    return {'status': 'passed', 'observations': len(records), 'mapped_characters': checked,
            'semantic_attribution': 'not_established_by_grounding'}


def materialize(index, plan, limits=None):
    """Pure accepted-artifact construction; no model, network, raw retention or clock."""
    limits = limits_for(limits)
    plan = validate_plan(index, plan)
    if len(plan['contributions']) > limits['candidates']:
        raise Failure('contribution_candidate_limit', 'resource_limit')
    source = source_descriptor(index)
    records, maps, decisions = [], [], []
    for number, contribution in enumerate(plan['contributions']):
        try:
            record, mapping = _one_record(index, plan, number, source, limits)
            records.append(record); maps.append(mapping)
            decisions.append({'container': contribution['container'], 'status': 'emitted',
                              'observation_id': record['observation_id'], 'reasons': [],
                              'decision': '/contributions/' + str(number)})
        except (Failure, ahif.Invalid) as exc:
            reason = exc.code if isinstance(exc, Failure) else 'ahif_semantic_or_field_bound_refusal'
            decisions.append({'container': contribution['container'], 'status': 'no_evidence' if reason == 'no_actual_contribution_evidence' else 'unsupported',
                              'observation_id': None, 'reasons': [reason], 'decision': '/contributions/' + str(number)})
    records.sort(key=lambda r: r['observation_id'])
    maps.sort(key=lambda r: r['observation_id'])
    if len({r['observation_id'] for r in records}) != len(records):
        raise Failure('identical_observation_duplicate')
    record_bytes = b''.join(C(row) + b'\n' for row in records)
    coverage = {'source_id': source['source_id'], 'account_key': None,
                'scope_description': 'Supplied capture and finalized plan selections only; site, account and discovery completeness are not established.',
                'status': 'unknown', 'basis': 'Bounded structural interpretation of supplied evidence.',
                'selection_description': 'Concrete contribution containers and source-linked fields in the finalized plan.',
                'start': unknown(), 'end': unknown(), 'known_gaps': [], 'reported_totals': []}
    manifest = {'format': 'AHIF', 'format_version': '0.1.1', 'dataset_id': 'ahif-html-' + plan_id(plan)[7:],
                'sources': [source], 'coverage': [coverage],
                'files': [{'path': 'records.jsonl', 'role': 'records', 'sha256': sha(record_bytes),
                           'byte_length': len(record_bytes), 'row_count': len(records)}]}
    ahif.structural('manifest', manifest)
    refs = {n['ref'] for n in index['nodes']}
    selected = {c['container'] for c in plan['contributions']}
    excluded = {x['node'] for x in plan['rejected']}
    unresolved = {x['node'] for x in plan['unresolved']}
    # These describe index regions, not a recall/completeness claim.
    interpretation = {'interpretation_version': '1.1.0', 'plan_id': plan_id(plan), 'profile': PROFILE,
                      'profile_sha256': PROFILE_SHA, 'capture_sha256': index['capture']['sha256'],
                      'gate_contract': GATE_CONTRACT, 'gate_contract_sha256': GATE_SHA,
                      'index_id': index['index_id'], 'review': plan['review'],
                      'region_accounting': {'indexed_nodes': len(refs), 'selected_containers': sorted(selected),
                                            'rejected_regions': plan['rejected'], 'unresolved_regions': plan['unresolved'],
                                            'not_explicitly_classified_nodes': sorted(refs - selected - excluded - unresolved)},
                      'indicators': index['indicators'], 'coverage_claim': 'not_established',
                      'uncertainties': ['source authenticity', 'personal authorship', 'CSS-dependent visibility',
                                        'uncaptured contributions', 'inline semantic quotation', 'cross-capture handle continuity', 'source-local appearance equivalence and duplication unresolved']}
    files = {'bundle/manifest.json': C(manifest) + b'\n', 'bundle/records.jsonl': record_bytes,
             'evidence/capture-manifest.json': C({'capture_manifest_version': '1.0.0', **index['capture'], 'raw_retention': 'external_supplied_bytes'}) + b'\n',
             'evidence/index.json': C(index) + b'\n', 'evidence/finalized-plan.json': C(plan) + b'\n',
             'evidence/source-map.jsonl': b''.join(C(row) + b'\n' for row in maps),
             'evidence/decisions.jsonl': b''.join(C(row) + b'\n' for row in decisions),
             'evidence/interpretation.json': C(interpretation) + b'\n'}
    if sum(len(value) for value in files.values()) > limits['output_bytes']:
        raise Failure('canonical_output_byte_limit', 'resource_limit')
    has_partial = bool(plan['unresolved'] or index['indicators'] or any(d['status'] != 'emitted' for d in decisions))
    status = 'partial_execution' if has_partial else 'complete_execution' if records else 'no_contributions_observed'
    result = {'run_status_version': '1.0.0', 'status': status, 'plan_id': plan_id(plan),
              'capture_sha256': index['capture']['sha256'], 'profile_sha256': PROFILE_SHA,
              'record_observations': len(records), 'distinct_record_keys': len({C(r['record_key']) for r in records}),
              'text_parts': sum(len(r['content']['parts']) for r in records),
              'text_characters': sum(len(p['text']) for r in records for p in r['content']['parts']),
              'unsupported_contributions': sum(d['status'] != 'emitted' for d in decisions),
              'coverage': 'not_established', 'limits': limits,
              'canonical_files': [{'path': name, 'sha256': sha(files[name]), 'byte_length': len(files[name])} for name in sorted(files)]}
    result['canonical_sha256'] = sha(C(result['canonical_files']))
    validate('run-status', result)
    grounding = verify_source_maps(index, plan, records, maps)
    return files, result, grounding


def execute_index(index, plan, destination, limits=None):
    files, result, grounding = materialize(index, plan, limits)
    with fresh(destination) as stage:
        for name, data in files.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.write_bytes(data)
        ahif_result = ahif.validate_bundle(stage / 'bundle', require_canonical=True)
        (stage / 'verification').mkdir(mode=0o700)
        write_json(stage / 'verification/ahif-check.json', ahif_result)
        write_json(stage / 'verification/extraction-check.json', grounding)
        write_json(stage / 'run-receipt.json', result)
        from .review import write_review
        write_review(stage, stage / 'review')
        # The per-page ceiling includes required review, verification and receipt
        # sidecars, not only the canonical extraction set. Atomic staging prevents
        # a quota failure from publishing a success-shaped partial directory.
        total_bytes = sum(path.stat().st_size for path in stage.rglob('*') if path.is_file())
        if total_bytes > limits_for(limits)['output_bytes']:
            raise Failure('output_total_byte_limit', 'resource_limit')
    return result


def extract(capture, plan, destination, metadata=None, limits=None):
    if not isinstance(plan, dict):
        plan = load_json(plan)
    evidence = indexing.build(Path(capture), metadata=metadata, limits=limits)
    return execute_index(evidence, plan, destination, limits=limits)


def verify(capture, plan, run, metadata=None, limits=None):
    """Rebuild from supplied bytes and externally supplied finalized plan.

    Stored receipts cannot authorize changed output; even rehashed tampering fails.
    """
    run = check_path(run)
    if not isinstance(plan, dict):
        plan = load_json(plan)
    original_receipt = load_json(run / 'run-receipt.json')
    validate('run-status', original_receipt)
    if metadata is None:
        metadata = load_json(run / 'evidence/capture-manifest.json')['metadata']
    if limits is None:
        limits = original_receipt['limits']
    rebuilt_index = indexing.build(Path(capture), metadata=metadata, limits=limits)
    files, result, grounding = materialize(rebuilt_index, plan, limits)
    for name in CANONICAL_PATHS:
        if safe_read(run / name, limits_for(limits)['output_bytes']) != files[name]:
            raise Failure('canonical_reexecution_mismatch:' + name, 'verification_failure')
    # The fixed accepted set is independent of the candidate receipt's paths.
    for subdir in ('bundle', 'evidence'):
        actual = set()
        for item in (run / subdir).rglob('*'):
            check_path(item)
            if item.is_dir():
                continue
            if not item.is_file():
                raise Failure('nonregular_accepted_artifact', 'verification_failure')
            actual.add(item.relative_to(run).as_posix())
        expected = {p for p in CANONICAL_PATHS if p.startswith(subdir + '/')}
        if actual != expected:
            raise Failure('accepted_artifact_inventory_mismatch', 'verification_failure')
    if original_receipt != result:
        raise Failure('run_receipt_reexecution_mismatch', 'verification_failure')
    checked = ahif.validate_bundle(run / 'bundle', require_canonical=True)
    if load_json(run / 'verification/ahif-check.json') != checked or load_json(run / 'verification/extraction-check.json') != grounding:
        raise Failure('verification_receipt_mismatch', 'verification_failure')
    return {'status': 'passed', 'verification': 'full_capture_plan_reexecution',
            'canonical_sha256': result['canonical_sha256'], 'canonical_files_compared': len(files),
            'record_observations': result['record_observations'],
            'source_map_characters': grounding['mapped_characters'], 'model_calls': 0,
            'metadata_basis': 'supplied_or_stored_capture_declarations', 'authenticity': 'not_established'}


def review(run, destination, limits=None):
    from .review import review as render
    return render(run, destination, limits=limits)
