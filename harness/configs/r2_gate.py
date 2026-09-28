"""r2_gate (offline): r2_shortnoul's cached answers, with rct gated on the text explicitly stating randomisation
(textsig.stated_random) and clinical_trial unchanged. Rubric v2 says an RCT must state random allocation."""
import textsig
from cache import answers
MEMBER = 'r2_shortnoul'
NAME = 'r2_gate'
NOTES = 'r2_shortnoul + hard gate: rct only if the text states randomisation (regex, 10 languages)'
def questions(): return {}
def state_for(w): return {}
def derive(a, w):
    mod, d = answers(MEMBER)
    if w['work_id'] not in d: return {}
    out = mod.derive(d[w['work_id']], w)
    if not textsig.stated_random(w): out['rct'] = 0.0
    return out
