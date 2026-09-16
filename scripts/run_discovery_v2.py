#!/usr/bin/env python3
"""Register then execute an eight-page, paired-arm synthetic discovery evaluation.

No provisioning occurs here. `prepare` freezes inputs without a provider call;
`run` checks that freeze before each job. Gold/manual plans are evaluator-only.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from ahif_html.common import Failure, check_path, load_json, safe_read, sha, write_json
from ahif_html.provider import validate_config
from ahif_html.evaluate import score_records, _load_records, _aggregate, validate_splits

ROOT=Path(__file__).resolve().parents[1]
CORPUS=ROOT/'examples/discovery-v2'
PAGES=tuple(f'{family}-{variant}' for family in ['cards','feed','table','catalog'] for variant in ['a','b'])
JOBS=tuple({'id':f'{page}-{arm}','capture':page,'arm':arm,'repeat':False} for page in PAGES for arm in ['planner','reviewer'])+(
    {'id':'cards-a-repeat','capture':'cards-a','arm':'planner','repeat':True},
    {'id':'table-a-repeat','capture':'table-a','arm':'planner','repeat':True},)


def artifact_inventory():
    files=[p for p in (ROOT/'src/ahif_html').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.txt','.md') and '__pycache__' not in p.parts]
    files.extend([Path(__file__),ROOT/'uv.lock',ROOT/'pyproject.toml'])
    files.extend(p for p in CORPUS.glob('*') if p.is_file())
    return {p.relative_to(ROOT).as_posix():sha(safe_read(p)) for p in sorted(files)}


def prepare(config_path, destination, calls_per_job=12, seconds_per_job=300, max_seconds=2100):
    if not 1<=calls_per_job<=16 or not 1<=seconds_per_job<=300 or not 1<=max_seconds<=2100:
        raise Failure('trial_budget_invalid')
    config=validate_config(load_json(config_path))
    if config['mode']!='live' or not config['data_approval']['approved'] or config['data_approval']['data_classes']!=['synthetic']:
        raise Failure('trial_requires_live_synthetic_approval')
    dataset=load_json(CORPUS/'dataset.json');validate_splits(dataset)
    by_id={p['id']:p for p in dataset['pages']}
    if set(by_id)!=set(PAGES):raise Failure('trial_inventory_mismatch')
    destination=check_path(destination)
    if destination.exists():raise Failure('trial_destination_must_be_fresh')
    destination.mkdir(parents=True,mode=0o700)
    (destination/'captures').mkdir();(destination/'evaluator-only').mkdir(mode=0o700)
    inventory={};configs={}
    for name in PAGES:
        page=by_id[name];inventory[name]={**page,'files':{}}
        for key in ['capture','metadata','gold','plan']:
            source=CORPUS/page[key];raw=safe_read(source)
            if key=='capture' and sha(raw) not in config['data_approval']['capture_sha256']:raise Failure('trial_capture_not_preapproved')
            target=destination/('evaluator-only' if key in ['gold','plan'] else 'captures')/page[key]
            target.write_bytes(raw);inventory[name]['files'][key]={'path':target.relative_to(destination).as_posix(),'sha256':sha(raw)}
    for job in JOBS:
        cfg=json.loads(json.dumps(config));cfg['reviewer']=job['arm']=='reviewer'
        cfg['data_approval']['capture_sha256']=[inventory[job['capture']]['files']['capture']['sha256']]
        cfg['budgets'].update(max_calls=calls_per_job,max_wall_seconds=seconds_per_job,max_retries=0,max_repairs=2,
                             max_input_tokens_total=calls_per_job*cfg['num_ctx'],max_output_tokens_total=calls_per_job*cfg['budgets']['max_output_tokens_per_call'])
        validate_config(cfg);path=destination/(job['id']+'.config.json');write_json(path,cfg);configs[job['id']]=sha(safe_read(path))
    registration={'version':'2.0.0','designation':'discovery-v2-paired-construction-1','mode':'live','model':config['model'],
      'provider_location':config['provider_location'],'tunnel_declaration':config['tunnel_declaration'],
      'annotation_provenance':'agent_authored_construction_truth','human_reviewed':False,'real_capture_pilot':'not_run',
      'capture_inventory':inventory,'jobs':[{**j,'family':by_id[j['capture']]['family'],'split':by_id[j['capture']]['split']} for j in JOBS],
      'per_arm_budget':{'max_calls':calls_per_job,'max_seconds':seconds_per_job,'max_output_tokens_per_call':config['budgets']['max_output_tokens_per_call'],'num_ctx':config['num_ctx'],'max_tool_calls':config['budgets']['max_tool_calls'],'max_inspected_characters':config['budgets']['max_inspected_characters'],'max_extraction_output_bytes':8388608},
      'shared_budget':{'max_calls':len(JOBS)*calls_per_job,'max_seconds':max_seconds,'max_tool_calls':len(JOBS)*config['budgets']['max_tool_calls'],'max_inspected_characters':len(JOBS)*config['budgets']['max_inspected_characters'],'max_reserved_input_tokens':len(JOBS)*calls_per_job*config['num_ctx'],'max_reserved_output_tokens':len(JOBS)*calls_per_job*config['budgets']['max_output_tokens_per_call'],'max_trial_output_bytes':134217728},
      'implementation_and_input_sha256':artifact_inventory(),'configuration_sha256':configs,
      'matching_policy':load_json(CORPUS/'matching-policy.json'),
      'limitations':['All missed and failed-job contributions stay in each arm denominator. Repeats are reported separately.','Related pages remain within one family/thread/lineage split. Reserved table/catalog families are constructed synthetic evaluation cases, not independent human-reviewed real holdouts.','No fixture names, gold, expected IDs or manual plans are passed to the provider.','Provider billing is unknown unless reconciled separately; infrastructure teardown is controlled outside this runner.']}
    write_json(destination/'registration.json',registration)
    return registration


def verify_frozen(destination,registration):
    if artifact_inventory()!=registration['implementation_and_input_sha256']:raise Failure('trial_frozen_implementation_changed')
    for job,expected in registration['configuration_sha256'].items():
        if sha(safe_read(destination/(job+'.config.json')))!=expected:raise Failure('trial_frozen_configuration_changed')
    for page in registration['capture_inventory'].values():
        for item in page['files'].values():
            if sha(safe_read(destination/item['path']))!=item['sha256']:raise Failure('trial_frozen_capture_changed')


def observed(entries,field):
    known=0;missing=[]
    for entry in entries:
        if entry['status']=='not_run' or entry.get('worker_started') is False:continue
        receipt=entry.get('receipt')
        if receipt is None:missing.append(entry['id']);continue
        op=receipt.get('operation')
        if op is None:continue
        value=op
        for component in field:value=value.get(component) if isinstance(value,dict) else None
        if type(value) is int:known+=value
        else:missing.append(entry['id'])
    return {'value':None if missing else known,'known_lower_bound':known,'incomplete_jobs':missing}


def score(destination,registration,entries,gold_override=None):
    # Gold is used only after every model worker has finished. Matching is unchanged
    # from registration; convenient text overlap cannot silently rescue a wrong ref.
    for entry in entries:
        page=registration['capture_inventory'][entry['capture']]
        records_path=destination/entry['id']/'extraction/bundle/records.jsonl'
        try:
            if entry.get('grounding',{}).get('status')=='failed':raise Failure('invalid_output_excluded_after_verification_failure')
            records=_load_records(records_path) if records_path.exists() else []
        except (Failure,OSError,ValueError,TypeError):
            records=[];entry['scoring_error']={'reason':'invalid_output_excluded','reference_denominator_retained':True}
        gold=gold_override[entry['capture']] if gold_override is not None else load_json(destination/page['files']['gold']['path'])
        try:entry['metrics']=score_records(gold,records)
        except (Failure,AttributeError,KeyError,TypeError,ValueError):
            records=[];entry['scoring_error']={'reason':'invalid_record_shape_excluded','reference_denominator_retained':True};entry['metrics']=score_records(gold,[])
        outcomes={x['container']:x for x in entry['metrics']['reference_outcomes']}
        known=[g for g in gold['contributions'] if g['actor_id'] is not None];unknown=[g for g in gold['contributions'] if g['actor_id'] is None]
        seen=set();expected=set(outcomes);unmatched=[]
        for record in records:
            container=record.get('extensions',{}).get('org.ahif-html:extraction',{}).get('container')
            if container in expected and container not in seen:seen.add(container)
            else:unmatched.append(record)
        entry['attribution_denominators']={'known_reference':len(known),'unknown_reference':len(unknown),'missed_known':sum(not outcomes[g['container']]['matched'] for g in known),'missed_unknown':sum(not outcomes[g['container']]['matched'] for g in unknown),'usable_known':sum(outcomes[g['container']]['correct_attribution'] and outcomes[g['container']]['exact_ordered_parts'] for g in known),'usable_unknown':sum(outcomes[g['container']]['correct_attribution'] and outcomes[g['container']]['exact_ordered_parts'] for g in unknown)}
        entry['unmatched_evidence']={'observations':len(unmatched),'assigned_actor':sum(r.get('actor') is not None for r in unmatched),'unknown_actor':sum(r.get('actor') is None for r in unmatched),'contamination_assessment':'not_assessed_for_unmatched_emissions'}
        entry['metric_scope']={'attribution_correctness':'exact-container matched records; missed known/unknown and unmatched assignments separately counted','contamination':'gold forbidden fragments in matched records only; unmatched emissions require review'}
    by_arm={arm:_aggregate([e for e in entries if e['arm']==arm and not e['repeat']]) for arm in ['planner','reviewer']}
    by_family={family:{arm:_aggregate([e for e in entries if e['family']==family and e['arm']==arm and not e['repeat']]) for arm in ['planner','reviewer']} for family in sorted({e['family'] for e in entries})}
    return {'scoring_failures':[e['id'] for e in entries if e.get('scoring_error')],'same_inventory_by_arm':by_arm,'per_family_by_arm':by_family,'attribution_denominators_by_arm':{arm:{key:sum(e['attribution_denominators'][key] for e in entries if e['arm']==arm and not e['repeat']) for key in ['known_reference','unknown_reference','missed_known','missed_unknown','usable_known','usable_unknown']} for arm in ['planner','reviewer']},'unmatched_evidence_by_arm':{arm:{key:sum(e['unmatched_evidence'][key] for e in entries if e['arm']==arm and not e['repeat']) for key in ['observations','assigned_actor','unknown_actor']} for arm in ['planner','reviewer']},
            'held_out_by_arm':{arm:_aggregate([e for e in entries if e['split']=='held_out' and e['arm']==arm and not e['repeat']]) for arm in ['planner','reviewer']}}


@contextmanager
def cancellation_window():
    requested=[]
    old={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    def cancel(signum,_frame):requested.append(signum)
    for sig in old:signal.signal(sig,cancel)
    try:yield requested
    finally:
        for sig,handler in old.items():signal.signal(sig,handler)



def terminate_owned(process):
    result={'status':'already_exited'}
    if process.poll() is not None:return result
    try:
        try:os.killpg(process.pid,signal.SIGINT)
        except ProcessLookupError:pass
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait(timeout=5)
        return {'status':'terminated_and_waited','exit_code':process.returncode}
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {'status':'termination_unconfirmed','error_type':type(exc).__name__}


def run(destination):
    destination=check_path(destination);registration=load_json(destination/'registration.json');registration_sha=sha(safe_read(destination/'registration.json'))
    if (destination/'trial-started.json').exists():raise Failure('trial_cannot_restart')
    verify_frozen(destination,registration)
    # Retain the registered gold in the parent only so later filesystem tampering
    # cannot silently change the denominator. No worker receives this mapping.
    frozen_gold={name:load_json(destination/page['files']['gold']['path']) for name,page in registration['capture_inventory'].items()}
    write_json(destination/'trial-started.json',{'version':'2.0.0','registration_sha256':registration_sha,'mode':'live'})
    started=time.monotonic();entries=[];charged=0;stop_reason=None;budget=registration['shared_budget'];cap=registration['per_arm_budget']['max_calls']
    with cancellation_window() as cancellation:
      for job in registration['jobs']:
        if cancellation:stop_reason=stop_reason or 'host_cancelled'
        remaining=budget['max_seconds']-(time.monotonic()-started)
        if remaining<registration['per_arm_budget']['max_seconds']:stop_reason=stop_reason or 'shared_wall_budget_insufficient_for_equal_arm'
        if charged+cap>budget['max_calls']:stop_reason=stop_reason or 'shared_call_budget_exhausted'
        if sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())+registration['per_arm_budget']['max_extraction_output_bytes']+3*1048576>budget['max_trial_output_bytes']:stop_reason=stop_reason or 'shared_output_reservation_limit'
        if not stop_reason:
            try:verify_frozen(destination,registration)
            except (Failure,OSError,ValueError):stop_reason='trial_frozen_inputs_changed'
        if stop_reason:
            entries.append({**job,'status':'not_run','reason':stop_reason,'worker_started':False,'provider_call_budget_charge':0});continue
        page=registration['capture_inventory'][job['capture']];run_path=destination/job['id']
        code='import json,sys\nfrom ahif_html.common import load_json\nfrom ahif_html.planner import discover\nresult=discover(sys.argv[1],load_json(sys.argv[2]),sys.argv[3],load_json(sys.argv[4]),limits={"output_bytes":8388608})\nprint(json.dumps({k:result.get(k) for k in ("status","failure")},sort_keys=True))\n'
        command=[sys.executable,'-c',code,str(destination/page['files']['capture']['path']),str(destination/(job['id']+'.config.json')),str(run_path),str(destination/page['files']['metadata']['path'])]
        began=time.monotonic();termination=None;peak_rss_kib=None;process=None;worker_error=None;owned_cleanup=None
        try:
          with (destination/(job['id']+'.process.log')).open('w') as log:
            process=subprocess.Popen(command,cwd=destination/'captures',stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            while process.poll() is None:
                try:
                    rss=next(int(line.split()[1]) for line in Path(f'/proc/{process.pid}/status').read_text().splitlines() if line.startswith('VmHWM:'))
                    peak_rss_kib=max(peak_rss_kib or 0,rss)
                except (OSError,StopIteration):pass
                if time.monotonic()-began>registration['per_arm_budget']['max_seconds']+5:termination='host_job_wall_limit'
                if time.monotonic()-started>budget['max_seconds']:termination='host_shared_wall_limit'
                if cancellation:termination='host_cancelled'
                if termination:
                    owned_cleanup=terminate_owned(process)
                    break
                time.sleep(.2)
        except OSError as exc:
            worker_error={'reason':'worker_launch_or_monitor_error','error_type':type(exc).__name__}
            if process is not None:
                owned_cleanup=terminate_owned(process);worker_error['owned_process_cleanup']=owned_cleanup
        receipt=None;receipt_error=None;receipt_path=run_path/'discovery-receipt.json'
        if process is not None:
            try:
                receipt=load_json(receipt_path)
                if not isinstance(receipt,dict) or not isinstance(receipt.get('status'),str):raise ValueError('receipt_shape')
                op=receipt.get('operation')
                if op is not None and (not isinstance(op,dict) or type(op.get('calls')) is not int or not 0<=op['calls']<=cap):raise ValueError('receipt_call_count')
            except (Failure,OSError,ValueError) as exc:receipt=None;receipt_error={'reason':'worker_receipt_unavailable_or_invalid','error_type':type(exc).__name__}
        charge=0 if process is None else cap if receipt is None else (receipt.get('operation') or {}).get('calls',0)
        charged+=charge
        if termination=='host_cancelled':stop_reason='host_cancelled'
        if owned_cleanup and owned_cleanup['status']=='termination_unconfirmed':stop_reason='owned_worker_cleanup_required'
        if worker_error:stop_reason=stop_reason or 'worker_launch_or_monitor_error'
        if receipt_error:stop_reason=stop_reason or 'worker_receipt_unavailable_or_invalid'
        if receipt and receipt.get('failure') in ['provider_http_error','provider_transport_error','provider_local_model_not_verified']:stop_reason='provider_infrastructure_unavailable'
        entry={**job,'status':receipt['status'] if receipt else 'processing_failure','receipt':receipt,'worker_started':process is not None,'worker_pid':process.pid if process else None,'owned_process_cleanup':owned_cleanup,'worker_error':worker_error,'receipt_error':receipt_error,'exit_code':process.returncode if process else None,'host_termination':termination,'elapsed_seconds':f'{time.monotonic()-began:.3f}','peak_worker_rss_kib':peak_rss_kib,'provider_call_budget_charge':charge};entries.append(entry)
        write_json(destination/'progress.json',{'completed_jobs':len(entries),'charged_calls':charged,'results':entries})
        print(json.dumps({'job':job['id'],'status':entry['status'],'failure':receipt and receipt.get('failure'),'charged_calls':charged}),flush=True)
    cleanup_required=any((e.get('owned_process_cleanup') or {}).get('status')=='termination_unconfirmed' for e in entries)
    write_json(destination/'inference-finished.json',{'version':'2.0.0','calls':observed(entries,['calls']),'charged_calls':charged,'jobs':len(entries),'elapsed_seconds':f'{time.monotonic()-started:.3f}','no_more_provider_calls':not cleanup_required,'cleanup_required':cleanup_required})
    print(json.dumps({'event':'inference_finished','charged_calls':charged,'no_more_provider_calls':not cleanup_required,'cleanup_required':cleanup_required}),flush=True)
    integrity_failures=[];freeze_checks=[]
    def final_freeze(phase):
        try:
            verify_frozen(destination,registration)
            if sha(safe_read(destination/'registration.json'))!=registration_sha:raise Failure('trial_registration_changed')
            freeze_checks.append({'phase':phase,'status':'passed'})
        except (Failure,OSError,ValueError) as exc:
            freeze_checks.append({'phase':phase,'status':'failed','error_type':type(exc).__name__})
            if 'frozen_inputs_changed' not in integrity_failures:integrity_failures.append('frozen_inputs_changed')
    final_freeze('after_inference')
    for entry in entries:
        accepted=destination/entry['id']/'extraction'
        if not (accepted/'bundle/records.jsonl').exists():
            entry['grounding']={'status':'not_run','reason':'no_accepted_bundle'};continue
        page=registration['capture_inventory'][entry['capture']]
        command=[sys.executable,'-m','ahif_html','verify','--capture',str(destination/page['files']['capture']['path']),'--metadata',str(destination/page['files']['metadata']['path']),'--plan',str(accepted/'evidence/finalized-plan.json'),'--run',str(accepted)]
        try:
            check=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=70)
            (destination/(entry['id']+'.verification.log')).write_text(check.stdout+check.stderr)
            try:result=json.loads(check.stdout)
            except json.JSONDecodeError:result={'status':'verification_failure','reason':'unparsed_verifier_response'}
            if not isinstance(result,dict):result={'status':'verification_failure','reason':'invalid_verifier_response_shape'}
            entry['grounding']={'status':'passed' if check.returncode==0 and result.get('status')=='passed' else 'failed','exit_code':check.returncode,'verification':result,'model_calls':0}
        except (OSError,subprocess.TimeoutExpired) as exc:
            entry['grounding']={'status':'failed','reason':'verifier_unavailable_or_timeout','error_type':type(exc).__name__,'model_calls':0}
        if entry['grounding']['status']!='passed':integrity_failures.append(entry['id'])
    repeat_comparisons=[]
    accepted_files=['bundle/manifest.json','bundle/records.jsonl','evidence/capture-manifest.json','evidence/decisions.jsonl','evidence/finalized-plan.json','evidence/index.json','evidence/interpretation.json','evidence/source-map.jsonl']
    for repeated in (e for e in entries if e['repeat']):
        initial=next(e for e in entries if e['capture']==repeated['capture'] and e['arm']=='planner' and not e['repeat'])
        comparison={'capture':repeated['capture'],'initial_job':initial['id'],'repeat_job':repeated['id'],'initial_status':initial['status'],'repeat_status':repeated['status']}
        if initial['grounding']['status']=='passed' and repeated['grounding']['status']=='passed':
            comparison['canonical_files']={name:{'initial_sha256':sha(safe_read(destination/initial['id']/'extraction'/name)),'repeat_sha256':sha(safe_read(destination/repeated['id']/'extraction'/name))} for name in accepted_files}
            comparison['byte_identical']=all(x['initial_sha256']==x['repeat_sha256'] for x in comparison['canonical_files'].values())
        else:comparison.update(byte_identical=None,reason='both_attempts_not_accepted_and_verified')
        repeat_comparisons.append(comparison)
    final_freeze('before_scoring')
    scores=score(destination,registration,entries,gold_override=frozen_gold)
    integrity_failures.extend(x for x in scores['scoring_failures'] if x not in integrity_failures)
    final_freeze('before_report')
    summary={'version':'2.0.0','registration_sha256':registration_sha,'mode':'live','status':'failed_integrity' if integrity_failures else 'completed_with_all_outcomes_recorded','mechanical_integrity_failures':integrity_failures,'cleanup_required':cleanup_required,'freeze_checks':freeze_checks,'repeat_comparisons':repeat_comparisons,'results':entries,**scores,'provider_call_budget_charge':charged,'within_call_limit':charged<=budget['max_calls'],'stop_reason':stop_reason,'elapsed_seconds':f'{time.monotonic()-started:.3f}','human_reviewed':False,'real_capture_pilot':'not_run','monetary_cost':None,'observed_counts':{label:observed(entries,path) for label,path in [('calls',['calls']),('tool_calls',['tool_calls']),('input_tokens',['actual_input_tokens']),('output_tokens',['actual_output_tokens']),('inspected_characters',['inspection','inspected_characters'])]}}
    write_json(destination/'trial-report.json',summary);return summary


def export_safe(destination,out):
    """Create a local allowlisted fictional evidence package; never publish it.

    Original operational files remain intact and every copied/refused item keeps
    its original hash. This is scoped export checking, not general secret redaction.
    """
    destination=check_path(destination);out=check_path(out)
    if out.exists():raise Failure('trial_export_destination_must_be_fresh')
    registration=load_json(destination/'registration.json')
    if registration['annotation_provenance']!='agent_authored_construction_truth':raise Failure('trial_export_scope_invalid')
    out.mkdir(parents=True,mode=0o700)
    forbidden=[str(ROOT).encode(),str(Path.home()).encode(),b'RUNPOD_API_KEY',b'Authorization: Bearer']
    tunnel=registration.get('tunnel_declaration') or {}
    if tunnel.get('resource_id'):forbidden.append(tunnel['resource_id'].encode())
    allowed=[]
    for page in registration['capture_inventory'].values():
        for key in ['capture','metadata']:allowed.append(destination/page['files'][key]['path'])
    for job in registration['jobs']:
        run=destination/job['id']
        for name in ['finalized-plan.json','tools.jsonl','attempts.jsonl','discovery/node-aliases.json',
                     'extraction/bundle/manifest.json','extraction/bundle/records.jsonl',
                     'extraction/evidence/index.json','extraction/evidence/finalized-plan.json',
                     'extraction/evidence/capture-manifest.json','extraction/evidence/source-map.jsonl',
                     'extraction/evidence/decisions.jsonl','extraction/evidence/interpretation.json']:
            path=run/name
            if path.is_file():allowed.append(path)
        allowed.extend(sorted((run/'discovery').glob('call-*.json')))
    rows=[]
    for path in allowed:
        raw=safe_read(path,134217728);relative=path.relative_to(destination)
        row={'path':relative.as_posix(),'original_sha256':sha(raw),'byte_length':len(raw)}
        if any(x in raw for x in forbidden):row.update(status='omitted',reason='operational_value_detected')
        else:
            target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            row.update(status='copied_verbatim',export_sha256=sha(raw))
        rows.append(row)
    manifest={'version':'1.0.0','scope':'local fictional evidence allowlist; no publication performed',
              'original_registration_sha256':sha(safe_read(destination/'registration.json')),
              'captures':{name:page['files']['capture']['sha256'] for name,page in registration['capture_inventory'].items()},
              'artifacts':rows,'omitted_classes':['provider configuration and authorization declarations','resource IDs and host keys','process logs and absolute machine paths','operational receipts outside this allowlist'],
              'limitations':['Known operational-value scanning is not a general secret detector. Source prompt-injection text remains inert evidence.','Gold and manual plans are separate construction annotations and were never sent to inference.','Original operational artifacts remain retained; this package is not an authenticated source claim.']}
    write_json(out/'export-manifest.json',manifest);return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--calls-per-job',type=int,default=12);p.add_argument('--seconds-per-job',type=int,default=300);p.add_argument('--max-seconds',type=int,default=2100)
    p=sub.add_parser('run');p.add_argument('--run',type=Path,required=True)
    p=sub.add_parser('check');p.add_argument('--run',type=Path,required=True)
    p=sub.add_parser('export');p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare':r=prepare(args.config,args.out,args.calls_per_job,args.seconds_per_job,args.max_seconds);print(json.dumps({'status':'registered_without_inference','jobs':len(r['jobs']),'shared_budget':r['shared_budget']}))
    elif args.command=='check':verify_frozen(args.run,load_json(args.run/'registration.json'));print('{"status":"freeze_matches"}')
    elif args.command=='export':r=export_safe(args.run,args.out);print(json.dumps({'status':'local_export_created','copied':sum(x['status']=='copied_verbatim' for x in r['artifacts']),'omitted':sum(x['status']=='omitted' for x in r['artifacts'])}))
    else:r=run(args.run);print(json.dumps({'status':r['status'],'calls':r['observed_counts']['calls'],'report':str(args.run/'trial-report.json')}))

if __name__=='__main__':main()
