"""Scoring for the improvement loop. A config yields, per work, a score in [0,1] per shipped class.
Truth = Opus judge design (12 classes) mapped onto the shipped classes (parents implied).
Per class we report, at the precision bar: the lowest threshold whose Wilson lower bound clears the bar,
precision and recall there, and the count of positives. Recall is pool-relative (the eval oversamples hard cases).
"""
import math, collections

BARS = {'rct': 0.99, 'meta_analysis': 0.98, 'systematic_review': 0.97, 'protocol': 0.97,
        'clinical_trial': 0.95, 'case_report': 0.95, 'observational': 0.95, 'other_primary_research': 0.95}
CLASSES = list(BARS)

# judge 12-class design -> shipped classes (parents implied)
TRUTH = {
    'rct': {'rct', 'clinical_trial'},
    'nonrandomized_trial': {'clinical_trial'},
    'observational': {'observational'},
    'case_report': {'case_report'},
    'systematic_review': {'systematic_review'},
    'meta_analysis': {'meta_analysis', 'systematic_review'},
    'protocol': {'protocol'},
    'other_primary_research': {'other_primary_research'},
    'narrative_review': set(), 'editorial_letter': set(), 'guideline': set(), 'unknown': set(), 'secondary_analysis': set(),
}

def truth_sets(judge_design, is_rct=None):
    """is_rct: the judge's explicit flag. The judge answers design=rct for secondary analyses of RCTs ("underlying design")
    but is_rct=False ("this paper is not the trial"). The shipped RCT value means the paper reports the trial, so truth for
    rct (and the RCT half of clinical_trial) follows is_rct when it is available."""
    t = set(TRUTH.get(judge_design, set()))
    if is_rct is not None and judge_design == 'rct':
        if not is_rct: t.discard('rct'); t.discard('clinical_trial')
    return t

def wilson_lower(k, n, z=1.645):  # one-sided 95% lower bound (a bar means "at least 0.99"; two-sided 95% was unreachable at n~350 with zero FPs)
    if n == 0: return 0.0
    p = k / n; d = 1 + z * z / n
    c = p + z * z / (2 * n); r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - r) / d

def sweep(scores, truths, bar, grid=None):
    """scores: list[float]; truths: list[bool]. Returns dict for the best (lowest) threshold meeting the bar on the
    Wilson lower bound, plus the full curve at a coarse grid."""
    grid = grid or [i / 100 for i in range(30, 100)] + [0.995, 0.999]
    n_true = sum(truths)
    curve = []
    best = None
    for t in grid:
        pos = [(s >= t) for s in scores]
        n_pos = sum(pos); tp = sum(1 for p_, tr in zip(pos, truths) if p_ and tr)
        prec = tp / n_pos if n_pos else 0.0; rec = tp / n_true if n_true else 0.0
        wl = wilson_lower(tp, n_pos) if n_pos else 0.0
        row = {'t': t, 'n_pos': n_pos, 'tp': tp, 'precision': prec, 'wilson_lower': wl, 'recall': rec}
        curve.append(row)
        if best is None and n_pos >= 20 and wl >= bar:
            best = row
    # also report precision/recall at the highest-recall point with plain precision >= bar (no CI), as a softer read
    soft = next((r for r in curve if r['n_pos'] >= 20 and r['precision'] >= bar), None)
    return {'n_true': n_true, 'at_bar': best, 'soft': soft, 'curve': curve}

def score_run(preds, judged, split=None):
    """preds: {work_id: {class: score}}; judged: {work_id: judge_record with 'design'}; returns per-class results."""
    ids = [i for i in preds if i in judged and (split is None or judged[i].get('split') == split)]
    out = {'n': len(ids), 'classes': {}}
    for c in CLASSES:
        scores = [preds[i].get(c, 0.0) for i in ids]
        truths = [c in truth_sets(judged[i]['design'], judged[i].get('is_rct')) for i in ids]
        out['classes'][c] = sweep(scores, truths, BARS[c])
    return out

def fmt(res):
    lines = [f"n={res['n']}", f"{'class':24s} {'bar':>5s} {'n_true':>6s} | {'t*':>5s} {'n_pos':>5s} {'prec':>6s} {'wilson':>6s} {'recall':>6s} | soft t/prec/recall"]
    for c, r in res['classes'].items():
        b = r['at_bar']; s = r['soft']
        bs = f"{b['t']:5.2f} {b['n_pos']:5d} {b['precision']:6.3f} {b['wilson_lower']:6.3f} {b['recall']:6.3f}" if b else f"{'-':>5s} {'-':>5s} {'-':>6s} {'-':>6s} {'-':>6s}"
        ss = f"{s['t']:.2f}/{s['precision']:.3f}/{s['recall']:.3f}" if s else '-'
        lines.append(f"{c:24s} {BARS[c]:5.2f} {r['n_true']:6d} | {bs} | {ss}")
    return "\n".join(lines)
