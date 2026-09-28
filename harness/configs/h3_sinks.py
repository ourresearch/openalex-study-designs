"""H3: richer sink options for the known RCT / trial confusers. Adds Choice options that pull secondary analyses,
sub-studies, follow-ups and economic/modelling papers out of the trial classes. Those sinks map to nothing shipped.
Questions otherwise as v1; derive as v1.
"""
import configs.v1 as v1
NAME = 'h3_sinks'
NOTES = 'v1 + sink options: secondary_analysis, trial_followup, economic_modelling'

DESIGN = dict(v1.DESIGN)
DESIGN.update({
    "secondary_analysis": "secondary, post-hoc, pooled or sub-study analysis of data from an earlier trial or cohort (not its primary report)",
    "trial_followup": "long-term follow-up or extension report of a previously published trial",
    "economic_modelling": "cost-effectiveness, decision-model, or simulation study built on trial or literature data",
})
RULE = v1.RULE

def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": DESIGN}}
    for k, v in v1.NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q

def state_for(w):
    s = {"rule_design": RULE, "title": w.get("title") or ""}
    if w.get("venue"): s["venue"] = w["venue"]
    if w.get("abstract"): s["abstract"] = w["abstract"][:6000]
    return s

def derive(a, w):
    d = v1.derive(a, w)
    pr = a["design"]["probabilities"]
    sink = pr.get("secondary_analysis", 0) + pr.get("trial_followup", 0)
    # the Noul-based rct score does not see the Choice; damp it by the sink mass so a confident secondary analysis cannot ship as RCT
    d["rct"] = d["rct"] * (1 - sink)
    return d
