from pathlib import Path
import importlib.util
import json
import pytest
from ahif_html.common import Failure, load_json, sha, write_json
from ahif_html.evaluate import evaluate, validate_splits
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('discovery_v2_runner',ROOT/'scripts/run_discovery_v2.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


def config(tmp_path):
    cfg=load_json(ROOT/'examples/model-config.remote-tunnel.example.json')
    cfg['data_approval'].update(approved=True,capture_sha256=[sha((runner.CORPUS/(p+'.html')).read_bytes()) for p in runner.PAGES],declaration='Offline registration test only; no inference is invoked.')
    cfg['model']='offline-registration-test';cfg['endpoint']='http://127.0.0.1:14999'
    cfg['tunnel_declaration']['resource_id']='offline-test-no-resource'
    path=tmp_path/'config.json';write_json(path,cfg);return path


def test_construction_has_eight_pages_four_grouped_families_and_independent_gold(tmp_path):
    dataset=load_json(runner.CORPUS/'dataset.json');assert len(dataset['pages'])==8
    validate_splits(dataset);assert len({p['family'] for p in dataset['pages']})==4
    allgold=[g for p in dataset['pages'] for g in load_json(runner.CORPUS/p['gold'])['contributions']]
    assert len(allgold)==26
    assert sum(g['actor_id'] is not None for g in allgold)==20
    result=evaluate(runner.CORPUS/'dataset.json',runner.CORPUS/'evaluation-config.json',tmp_path/'manual')
    assert result['aggregate']['end_to_end_usable_recall']['numerator']==26
    assert result['aggregate']['ordered_parts_exact']['numerator']==26
    assert result['aggregate']['attribution']['wrong_account']==0
    assert all(x['grounding']['status']=='passed' for x in result['pages'])


def test_prepare_registers_equal_arms_and_fixed_repeats_without_provider(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'artifact_inventory',lambda:{'synthetic_test_snapshot':'fixed'})
    registration=runner.prepare(config(tmp_path),tmp_path/'trial')
    assert len(registration['jobs'])==18
    assert len([j for j in registration['jobs'] if not j['repeat']])==16
    assert {j['capture'] for j in registration['jobs'] if j['repeat']}=={'cards-a','table-a'}
    for page in runner.PAGES:
        cfgs=[load_json(tmp_path/'trial'/(page+'-'+arm+'.config.json')) for arm in ['planner','reviewer']]
        assert cfgs[0]['budgets']==cfgs[1]['budgets']
        assert cfgs[0]['reviewer'] is False and cfgs[1]['reviewer'] is True
    assert not (tmp_path/'trial/trial-started.json').exists()
    runner.verify_frozen(tmp_path/'trial',registration)


def test_frozen_configuration_and_captures_cannot_be_changed(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'artifact_inventory',lambda:{'synthetic_test_snapshot':'fixed'})
    registration=runner.prepare(config(tmp_path),tmp_path/'trial')
    path=tmp_path/'trial/cards-a-planner.config.json';path.write_text(path.read_text()+'\n')
    with pytest.raises(Failure,match='trial_frozen_configuration_changed'):runner.verify_frozen(tmp_path/'trial',registration)


def test_failures_keep_all_gold_in_both_arm_denominators_and_repeats_separate(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'artifact_inventory',lambda:{'synthetic_test_snapshot':'fixed'})
    registration=runner.prepare(config(tmp_path),tmp_path/'trial')
    entries=[{**job,'status':'not_run'} for job in registration['jobs']]
    result=runner.score(tmp_path/'trial',registration,entries)
    for arm in ['planner','reviewer']:
        metrics=result['same_inventory_by_arm'][arm]
        assert metrics['contribution_recall']['denominator']==26
        assert metrics['contribution_recall']['numerator']==0
        assert metrics['contribution_precision']['value'] is None
    assert len(entries)==18
    assert all(e['metrics']['contribution_recall']['denominator'] in (3,4) for e in entries)


def test_unknown_usage_is_not_zero_and_unstarted_jobs_are_zero():
    entries=[{'id':'a','status':'not_run'},{'id':'b','status':'processing_failure','receipt':None}, {'id':'c','status':'partial_execution','receipt':{'operation':{'calls':3}}}]
    assert runner.observed(entries,['calls'])=={'value':None,'known_lower_bound':3,'incomplete_jobs':['b']}


def test_fictional_export_is_allowlisted_verbatim_and_omits_operational_values(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'artifact_inventory',lambda:{'synthetic_test_snapshot':'fixed'})
    runner.prepare(config(tmp_path),tmp_path/'trial')
    discovery=tmp_path/'trial/cards-a-planner/discovery';discovery.mkdir(parents=True)
    write_json(discovery/'call-0001.json',{'request':{'messages':[{'content':'Fictional source evidence'}]},'response':{'action':'propose'}})
    write_json(discovery/'call-0002.json',{'operational':'offline-test-no-resource'})
    (tmp_path/'trial/cards-a-planner/attempts.jsonl').write_text('{"reason":"unknown_node_reference"}\n')
    exported=runner.export_safe(tmp_path/'trial',tmp_path/'safe')
    by_path={x['path']:x for x in exported['artifacts']}
    assert by_path['cards-a-planner/discovery/call-0001.json']['status']=='copied_verbatim'
    assert by_path['cards-a-planner/discovery/call-0002.json']['status']=='omitted'
    assert (tmp_path/'safe/cards-a-planner/attempts.jsonl').exists()
    assert not (tmp_path/'safe/cards-a-planner.config.json').exists()
    assert not (tmp_path/'safe/registration.json').exists()
    assert not (tmp_path/'safe/evaluator-only').exists()


def test_runner_orchestration_mocked_workers_preserves_all_eighteen_outcomes(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'artifact_inventory',lambda:{'synthetic_test_snapshot':'fixed'})
    registration=runner.prepare(config(tmp_path),tmp_path/'trial')
    calls=[]
    class FakeProcess:
        returncode=0
        pid=999999999
        def poll(self):return 0
    def fake_worker(command,**kwargs):
        compile(command[2],'<test-generated-worker>','exec')
        assert 'gold' not in str(command) and 'evaluator-only' not in str(command)
        assert '"output_bytes":8388608' in command[2]
        destination=Path(command[5]);destination.mkdir()
        write_json(destination/'discovery-receipt.json',{'status':'unresolved_plan','failure':'test_mock_worker_only','operation':{'calls':1,'actual_input_tokens':0,'actual_output_tokens':0,'tool_calls':0,'inspection':{'inspected_characters':0}}})
        calls.append(command);return FakeProcess()
    monkeypatch.setattr(runner.subprocess,'Popen',fake_worker)
    result=runner.run(tmp_path/'trial')
    assert len(calls)==18 and len(result['results'])==18
    assert result['observed_counts']['calls']['value']==18
    assert result['same_inventory_by_arm']['planner']['contribution_recall']['denominator']==26
    assert result['same_inventory_by_arm']['reviewer']['contribution_recall']['denominator']==26
    assert all(x['status']=='unresolved_plan' for x in result['results'])
    with pytest.raises(Failure,match='trial_cannot_restart'):runner.run(tmp_path/'trial')


def test_shared_wall_stop_does_not_shrink_arm_budget_or_drop_gold(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'artifact_inventory',lambda:{'synthetic_test_snapshot':'fixed'})
    runner.prepare(config(tmp_path),tmp_path/'trial',max_seconds=1)
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**kw:pytest.fail('no job should start with insufficient equal-arm budget'))
    result=runner.run(tmp_path/'trial')
    assert len(result['results'])==18
    assert all(x['status']=='not_run' for x in result['results'])
    assert result['observed_counts']['calls']['value']==0
    assert result['same_inventory_by_arm']['reviewer']['contribution_recall']['denominator']==26


def frozen_trial(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'artifact_inventory',lambda:{'synthetic_test_snapshot':'fixed'})
    runner.prepare(config(tmp_path),tmp_path/'trial')
    return tmp_path/'trial'


def test_launch_failure_is_zero_calls_and_all_gold_retained(tmp_path,monkeypatch):
    trial=frozen_trial(tmp_path,monkeypatch)
    def fail(*a,**kw):raise OSError('mock launch failure')
    monkeypatch.setattr(runner.subprocess,'Popen',fail)
    result=runner.run(trial)
    assert result['provider_call_budget_charge']==0
    assert result['observed_counts']['calls']['value']==0
    assert len(result['results'])==18
    assert result['results'][0]['status']=='processing_failure'
    assert all(x['status']=='not_run' for x in result['results'][1:])
    assert result['attribution_denominators_by_arm']['planner']['missed_known']==20
    assert result['attribution_denominators_by_arm']['planner']['missed_unknown']==6


def test_malformed_receipt_charges_started_worker_and_keeps_remaining_jobs(tmp_path,monkeypatch):
    trial=frozen_trial(tmp_path,monkeypatch)
    class Fake:
        returncode=0;pid=999999999
        def poll(self):return 0
    def fake(command,**kw):
        p=Path(command[5]);p.mkdir();(p/'discovery-receipt.json').write_text('{broken')
        return Fake()
    monkeypatch.setattr(runner.subprocess,'Popen',fake)
    result=runner.run(trial)
    assert result['provider_call_budget_charge']==12
    assert result['observed_counts']['calls']['value'] is None
    assert len(result['results'])==18
    assert result['results'][0]['receipt_error']['reason']=='worker_receipt_unavailable_or_invalid'


@pytest.mark.parametrize('failure',['timeout','oserror','scalar','malformed_records'])
def test_verification_and_corrupt_output_failures_never_lose_report(tmp_path,monkeypatch,failure):
    trial=frozen_trial(tmp_path,monkeypatch);count=[]
    class Fake:
        returncode=0;pid=999999999
        def poll(self):return 0
    def fake(command,**kw):
        p=Path(command[5]);p.mkdir();count.append(p)
        write_json(p/'discovery-receipt.json',{'status':'complete_execution','failure':None,'operation':{'calls':1}})
        if len(count)==1:
            bundle=p/'extraction/bundle';bundle.mkdir(parents=True)
            (bundle/'records.jsonl').write_text('{invalid JSON\n')
        return Fake()
    def verify(*a,**kw):
        if failure=='timeout':raise runner.subprocess.TimeoutExpired('mock verifier',70)
        if failure=='oserror':raise OSError('mock verifier unavailable')
        return runner.subprocess.CompletedProcess([],0,'[]' if failure=='scalar' else '{"status":"failed"}','')
    monkeypatch.setattr(runner.subprocess,'Popen',fake);monkeypatch.setattr(runner.subprocess,'run',verify)
    result=runner.run(trial)
    assert len(result['results'])==18 and result['status']=='failed_integrity'
    assert result['results'][0]['grounding']['status']=='failed'
    assert result['results'][0]['metrics']['contribution_recall']['denominator']==4
    assert result['results'][0]['metrics']['end_to_end_usable_recall']['numerator']==0
    assert result['same_inventory_by_arm']['planner']['contribution_recall']['denominator']==26


def test_registration_tamper_after_last_job_fails_freeze_and_retains_original_digest(tmp_path,monkeypatch):
    trial=frozen_trial(tmp_path,monkeypatch);initial=sha((trial/'registration.json').read_bytes());calls=[]
    class Fake:
        returncode=0;pid=999999999
        def poll(self):return 0
    def fake(command,**kw):
        p=Path(command[5]);p.mkdir();calls.append(p)
        write_json(p/'discovery-receipt.json',{'status':'unresolved_plan','failure':'mock','operation':{'calls':1}})
        if len(calls)==18:
            r=trial/'registration.json';r.write_text(r.read_text()+'\n')
            g=trial/'evaluator-only/cards-a.gold.json';j=load_json(g);j['contributions']=[];write_json(g,j)
        return Fake()
    monkeypatch.setattr(runner.subprocess,'Popen',fake)
    result=runner.run(trial)
    assert len(result['results'])==18 and result['status']=='failed_integrity'
    assert result['registration_sha256']==initial
    assert 'frozen_inputs_changed' in result['mechanical_integrity_failures']
    assert result['same_inventory_by_arm']['planner']['contribution_recall']['denominator']==26


def test_monitor_error_terminates_and_waits_owned_process(tmp_path,monkeypatch):
    trial=frozen_trial(tmp_path,monkeypatch);signals=[];waited=[]
    class Fake:
        returncode=None;pid=999999999;n=0
        def poll(self):
            self.n+=1
            if self.n==1:raise OSError('mock monitor error')
            return self.returncode
        def wait(self,timeout):self.returncode=-2;waited.append(True);return self.returncode
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**kw:Fake())
    monkeypatch.setattr(runner.os,'killpg',lambda pid,sig:signals.append((pid,sig)))
    result=runner.run(trial)
    assert signals and waited
    assert result['results'][0]['worker_error']['owned_process_cleanup']['status']=='terminated_and_waited'
    assert len(result['results'])==18 and result['provider_call_budget_charge']==12


def test_unmatched_assignment_is_counted_and_contamination_is_unassessed(tmp_path,monkeypatch):
    trial=frozen_trial(tmp_path,monkeypatch);registration=load_json(trial/'registration.json')
    job=registration['jobs'][0];bundle=trial/job['id']/'extraction/bundle';bundle.mkdir(parents=True)
    write_json(bundle/'records.jsonl',{'observation_id':'unmatched','extensions':{'org.ahif-html:extraction':{'container':'invented'}},'actor':{'id':'invented-author'},'record_key':{'id':'invented-key'},'content':{'parts':[{'role':'body','text':'Quoted material','attribution':{'relation':'record_actor'}}]}})
    entries=[{**j,'status':'not_run'} for j in registration['jobs']]
    result=runner.score(trial,registration,entries)
    assert entries[0]['unmatched_evidence']['assigned_actor']==1
    assert entries[0]['unmatched_evidence']['contamination_assessment']=='not_assessed_for_unmatched_emissions'
    assert result['unmatched_evidence_by_arm']['planner']['assigned_actor']==1
    assert result['attribution_denominators_by_arm']['planner']['known_reference']==20


def test_unconfirmed_owned_worker_termination_requests_cleanup_without_false_finished_claim(tmp_path,monkeypatch):
    trial=frozen_trial(tmp_path,monkeypatch)
    class Fake:
        returncode=None;pid=999999999
        def poll(self):raise OSError('mock monitoring failure')
    monkeypatch.setattr(runner.subprocess,'Popen',lambda *a,**kw:Fake())
    monkeypatch.setattr(runner,'terminate_owned',lambda process:{'status':'termination_unconfirmed','error_type':'OSError'})
    result=runner.run(trial);marker=load_json(trial/'inference-finished.json')
    assert result['stop_reason']=='owned_worker_cleanup_required'
    assert result['cleanup_required'] is True
    assert marker['no_more_provider_calls'] is False and marker['cleanup_required'] is True
    assert len(result['results'])==18
