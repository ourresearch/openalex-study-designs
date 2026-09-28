"""r2_base: the tagger request built straight from rubric_v2 (the schema definitions the judge now uses).
secondary_analysis is an option (sink); derive as v1 plus damping rct / clinical_trial by the sink mass."""
import configs.v1 as v1
import rubric_v2 as R
NAME = 'r2_base'
NOTES = 'rubric v2 texts verbatim (rule, 13 options incl. secondary_analysis sink, 2 Nouls)'
RULE = R.RULE; DESIGN = dict(R.DESIGN); NOULS = dict(R.NOULS)
def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": DESIGN}}
    for k, v in NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q
def state_for(w):
    s = {"rule_design": RULE, "title": w.get("title") or ""}
    if w.get("venue"): s["venue"] = w["venue"]
    if w.get("abstract"): s["abstract"] = w["abstract"][:6000]
    return s
def derive(a, w):
    d = v1.derive(a, w); sec = a["design"]["probabilities"].get("secondary_analysis", 0)
    d["rct"] = d["rct"] * (1 - sec); d["clinical_trial"] = d["clinical_trial"] * (1 - sec)
    return d
