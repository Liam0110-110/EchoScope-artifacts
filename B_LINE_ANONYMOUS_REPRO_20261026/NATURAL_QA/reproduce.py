#!/usr/bin/env python3
"""Offline output-level replay of two frozen scoring views; Python 3.9+ standard library."""
import argparse,hashlib,json,math,pathlib
from score_views import score_view
ROOT=pathlib.Path(__file__).resolve().parent
ORDER=('qwen35_27b','qwen35','ministral3','gemma3_4b')
CHOICES=('StrongSQ_A','StrongSQ_B','StrongSQ_A','StrongSQ_B')
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def unique(rs):
 result={r['id']:r for r in rs}
 assert len(result)==len(rs),'Duplicate IDs'
 return result
def compare(a,e,path='result'):
 if isinstance(e,dict):
  assert isinstance(a,dict) and set(a)==set(e),path+': keys differ'
  for k,v in e.items():compare(a[k],v,path+'/'+k)
 elif isinstance(e,list):
  assert len(a)==len(e),path+': count differs'
  for i,(x,y) in enumerate(zip(a,e)):compare(x,y,path+'/'+str(i))
 elif isinstance(e,(int,float)) and not isinstance(e,bool):assert math.isclose(a,e,rel_tol=1e-12,abs_tol=1e-12),path+': numerical mismatch'
 else:assert a==e,path+': mismatch'
def run():
 for name,digest in read(ROOT/'MANIFEST.json')['files'].items():
  p=(ROOT/name).resolve();assert ROOT in p.parents and p.is_file(),'Unsafe/missing manifest member'
  assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,'Changed member: '+name
 public=rows(ROOT/'data/test.public.jsonl');inputs=unique(public);gold=unique(rows(ROOT/'data/gold.jsonl'))
 assert len(inputs)==100 and len({r['source_group_id'] for r in public})==100 and set(inputs)==set(gold)
 assert all(set(r)=={'id','split','question','answer','evidence','source_group_id','answer_source'} for r in public)
 assert all(set(r)=={'id','support_gold','answer_type','relevance_gold'} for r in gold.values())
 expected=read(ROOT/'expected_results.json');out={'schema':'NQA_ANONYMOUS_EXPECTED_AGGREGATES_V1','n_unique_test_source_groups':100,'models':{}}
 for model,strong in zip(ORDER,CHOICES):
  raw=rows(ROOT/f'data/{model}.raw.jsonl')
  assert len(raw)==400 and {(r['id'],r['method']) for r in raw}=={(i,m) for i in inputs for m in ['SQ','NQ','router',strong]}
  assert all(set(r)=={'id','method','raw_text','finish_reason','status','source_raw_sha256'} for r in raw)
  views={}
  for view in ['strict','lpc3']:
   result=score_view(inputs,gold,raw,strong,strict=(view=='strict'))
   views[view]={k:v for k,v in result.items() if k not in ['rows','strata']}
  out['models'][model]={'selected_strong':strong,'views':views}
  compare(out['models'][model],expected['models'][model],model)
 compare(out,expected)
 return out
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=pathlib.Path);args=ap.parse_args();out=run()
 if args.out:args.out.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
 print('PASS: four deployments, 100 shared source groups, 1600 raw outputs; strict and LPC3 reproduce accepted aggregates.')
 for m,d in out['models'].items():
  c=d['views']['lpc3']['HSQ_minus_SQ'];print(m, 'SQ',d['views']['lpc3']['overall']['SQ']['correct'],'HSQ',d['views']['lpc3']['overall']['HSQ']['correct'],'delta',c['delta_accuracy'],'CI',c['ci95_paired_source_group_bootstrap'],'exact_p',c['p_mcnemar_exact_two_sided'])
