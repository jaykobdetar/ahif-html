"""Restricted plans select source evidence; they cannot supply source values."""
from __future__ import annotations
from .common import Failure, PROFILE, bound, validate
from .index import attrs, by_ref, descendants, read_value, text_segments

def plan_id(plan):return bound('plan',plan)

def validate_plan(index,plan):
    validate('plan',plan)
    if index.get('index_id')!=bound('index',{k:v for k,v in index.items() if k!='index_id'}):raise Failure('index_integrity_mismatch')
    if plan['capture_sha256']!=index['capture']['sha256'] or plan['index_id']!=index['index_id']:raise Failure('plan_capture_index_mismatch')
    lookup=by_ref(index)
    def exists(ref):
        if ref not in lookup:raise Failure('unknown_node_reference')
        return lookup[ref]
    def evidence(refs,scope):
        if not refs:raise Failure('semantic_evidence_required')
        for r in refs:
            if r not in scope:raise Failure('evidence_outside_container')
            if exists(r)['flags'] or exists(r)['kind']=='comment':raise Failure('unsupported_evidence_region')
    def value(v,scope):
        if v is None:return
        if v['node'] not in scope:raise Failure('field_outside_container')
        read_value(index,v)
    used=[];containers=set()
    for c in plan['contributions']:
        root=exists(c['container'])
        if root['kind']!='element' or root['flags']:raise Failure('contribution_container_invalid')
        if c['container'] in containers:raise Failure('duplicate_contribution_container')
        containers.add(c['container']); scope={n['ref'] for n in descendants(index,c['container'])}
        evidence(c['evidence'],scope)
        identity=c['identity']
        if identity:
            if 'start' in identity['source'] or 'end' in identity['source']:raise Failure('identity_slice_unsupported')
            value(identity['source'],scope);evidence(identity['evidence'],scope)
            if identity['kind']=='native':
                if identity['basis']!='documented_native' or identity['source'].get('attribute') not in PROFILE['native_attributes'] or not index['capture']['metadata']['source_url']:raise Failure('native_identity_unsupported')
            elif identity['basis']!='identity_link' or identity['source'].get('attribute')!='href':raise Failure('identity_uri_unsupported')
        if c['author']:
            a=c['author'];evidence(a['evidence'],scope);value(a['label'],scope)
            if a['identity']:
                if 'start' in a['identity']['source'] or 'end' in a['identity']['source']:raise Failure('identity_slice_unsupported')
                value(a['identity']['source'],scope)
                if a['identity']['kind']=='native':raise Failure('native_actor_identity_unsupported')
                if a['identity']['kind']=='uri' and (a['identity']['basis']!='identity_link' or a['identity']['source'].get('attribute')!='href'):raise Failure('actor_uri_unsupported')
                if a['identity']['kind']=='handle' and a['identity']['basis']!='source_label':raise Failure('actor_handle_basis_invalid')
        value(c['created'],scope);value(c['updated'],scope)
        excluded=set()
        for x in c['excluded']:
            if x['node'] not in scope or x['node']==c['container']:raise Failure('exclusion_outside_container')
            excluded.add(x['node'])
        for p in c['parts']:
            if p['root'] not in scope or exists(p['root'])['kind'] not in ('element','text'):raise Failure('part_outside_container')
            if exists(p['root'])['flags']:raise Failure('unsupported_part_region')
            evidence(p['evidence'],scope)
            globally_excluded={n['ref'] for x in excluded for n in descendants(index,x)}
            if p['root'] in globally_excluded:raise Failure('part_root_globally_excluded')
            part_scope={n['ref'] for n in descendants(index,p['root'])}
            for x in p['exclude']:
                if x not in part_scope or x==p['root']:raise Failure('part_exclusion_outside_root')
            if p['role'] in ('body','title'):
                blocked={n['ref'] for x in (set(p['exclude'])|excluded) for n in descendants(index,x)}
                boundaries={n['ref'] for n in descendants(index,p['root']) if n['tag'] in ('blockquote','pre','code')}
                if boundaries-blocked:raise Failure('structural_quote_or_code_boundary_required')
            if p['role'] in ('quote','signature','interface','link_preview') and p['attribution']=='record_actor':raise Failure('nonbody_actor_attribution_unsupported')
            for segment in text_segments(index,p['root'],list(excluded|set(p['exclude']))):
                for m in segment['mappings']:
                    if 'source' not in m:continue
                    s=m['source'];key=(s['node'],s['kind'],s.get('attribute'))
                    for prior,a,b in used:
                        if prior==key and max(a,s['start'])<min(b,s['end']):raise Failure('overlapping_source_selection')
                    used.append((key,s['start'],s['end']))
        for r in c['relations']:
            if r['target'] and ('start' in r['target'] or 'end' in r['target']):raise Failure('identity_slice_unsupported')
            value(r['target'],scope);evidence(r['evidence'],scope)
            if (r['target'] is None)!=(r['kind']=='unknown'):raise Failure('relation_target_kind_invalid')
            if r['kind']=='native' and not index['capture']['metadata']['source_url']:raise Failure('native_relation_namespace_missing')
        for link in c['links']:value(link['source'],scope)
        for state in ('state','completeness'):
            if c[state]:evidence(c[state]['evidence'],scope)
    # Every nested contribution must be a hard exclusion in each ancestor body.
    for c in plan['contributions']:
        for p in c['parts']:
            for other in containers-{c['container']}:
                if other in {n['ref'] for n in descendants(index,c['container'],False)} and p['root'] in {n['ref'] for n in descendants(index,other)}:raise Failure('nested_contribution_ownership_violation')
            subtree={n['ref'] for n in descendants(index,p['root'])}
            exclusions=set(p['exclude'])|{x['node'] for x in c['excluded']}
            covered={n['ref'] for x in exclusions for n in descendants(index,x)}
            if (containers-{c['container']})&subtree-covered:raise Failure('nested_contribution_not_excluded')
    for x in plan['rejected']+plan['unresolved']:exists(x['node'])
    return plan
