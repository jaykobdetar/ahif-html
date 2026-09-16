"""Fresh fictional reconstruction of user-described findings, never original reviewer tests."""
import argparse, hashlib, json, platform, sys
from pathlib import Path
from datetime import datetime, timezone
import ahif_html
from ahif_html import plans, executor, common
from ahif_html.common import Failure, write_json, load_json

parser=argparse.ArgumentParser()
parser.add_argument('--out',required=True)
parser.add_argument('--tests',required=True)
parser.add_argument('--phase',required=True)
args=parser.parse_args()
sys.path.insert(0,args.tests)
from test_revision_semantic_gates import setup, element, text_node, part, contribution, plan_for, empty_case, META
out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
scenarios=[]
for case,tag,role,selection,relocated in [
    ('quote_child_element','blockquote','body','element',False),
    ('quote_child_text_title','blockquote','title','text',False),
    ('code_deep_child','code','body','element',False),
    ('pre_container_relocated','pre','body','element',True),
]:
    directory=out/case;directory.mkdir()
    inside='<span id="selected">Fictional quoted wording.</span>'
    inside='<section id="inner">'+inside+'</section>' if relocated else '<span><span>'+inside+'</span></span>'
    capture,evidence=setup(directory,'<article id="outer"><'+tag+'>'+inside+'</'+tag+'></article>')
    root=element(evidence,'inner' if relocated else 'outer')
    chosen=element(evidence,'selected')
    if selection=='text':chosen=text_node(evidence,chosen)
    scenarios.append((case,directory,capture,plan_for(evidence,[contribution(root,[part(chosen,role)])]),'ancestor_refusal'))
directory=out/'quote_known_actor';directory.mkdir()
capture,evidence=setup(directory,'<article id="outer"><header><span id="author">Fictional Delta</span></header><blockquote><span id="selected">Another persons wording.</span></blockquote></article>')
root,chosen,author=[element(evidence,name) for name in ('outer','selected','author')]
selected=contribution(root,[part(chosen)])
selected['parts'][0]['attribution']='record_actor'
selected['author']={'identity':None,'label':{'node':text_node(evidence,author),'kind':'text'},'evidence':[author]}
scenarios.append(('quote_known_actor',directory,capture,plan_for(evidence,[selected]),'ancestor_refusal'))
for case in ['unknown_relation','empty_native','blank_native','empty_uri','unfounded_state','state_marker']:
    directory=out/case;directory.mkdir()
    capture,evidence,plan=empty_case(directory,case)
    scenarios.append((case,directory,capture,plan,'textless_positive' if case=='state_marker' else 'no_evidence_omission'))
directory=out/'positive_body_quote_body';directory.mkdir()
capture,evidence=setup(directory,'<article id="outer"><div id="body"><p>Before.</p><blockquote id="quote"><span>Quoted.</span></blockquote><p>After.</p></div></article>')
body=part(element(evidence,'body'));body['exclude']=[element(evidence,'quote')]
quote=part(element(evidence,'quote'),'quote');quote['attribution']='other'
scenarios.append(('positive_body_quote_body',directory,capture,plan_for(evidence,[contribution(element(evidence,'outer'),[body,quote])]),'positive_parts'))
results=[]
for case,directory,capture,plan,expectation in scenarios:
    write_json(directory/'attempted-plan.json',plan)
    write_json(directory/'metadata.json',META)
    row={'case':case,'expectation':expectation,'capture_sha256':hashlib.sha256(capture.read_bytes()).hexdigest(),
         'capture_text':capture.read_text(),'attempted_plan_sha256':hashlib.sha256((directory/'attempted-plan.json').read_bytes()).hexdigest()}
    try:
        result=executor.extract(capture,directory/'attempted-plan.json',directory/'run',META)
        replay=executor.verify(capture,directory/'attempted-plan.json',directory/'run',META)
        records=[json.loads(line) for line in (directory/'run/bundle/records.jsonl').read_text().splitlines()]
        decisions=[json.loads(line) for line in (directory/'run/evidence/decisions.jsonl').read_text().splitlines()]
        row.update(execution={'status':'returned','result':result},replay=replay,
                   ahif=load_json(directory/'run/verification/ahif-check.json'),
                   source_map=load_json(directory/'run/verification/extraction-check.json'),
                   records=records,decisions=decisions)
        row['reconstructed_invariant_passed']=(expectation=='no_evidence_omission' and len(records)==0 and decisions[0]['reasons']==['no_actual_contribution_evidence'] or
            expectation=='textless_positive' and len(records)==1 and records[0]['content']['parts']==[] or
            expectation=='positive_parts' and [(p['role'],p['text']) for p in records[0]['content']['parts']]==[('body','Before.'),('quote','Quoted.'),('body','After.')])
    except Failure as exc:
        row.update(execution={'status':'refused','reason':exc.code,'run_status':exc.status},replay={'status':'not_run','reason':'no_accepted_extraction'},
                   ahif={'status':'not_run','reason':'no_accepted_bundle'},source_map={'status':'not_run','reason':'no_accepted_extraction'})
        row['reconstructed_invariant_passed']=expectation=='ancestor_refusal' and exc.code=='structural_quote_or_code_ancestor_forbids_body_title'
    write_json(directory/'probe-receipt.json',row)
    results.append({'case':case,'expectation':expectation,'execution_status':row['execution']['status'],
                    'reason':row['execution'].get('reason'),'record_observations':row['execution'].get('result',{}).get('record_observations'),
                    'reconstructed_invariant_passed':row['reconstructed_invariant_passed']})
summary={'designation':'reconstructed-user-findings-fictional-probes-v2','phase':args.phase,
         'annotation_provenance':'implementation-agent construction truth; original reviewer files unavailable',
         'time_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'software_version':ahif_html.__version__,
         'implementation':[{'module':m.__name__,'path':m.__file__,'sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()} for m in (common,plans,executor)],
         'model_calls':0,'cases':results}
write_json(out/'summary.json',summary)
print(json.dumps(summary,indent=2))
