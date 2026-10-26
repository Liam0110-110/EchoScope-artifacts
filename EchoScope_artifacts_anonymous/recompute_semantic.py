"""Recompute expected semantic accuracy and exact unresolved-label bounds."""
from pathlib import Path
from collections import defaultdict, Counter
from fractions import Fraction
from itertools import product
import json,hashlib,shutil
O=Path(__file__).resolve().parents[1]
D=O/'verification/semantic_intake'
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
mp=rows(D/'PRIVATE_use_mapping.jsonl');auto=rows(D/'automatic_scoring.jsonl')
agree={r['review_id']:r['correctness'] for r in rows(D/'dual_review/agreed_labels.jsonl')}
disputed=rows(D/'dual_review/adjudication_queue.jsonl');ids=[r['review_id'] for r in disputed]
assert len(agree)==50 and len(ids)==2
scenarios=[];all_rows=[]
for bits in product([0,1],repeat=len(ids)):
    labels={**agree,**dict(zip(ids,bits))}; sc=defaultdict(Fraction);mass=defaultdict(Fraction)
    for r in auto+mp:
        corr=labels[r['review_id']] if 'review_id' in r else r['correctness']
        for u in r['uses']:
            k=(u['branch'],u['model'],u['method'],u['condition'],u.get('calibration_size',0),u.get('readout','expected'),r['fact_id'])
            p=Fraction(u['probability']);sc[k]+=p*corr;mass[k]+=p
    assert len(sc)==5328 and all(v==1 for v in mass.values())
    all_rows.append(sc)
    def mean(branch,method,condition,cal=0,readout='expected'):
        vals=[v for k,v in sc.items() if (k[0],k[2],k[3],k[4],k[5])==(branch,method,condition,cal,readout)]
        return float(sum(vals)/len(vals))
    scenarios.append({'labels':dict(zip(ids,bits)),
      'H1':mean('fixed','vanilla','N')-mean('fixed','vanilla','A_para'),
      'H2':mean('fixed','semantic_0.90','A_para')-mean('fixed','exact_text','A_para'),
      'correct_copy_cost':mean('fixed','semantic_0.90','B_para')-mean('fixed','exact_text','B_para'),
      'learned_GroupVote_R2_attack_minus_clean':mean('learned','GroupVote','A_exact',13,'R2')-mean('learned','GroupVote','N',13,'R2')})
summary=[];point_rows=[]
for k in sorted(all_rows[0]):
    v=[d[k] for d in all_rows]
    point_rows.append(dict(zip(['branch','model','method','condition','calibration_size','readout','fact_id'],k),semantic_lower=float(min(v)),semantic_upper=float(max(v))))
for cell in sorted(set(k[:-1] for k in all_rows[0])):
    vals=[]
    for sc in all_rows:
        arr=[v for k,v in sc.items() if k[:-1]==cell];vals.append(float(sum(arr)/len(arr)))
    summary.append(dict(zip(['branch','model','method','condition','calibration_size','readout'],cell),n=len(arr),semantic_lower=min(vals),semantic_upper=max(vals)))
means=[]
for cell in sorted(set((k[0],*k[2:-1]) for k in all_rows[0])):
    vals=[]
    for sc in all_rows:
        arr=[v for k,v in sc.items() if (k[0],*k[2:-1])==cell];vals.append(float(sum(arr)/len(arr)))
    means.append(dict(zip(['branch','method','condition','calibration_size','readout'],cell),n=len(arr),semantic_lower=min(vals),semantic_upper=max(vals)))
effects={k:{'lower':min(s[k] for s in scenarios),'upper':max(s[k] for s in scenarios)} for k in scenarios[0] if k!='labels'}
rec={'status':'50_CONSENSUS_LABELS_2_AWAIT_ADJUDICATION','cards':52,'agreed':50,'disputed':2,'ambiguous':0,'agreed_correctness':dict(Counter(agree.values())),
 'duplicate_return_8_excluded':True,'input_files':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((D/'inputs').glob('*.jsonl'))],
 'distinct_reviewers':['003','004'],'unresolved_case':'One question, two capitalization variants of Machine learning vs Modern Machine Learning.',
 'bound_method':'Enumerate all four shared-candidate 0/1 label assignments, preserving each question/candidate across all uses. Conservative: allows the two case variants to differ. These are identification bounds, not confidence intervals.',
 'votes_changed':False,'aliases_changed':False,'new_model_calls':0,'effects':effects,'scenarios':scenarios}
for n,obj in [('consensus_summary.json',summary),('consensus_fixed_model_means.json',means),('consensus_receipt.json',rec)]:
    (D/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
(D/'consensus_score_bounds.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in point_rows))
print(json.dumps(rec,ensure_ascii=False,indent=2))
print('FIXED MEANS:')
for r in means:
    if r['branch']=='fixed':print(r)
