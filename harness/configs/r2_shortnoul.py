"""r2_shortnoul: rubric v2 texts with v1's original one-clause is_rct Noul (long Nouls have cost recall three times)."""
import configs.v1 as v1, configs.r2_base as b
NAME = 'r2_shortnoul'
NOTES = 'rubric v2 options + v1 short is_rct Noul'
RULE = b.RULE; DESIGN = dict(b.DESIGN); NOULS = dict(v1.NOULS)
def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": DESIGN}}
    for k, v in NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q
def state_for(w): return b.state_for(w)
def derive(a, w): return b.derive(a, w)
