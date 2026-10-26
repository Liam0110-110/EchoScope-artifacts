#!/usr/bin/env python3
"""Validate frozen G7 short-answer reviews and compare two reviewers. CPU only."""
from pathlib import Path
import json,hashlib,datetime,argparse

def load(p):
 rs=[json.loads(s) for s in Path(p).read_text(encoding='utf-8').splitlines() if s.strip()]
 if len({x['review_id'] for x in rs})!=len(rs):raise ValueError('duplicate review ID')
 return {x['review_id']:x for x in rs}
def sha(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def validate(cards,rs):
 errors=[]
 if set(cards)!=set(rs):errors.append('return IDs do not equal all frozen cards')
 for key,c in cards.items():
  if sha({k:v for k,v in c.items() if k!='payload_sha256'})!=c['payload_sha256']:errors.append(key+': frozen payload modified')
  if key not in rs:continue
  r=rs[key]
  if r.get('payload_sha256')!=c['payload_sha256']:errors.append(key+': payload hash mismatch')
  if r.get('judgment') not in {'correct','incorrect','ambiguous'}:errors.append(key+': invalid/PENDING judgment')
  if not str(r.get('reason','')).strip():errors.append(key+': reason required')
  if not isinstance(r.get('rule_ids'),list) or not r['rule_ids'] or any(x not in ['M-1','M-2','M-3','1','2','3','4','5','6'] for x in r['rule_ids']):errors.append(key+': cite valid frozen rule IDs')
  if not isinstance(r.get('reference_issue'),bool):errors.append(key+': reference_issue must be boolean')
  if r.get('reference_issue') and r.get('judgment')!='ambiguous':errors.append(key+': disputed reference must remain ambiguous')
  if not str(r.get('reviewer_id','')).strip() or r.get('independent_review_completed') is not True:errors.append(key+': reviewer/declaration required')
  try:
   dt=datetime.datetime.fromisoformat(r.get('reviewed_at','').replace('Z','+00:00'))
   if dt.tzinfo is None:raise ValueError()
  except (ValueError,TypeError):errors.append(key+': timestamp with timezone required')
 return errors

def main():
 p=argparse.ArgumentParser();p.add_argument('--cards',required=True);p.add_argument('--r1',required=True);p.add_argument('--r2');p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 try:
  cards=load(a.cards);r1=load(a.r1);errors=validate(cards,r1);r2=None
  if a.r2:
   r2=load(a.r2);errors+=validate(cards,r2)
   if {x.get('reviewer_id') for x in r1.values()} & {x.get('reviewer_id') for x in r2.values()}:errors.append('R1/R2 reviewer IDs overlap')
  receipt={'status':'FAIL' if errors else 'FORMAT_AND_BINDING_PASS','cards':len(cards),'errors':errors,'semantic_truth_certified':False,'aliases_modified':False,'model_calls':0}
  if not errors and r2:
   agreed=[];disputed=[];unclear=[]
   for k,c in cards.items():
    x,y=r1[k],r2[k];row={'review_id':k,'payload_sha256':c['payload_sha256'],'r1':x,'r2':y}
    if (x['judgment'],x['reference_issue'])!=(y['judgment'],y['reference_issue']):row['card']=c;disputed.append(row)
    elif x['judgment']=='ambiguous':row['card']=c;unclear.append(row)
    else:row['correctness']=int(x['judgment']=='correct');agreed.append(row)
   for name,rows in [('agreed_labels.jsonl',agreed),('adjudication_queue.jsonl',disputed),('ambiguous_queue.jsonl',unclear)]:
    (out/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
   receipt.update(agreed=len(agreed),disputed=len(disputed),ambiguous=len(unclear))
 except Exception as e:receipt={'status':'FAIL','errors':[str(e)]}
 (out/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(receipt,ensure_ascii=False));return 2 if receipt['status']=='FAIL' else 0
if __name__=='__main__':raise SystemExit(main())
