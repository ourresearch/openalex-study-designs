"""H10: rule-text variant. Explicit abstention rule, explicit CONSORT-style cues, pilot RCTs count, registration numbers
and 'randomized' in the title do not make a secondary analysis the trial. Everything else as v1.
"""
import configs.v1 as v1
NAME = 'h10_rule'
NOTES = 'v1 with a stricter, more explicit rule text'

RULE = ("Classify the study design of this paper from its title and abstract. Judge only what this paper itself reports; "
        "ignore designs it cites, discusses, or builds on. Answer unknown unless the design is stated or unambiguous from the "
        "described methods. A protocol for a trial is not the trial. A secondary, post-hoc, pooled or sub-study analysis of "
        "an earlier trial is not the trial, even if the title says randomized or gives a registration number. A pilot or "
        "feasibility trial with random allocation is still a randomized controlled trial. A meta-analysis pools numbers; a "
        "systematic review without pooling is not a meta-analysis.")

def questions(): return v1.questions()

def state_for(w):
    s = {"rule_design": RULE, "title": w.get("title") or ""}
    if w.get("venue"): s["venue"] = w["venue"]
    if w.get("abstract"): s["abstract"] = w["abstract"][:6000]
    return s

def derive(a, w): return v1.derive(a, w)
