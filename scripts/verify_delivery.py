#!/usr/bin/env python3
"""Run model-free delivery checks in fresh OS-isolated CLI processes.

Run with the project's .venv Python. No network/model access is required.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time
from ahif_html.common import C, PROFILE, PROFILE_SHA, fresh, load_json, sha, write_json
from ahif_html.index import build
from ahif_html.plans import plan_id
from ahif_html.recipes import instantiate

ROOT=Path(__file__).resolve().parents[1]

@contextmanager
def retained(destination):
    error=None
    with fresh(destination) as stage:
        try:yield stage
        except Exception as exc:
            write_json(stage/'failed-delivery.json',{'status':'failed','exception_type':type(exc).__name__,'reason':str(exc)[:4000]})
            error=exc
    if error:raise error

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    commands=[];start=time.monotonic()
    with retained(args.out) as out:
        def run(label,arguments,expected=0,env=None,cwd=ROOT):
            command=[sys.executable,*map(str,arguments)]
            began=time.monotonic()
            result=subprocess.run(command,cwd=cwd,env={**os.environ,**(env or {})},capture_output=True,text=True,timeout=90)
            (out/(label+'.stdout.txt')).write_text(result.stdout);(out/(label+'.stderr.txt')).write_text(result.stderr)
            row={'name':label,'command':command,'cwd':str(cwd),'exit_code':result.returncode,'expected_exit_code':expected,'passed':result.returncode==expected,'elapsed_seconds':f'{time.monotonic()-began:.6f}'}
            commands.append(row)
            if result.returncode!=expected:raise RuntimeError(label+' failed; '+result.stdout[-2000:]+result.stderr[-2000:])
            return result
        run('tests',['-m','pytest','-q'])
        run('sandbox',['-m','ahif_html','sandbox-check'])
        fixture=ROOT/'examples/fictional';recipes=ROOT/'examples/recipes';capture=fixture/'forum.html';metadata=fixture/'forum.metadata.json';plan=fixture/'forum.plan.json'
        run('inspect',['-m','ahif_html','inspect','--capture',capture,'--metadata',metadata,'--out',out/'inspect'])
        run('extract',['-m','ahif_html','extract','--capture',capture,'--metadata',metadata,'--plan',plan,'--out',out/'m1'])
        run('verify',['-m','ahif_html','verify','--capture',capture,'--plan',plan,'--run',out/'m1'])
        for page in ['thread-a','thread-b']:
            run('recipe-'+page,['-m','ahif_html','apply-recipe','--capture',recipes/(page+'.html'),'--metadata',recipes/'metadata.json','--recipe',recipes/'thread.recipe.json','--out',out/('recipe-'+page)])
        run('recipe-mismatch',['-m','ahif_html','apply-recipe','--capture',recipes/'mismatch.html','--metadata',recipes/'metadata.json','--recipe',recipes/'thread.recipe.json','--out',out/'recipe-mismatch'],2)
        base=load_json(out/'recipe-thread-a/evidence/finalized-plan.json')
        correction={'correction_version':'1.0.0','base_plan_id':plan_id(base),'reviewer':{'kind':'agent','name':'delivery-validation-agent'},'edits':[{'contribution':base['contributions'][0]['container'],'field':'author','value':None,'reason':'ambiguous'}]}
        # Demonstrate a conservative source-selection correction, not a human event.
        write_json(out/'correction.json',correction)
        run('correct',['-m','ahif_html','correct','--capture',recipes/'thread-a.html','--run',out/'recipe-thread-a','--corrections',out/'correction.json','--out',out/'corrected'])
        run('verify-correction',['-m','ahif_html','verify','--capture',recipes/'thread-a.html','--plan',out/'corrected/run/evidence/finalized-plan.json','--run',out/'corrected/run'])
        run('review',['-m','ahif_html','review','--run',out/'m1','--out',out/'review-copy'])
        run('evaluate',['-m','ahif_html','evaluate','--dataset',fixture/'dataset.json','--config',fixture/'evaluation-config.json','--out',out/'evaluation'])
        moved=out/'relocated';moved.mkdir();(moved/'capture.html').write_bytes(capture.read_bytes());os.utime(moved/'capture.html',(1,2))
        def reverse(x):
            if isinstance(x,dict):return {k:reverse(v) for k,v in reversed(list(x.items()))}
            if isinstance(x,list):return [reverse(v) for v in x]
            return x
        (moved/'plan.json').write_text(json.dumps(reverse(load_json(plan))))
        time.sleep(1.1)
        run('replay-relocated',['-m','ahif_html','extract','--capture',moved/'capture.html','--metadata',metadata,'--plan',moved/'plan.json','--out',out/'replay'],env={'PYTHONHASHSEED':'927','TZ':'Pacific/Honolulu'},cwd=moved)
        left=load_json(out/'m1/run-receipt.json');right=load_json(out/'replay/run-receipt.json')
        if left!=right:raise RuntimeError('canonical replay differs')
        write_json(out/'replay-check.json',{'status':'passed','canonical_sha256':left['canonical_sha256'],'model_calls':0,'changes':['fresh process','different cwd/capture path','capture mtime','wall clock elapsed','PYTHONHASHSEED','TZ','JSON object property order'],'canonical_files':left['canonical_files']})
        # A small batch demonstrates shared explicit input/output/wall budgets.
        batchdir=out/'batch-input';batchdir.mkdir()
        for name,source in [('capture.html',capture),('metadata.json',metadata),('plan.json',plan)]: (batchdir/name).write_bytes(source.read_bytes())
        write_json(batchdir/'batch.json',{'batch_version':'1.0.0','pages':[{'id':'page1','capture':'capture.html','metadata':'metadata.json','plan':'plan.json'}],'max_total_input_bytes':8388608,'max_total_output_bytes':8388608,'max_wall_seconds':30})
        run('batch',['-m','ahif_html','batch','--manifest',batchdir/'batch.json','--out',out/'batch'])
        files={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for scope in ['src','tests','examples','scripts'] for p in (ROOT/scope).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
        receipt={'delivery_receipt_version':'1.0.0','status':'passed','executed_at':datetime.now(timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform(),'dependencies':{name:importlib.metadata.version(name) for name in ['ahif-html','html5lib','jsonschema','referencing','pytest']},'uv_lock_sha256':sha((ROOT/'uv.lock').read_bytes()),'profile_sha256':PROFILE_SHA,'commands':commands,'source_and_fixture_sha256':files,'elapsed_seconds':f'{time.monotonic()-start:.6f}','children_peak_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'model_calls':0,'raw_real_captures_used':0,'human_annotations':False}
        write_json(out/'delivery-receipt.json',receipt)
    print(str(args.out.absolute()/'delivery-receipt.json'))

if __name__=='__main__':main()
