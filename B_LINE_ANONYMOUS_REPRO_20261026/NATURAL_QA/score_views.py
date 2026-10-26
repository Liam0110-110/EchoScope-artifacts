"""Frozen reporting score_view function; intake/runtime validation intentionally excluded."""
import collections
import contract as P
import statistical_core as S

def score_view(inputs,gold,raw,strong,strict=False):
    """One denominator and prompt selection for both views; H_SQ is re-derived per view."""
    scored={}
    for r in raw:
        parsed=P.evaluate(r.get('raw_text',''),r['method'],r.get('finish_reason'),r['status'])
        prefix='strict_' if strict else ''
        scored[r['id'],r['method']]={'status':parsed[prefix+'status'],'label':parsed[prefix+'label'],'route':parsed[prefix+'route']}
    result=[];router_confusion=collections.Counter()
    for ident,source in inputs.items():
        labels={}
        for method in ['SQ','NQ',strong]:
            p=scored[ident,method];labels[method]=p['label'] if p['status']=='ok' else None
        r=scored[ident,'router'];route=r['route'] if r['status']=='ok' else None
        labels['HSQ']=labels['NQ'] if route=='standalone' else labels['SQ'] if route=='dependent' else None
        kind=gold[ident]['answer_type']
        labels['reviewed_type_HSQ']=labels['NQ'] if kind=='standalone' else labels['SQ'] if kind=='dependent' else None
        router_confusion[kind,route or '<failure>']+=1
        result.append({'id':ident,'source_group_id':source['source_group_id'],'answer_source':source['answer_source'],'support_gold':gold[ident]['support_gold'],'answer_type':kind,'relevance_gold':gold[ident]['relevance_gold'],'labels':labels,'correct':{m:v==gold[ident]['support_gold'] for m,v in labels.items()}})
    def contrast(baseline,intervention):
        x=S.contrast(result,baseline,intervention);x['inference']='descriptive_unadjusted_not_independent_confirmation';return x
    methods=['SQ','NQ',strong,'HSQ'];status={m:dict(collections.Counter(scored[i,m]['status'] for i in inputs)) for m in ['SQ','NQ','router',strong]}
    coverage={m:sum(scored[i,m]['status']=='ok' for i in inputs) for m in status}
    return {'overall':{m:S.metric(result,m) for m in methods},'HSQ_minus_SQ':contrast('SQ','HSQ'),'HSQ_minus_NQ':contrast('NQ','HSQ'),'HSQ_minus_StrongSQ':contrast(strong,'HSQ'),'status_counts':status,'valid_call_counts':coverage,
            'router':{'correct':sum(n for (g,p),n in router_confusion.items() if g==p),'n':len(inputs),'valid':coverage['router'],'confusion':[{'gold':g,'predicted':p,'n':n} for (g,p),n in sorted(router_confusion.items())]},
            'reviewed_type_reference':{'metric':S.metric(result,'reviewed_type_HSQ'),'role':'human-type diagnostic, not deployable and not a mathematical upper bound'},
            'strata':{axis:{value:{'n':len(subset),'methods':{m:S.metric(subset,m) for m in methods}} for value in sorted({r[axis] for r in result}) for subset in [[r for r in result if r[axis]==value]]} for axis in ['answer_type','answer_source','support_gold','relevance_gold']},'rows':result}
