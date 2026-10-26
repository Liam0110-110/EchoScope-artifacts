"""LPC3: explicit top-level label, optional unscored JSON reason metadata."""
import hashlib,json,re
VERSION='NQA_LABEL_COMPATIBILITY_V3'
SUPPORT={'supported','contradicted','not_established','uncertain'}
ROUTES={'standalone','dependent','ambiguous'}

def pairs(items):
    out={}
    for k,v in items:
        if k in out:raise ValueError('Duplicate JSON key')
        out[k]=v
    return out
def loads(text):
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def parse(raw,method,strict=False):
    text=raw if strict else raw.strip();transport='raw_json'
    if not strict:
        m=re.fullmatch(r'```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```',text)
        if m:
            if '```' in m.group(1):return None
            text=m.group(1).strip();transport='single_complete_fence'
    try:x=loads(text)
    except (ValueError,TypeError):return None
    key='route' if method=='router' else 'source_support';allowed=ROUTES if method=='router' else SUPPORT
    if not isinstance(x,dict) or key not in x or not set(x)<={key,'reason'}:return None
    if not isinstance(x[key],str) or x[key] not in allowed:return None
    if strict and (set(x)!={key,'reason'} or not isinstance(x['reason'],str)):return None
    return {'value':x[key],'transport':transport,'reason_metadata':x.get('reason'),'reason_type':type(x.get('reason')).__name__}
def evaluate(raw,method,finish_reason,status='completed'):
    if finish_reason=='length' or status in {'truncated','input_over_budget','generation_error','interrupted_no_retry','not_attempted','missing'}:
        return {'status':'truncated' if finish_reason=='length' else status,'label':None,'route':None,'strict_status':'truncated' if finish_reason=='length' else status,'strict_label':None,'strict_route':None,'transport':None,'reason_type':None}
    p=parse(raw,method);s=parse(raw,method,strict=True);r=method=='router'
    return {'status':'ok' if p else 'invalid_schema','label':p['value'] if p and not r else None,'route':p['value'] if p and r else None,
            'strict_status':'ok' if s else 'invalid_schema','strict_label':s['value'] if s and not r else None,'strict_route':s['value'] if s and r else None,
            'transport':p['transport'] if p else None,'reason_type':p['reason_type'] if p else None}
