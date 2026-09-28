"""H15: h14 + the non-randomized-trial boundary fixed (investigators prospectively assign the intervention; retrospective
series of treated patients are observational). Keeps h14's rule line and rct text. Attribution pair with h15b.
"""
import configs.v1 as v1, configs.h14_scope as h14
NAME = 'h15_nrt'
NOTES = 'h14 + nrt = prospective investigator-assigned intervention; retrospective treated series -> observational'

RULE = h14.RULE
DESIGN = dict(h14.DESIGN)
DESIGN["nonrandomized_trial"] = ("interventional trial without randomization in which the investigators prospectively assigned the intervention "
                                 "(single-arm, phase I/II, controlled before-after) and report its results")
DESIGN["observational"] = ("observational study of human participants with no investigator-assigned intervention: cohort, case-control, "
                           "cross-sectional, registry, survey, genetic association, or a retrospective series of patients who received routine treatment")

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
