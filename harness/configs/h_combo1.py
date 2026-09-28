"""Combo 1: stricter rule (h10) + code-extracted signals (h5) + sink options (h3) + conjunctive RCT Nouls (h2).
"""
import configs.v1 as v1, configs.h5_features as h5, configs.h3_sinks as h3, configs.h2_conj as h2, configs.h10_rule as h10
NAME = 'h_combo1'
NOTES = 'h10 rule + h5 signals + h3 sinks + h2 conjunctive Nouls'

RULE = h10.RULE + (" The `signals` field lists facts extracted by code; a registration number or the word randomized is evidence, "
                   "not proof, that this paper is the trial's primary report.")

def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": h3.DESIGN}}
    for k, v in h2.NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q

def state_for(w):
    s = {"rule_design": RULE, "signals": h5.signals(w), "title": w.get("title") or ""}
    if w.get("venue"): s["venue"] = w["venue"]
    if w.get("abstract"): s["abstract"] = w["abstract"][:6000]
    return s

def derive(a, w):
    d = h2.derive(a, w)
    pr = a["design"]["probabilities"]
    d["rct"] = d["rct"] * (1 - pr.get("secondary_analysis", 0) - pr.get("trial_followup", 0))
    return d
