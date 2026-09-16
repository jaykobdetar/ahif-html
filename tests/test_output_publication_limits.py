"""Reconstructed HTML-REV-003 checks; original reviewer files were unavailable."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/fictional/forum.html'


def inspect(tmp_path, name, cap=None):
    out = tmp_path / name
    command = [sys.executable, '-m', 'ahif_html', 'inspect', '--capture', str(FIXTURE), '--out', str(out)]
    if cap is not None:
        limits = tmp_path / (name + '-limits.json')
        limits.write_text(json.dumps({'output_bytes': cap}))
        command += ['--limits', str(limits)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    return result, out, json.loads(result.stdout)


def size(directory):
    return sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())


def test_inspect_honors_100_byte_accepted_output_limit(tmp_path):
    process, out, receipt = inspect(tmp_path, 'small', 100)
    assert process.returncode == 2
    assert receipt['status'] == 'resource_limit'
    assert receipt['reason'] == 'output_total_byte_limit'
    assert not (out / 'index.json').exists()
    assert sorted(p.name for p in out.iterdir()) == ['failed-attempt.json']
    assert size(out) <= 4096  # Separately declared diagnostic ceiling, not accepted output.


def test_inspect_positive_and_exact_output_boundary(tmp_path):
    process, out, receipt = inspect(tmp_path, 'normal')
    assert process.returncode == 0
    assert receipt['status'] == 'complete_execution'
    exact = size(out)
    assert exact > 100
    process2, out2, receipt2 = inspect(tmp_path, 'exact', exact)
    assert process2.returncode == 0 and receipt2['status'] == 'complete_execution'
    assert size(out2) == exact
    assert {p.name: p.read_bytes() for p in out.iterdir()} == {p.name: p.read_bytes() for p in out2.iterdir()}


def test_inspect_one_byte_over_limit_has_only_bounded_failure(tmp_path):
    process, normal, _ = inspect(tmp_path, 'measure')
    assert process.returncode == 0
    exact = size(normal)
    process2, limited, receipt = inspect(tmp_path, 'below', exact - 1)
    assert process2.returncode == 2 and receipt['status'] == 'resource_limit'
    assert not (limited / 'index.json').exists()
    assert size(limited) <= 4096


def test_atomic_publisher_counts_all_files_at_exact_boundary(tmp_path):
    from ahif_html.common import Failure, fresh
    with fresh(tmp_path / 'exact', output_limit=7) as stage:
        (stage / 'one').write_bytes(b'abc')
        (stage / 'nested').mkdir()
        (stage / 'nested/two').write_bytes(b'defg')
    assert size(tmp_path / 'exact') == 7
    with pytest.raises(Failure, match='output_total_byte_limit'):
        with fresh(tmp_path / 'over', output_limit=6) as stage:
            (stage / 'one').write_bytes(b'abc')
            (stage / 'nested').mkdir()
            (stage / 'nested/two').write_bytes(b'defg')
    assert not (tmp_path / 'over').exists()


def test_separate_review_counts_html_template_and_receipt(tmp_path):
    from ahif_html.common import load_json
    from ahif_html.executor import extract
    fixture = ROOT / 'examples/fictional'
    extract(fixture/'forum.html', fixture/'forum.plan.json', tmp_path/'run', load_json(fixture/'forum.metadata.json'))
    def render(name, cap=None):
        command=[sys.executable,'-m','ahif_html','review','--run',str(tmp_path/'run'),'--out',str(tmp_path/name)]
        if cap:
            limit=tmp_path/(name+'.json');limit.write_text(json.dumps({'output_bytes':cap}));command+=['--limits',str(limit)]
        return subprocess.run(command,capture_output=True,text=True,timeout=15)
    assert render('normal').returncode==0
    exact=size(tmp_path/'normal')
    assert render('exact',exact).returncode==0
    failure=render('small',exact-1)
    assert failure.returncode==2
    assert json.loads(failure.stdout)['reason']=='output_total_byte_limit'
    assert not (tmp_path/'small/index.html').exists()


def test_correction_outer_limit_counts_its_own_sidecars(tmp_path):
    from ahif_html.common import Failure,load_json
    from ahif_html.executor import extract
    from ahif_html.plans import plan_id
    from ahif_html.recipes import correct
    fixture=ROOT/'examples/fictional'
    capture=fixture/'forum.html';plan=load_json(fixture/'forum.plan.json');metadata=load_json(fixture/'forum.metadata.json')
    correction={'correction_version':'1.0.0','base_plan_id':plan_id(plan),'reviewer':{'kind':'agent','name':'fictional-limit-test'},'edits':[{'contribution':plan['contributions'][0]['container'],'field':'kind','value':'reply','reason':'ambiguous'}]}
    extract(capture,plan,tmp_path/'base',metadata)
    correct(capture,tmp_path/'base',correction,tmp_path/'measure')
    cap=size(tmp_path/'measure/run')+20
    assert size(tmp_path/'measure')>cap
    extract(capture,plan,tmp_path/'bounded-base',metadata,{'output_bytes':cap})
    with pytest.raises(Failure,match='output_total_byte_limit'):
        correct(capture,tmp_path/'bounded-base',correction,tmp_path/'bounded-correction',limits={'output_bytes':cap})
    assert not (tmp_path/'bounded-correction').exists()


def test_evaluation_outer_budget_includes_registration_and_reports(tmp_path):
    fixture=ROOT/'examples/fictional'
    config=json.loads((fixture/'evaluation-config.json').read_text())
    config['budgets']['max_total_output_bytes']=100
    path=tmp_path/'config.json';path.write_text(json.dumps(config));out=tmp_path/'evaluation'
    process=subprocess.run([sys.executable,'-m','ahif_html','evaluate','--dataset',str(fixture/'dataset.json'),'--config',str(path),'--out',str(out)],capture_output=True,text=True,timeout=15)
    assert process.returncode==2
    assert json.loads(process.stdout)['status']=='resource_limit'
    assert not (out/'evaluation.json').exists()
    assert size(out)<=4096
