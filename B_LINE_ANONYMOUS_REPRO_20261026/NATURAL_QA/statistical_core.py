import collections,math,random
SEED=20261026
BOOTSTRAPS=10000

def percentile(values, proportion):
    values = sorted(values)
    if not values:
        return None
    x = (len(values) - 1) * proportion
    low, high = math.floor(x), math.ceil(x)
    return values[low] + (values[high] - values[low]) * (x - low)

def paired_bootstrap(rows, group_key='source_group_id', seed=SEED, reps=BOOTSTRAPS):
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row[group_key]].append(row)
    groups = list(grouped.values())
    if not groups:
        return [None, None]
    rng = random.Random(seed)
    deltas = []
    for _ in range(reps):
        chosen = [groups[rng.randrange(len(groups))] for __ in range(len(groups))]
        denominator = sum(len(g) for g in chosen)
        deltas.append(sum(r['delta'] for group in chosen for r in group) / denominator)
    return [percentile(deltas, .025), percentile(deltas, .975)]

def mcnemar_exact(recoveries, harms):
    """Two-sided conditional binomial test; no continuity correction."""
    n = recoveries + harms
    if n == 0:
        return 1.0
    p = sum(math.comb(n, k) for k in range(min(recoveries, harms) + 1)) / 2 ** n
    return min(1.0, 2.0 * p)

def ratio(numerator, denominator):
    return None if denominator == 0 else numerator / denominator

def metric(rows, method):
    correct = sum(r['correct'][method] for r in rows)
    valid = [r for r in rows if r['labels'][method] is not None]
    non_supported = [r for r in rows if r['support_gold'] != 'supported']
    supported = [r for r in rows if r['support_gold'] == 'supported']
    false_accept = sum(r['labels'][method] == 'supported' for r in non_supported)
    false_reject = sum(r['labels'][method] != 'supported' for r in supported)
    confusion = collections.Counter((r['support_gold'], r['labels'][method] or '<failure>') for r in rows)
    return {
        'n': len(rows), 'correct': correct, 'accuracy': ratio(correct, len(rows)),
        'valid_n': len(valid), 'coverage': ratio(len(valid), len(rows)),
        'valid_only_accuracy_diagnostic': ratio(sum(r['correct'][method] for r in valid), len(valid)),
        'false_accept_n': false_accept,
        'false_accept_rate_all': ratio(false_accept, len(rows)),
        'false_accept_given_not_supported': ratio(false_accept, len(non_supported)),
        'false_reject_n_includes_failures': false_reject,
        'false_reject_rate_all': ratio(false_reject, len(rows)),
        'false_reject_given_supported': ratio(false_reject, len(supported)),
        'support_confusion': [{'gold': k[0], 'predicted': k[1], 'n': v} for k,v in sorted(confusion.items())]
    }

def contrast(rows, baseline='SQ', intervention='HSQ', compute_ci=True):
    paired = [dict(r, delta=int(r['correct'][intervention])-int(r['correct'][baseline])) for r in rows]
    recoveries = sum(r['delta'] == 1 for r in paired)
    harms = sum(r['delta'] == -1 for r in paired)
    return {
        'n': len(rows), 'groups': len({r['source_group_id'] for r in rows}),
        'baseline': baseline, 'intervention': intervention,
        'delta_accuracy': ratio(recoveries-harms, len(rows)),
        'recoveries_n': recoveries, 'harms_n': harms,
        'recoveries_rate_all': ratio(recoveries, len(rows)),
        'harms_rate_all': ratio(harms, len(rows)),
        'harms_given_baseline_correct': ratio(harms, sum(r['correct'][baseline] for r in rows)),
        'recoveries_given_baseline_wrong': ratio(recoveries, sum(not r['correct'][baseline] for r in rows)),
        'ci95_paired_source_group_bootstrap': paired_bootstrap(paired) if compute_ci else None,
        'p_mcnemar_exact_two_sided': mcnemar_exact(recoveries, harms) if rows else None,
        'inference': 'primary' if baseline == 'SQ' and intervention == 'HSQ' else 'secondary_exploratory_no_multiplicity_adjustment'
    }
