"""Versioned structural recipes and source-selecting corrections."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from .common import Failure, PROFILE_SHA, bound, fresh, load_json, limits_for, validate, write_json
from .index import build, by_ref, descendants, select
from .plans import plan_id, validate_plan

def instantiate(index,recipe,limits=None):
    caps=limits_for(limits)
    validate('recipe',recipe)
    if recipe['profile_sha256']!=PROFILE_SHA:raise Failure('recipe_profile_mismatch','unresolved_plan')
    names=[b['name'] for b in recipe['bindings']]
    if len(set(names))!=len(names) or '$container' in names:raise Failure('recipe_duplicate_binding','unresolved_plan')
    if recipe['containers']['minimum']>recipe['containers']['maximum']:raise Failure('recipe_cardinality_invalid','unresolved_plan')
    if len(index['nodes'])>caps['selector_work']:raise Failure('recipe_selector_work_limit','resource_limit')
    root=index['nodes'][0]['ref'];containers=select(index,root,recipe['containers']['selector'])
    if not recipe['containers']['minimum']<=len(containers)<=recipe['containers']['maximum']:raise Failure('recipe_container_cardinality_mismatch','unresolved_plan')
    contributions=[];work=len(index['nodes'])
    for container in containers:
        bindings={'$container':container}
        for binding in recipe['bindings']:
            work+=len(descendants(index,container))
            if work>caps['selector_work']:raise Failure('recipe_selector_work_limit','resource_limit')
            matches=select(index,container,binding['selector'])
            if binding['kind']=='text':matches=[n['ref'] for r in matches for n in descendants(index,r) if n['kind']=='text' and not n['flags']]
            if len(matches)!=1:raise Failure('recipe_binding_cardinality_mismatch','unresolved_plan')
            bindings[binding['name']]=matches[0]
        def resolve(x):
            if isinstance(x,str) and x.startswith('$'):
                if x not in bindings:raise Failure('recipe_binding_missing','unresolved_plan')
                return bindings[x]
            if isinstance(x,list):return [resolve(v) for v in x]
            if isinstance(x,dict):return {k:resolve(v) for k,v in x.items()}
            return x
        contributions.append(resolve(recipe['contribution_template']))
    plan={'plan_version':'1.0.0','capture_sha256':index['capture']['sha256'],'index_id':index['index_id'],'profile':'html-structural-text/1.0.0','ancestry':[],
          'origin':{'kind':'recipe','producer':recipe['recipe_id']+':'+bound('recipe',recipe)},'review':{'status':'unreviewed','reviewer':None},'contributions':contributions,'rejected':[],'unresolved':[]}
    try:return validate_plan(index,plan)
    except Failure as exc:raise Failure('recipe_resolved_plan_mismatch:'+exc.code,'unresolved_plan') from exc

def apply_recipe(capture,recipe,destination,metadata=None,limits=None):
    from .executor import execute_index
    if not isinstance(recipe,dict):recipe=load_json(recipe)
    index=build(capture,metadata,limits);plan=instantiate(index,recipe,limits)
    return execute_index(index,plan,destination,limits)

def correct(capture,run,corrections,destination,metadata=None,limits=None):
    from .executor import execute_index, verify
    run=Path(run)
    if not isinstance(corrections,dict):corrections=load_json(corrections)
    validate('correction',corrections)
    original=load_json(run/'evidence/finalized-plan.json')
    if corrections['base_plan_id']!=plan_id(original):raise Failure('correction_base_plan_mismatch')
    if metadata is None:metadata=load_json(run/'evidence/capture-manifest.json')['metadata']
    verify(capture,original,run,metadata,limits)
    index=build(capture,metadata,limits);plan=deepcopy(original)
    for edit in corrections['edits']:
        matches=[c for c in plan['contributions'] if c['container']==edit['contribution']]
        if len(matches)!=1:raise Failure('correction_target_cardinality')
        matches[0][edit['field']]=deepcopy(edit['value'])
    plan['ancestry']=original['ancestry']+[plan_id(original)]
    plan['origin']={'kind':'correction','producer':bound('correction',corrections)}
    declaration=corrections['reviewer']
    plan['review']={'status':'human_reviewed' if declaration['kind']=='human' else 'agent_reviewed','reviewer':declaration['name']}
    validate_plan(index,plan)
    # Preserve operational correction declaration without changing accepted set.
    with fresh(destination,output_limit=limits_for(limits)['output_bytes']) as stage:
        result=execute_index(index,plan,stage/'run',limits)
        write_json(stage/'correction.json',corrections)
        write_json(stage/'correction-receipt.json',{'status':'applied','base_plan_id':plan_id(original),'new_plan_id':plan_id(plan),'review_declaration':'supplier_declaration_not_identity_verification'})
    return {**result,'run_subdirectory':'run'}
