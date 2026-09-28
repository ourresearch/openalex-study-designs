"""Certification: per class, precision / one-sided 95% lower bound / recall on all 5,069 judged works, at fixed thresholds.

  python harness/certify.py                          # the shipped tagger, its thresholds, the Opus 5 labels
  python harness/certify.py --judge opus-5.5         # the same answers against the Opus 5.5 re-judge
  python harness/certify.py --thresholds dev         # re-pick each threshold on the dev split instead
  python harness/certify.py --configs h15_nrt,g_mix  # any config in configs/ (thresholds picked on dev)

The shipped tagger (r2_gate4) is scored from benchmarks/data/dev/dev_jev_outputs.jsonl.gz through
tagger/study_design.py itself, so this is the production derivation. Needs no key and no text.
"""
import argparse, gzip, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import score as S
from run import load_eval, JUDGES, DEV
from compare import preds_for
from tagger import study_design as sd

def shipped_preds():
    """Scores recomputed from Jev's cached answers and the stored gate answers, checked against the stored scores."""
    out = {}
    for l in gzip.open(f'{DEV}/dev_jev_outputs.jsonl.gz', 'rt'):
        r = json.loads(l); s = sd.derive_from_gates(r['answers'], r['gates'])
        assert s == r['scores'], f"stored scores differ from tagger/study_design.py for {r['work_id']}"
        out[r['work_id']] = s
    return out

def table(name, preds, judged, thresholds, note):
    ids = [i for i in judged if i in preds]
    print(f"\n{name}: {note}, pooled dev + test (n={len(ids)})")
    print(f"| Class | bar | t | positives | FP | precision | one-sided 95% lower | recall |")
    print(f"|---|---|---|---|---|---|---|---|")
    for c in S.CLASSES:
        t = thresholds.get(c)
        if t is None: print(f"| {c} | {S.BARS[c]:.2f} | — | | | | | |"); continue
        pos = tp = nt = 0
        for i in ids:
            tr = c in S.truth_sets(judged[i]['design'], judged[i].get('is_rct')); s = preds[i].get(c, 0)
            nt += tr; pos += s >= t; tp += (s >= t) and tr
        wl = S.wilson_lower(tp, pos)
        flag = '' if wl >= S.BARS[c] else (' (point ok, bound short)' if pos and tp / pos >= S.BARS[c] else ' <-- BELOW BAR')
        print(f"| {c} | {S.BARS[c]:.2f} | {t:.2f} | {pos} | {pos - tp} | {tp / pos if pos else 0:.4f} | {wl:.4f}{flag} | {tp / nt if nt else 0:.3f} |")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--configs', default='r2_gate4')
    ap.add_argument('--judge', default='opus-5', choices=sorted(JUDGES))
    ap.add_argument('--thresholds', default='auto', choices=['auto', 'shipped', 'dev'],
                    help="shipped = tagger/study_design.THRESHOLDS; dev = lowest on the dev split meeting the bar; auto = shipped for r2_gate4, else dev")
    a = ap.parse_args()
    works, judged = load_eval(a.judge)
    dev = [i for i in judged if judged[i]['split'] == 'dev']
    print(f"judge: {a.judge}; {len(judged)} judged works ({len(dev)} dev)")
    for name in a.configs.split(','):
        preds = shipped_preds() if name == sd.CONFIG_NAME else preds_for(name, works, list(judged))[1]
        if not preds: print(f"\n{name}: no cached answers"); continue
        mode = a.thresholds if a.thresholds != 'auto' else ('shipped' if name == sd.CONFIG_NAME else 'dev')
        if mode == 'shipped':
            th, note = dict(sd.THRESHOLDS), 'shipped thresholds'
        else:
            res = S.score_run({i: preds[i] for i in dev if i in preds}, judged)
            th = {c: (r['at_bar']['t'] if r['at_bar'] else None) for c, r in res['classes'].items()}
            note = 'thresholds fixed on dev'
        table(name, preds, judged, th, note)

if __name__ == '__main__': main()
