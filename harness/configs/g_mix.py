"""g_mix: h15_nrt with GEPA run 1's rewritten observational / case_report / other_primary_research option texts, keeping
v1's short is_rct Noul (GEPA's long Noul cost 16 points of RCT recall, the h16 lesson again)."""
import configs.v1 as v1, configs.h15_nrt as h15, configs.g_run1 as g
NAME = 'g_mix'
NOTES = 'h15 + GEPA texts for observational/case_report/other_primary_research; v1 is_rct Noul'
RULE = h15.RULE
DESIGN = dict(h15.DESIGN)
for k in ('observational', 'case_report', 'other_primary_research'): DESIGN[k] = g.DESIGN[k]
def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": DESIGN}}
    for k, v in v1.NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q
def state_for(w):
    s = {"rule_design": RULE, "title": w.get("title") or ""}
    if w.get("venue"): s["venue"] = w["venue"]
    if w.get("abstract"): s["abstract"] = w["abstract"][:6000]
    return s
def derive(a, w): return v1.derive(a, w)
