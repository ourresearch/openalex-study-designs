"""r2_gate2 (offline): r2_gate + rct zeroed when the title says simulation / manikin / phantom / cadaver / in vitro
(textsig.simulation_title). No new Jev calls."""
import textsig
from cache import answers
MEMBER = 'r2_shortnoul'
NAME = 'r2_gate2'
NOTES = 'r2_gate + rct zeroed when the title says simulation/manikin/phantom/cadaver/in vitro'
def questions(): return {}
def state_for(w): return {}
def derive(a, w):
    mod, d = answers(MEMBER)
    if w['work_id'] not in d: return {}
    out = mod.derive(d[w['work_id']], w)
    if not textsig.stated_random(w) or textsig.simulation_title(w): out['rct'] = 0.0
    return out
