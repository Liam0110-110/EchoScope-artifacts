"""Exact-dedup refit replay for the publisher-study learning branch.

Pure standard library. Run from this directory:  python dedup_replay.py

1. Validation gate: refits all 36 frozen cells (SourceFit / F1S1 / GroupVote
   x N / A_exact x cal13 / cal26 x 3 models) from the frozen per-source answer
   matrices and compares R0 / R2 EM, iteration counts, and first-update row
   counts against evidence/learned/summary_36.json. Exits nonzero on mismatch.
2. Dedup replay: collapses the four byte-identical copy slots
   (__ELB_COPY_1..4) into a single slot (panel 47 -> 44) in calibration and
   test matrices, refits SourceFit and F1S1, and reports R0 / R2 EM together
   with the frozen attacked and clean baselines.
"""
import json, re, math, sys, io, os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
E56 = os.path.join(ROOT, "evidence", "learned")
DATA = os.path.join(ROOT, "data")

IDK_MARKER = "i don't know"
PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
ARTICLES = re.compile(r"\b(?:a|an|the)\b", re.UNICODE)

def is_idk(a):
    return a is None or IDK_MARKER in a.lower()

def norm(s):
    s = s.lower()
    s = PUNCT.sub(" ", s)
    s = ARTICLES.sub(" ", s)
    return " ".join(s.split())

def em_of(winner, aliases_norm):
    if winner is None or is_idk(winner):
        return 0.0
    return 1.0 if norm(winner) in aliases_norm else 0.0

def unique_plurality_row(answers):
    counts = {}
    for a in answers:
        if not is_idk(a):
            counts[a] = counts.get(a, 0) + 1
    if not counts:
        return False
    mx = max(counts.values())
    return sum(1 for v in counts.values() if v == mx) == 1

def provisional(row_answers, weights):
    sums, order = {}, []
    for a, w in zip(row_answers, weights):
        if is_idk(a):
            continue
        if a not in sums:
            sums[a] = 0.0
            order.append(a)
        sums[a] += w
    if not order:
        return None
    best = order[0]
    for a in order:
        if sums[a] > sums[best] + 1e-15:
            best = a
    return best

def fit_estimator(rows, max_iter=100, tol=1e-20):
    S = len(rows[0]["answers"])
    for r in rows:
        assert len(r["answers"]) == S
    eligible_rows = [r for r in rows if unique_plurality_row(r["answers"])]
    fallback = False
    if not eligible_rows:
        eligible_rows = rows
        fallback = True
    w = [1.0] * S
    iters = 0
    converged = False
    for it in range(1, max_iter + 1):
        active = eligible_rows if it == 1 else rows
        prov = {r["event_id"]: provisional(r["answers"], w) for r in active}
        w_new = []
        for s in range(S):
            E_s = [r for r in active if not is_idk(r["answers"][s])]
            if not E_s:
                r_s = 0.0
            else:
                r_s = sum(1.0 for r in E_s if r["answers"][s] == prov[r["event_id"]]) / len(E_s)
            w_new.append(S * r_s - 1.0)
        delta = math.sqrt(sum((a - b) ** 2 for a, b in zip(w_new, w)))
        w = w_new
        iters = it
        if delta < tol:
            converged = True
            break
    return {"weights": w, "iterations": iters, "converged": converged,
            "initial_rows_used": len(eligible_rows), "all_rows_fallback": fallback,
            "panel_size": S}

def readout_R0(row_answers, weights):
    order = sorted(range(len(weights)), key=lambda s: (-weights[s], s))
    selected = [s for s in order if not is_idk(row_answers[s])][:4]
    if not selected:
        return None
    sums, first = {}, {}
    for s in selected:
        a = row_answers[s]
        if a not in sums:
            sums[a] = 0.0
            first[a] = len(first)
        sums[a] += weights[s]
    best = None
    for a in sums:
        if best is None or sums[a] > sums[best] + 1e-12 or (abs(sums[a] - sums[best]) <= 1e-12 and first[a] < first[best]):
            best = a
    return best

def readout_R2(row_answers, weights, aliases_norm):
    sel = [s for s in range(len(weights)) if not is_idk(row_answers[s])]
    if not sel:
        return 0.0
    sums = {}
    for s in sel:
        sums[row_answers[s]] = sums.get(row_answers[s], 0.0) + weights[s]
    mx = max(sums.values())
    winners = [a for a, v in sums.items() if abs(v - mx) <= 1e-12]
    return sum(em_of(a, aliases_norm) for a in winners) / len(winners)

def load_all():
    rows = [json.loads(l) for l in io.open(os.path.join(DATA, "learned_branch_rows.jsonl"), encoding="utf-8")]
    part = json.load(io.open(os.path.join(DATA, "frozen_partition.json"), encoding="utf-8"))
    aliases = {}
    for l in io.open(os.path.join(DATA, "g7_aliases.jsonl"), encoding="utf-8"):
        d = json.loads(l)
        aliases[d["event_id"]] = {norm(a) for a in d["gold_aliases"]}
    return rows, part, aliases

def dedup_row(r, answers_key):
    keep = [i for i, sid in enumerate(r["source_ids"]) if sid not in ("__ELB_COPY_2", "__ELB_COPY_3", "__ELB_COPY_4")]
    return {"event_id": r["event_id"], "answers": [r[answers_key][i] for i in keep],
            "source_ids": [r["source_ids"][i] for i in keep]}

def run_cell(all_rows, part, aliases, model, cond, cal_size, method, dedup=False):
    answers_key = "F1S1_answers" if method == "F1S1" else "raw_answers"
    cal_ids = part["cal13"] if cal_size == 13 else part["cal26"]
    test_ids = part["test34"]
    if dedup:
        cal = [dedup_row(all_rows[e], answers_key) for e in cal_ids]
        test = [dedup_row(all_rows[e], answers_key) for e in test_ids]
    else:
        cal = [{"event_id": e, "answers": all_rows[e][answers_key]} for e in cal_ids]
        test = [{"event_id": e, "answers": all_rows[e][answers_key]} for e in test_ids]
    if method in ("SourceFit", "F1S1"):
        fitres = fit_estimator(cal)
        w = fitres["weights"]
    else:
        first = all_rows[test_ids[0]]
        w = [1.0 if not sid.startswith("__ELB_COPY") else (1.0 if dedup else 0.25)
             for sid in first["source_ids"]]
        fitres = {"iterations": 0, "converged": True, "initial_rows_used": 0,
                  "all_rows_fallback": False, "panel_size": len(w)}
    r0 = sum(em_of(readout_R0(tr["answers"], w), aliases[tr["event_id"]]) for tr in test)
    r2 = sum(readout_R2(tr["answers"], w, aliases[tr["event_id"]]) for tr in test)
    n = len(test)
    return {"R0_em": r0 / n, "R2_expected_em": r2 / n,
            "iterations": fitres["iterations"], "converged": fitres["converged"],
            "initial_rows_used": fitres["initial_rows_used"],
            "all_rows_fallback": fitres["all_rows_fallback"],
            "panel_size": fitres["panel_size"], "terminal_weights": w}

def main():
    rows, part, aliases = load_all()
    by_key = {(r["model"], r["condition"], r["event_id"]): r for r in rows}
    def make_map(model, cond):
        return {e: by_key[(model, cond, e)] for e in part["cal13"] + part["cal26"] + part["test34"]}
    truth = json.load(io.open(os.path.join(E56, "summary_36.json"), encoding="utf-8"))
    truth_by_id = {c["fit_id"]: c for c in truth}

    print("=== VALIDATION (36 frozen cells) ===")
    fails = 0
    for model in ["qwen35", "ministral3", "gemma3_4b"]:
        for cond in ["N", "A_exact"]:
            evmap = make_map(model, cond)
            for cs in [13, 26]:
                for method in ["SourceFit", "F1S1", "GroupVote"]:
                    fit_id = f"{model}|{cond}|cal{cs}|{method}"
                    got = run_cell(evmap, part, aliases, model, cond, cs, method)
                    t = truth_by_id[fit_id]
                    ok = (abs(got["R0_em"] - t["R0_em"]) < 1e-9
                          and abs(got["R2_expected_em"] - t["R2_expected_em"]) < 1e-9
                          and (method == "GroupVote" or
                               (got["iterations"] == t["iterations"]
                                and got["initial_rows_used"] == t["initial_rows_used"]
                                and got["all_rows_fallback"] == t["all_rows_fallback"])))
                    if not ok:
                        fails += 1
                        print("FAIL", fit_id, got, t)
    print(f"validation failures: {fails}/36")
    if fails:
        sys.exit(1)

    print("\n=== DEDUP->REFIT (A_exact, copies 4->1) ===")
    out = []
    for model in ["qwen35", "ministral3", "gemma3_4b"]:
        evmap = make_map(model, "A_exact")
        for cs in [13, 26]:
            for method in ["SourceFit", "F1S1"]:
                res = run_cell(evmap, part, aliases, model, "A_exact", cs, method, dedup=True)
                base = truth_by_id[f"{model}|A_exact|cal{cs}|{method}"]
                clean = truth_by_id[f"{model}|N|cal{cs}|{method}"]
                row = {"fit_id": f"{model}|A_exact_dedup|cal{cs}|{method}",
                       "R0_em_dedup": res["R0_em"], "R2_em_dedup": res["R2_expected_em"],
                       "R0_em_before": base["R0_em"], "clean_R0": clean["R0_em"],
                       "iterations": res["iterations"],
                       "copy_terminal_weight": res["terminal_weights"][0]}
                out.append(row)
                print(f"{model:11s} cal{cs:2d} {method:10s}: clean R0={clean['R0_em']:.4f}"
                      f"  attacked R0={base['R0_em']:.4f}  dedup R0={res['R0_em']:.4f}"
                      f" (R2 {res['R2_expected_em']:.4f})")
    io.open(os.path.join(BASE, "dedup_replay_run.json"), "w", encoding="utf-8").write(json.dumps(out, indent=1))
    print("\nsaved dedup_replay_run.json")

if __name__ == "__main__":
    main()
