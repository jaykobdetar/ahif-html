"""Explicit files, fresh destinations, machine-readable outcomes."""
from __future__ import annotations
import argparse
import sys
import time
from pathlib import Path
from .common import C, Failure, check_path, fresh, load_json, safe_read, sha, validate, write_json, limits_for, DIAGNOSTIC_OUTPUT_BYTES

def batch(manifest_path,destination):
    from .executor import extract
    from .evaluate import _deadline, _EvaluationDeadline
    manifest_path=Path(manifest_path);manifest=load_json(manifest_path);validate('batch',manifest)
    ids=[p['id'] for p in manifest['pages']]
    if len(set(ids))!=len(ids):raise Failure('batch_duplicate_id')
    root=manifest_path.absolute().parent
    def member(name):
        if not isinstance(name,str) or '\\' in name or Path(name).is_absolute() or '..' in Path(name).parts:raise Failure('batch_path_invalid')
        return check_path(root/name)
    inputs=[];total=0
    for p in manifest['pages']:
        capture=member(p['capture']);data=safe_read(capture);total+=len(data)
        inputs.append((p,capture,load_json(member(p['plan'])),load_json(member(p['metadata'])) if p['metadata'] else None))
    if total>manifest['max_total_input_bytes']:raise Failure('batch_input_limit','resource_limit')
    start=time.monotonic();results=[];output_bytes=0;deadline_exhausted=False
    reserve=1024+512*len(inputs)
    with fresh(destination) as stage:
        write_json(stage/'registration.json',{'manifest':manifest,'input_sha256':[sha(safe_read(c)) for _,c,_,_ in inputs]})
        output_bytes=(stage/'registration.json').stat().st_size
        if output_bytes+reserve>manifest['max_total_output_bytes']:raise Failure('batch_output_limit','resource_limit')
        for p,capture,plan,metadata in inputs:
            try:
                if deadline_exhausted or time.monotonic()-start>=manifest['max_wall_seconds'] or output_bytes>=manifest['max_total_output_bytes']:raise Failure('batch_budget_exhausted','resource_limit')
                remaining=manifest['max_total_output_bytes']-output_bytes-reserve
                if remaining<1:raise Failure('batch_output_limit','resource_limit')
                with _deadline(max(0.001,manifest['max_wall_seconds']-(time.monotonic()-start))):
                    result=extract(capture,plan,stage/p['id'],metadata,{'output_bytes':min(64*1024*1024,remaining)})
                output_bytes+=sum(x.stat().st_size for x in (stage/p['id']).rglob('*') if x.is_file())
            except Failure as exc:result={'status':exc.status,'reason':exc.code}
            except _EvaluationDeadline:
                deadline_exhausted=True
                result={'status':'resource_limit','reason':'batch_wall_limit'}
            results.append({'id':p['id'],**{k:v for k,v in result.items() if k in ('status','reason','canonical_sha256','record_observations')}})
        receipt={'status':'partial_execution' if any(p['status'] not in ('complete_execution','no_contributions_observed') for p in results) else 'complete_execution','pages':results,'input_bytes':total,'output_bytes':output_bytes,'coverage':'not_established'}
        for _ in range(5):
            write_json(stage/'batch-receipt.json',receipt)
            actual=sum(x.stat().st_size for x in stage.rglob('*') if x.is_file())
            if receipt['output_bytes']==actual:break
            receipt['output_bytes']=actual
        if actual>manifest['max_total_output_bytes']:raise Failure('batch_output_limit','resource_limit')
    return receipt

def parser():
    p=argparse.ArgumentParser(prog='ahif-html');sub=p.add_subparsers(dest='command',required=True)
    for name in ['inspect','discover','extract','verify','apply-recipe','correct']:
        q=sub.add_parser(name);q.add_argument('--capture',required=True,type=Path);q.add_argument('--metadata',type=Path);q.add_argument('--limits',type=Path)
        if name!='verify':q.add_argument('--out',required=True,type=Path)
        if name in ('extract','verify'):q.add_argument('--plan',required=True,type=Path)
        if name in ('verify','correct'):q.add_argument('--run',required=True,type=Path)
        if name=='discover':q.add_argument('--model-config',required=True,type=Path)
        if name=='apply-recipe':q.add_argument('--recipe',required=True,type=Path)
        if name=='correct':q.add_argument('--corrections',required=True,type=Path)
    q=sub.add_parser('review');q.add_argument('--run',required=True,type=Path);q.add_argument('--out',required=True,type=Path);q.add_argument('--limits',type=Path)
    q=sub.add_parser('evaluate');q.add_argument('--dataset',required=True,type=Path);q.add_argument('--config',required=True,type=Path);q.add_argument('--out',required=True,type=Path)
    q=sub.add_parser('batch');q.add_argument('--manifest',required=True,type=Path);q.add_argument('--out',required=True,type=Path)
    sub.add_parser('sandbox-check')
    return p

def main(argv=None):
    args=parser().parse_args(argv);isolation=None
    try:
        limits=load_json(args.limits) if getattr(args,'limits',None) else None
        caps=limits_for(limits)
        if args.command!='discover':
            from .isolation import deterministic_worker
            isolation=deterministic_worker(seconds=caps['wall_seconds'])
        metadata=load_json(args.metadata) if getattr(args,'metadata',None) else None
        if args.command=='inspect':
            from .index import build, Inspector
            value=build(args.capture,metadata,limits)
            with fresh(args.out,output_limit=caps['output_bytes']) as stage:
                write_json(stage/'index.json',value);write_json(stage/'inspection.json',Inspector(value,limits).audit())
                write_json(stage/'isolation.json',isolation)
            result={'status':'complete_execution','index_id':value['index_id'],'indexed_nodes':len(value['nodes']),'indicators':value['indicators'],'coverage':'not_established'}
        elif args.command=='extract':
            from .executor import extract
            result=extract(args.capture,args.plan,args.out,metadata,limits)
        elif args.command=='verify':
            from .executor import verify
            result=verify(args.capture,args.plan,args.run,metadata,limits)
        elif args.command=='review':
            from .review import review
            result=review(args.run,args.out,limits)
        elif args.command=='discover':
            from .planner import discover
            result=discover(args.capture,load_json(args.model_config),args.out,metadata,limits)
        elif args.command=='apply-recipe':
            from .recipes import apply_recipe
            result=apply_recipe(args.capture,args.recipe,args.out,metadata,limits)
        elif args.command=='correct':
            from .recipes import correct
            result=correct(args.capture,args.run,args.corrections,args.out,metadata,limits)
        elif args.command=='evaluate':
            from .evaluate import evaluate
            result=evaluate(args.dataset,args.config,args.out)
        elif args.command=='batch':result=batch(args.manifest,args.out)
        else:
            import socket,subprocess
            attempts={}
            for name,fn in [('socket',lambda:socket.socket()),('source_exec',lambda:subprocess.run(['/bin/true']))]:
                try:fn();attempts[name]='unexpectedly_allowed'
                except PermissionError:attempts[name]='denied_by_os'
            result={'status':'passed' if set(attempts.values())=={'denied_by_os'} else 'failed','attempts':attempts,'isolation':isolation}
        if isolation:result={**result,'worker_isolation':isolation}
        print(C(result).decode())
        return 0 if result.get('status') in ('passed','complete','complete_execution','partial_execution','no_contributions_observed','applied','generated') else 2
    except (Failure,MemoryError) as exc:
        result={'operation_receipt_version':'1.1.0','status':exc.status if isinstance(exc,Failure) else 'resource_limit','reason':exc.code if isinstance(exc,Failure) else 'worker_memory_limit','command':args.command,'isolation':isolation,'published_ahif':False,'diagnostic_output_limit':DIAGNOSTIC_OUTPUT_BYTES}
        dest=getattr(args,'out',None)
        if dest and not dest.exists():
            try:
                with fresh(dest,output_limit=DIAGNOSTIC_OUTPUT_BYTES) as stage:write_json(stage/'failed-attempt.json',result)
            except Failure:pass
        print(C(result).decode());return 2

if __name__=='__main__':sys.exit(main())
