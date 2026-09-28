"""Ensemble (offline): mean of per-class scores across several cached configs. No new Jev calls.
In production this is a two-stage shape: one request for everyone, extra prompts only on candidates.
"""
import math
from cache import answers
MEMBERS = ['h4_atomic', 'h_combo2', 'h15_nrt']
NAME = 'e_div3'
NOTES = 'offline mean of ' + '+'.join(MEMBERS)

def questions(): return {}
def state_for(w): return {}
def derive(a, w):
    outs = []
    for m in MEMBERS:
        mod, d = answers(m)
        if w['work_id'] in d: outs.append(mod.derive(d[w['work_id']], w))
    if not outs: return {}
    keys = outs[0].keys()
    return {k: math.fsum(o.get(k, 0) for o in outs) / len(outs) for k in keys}  # fsum: identical on every Python version
