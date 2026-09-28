"""Cached Jev answers per config, so every table here can be rescored without a Jev key.

runs/<name>__<model>.jsonl.gz ships with the repo: the answers Jev gave to that config on the 5,069 development-set
works (probabilities and yes/no scores only). A live run (run.py) writes runs/<name>__<hash>__<model>.jsonl, keyed by a
hash of the config's source, so an edited config is never scored on stale answers; a live cache wins when present.
"""
import gzip, hashlib, importlib, inspect, json, os
HERE = os.path.dirname(os.path.abspath(__file__))

def config_hash(mod):
    return hashlib.sha1(inspect.getsource(mod).encode()).hexdigest()[:10]

def live_path(mod, model='jev-1.13.0'):
    return f'{HERE}/runs/{mod.NAME}__{config_hash(mod)}__{model}.jsonl'

def path_for(mod, model='jev-1.13.0'):
    for p in (live_path(mod, model), f'{HERE}/runs/{mod.NAME}__{model}.jsonl.gz'):
        if os.path.exists(p): return p
    return None

def read(path):
    """{work_id: answers} from a cache file (.jsonl or .jsonl.gz); error rows are skipped."""
    op = gzip.open if path.endswith('.gz') else open
    d = {}
    with op(path, 'rt') as f:
        for l in f:
            r = json.loads(l)
            if 'answers' in r: d[r['work_id']] = r['answers']
    return d

_memo = {}
def answers(name, model='jev-1.13.0'):
    """(config module, {work_id: answers}) for a config; answers is {} if nothing is cached."""
    if (name, model) not in _memo:
        mod = importlib.import_module(f'configs.{name}'); p = path_for(mod, model)
        _memo[(name, model)] = (mod, read(p) if p else {})
    return _memo[(name, model)]
