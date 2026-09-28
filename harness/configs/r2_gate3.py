"""r2_gate3 (offline): r2_gate2 + rct zeroed when the title reads as a secondary analysis (textsig.secondary_title).
Scored with the first draft of that regex, which also matched "results from a randomized ..." and removed four
judged primary reports; the regex was then narrowed in textsig.py (r2_gate4), so this file now scores like r2_gate4."""
import textsig
from cache import answers
MEMBER = 'r2_shortnoul'
NAME = 'r2_gate3'
NOTES = 'r2_gate2 + rct zeroed when the title reads as a secondary/post-hoc/subgroup analysis or "data from a randomized trial"'
def questions(): return {}
def state_for(w): return {}
def derive(a, w):
    mod, d = answers(MEMBER)
    if w['work_id'] not in d: return {}
    out = mod.derive(d[w['work_id']], w)
    if not textsig.stated_random(w) or textsig.simulation_title(w) or textsig.secondary_title(w): out['rct'] = 0.0
    return out
