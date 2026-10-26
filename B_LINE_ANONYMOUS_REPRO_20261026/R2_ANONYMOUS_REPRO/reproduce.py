#!/usr/bin/env python3
"""Offline R2 reanalysis. Python 3.9+, standard library only; no model execution."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parent
CELLS = ('Fq1', 'Fq2', 'Dq1', 'Dq2')
METHODS = ('J', 'SQ', 'NQ', 'C', 'H_SQ', 'H_C')
MODELS = ('qwen35_27b', 'qwen35', 'ministral3', 'gemma3_4b')

def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))

def rows(name):
    return [json.loads(x) for x in (ROOT / name).read_text(encoding='utf-8').splitlines() if x.strip()]

def require(ok, message):
    if not ok:
        raise ValueError(message)

def quantile(values, p):
    values = sorted(values)
    z = (len(values) - 1) * p
    i = int(z)
    return values[i] + (values[min(i + 1, len(values) - 1)] - values[i]) * (z - i)

def paired_test(diffs, strata):
    wins, losses = diffs.count(1), diffs.count(-1)
    n = wins + losses
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(wins, losses) + 1)) / 2 ** n) if n else 1.0
    rng = random.Random(20261022)
    boot = [sum(diffs[rng.choice(ids)] for ids in strata.values() for _ in ids) / len(diffs) for _ in range(10000)]
    return dict(estimate=sum(diffs) / len(diffs), ci95=[quantile(boot, .025), quantile(boot, .975)], exact_two_sided_p=p,
                improved_topics=wins, harmed_topics=losses, unchanged_topics=diffs.count(0))

def compare(actual, expected, path='result'):
    if isinstance(expected, dict):
        require(isinstance(actual, dict), path + ': wrong type')
        for key, value in expected.items():
            require(key in actual, path + ': missing ' + key)
            compare(actual[key], value, path + '/' + key)
    elif isinstance(expected, list):
        require(len(actual) == len(expected), path + ': length mismatch')
        for i, (a, e) in enumerate(zip(actual, expected)):
            compare(a, e, path + '/' + str(i))
    elif isinstance(expected, (float, int)):
        require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), path + ': numeric mismatch')
    else:
        require(actual == expected, path + ': mismatch')

def run():
    manifest = read('MANIFEST.json')
    for name, digest in manifest['files'].items():
        p = (ROOT / name).resolve()
        require(ROOT in p.parents, 'Manifest path escapes package')
        require(hashlib.sha256(p.read_bytes()).hexdigest() == digest, 'SHA256 mismatch: ' + name)
    public_rows, gold_rows = rows('data/cases.jsonl'), rows('data/input_gold.jsonl')
    cases, gold = {x['case_id']: x for x in public_rows}, {x['case_id']: x for x in gold_rows}
    require(len(cases) == len(public_rows) == len(gold) == len(gold_rows) == 48, 'Input coverage')
    require(set(cases) == set(gold), 'Gold/public mismatch')
    ordered = sorted(cases)
    strata = defaultdict(list)
    for i, cid in enumerate(ordered):
        g = gold[cid]
        require(set(g['gold']) == set(CELLS), 'Incomplete input gold')
        require(g['gold']['Fq1'] == g['gold']['Fq2'] and g['gold']['Dq1'] != g['gold']['Dq2'], 'Paired design mismatch')
        strata[g['domain'], g['binding']].append(i)
    require(len(strata) == 4 and all(len(x) == 12 for x in strata.values()), 'Stratum coverage')
    cells = rows('data/cell_metrics.jsonl')
    ix = {(x['model'], x['case_id'], x['cell'], x['method']): x for x in cells}
    require(len(cells) == len(ix) == 4608, 'Duplicate or missing logical cells')
    expected_keys = {(m, c, k, method) for m in MODELS for c in ordered for k in CELLS for method in METHODS}
    require(set(ix) == expected_keys, 'Unexpected logical key set')
    for (m, cid, cell, method), x in ix.items():
        require(x['gold'] == gold[cid]['gold'][cell], 'Cell gold drift')
        require(x['correct'] == int(x['status'] == 'completed' and x['prediction'] == x['gold']), 'Correctness drift')
    cards_list = read('data/output_cards.json')['cards']
    cards = {x['card_id']: x for x in cards_list}
    require(len(cards_list) == len(cards) == 497, 'Card coverage')
    require(len({(x['question'], x['answer'], x['claim']) for x in cards_list}) == 497, 'Duplicate cards')
    reviews = read('data/reviews.json')
    labels = {role: {x['card_id']: x for x in reviews[role]} for role in ('A', 'B', 'D', 'final')}
    for role in ('A', 'B', 'final'):
        require(set(labels[role]) == set(cards) and len(reviews[role]) == 497, 'Review coverage: ' + role)
    disagreement = {c for c in cards if labels['A'][c]['faithfulness'] != labels['B'][c]['faithfulness'] or labels['A'][c]['faithfulness'] == 'uncertain'}
    require(set(labels['D']) == disagreement and len(reviews['D']) == 3, 'Adjudication mismatch')
    for cid in cards:
        source = labels['D'] if cid in disagreement else labels['A']
        require(labels['final'][cid]['faithfulness'] == source[cid]['faithfulness'], 'Final review merge mismatch')
    mapping = read('data/normalization_map.json')
    require(set(mapping) == set(cards), 'Mapping/card mismatch')
    lookup = {}
    for card_id, uses in mapping.items():
        for use in uses:
            key = use['model'], use['case_id'], use['cell']
            require(key not in lookup, 'Repeated normalization mapping')
            lookup[key] = card_id
            case = cases[use['case_id']]
            require(cards[card_id]['question'] == case['questions'][int(use['cell'][-1]) - 1], 'Card question mismatch')
            require(cards[card_id]['answer'] == case['full' if use['cell'].startswith('F') else 'fragment'], 'Card answer mismatch')
            require(use['H_C_route'] == ix[key + ('H_C',)]['route'], 'Mapping route mismatch')
    require(len(lookup) == 735, 'Resolved mapping coverage')
    normal = rows('data/normalization_coverage.jsonl')
    require(len(normal) == 768 and len({(x['model'], x['case_id'], x['cell']) for x in normal}) == 768, 'Normalization coverage')
    for x in normal:
        require(bool(x['resolved']) == ((x['model'], x['case_id'], x['cell']) in lookup), 'Resolution mapping mismatch')
    result = {'models': {}}
    scope_ids = set(read('data/scope_diagnostic.json')['hypothetically_ineligible_card_ids'])
    require(len(scope_ids) == 9 and all(labels['A'][c]['faithfulness'] == labels['B'][c]['faithfulness'] == 'faithful' for c in scope_ids), 'Scope diagnostic selection mismatch')
    for m in MODELS:
        def correct(cid, cell, method):
            x = ix[m, cid, cell, method]
            return int(x['status'] == 'completed' and x['prediction'] == gold[cid]['gold'][cell])
        common, successes = {}, {}
        for method in METHODS:
            b = [int(all(correct(cid, cell, method) for cell in CELLS)) for cid in ordered]
            successes[method] = b
            common[method] = dict(complete_topics=sum(b), F_correct=sum(correct(c, k, method) for c in ordered for k in ('Fq1', 'Fq2')),
                                  D_correct=sum(correct(c, k, method) for c in ordered for k in ('Dq1', 'Dq2')),
                                  status_counts=dict(Counter(ix[m, c, k, method]['status'] for c in ordered for k in CELLS)))
        def process(ineligible):
            scores = {'C': [], 'H_C': []}
            faithful, resolved = 0, 0
            for cid in ordered:
                per = {'C': [], 'H_C': []}
                for cell in CELLS:
                    card_id = lookup.get((m, cid, cell))
                    resolved += card_id is not None
                    f = bool(card_id and labels['final'][card_id]['faithfulness'] == 'faithful' and card_id not in ineligible)
                    faithful += f
                    per['C'].append(bool(correct(cid, cell, 'C') and f))
                    route = ix[m, cid, cell, 'H_C']['route']
                    per['H_C'].append(bool(correct(cid, cell, 'H_C') and (route == 'standalone' or (route == 'dependent' and f))))
                for method in per:
                    scores[method].append(per[method])
            return dict(resolved=resolved, faithful=faithful, C_cells=sum(map(sum, scores['C'])), C_topics=sum(map(all, scores['C'])),
                        H_C_cells=sum(map(sum, scores['H_C'])), H_C_topics=sum(map(all, scores['H_C'])))
        confusion = Counter()
        for cid in ordered:
            for form in ('F', 'D'):
                routes = [ix[m, cid, form + q, 'H_SQ']['route'] for q in ('q1', 'q2')]
                require(routes[0] == routes[1], 'Router not reused over questions')
                confusion['standalone' if form == 'F' else 'dependent', routes[0]] += 1
        harm = sum(all(correct(c, k, 'NQ') for k in ('Fq1', 'Fq2')) and not all(correct(c, k, 'H_SQ') for k in ('Fq1', 'Fq2')) for c in ordered)
        d = [h - s for h, s in zip(successes['H_SQ'], successes['SQ'])]
        result['models'][m] = dict(common=common, comparison=paired_test(d, strata), process=process(set()), hypothetical_scope_stress=process(scope_ids),
                                   router_correct=sum(n for (a, b), n in confusion.items() if a == b), full_pair_harms_vs_NQ=harm)
    a = Counter(x['faithfulness'] for x in labels['A'].values())
    b = Counter(x['faithfulness'] for x in labels['B'].values())
    agreement = sum(labels['A'][c]['faithfulness'] == labels['B'][c]['faithfulness'] for c in cards)
    pe = sum(a[k] * b[k] for k in set(a) | set(b)) / len(cards) ** 2
    result['review'] = dict(unique_cards=len(cards), agreement=agreement, cohens_kappa=(agreement / len(cards) - pe) / (1 - pe),
                           final_counts=dict(Counter(x['faithfulness'] for x in labels['final'].values())), unresolved_normalizations=768 - len(lookup))
    physical = rows('data/physical_costs.jsonl')
    require(len(physical) == len({(x['model'], x['task_id']) for x in physical}) == 3565, 'Physical duplicate/coverage')
    timing = read('data/allocation_sessions.json')
    supervised = sum(x['charged_card_seconds'] for x in timing['sessions']) / 3600
    require(math.isclose(supervised, timing['logged_supervisor_card_hours'], abs_tol=1e-12), 'Allocation sum mismatch')
    result['cost'] = dict(physical_calls=len(physical), physical_status_counts=dict(Counter(x['status'] for x in physical)),
                         supervised_card_hours=supervised, estimate_before_other_transitions=supervised + timing['reported_extra_card_seconds'] / 3600 + timing['estimated_export_card_hours'])
    compare(result, read('expected_results.json'))
    result['checks'] = dict(manifest_files_verified=len(manifest['files']), reference_metrics_match=True,
                           input_gold_and_question_answer_mapping_match=True, human_merge_reproduced=True,
                           inference_or_network_calls=0, bootstrap_draws_per_model=10000, bootstrap_seed=20261022)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='Optional output JSON outside the sealed package')
    args = parser.parse_args()
    result = run()
    if args.out:
        require(ROOT not in args.out.resolve().parents, 'Write results outside the sealed package')
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS: hashes, inputs, human merge, all four model scores, paired bootstrap/exact tests, and allocation sums.')
    print(json.dumps({'primary': result['models']['qwen35_27b']['comparison'], 'reviews': result['review'], 'cost': result['cost']}, ensure_ascii=False, indent=2))
