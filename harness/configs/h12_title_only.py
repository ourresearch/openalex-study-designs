"""H12: title only (abstract withheld). Answers the coverage question: how precise can the tagger be on the 44% of works
that have no abstract? Questions and derive as v1; the rule says the abstract is unavailable.
"""
import configs.v1 as v1
NAME = 'h12_title_only'
NOTES = 'v1 questions, title + venue only (no abstract) — coverage probe'

RULE = ("Classify the study design of this paper from its title alone; the abstract is not available. "
        "Judge what the paper itself reports, not what it cites. A protocol for a trial is not the trial; a secondary analysis "
        "of a trial is not the trial. Titles often state the design (e.g. 'a randomized controlled trial', 'systematic review and "
        "meta-analysis', 'a case report'); if the title does not, answer unknown.")

def questions(): return v1.questions()

def state_for(w):
    s = {"rule_design": RULE, "title": w.get("title") or ""}
    if w.get("venue"): s["venue"] = w["venue"]
    return s

def derive(a, w): return v1.derive(a, w)
