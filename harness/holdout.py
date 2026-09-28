"""Honest protocol: pick each class's threshold on dev (lowest t whose one-sided 95% Wilson lower bound clears the bar),
then report precision / recall / Wilson on test at that fixed threshold. No re-selection on test.
Run: python harness/holdout.py --configs v1,h15_nrt,e_div3 [--judge opus-5.5]
"""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import score as S
from run import load_eval, JUDGES
from compare import preds_for

def at_t(preds, judged, ids, cls, t):
    pos = tp = 0; n_true = 0
    for i in ids:
        if i not in preds: continue
        tr = cls in S.truth_sets(judged[i]['design'], judged[i].get('is_rct')); s = preds[i].get(cls, 0.0)
        n_true += tr; pos += s >= t; tp += (s >= t) and tr
    return {'n_pos': pos, 'tp': tp, 'fp': pos - tp, 'precision': tp / pos if pos else 0, 'wilson': S.wilson_lower(tp, pos), 'recall': tp / n_true if n_true else 0, 'n_true': n_true}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--configs', required=True); ap.add_argument('--judge', default=None, choices=sorted(JUDGES)); a = ap.parse_args()
    works, judged = load_eval(a.judge)
    dev = [i for i in judged if judged[i]['split'] == 'dev']; test = [i for i in judged if judged[i]['split'] == 'test']
    for name in a.configs.split(','):
        mod, preds = preds_for(name, works, dev + test)
        res = S.score_run({i: preds[i] for i in dev if i in preds}, judged)
        print(f"\n{name}: threshold from dev, evaluated on test (n_test={len(test)})")
        print(f"  {'class':24s} {'bar':>5s} {'t(dev)':>6s} | {'test n_pos':>10s} {'fp':>3s} {'prec':>6s} {'wilson':>6s} {'recall':>6s}")
        for c in S.CLASSES:
            b = res['classes'][c]['at_bar']
            if not b: print(f"  {c:24s} {S.BARS[c]:5.2f} {'—':>6s}"); continue
            r = at_t(preds, judged, test, c, b['t'])
            flag = '' if r['precision'] >= S.BARS[c] else '  <-- below bar on test'
            print(f"  {c:24s} {S.BARS[c]:5.2f} {b['t']:6.2f} | {r['n_pos']:10d} {r['fp']:3d} {r['precision']:6.3f} {r['wilson']:6.3f} {r['recall']:6.3f}{flag}")

if __name__ == '__main__': main()
