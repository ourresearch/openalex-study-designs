"""Improvement-loop harness. One config = one Python module in configs/ exposing NAME, NOTES, questions(), state_for(w),
derive(answers, w). Runs Jev once per work on the development set (answers cached per config hash, never overwritten),
scores against the judge, prints the per-class table and appends a row to runs/ledger_local.jsonl.

  python harness/run.py --config r2_gate4                         # scored from the shipped cache: no key, no text
  python harness/run.py --config my_idea --works works.jsonl      # a new config: calls Jev (JEV_API_KEY)

Offline configs (questions() == {}: the gates and ensembles) derive from other configs' caches and never call Jev.
A new config needs the text: build works.jsonl with `python -m tagger.fetch_works --ids benchmarks/data/dev/dev_set.jsonl.gz`.
Cache: harness/runs/<name>__<hash>__<model>.jsonl (one Jev answer per work). Re-running an unchanged config is free.
"""
import argparse, gzip, importlib, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
import score as S
import cache
from cache import config_hash  # noqa: F401  (kept importable from run, as before)

DEV = f'{ROOT}/benchmarks/data/dev'
JUDGES = {'opus-5': 'opus_5', 'opus-5.5': 'opus_5_5'}

def opn(path):
    return gzip.open(path, 'rt') if path.endswith('.gz') else open(path)

def load_eval(judge=None, works_path=None):
    """works: {work_id: {work_id, pool, split, gates (+ title, venue, abstract if works_path)}};
    judged: {work_id: {design, is_rct, human_subjects, split, pool}} under the chosen judge (default opus-5, or $JUDGE)."""
    judge = judge or os.environ.get('JUDGE', 'opus-5'); sfx = JUDGES[judge]
    works, judged = {}, {}
    for l in opn(f'{DEV}/dev_set.jsonl.gz'):
        r = json.loads(l)
        works[r['work_id']] = {'work_id': r['work_id'], 'pool': r['pool'], 'split': r['split']}
        if r.get(f'label_{sfx}'):
            judged[r['work_id']] = {'design': r[f'label_{sfx}'], 'is_rct': r[f'is_rct_{sfx}'],
                                    'human_subjects': r[f'human_subjects_{sfx}'], 'split': r['split'], 'pool': r['pool']}
    for l in opn(f'{DEV}/dev_jev_outputs.jsonl.gz'):
        r = json.loads(l)
        if r['work_id'] in works: works[r['work_id']]['gates'] = r['gates']
    if works_path:
        for l in opn(works_path):
            r = json.loads(l)
            if r.get('work_id') in works and 'error' not in r:
                works[r['work_id']].update({k: r.get(k) for k in ('title', 'venue', 'abstract')})
    return works, judged

def label(mod, works, path, rps, concurrency, model):
    """Jev answers for works, reusing the cache at path and appending new answers to it."""
    done = cache.read(path) if os.path.exists(path) else {}
    todo = [w for w in works if w['work_id'] not in done]
    print(f"jev: {len(done)} cached, {len(todo)} to label", file=sys.stderr, flush=True)
    if not todo: return done
    missing = [w['work_id'] for w in todo if 'title' not in w]
    if missing:
        sys.exit(f"{len(missing)} works have no text; pass --works (built by python -m tagger.fetch_works)")
    from tagger.study_design import JevClient
    c = JevClient(concurrency=concurrency, rps=rps, model=model); Q = mod.questions(); n = [0, 0]; t0 = time.perf_counter()
    lock = threading.Lock()
    with open(path, 'a') as out:
        def one(w):
            r = c.decide(mod.state_for(w), Q)
            with lock:
                if not r['ok']:
                    n[1] += 1; out.write(json.dumps({'work_id': w['work_id'], 'error': r.get('error'), 'status': r.get('status')}) + '\n'); return
                done[w['work_id']] = r['answers']; n[0] += 1
                out.write(json.dumps({'work_id': w['work_id'], 'answers': r['answers']}) + '\n')
                if sum(n) % 500 == 0: out.flush(); print(f"  {sum(n)}/{len(todo)} err={n[1]}", file=sys.stderr, flush=True)
        with ThreadPoolExecutor(concurrency) as ex:
            for f in [ex.submit(one, w) for w in todo]: f.result()
    print(f"jev done ok={n[0]} err={n[1]} tok/work={c.total_tokens / max(1, n[0]):.0f} {time.perf_counter() - t0:.0f}s", file=sys.stderr, flush=True)
    return done

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--config', required=True); ap.add_argument('--split', default='dev')
    ap.add_argument('--judge', default=None, choices=sorted(JUDGES)); ap.add_argument('--works', help='JSONL with title/venue/abstract (tagger.fetch_works)')
    ap.add_argument('--limit', type=int); ap.add_argument('--rps', type=float, default=20); ap.add_argument('--concurrency', type=int, default=16)
    ap.add_argument('--model', default='jev-1.13.0'); ap.add_argument('--no-ledger', action='store_true'); ap.add_argument('--curve', action='store_true')
    a = ap.parse_args()
    mod = importlib.import_module(f'configs.{a.config}'); h = config_hash(mod)
    works, judged = load_eval(a.judge, a.works)
    ids = [i for i in works if a.split == 'all' or works[i]['split'] == a.split]
    if a.limit: ids = ids[:a.limit]
    print(f"config {mod.NAME} [{h}] split={a.split} works={len(ids)} judged={sum(i in judged for i in ids)}", file=sys.stderr, flush=True)
    if mod.questions():
        shipped = f'{HERE}/runs/{mod.NAME}__{a.model}.jsonl.gz'; live = cache.live_path(mod, a.model)
        if not os.path.exists(live) and os.path.exists(shipped):
            done = cache.read(shipped)
            print(f"jev: using the shipped answers {os.path.relpath(shipped, ROOT)}", file=sys.stderr, flush=True)
        else:
            done = label(mod, [works[i] for i in ids], live, a.rps, a.concurrency, a.model)
        preds = {i: mod.derive(done[i], works[i]) for i in ids if i in done}
    else:  # offline config: derives from other configs' caches
        preds = {i: mod.derive({}, works[i]) for i in ids}
        preds = {i: p for i, p in preds.items() if p}
    result = S.score_run(preds, judged, split=None if a.split == 'all' else a.split)
    print(S.fmt(result))
    if a.curve:
        for c, r in result['classes'].items():
            print(c, [(x['t'], x['n_pos'], round(x['precision'], 3), round(x['recall'], 3)) for x in r['curve'] if x['t'] in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99)])
    if not a.no_ledger:
        row = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), 'config': mod.NAME, 'hash': h, 'notes': mod.NOTES, 'model': a.model, 'split': a.split,
               'judge': a.judge or os.environ.get('JUDGE', 'opus-5'), 'n': result['n'],
               'classes': {c: ({'t': r['at_bar']['t'], 'precision': round(r['at_bar']['precision'], 4), 'recall': round(r['at_bar']['recall'], 4), 'n_pos': r['at_bar']['n_pos']} if r['at_bar'] else None)
                           for c, r in result['classes'].items()}}
        os.makedirs(f'{HERE}/runs', exist_ok=True)
        with open(f'{HERE}/runs/ledger_local.jsonl', 'a') as f: f.write(json.dumps(row) + '\n')

if __name__ == '__main__': main()
