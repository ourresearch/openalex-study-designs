"""Combo 2: h14 sharpened option texts + h5 code-extracted signals + primary_report Noul (from h2) gating rct and
clinical_trial + secondary_analysis sink option (from h3). Rule = h14's (v1 + commentary line), not h10's stricter one.
"""
import configs.v1 as v1, configs.h5_features as h5, configs.h14_scope as h14
NAME = 'h_combo2'
NOTES = 'h14 texts + h5 signals + primary_report gate on rct/clinical_trial + secondary_analysis sink'

RULE = h14.RULE + (" The `signals` field lists facts extracted by code from the text; a registration number or the word randomized "
                   "is evidence, not proof, that this paper is the trial's primary report.")
DESIGN = dict(h14.DESIGN)
DESIGN["secondary_analysis"] = "secondary, post-hoc, subgroup, pooled or sub-study analysis of data from an earlier trial or cohort (not its primary report)"
NOULS = dict(v1.NOULS)
NOULS["primary_report"] = ("Is this paper the primary report of the study's results (or a follow-up/updated results report of the same trial), "
                           "rather than a protocol, a secondary, post-hoc, subgroup or exploratory analysis, or a pooled analysis?")

def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": DESIGN}}
    for k, v in NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q

def state_for(w):
    s = {"rule_design": RULE, "signals": h5.signals(w), "title": w.get("title") or ""}
    if w.get("venue"): s["venue"] = w["venue"]
    if w.get("abstract"): s["abstract"] = w["abstract"][:6000]
    return s

def derive(a, w):
    d = v1.derive(a, w)
    pr = a["design"]["probabilities"]; prim = a["primary_report"]["noul"]; sec = pr.get("secondary_analysis", 0)
    d["rct"] = min(d["rct"], prim) * (1 - sec)
    d["clinical_trial"] = min(d["clinical_trial"], prim) * (1 - sec)
    return d
