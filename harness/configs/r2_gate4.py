"""r2_gate4 (offline), the configuration that ships: r2_shortnoul's cached answers with the three code gates on rct
(stated randomisation, simulation title, secondary-analysis title). tagger/study_design.py is this config."""
import textsig
from cache import answers
MEMBER = 'r2_shortnoul'
NAME = 'r2_gate4'
NOTES = 'r2_gate2 + secondary-analysis title gate (narrow: secondary|post-hoc|subgroup|ancillary analysis; safety|data|analysis from a randomized; in the NAME trial)'
def questions(): return {}
def state_for(w): return {}
def derive(a, w):
    mod, d = answers(MEMBER)
    if w['work_id'] not in d: return {}
    out = mod.derive(d[w['work_id']], w)
    if not textsig.stated_random(w) or textsig.simulation_title(w) or textsig.secondary_title(w): out['rct'] = 0.0
    return out
