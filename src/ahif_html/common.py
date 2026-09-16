"""Bounded I/O and pinned restricted JSON primitives."""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
from jsonschema import Draft202012Validator

PACKAGE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('ahif_html_pinned_checker',PACKAGE/'vendor/ahif_011/reference/validate_bundle.py')
ahif=importlib.util.module_from_spec(spec)
spec.loader.exec_module(ahif)
C=ahif.canonical
sha=lambda data:hashlib.sha256(data).hexdigest()

def bound(domain,value):return 'sha256:'+sha(('AHIF-HTML:'+domain+':1.0.0\n').encode()+C(value))

class Failure(ValueError):
    def __init__(self,code,status='invalid_input'):
        self.code=code;self.status=status;super().__init__(code)

DEFAULT_LIMITS={'input_bytes':8*1024*1024,'nodes':100000,'depth':256,'candidates':5000,
 'output_bytes':64*1024*1024,'tool_calls':64,'inspected_characters':120000,
 'tool_characters':12000,'selector_work':1000000,'structured_data_bytes':262144,
 'wall_seconds':60,'parts_per_record':128}
PROFILE={'id':'html-structural-text','version':'1.0.0','parser':'html5lib','parser_version':'1.1',
 'index_version':'1.0.0','text_policy':'parsed-codepoints-block-boundaries/1.0.0',
 'fidelity':'transformed','language':'und','visibility':'unknown','completeness':'unknown',
 'native_attributes':['data-post-id','data-comment-id','data-review-id'],
 'excluded_tags':['script','style','template','noscript','iframe','object','embed','input','textarea','select','button','form'],
 'hidden_policy':'HTML hidden and aria-hidden=true excluded with explicit reasons; CSS visibility not inferred',
 'limits':DEFAULT_LIMITS}
PROFILE_SHA=sha(C(PROFILE))
# Validation semantics are versioned separately from the unchanged parser/text
# profile. Old plans remain readable; repaired gates apply to every new execution.
GATE_CONTRACT={'id':'ahif-html-evidence-gates','version':'1.1.0',
 'protected_roles':'quote/code ancestry cannot become body/title through narrower selections',
 'textless_actions':'positive source-derived identity, relationship or registered state evidence required',
 'publication':'all accepted files counted before atomic publication'}
GATE_SHA=sha(C(GATE_CONTRACT))
DIAGNOSTIC_OUTPUT_BYTES=4096

def check_path(path):
    p=Path(path).absolute()
    if any(x.is_symlink() for x in (p,*p.parents)):raise Failure('symlink_path_refused')
    return p

def safe_read(path,limit=8*1024*1024):
    p=check_path(path)
    if not p.is_file():raise Failure('input_not_regular_file')
    if p.stat().st_size>limit:raise Failure('input_byte_limit','resource_limit')
    with p.open('rb') as stream:data=stream.read(limit+1)
    if len(data)>limit:raise Failure('input_byte_limit','resource_limit')
    return data

def load_json(path,limit=8*1024*1024):
    try:return ahif.strict_loads(safe_read(path,limit))
    except (ahif.Invalid,ValueError,UnicodeError,RecursionError) as exc:raise Failure('restricted_json_invalid') from exc

def write_json(path,value):Path(path).write_bytes(C(value)+b'\n')

def schema(name):return load_json(PACKAGE/'schemas'/f'{name}.schema.json')

def validate(name,value):
    try:
        ahif.check_values(value)
        Draft202012Validator(schema(name)).validate(value)
    except Exception as exc:
        if isinstance(exc,Failure):raise
        raise Failure(name+'_schema_invalid') from exc
    return value

def limits_for(overrides=None):
    value={**DEFAULT_LIMITS,**(overrides or {})}
    if set(value)!=set(DEFAULT_LIMITS) or any(type(v)!=int or v<1 or v>DEFAULT_LIMITS[k] for k,v in value.items()):
        raise Failure('resource_limits_invalid')
    return value

def directory_bytes(directory):
    return sum(p.stat().st_size for p in Path(directory).rglob('*') if p.is_file())

@contextmanager
def fresh(destination, *, output_limit=None):
    if output_limit is not None and (type(output_limit) is not int or output_limit<1):
        raise Failure('output_limit_invalid')
    dest=check_path(destination)
    if dest.exists() or dest==Path.cwd() or dest in Path.cwd().parents:raise Failure('output_must_be_fresh_dedicated_directory')
    dest.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temp=Path(tempfile.mkdtemp(prefix='.ahif-html-',dir=dest.parent))
    try:
        yield temp
        if output_limit is not None and directory_bytes(temp)>output_limit:
            raise Failure('output_total_byte_limit','resource_limit')
        if dest.exists():raise Failure('output_already_exists')
        temp.rename(dest)
    finally:
        if temp.exists():shutil.rmtree(temp)
