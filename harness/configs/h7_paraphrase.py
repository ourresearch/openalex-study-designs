"""H7: self-consistency inside one request. Three paraphrases of the RCT question; rct = min of the three (and the
human gate). The eval showed 2-3% paraphrase flips on shaky works; requiring agreement should trade recall for precision.
Choice and other classes as v1.
"""
import configs.v1 as v1
NAME = 'h7_paraphrase'
NOTES = 'v1 + two paraphrased is_rct Nouls; rct = min over the three phrasings'

NOULS = dict(v1.NOULS)
NOULS.update({
    "is_rct_b": "Does this paper report the results of a trial in which participants were assigned to groups by chance (randomization)?",
    "is_rct_c": "Would a systematic reviewer include this paper as a randomized controlled trial (primary results, random allocation to interventions)?",
})

def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": v1.DESIGN}}
    for k, v in NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q

def state_for(w): return v1.state_for(w)

def derive(a, w):
    d = v1.derive(a, w)
    if a["human_subjects"]["noul"] < 0.5: d["rct"] = 0.0
    else: d["rct"] = min(a["is_rct"]["noul"], a["is_rct_b"]["noul"], a["is_rct_c"]["noul"])
    return d
