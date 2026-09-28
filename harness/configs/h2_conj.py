"""H2: conjunctive Nouls for RCT. Three independent yes/no facts (randomised allocation, primary report of results,
human participants) must all hold; rct score = min of the three Nouls. Choice and the other classes as v1.
"""
import configs.v1 as v1
NAME = 'h2_conj'
NOTES = 'v1 + Nouls randomized_allocation + primary_report; rct = min(is_rct, randomized, primary_report) gated on human'

NOULS = dict(v1.NOULS)
NOULS.update({
    "randomized_allocation": "In the study this paper reports, were participants (or clusters) randomly allocated to interventions?",
    "primary_report": "Is this paper the primary report of the study's results, rather than a protocol, secondary or post-hoc analysis, sub-study, follow-up, or pooled analysis?",
})
RULE = v1.RULE

def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": v1.DESIGN}}
    for k, v in NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q

def state_for(w): return v1.state_for(w)

def derive(a, w):
    d = v1.derive(a, w)
    if a["human_subjects"]["noul"] < 0.5: d["rct"] = 0.0
    else: d["rct"] = min(a["is_rct"]["noul"], a["randomized_allocation"]["noul"], a["primary_report"]["noul"])
    return d
