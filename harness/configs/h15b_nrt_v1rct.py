"""H15b: h15 but with v1's rule text (no commentary line) and v1's rct option text. Attribution pair with h15:
if RCT recall comes back here, h14's rule line / rct wording is what shifted the is_rct Noul.
"""
import configs.v1 as v1, configs.h15_nrt as h15
NAME = 'h15b_nrt_v1rct'
NOTES = 'h15 with v1 rule + v1 rct option text (attribution of the RCT recall drop in h14)'

RULE = v1.RULE
DESIGN = dict(h15.DESIGN)
DESIGN["rct"] = v1.DESIGN["rct"]

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
