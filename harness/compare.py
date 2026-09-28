"""Score every cached config on the same judged works and print one comparison table.
Run: python harness/compare.py [--split dev|test|all] [--configs v1,h2_conj,...] [--pool rct_candidates] [--judge opus-5.5]
Cells: recall at the precision bar (Wilson lower bound >= bar); '—' = no threshold clears the bar with >= 20 positives.
"""
import argparse, glob, importlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import score as S
import cache
from run import load_eval, JUDGES

def preds_for(name, works, ids, model='jev-1.13.0'):
    """(config module, {work_id: {class: score}}), or (module, None) when no answers are cached for that config."""
    mod = importlib.import_module(f'configs.{name}')
    if not mod.questions():  # offline config: derives from its members' caches
        out = {i: mod.derive({}, works[i]) for i in ids}
        out = {i: p for i, p in out.items() if p}
        return mod, (out or None)
    _, done = cache.answers(name, model)
    if not done: return mod, None
    return mod, {i: mod.derive(done[i], works[i]) for i in ids if i in done}

def all_configs():
    names = set(os.path.basename(p)[:-3] for p in glob.glob(f'{HERE}/configs/*.py')) - {'__init__'}
    return sorted(names)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--split', default='dev'); ap.add_argument('--configs')
    ap.add_argument('--pool'); ap.add_argument('--model', default='jev-1.13.0'); ap.add_argument('--soft', action='store_true')
    ap.add_argument('--judge', default=None, choices=sorted(JUDGES)); a = ap.parse_args()
    works, judged = load_eval(a.judge)
    ids = [i for i in judged if (a.split == 'all' or judged[i]['split'] == a.split) and (not a.pool or judged[i]['pool'] == a.pool)]
    names = a.configs.split(',') if a.configs else all_configs()
    print(f"split={a.split} judged={len(ids)} judge={a.judge or os.environ.get('JUDGE', 'opus-5')}" + (f" pool={a.pool}" if a.pool else ""))
    hdr = f"{'config':16s} " + " ".join(f"{c[:12]:>13s}" for c in S.CLASSES)
    print(hdr); print("-" * len(hdr))
    preds = None
    for name in names:
        mod, preds = preds_for(name, works, ids, a.model)
        if preds is None: print(f"{name:16s} (no cache)"); continue
        res = S.score_run(preds, judged)
        cells = []
        for c in S.CLASSES:
            r = res['classes'][c]; b = r['soft'] if a.soft else r['at_bar']
            cells.append(f"{b['recall']:.3f}@{b['t']:.2f}" if b else "      —      ")
        print(f"{name:16s} " + " ".join(f"{x:>13s}" for x in cells))
    if preds: print("\nn_true per class:", {c: S.score_run(preds, judged)['classes'][c]['n_true'] for c in S.CLASSES})

if __name__ == '__main__': main()
