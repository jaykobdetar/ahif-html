"""Immutable, capture-bound HTML5 evidence index and bounded inspection."""
from __future__ import annotations
import codecs
import time
from pathlib import Path
from urllib.parse import urlsplit
import html5lib
from .common import C, PROFILE, Failure, bound, limits_for, safe_read, sha, validate, ahif

NATIVE = set(PROFILE['native_attributes'])
BLOCKS = set('address article aside blockquote div dl dt dd fieldset figcaption figure footer h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section table tr ul'.split())
SAFE_ATTRIBUTES = set('id class href datetime role aria-hidden aria-expanded hidden itemprop itemtype rel data-kind data-parent-id data-state data-truncated data-post-id data-comment-id data-review-id data-parent-post-id data-quote-post-id data-repost-post-id data-parent-comment-id data-parent-review-id'.split())
DEFAULT_METADATA = {'metadata_version':'1.0.0','capture_kind':'html_response','source_url':None,'captured_at':None,'provenance':None,'data_class':'unknown','access':'unknown','redistribution':{'status':'unknown','basis':'No supplier declaration supplied.'},'encoding':None,'decode_errors':'strict','screenshot':None}

def attrs(node): return {a['name']:a['value'] for a in node['attrs']}
def by_ref(index): return {n['ref']:n for n in index['nodes']}

def build(capture:Path, metadata=None, limits=None):
    caps=limits_for(limits); started=time.monotonic()
    raw=safe_read(capture,caps['input_bytes'])
    meta={**DEFAULT_METADATA,**(metadata or {})}
    validate('capture',meta)
    if meta['captured_at'] is not None:
        try:ahif.check_time(meta['captured_at'])
        except (ahif.Invalid,ValueError) as exc:raise Failure('capture_time_semantic_invalid') from exc
    if meta['capture_kind']=='rendered_dom' and not meta['provenance']:
        raise Failure('rendered_dom_provenance_required')
    encoding=meta['encoding']; evidence='supplier_encoding' if encoding else 'utf8_default'
    if raw.startswith(codecs.BOM_UTF8):
        if encoding and codecs.lookup(encoding).name!='utf-8':raise Failure('encoding_bom_conflict')
        encoding='utf-8-sig';evidence='utf8_bom'
    elif raw.startswith((codecs.BOM_UTF16_LE,codecs.BOM_UTF16_BE)):
        declared=codecs.lookup(encoding).name if encoding else None
        bom_encoding='utf-16-le' if raw.startswith(codecs.BOM_UTF16_LE) else 'utf-16-be'
        if declared and declared not in ('utf-16',bom_encoding):raise Failure('encoding_bom_conflict')
        encoding='utf-16';evidence='utf16_bom'
    else: encoding=encoding or 'utf-8'
    try: decoded=raw.decode(encoding,errors=meta['decode_errors'])
    except (UnicodeError,LookupError) as exc:raise Failure('capture_decode_failed') from exc
    # html5lib handles entities, CR/LF preprocessing, and malformed tree repair once.
    parser=html5lib.HTMLParser(tree=html5lib.getTreeBuilder('dom'),namespaceHTMLElements=False)
    doc=parser.parse(decoded,scripting=False)
    parser_info={'name':'html5lib','version':html5lib.__version__,'treebuilder':'dom','scripting':False,'index_version':'1.0.0'}
    capture_info={'sha256':sha(raw),'byte_length':len(raw),'metadata':meta,'decoding':{'encoding':encoding,'evidence':evidence,'errors':meta['decode_errors'],'replacement_characters':decoded.count('\ufffd'),'exact_character_recovery':meta['decode_errors']=='strict','parser_repairs':len(parser.errors),'raw_byte_spans':'unsupported'}}
    base=bound('node-scope',{'capture_sha256':sha(raw),'parser':parser_info})
    nodes=[]; indicators=[]; stack=[(doc,None,0,[])]; node_prefix=base+':'
    while stack:
        obj,parent,depth,inherited=stack.pop()
        if obj.nodeType not in (obj.DOCUMENT_NODE,obj.ELEMENT_NODE,obj.TEXT_NODE,obj.COMMENT_NODE):continue
        if len(nodes)>=caps['nodes']:raise Failure('indexed_node_limit','resource_limit')
        if depth>caps['depth']:raise Failure('indexed_depth_limit','resource_limit')
        if time.monotonic()-started>caps['wall_seconds']:raise Failure('index_wall_limit','resource_limit')
        kind={obj.DOCUMENT_NODE:'document',obj.ELEMENT_NODE:'element',obj.TEXT_NODE:'text',obj.COMMENT_NODE:'comment'}[obj.nodeType]
        tag=obj.tagName.lower() if kind=='element' else None
        attributes=sorted([{'name':a.name,'value':a.value} for a in obj.attributes.values()],key=lambda a:a['name']) if kind=='element' else []
        at={a['name']:a['value'] for a in attributes}; flags=list(inherited)
        if tag in PROFILE['excluded_tags'] and 'unsupported_subtree' not in flags:flags.append('unsupported_subtree')
        if ('hidden' in at or at.get('aria-hidden','').lower()=='true') and 'hidden' not in flags:flags.append('hidden')
        ref=node_prefix+str(len(nodes))
        node={'ref':ref,'kind':kind,'tag':tag,'attrs':attributes,'text':obj.data if kind in ('text','comment') else None,'parent':parent,'children':[],'order':len(nodes),'depth':depth,'flags':flags}
        nodes.append(node)
        if parent is not None:nodes[int(parent.rsplit(':',1)[1])]['children'].append(ref)
        if tag in ('iframe','frame'):indicators.append({'code':'unrepresented_frame','ref':ref})
        if tag=='template' and any(k.startswith('shadowroot') for k in at):indicators.append({'code':'unrepresented_shadow_root','ref':ref})
        if at.get('aria-expanded')=='false':indicators.append({'code':'collapsed_region_indicator','ref':ref})
        if at.get('data-truncated')=='true':indicators.append({'code':'truncation_indicator','ref':ref})
        if at.get('rel') in ('next','prev') or 'pagination' in at.get('class','').lower():indicators.append({'code':'pagination_indicator','ref':ref})
        if kind=='text' and not flags:
            lower=obj.data.lower()
            for term,code in [('loading','loading_indicator'),('load more','additional_content_indicator'),('show more','additional_content_indicator'),('truncated','truncation_indicator')]:
                if term in lower:indicators.append({'code':code,'ref':ref})
        for child in reversed(list(obj.childNodes)):stack.append((child,ref,depth+1,flags))
    result={'index_version':'1.0.0','capture':capture_info,'parser':parser_info,'nodes':nodes,'indicators':indicators}
    result['index_id']=bound('index',result)
    # Enforce restricted Unicode/number profile on parsed output too.
    try:C(result)
    except Exception as exc:raise Failure('parsed_evidence_restricted_json_invalid') from exc
    return result

def descendants(index,ref,include_self=True):
    lookup=by_ref(index)
    if ref not in lookup:raise Failure('unknown_node_reference')
    found=[];stack=[ref]
    while stack:
        n=lookup[stack.pop()];found.append(n);stack.extend(reversed(n['children']))
    return found if include_self else found[1:]

def read_value(index,value):
    if not isinstance(value,dict) or set(value)-{'node','kind','attribute','start','end'}:raise Failure('value_reference_invalid')
    lookup=by_ref(index); node=lookup.get(value.get('node'))
    if node is None:raise Failure('unknown_node_reference')
    if node['flags'] or node['kind']=='comment':raise Failure('unsupported_value_region')
    if value.get('kind')=='text' and node['kind']=='text' and 'attribute' not in value:raw=node['text']
    elif value.get('kind')=='attribute' and node['kind']=='element' and value.get('attribute') in attrs(node):raw=attrs(node)[value['attribute']]
    else:raise Failure('value_source_invalid')
    if ('start' in value)!=('end' in value):raise Failure('slice_pair_required')
    if 'start' in value:
        a,b=value['start'],value['end']
        if type(a)!=int or type(b)!=int or not 0<=a<=b<=len(raw):raise Failure('slice_bounds_invalid')
        raw=raw[a:b]
    return raw

def select(index,scope,selector):
    if not isinstance(selector,dict) or not selector or set(selector)-{'tag','attribute','equals','class_token'} or any(not isinstance(v,str) or len(v)>1024 for v in selector.values()) or ('equals' in selector and 'attribute' not in selector):raise Failure('selector_invalid')
    selected=[]
    for n in descendants(index,scope):
        if n['kind']!='element':continue
        a=attrs(n)
        if 'tag' in selector and n['tag']!=selector['tag']:continue
        if 'attribute' in selector and selector['attribute'] not in a:continue
        if 'equals' in selector and a[selector['attribute']]!=selector['equals']:continue
        if 'class_token' in selector and selector['class_token'] not in a.get('class','').split():continue
        selected.append(n['ref'])
    return selected

def text_segments(index,root_ref,excluded):
    lookup=by_ref(index)
    if root_ref not in lookup:raise Failure('unknown_node_reference')
    blocked=set(excluded); pieces=[];tokens=[]
    def flush():
        nonlocal tokens
        while tokens and 'insertion' in tokens[0]:tokens.pop(0)
        while tokens and 'insertion' in tokens[-1]:tokens.pop()
        if tokens:
            out=''; maps=[]
            for token in tokens:
                text=token['text']
                if not text:continue
                maps.append({'output_start':len(out),'output_end':len(out)+len(text),**{k:v for k,v in token.items() if k!='text'}});out+=text
            if out:pieces.append({'text':out,'mappings':maps})
        tokens=[]
    def insert(text,operation,ref):
        if tokens and 'insertion' in tokens[-1] and operation=='block_boundary':return
        tokens.append({'text':text,'insertion':{'operation':operation,'node':ref}})
    def visit(ref):
        n=lookup[ref]
        if ref in blocked or n['flags']:
            flush();return
        if n['kind']=='text':
            tokens.append({'text':n['text'],'source':{'node':ref,'kind':'text','start':0,'end':len(n['text'])}});return
        if n['kind']=='comment':return
        if n['tag']=='br':insert('\n','line_break',ref);return
        if n['tag'] in BLOCKS:insert('\n','block_boundary',ref)
        if n['tag'] in ('td','th'):
            siblings=lookup[n['parent']]['children'] if n['parent'] else []
            if any(lookup[r]['tag'] in ('td','th') for r in siblings[:siblings.index(ref)]):insert('\t','table_cell',ref)
        for c in n['children']:visit(c)
        if n['tag'] in BLOCKS:insert('\n','block_boundary',ref)
    visit(root_ref);flush();return pieces

class Inspector:
    """A data-only gateway. Truncated views are never extraction values."""
    def __init__(self,index,limits=None):
        self.index=index;self.nodes=by_ref(index);self.limits=limits_for(limits);self.calls=0;self.characters=0;self.exposed=set();self.inspected=set();self.started=time.monotonic();self.tool_elapsed=0;self.selector_work=0
    def _node(self,n,max_characters=1000):
        self.exposed.add(n['ref'])
        out={k:n[k] for k in ('ref','kind','tag','parent','children','order','depth','flags')}
        out['children']=out['children'][:100];out['children_truncated']=len(n['children'])>100
        if n['flags'] or n['kind']=='comment':out.update({'text':None,'attrs':[],'withheld':True});return out
        value=n['text'] or ''
        out.update({'text':value[:max_characters],'text_length':len(value),'truncated':len(value)>max_characters,'attrs':[]})
        for a in n['attrs']:
            if a['name'] not in SAFE_ATTRIBUTES:continue
            val=a['value']
            if a['name']=='href':
                try:
                    u=urlsplit(val)
                    if u.username or u.password or u.query or u.scheme not in ('','http','https'):val='[withheld unsafe or query-bearing URL]'
                except ValueError:val='[withheld URL]'
            out['attrs'].append({'name':a['name'],'value':val[:1024],'truncated':len(val)>1024})
        return out
    def call(self,name,args):
        exposed,inspected=set(self.exposed),set(self.inspected)
        try:return self._call(name,args)
        except Exception:
            self.exposed,self.inspected=exposed,inspected
            raise
    def _call(self,name,args):
        exposed_before,inspected_before=set(self.exposed),set(self.inspected)
        if not isinstance(args,dict):raise Failure('tool_arguments_invalid')
        started=time.monotonic();self.calls+=1
        if self.calls>self.limits['tool_calls'] or self.tool_elapsed>self.limits['wall_seconds']:raise Failure('inspection_budget_exhausted','resource_limit')
        def integer(key,default,maximum):
            v=args.get(key,default)
            if type(v)!=int or not 0<=v<=maximum:raise Failure('tool_arguments_invalid')
            return v
        def node():
            n=self.nodes.get(args.get('node_ref'))
            if n is None:raise Failure('unknown_node_reference')
            return n
        allow={'page_outline':{'start','limit','max_characters'},'inspect_node':{'node_ref','depth','max_characters'},'inspect_neighbors':{'node_ref','max_nodes'},'read_attribute':{'node_ref','attribute'},'search_text':{'literal_query','limit'},'find_structural_candidates':{'criteria','limit'},'preview_plan':{'plan_fragment'}}
        if name not in allow or set(args)-allow[name]:raise Failure('tool_not_allowed')
        max_chars=integer('max_characters',1000,self.limits['tool_characters']) if 'max_characters' in allow[name] else 1000
        if name=='page_outline':
            start=integer('start',0,len(self.index['nodes']));limit=integer('limit',30,100)
            chosen=self.index['nodes'][start:start+limit];result={'nodes':[self._node(n,min(max_chars,300)) for n in chosen],'next_start':start+len(chosen) if start+len(chosen)<len(self.index['nodes']) else None,'indexed_nodes':len(self.nodes)}
        elif name=='inspect_node':
            n=node();depth=integer('depth',1,8);selected=[x for x in descendants(self.index,n['ref']) if x['depth']<=n['depth']+depth];chosen=selected[:100]
            result={'nodes':[self._node(x,max_chars) for x in chosen],'truncated_nodes':len(selected)>100};self.inspected.update(x['ref'] for x in chosen)
        elif name=='inspect_neighbors':
            n=node();radius=integer('max_nodes',6,30);chosen=self.index['nodes'][max(0,n['order']-radius):n['order']+radius+1];result={'nodes':[self._node(x,300) for x in chosen]};self.inspected.update(x['ref'] for x in chosen)
        elif name=='read_attribute':
            n=node();key=args.get('attribute')
            if key not in SAFE_ATTRIBUTES:raise Failure('model_attribute_not_allowed')
            safe=self._node(n);value=next((a for a in safe['attrs'] if a['name']==key),None);result={'node':n['ref'],'attribute':key,'value':value};self.inspected.add(n['ref'])
        elif name=='search_text':
            q=args.get('literal_query');limit=integer('limit',10,50)
            if not isinstance(q,str) or not 1<=len(q)<=256:raise Failure('tool_arguments_invalid')
            matches=[n for n in self.index['nodes'] if n['kind']=='text' and not n['flags'] and q in n['text']]
            result={'nodes':[self._node(x,1000) for x in matches[:limit]],'truncated_results':len(matches)>limit}
        elif name=='find_structural_candidates':
            criteria=args.get('criteria',{'tag':'article'});limit=integer('limit',20,100)
            self.selector_work+=len(self.index['nodes'])
            if self.selector_work>self.limits['selector_work']:raise Failure('selector_work_limit','resource_limit')
            refs=select(self.index,self.index['nodes'][0]['ref'],criteria);result={'nodes':[self._node(self.nodes[r],300) for r in refs[:limit]],'truncated_results':len(refs)>limit,'not_completeness_proof':True}
        else:
            from .plans import validate_plan
            validate_plan(self.index,args.get('plan_fragment'));result={'valid':True,'contributions':len(args['plan_fragment']['contributions'])}
        size=len(C(result).decode('utf-8'))
        if size>self.limits['tool_characters']:
            # Do not cut serialized JSON: return a clearly labeled empty preview.
            self.exposed,self.inspected=exposed_before,inspected_before
            result={'truncated':True,'reason':'tool_result_character_limit','suggestion':'Request fewer nodes or a smaller depth.','result_characters':size}
            size=len(C(result))
        self.characters+=size
        if self.characters>self.limits['inspected_characters']:raise Failure('inspection_character_limit','resource_limit')
        self.tool_elapsed+=time.monotonic()-started
        return result
    def audit(self):
        candidates=[n['ref'] for n in self.index['nodes'] if n['kind']=='element' and not n['flags'] and (n['tag'] in ('article','li','blockquote') or NATIVE.intersection(attrs(n)))]
        return {'indexed_nodes':len(self.nodes),'exposed':sorted(self.exposed),'inspected':sorted(self.inspected),'unreviewed_candidates':sorted(set(candidates)-self.inspected),'tool_calls':self.calls,'selector_work':self.selector_work,'inspected_characters':self.characters,'not_completeness_proof':True}
