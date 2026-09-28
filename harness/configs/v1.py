"""Baseline: the first version of the request (design Choice, 12 options; is_rct + human_subjects Nouls).
derive(): rct = is_rct Noul AND human_subjects (the first version's shape); clinical_trial = max(rct, nonrandomized_trial);
systematic_review = max(sr, meta_analysis); the rest = the Choice probability.
"""
NAME = 'v1'
NOTES = 'baseline: the first version of the request'

RULE = ("Classify the study design of this paper from its title and abstract. "
        "Judge what the paper itself reports, not what it cites or discusses. "
        "A protocol for a trial is not the trial; a secondary analysis of a trial is not the trial. "
        "If the design cannot be told from the text, answer unknown.")
DESIGN = {
    "rct": "randomized controlled trial: participants randomly allocated to interventions",
    "nonrandomized_trial": "interventional clinical trial without randomization (single-arm, phase I/II, before-after)",
    "observational": "observational human study: cohort, case-control, cross-sectional, registry, survey",
    "case_report": "case report or small case series",
    "systematic_review": "systematic literature review without pooled quantitative meta-analysis",
    "meta_analysis": "meta-analysis (pooled quantitative synthesis of studies)",
    "narrative_review": "narrative or expert review, not systematic",
    "editorial_letter": "editorial, commentary, letter, opinion, correspondence",
    "protocol": "study or trial protocol: planned methods, no results yet",
    "guideline": "clinical practice guideline or consensus recommendations",
    "other_primary_research": "other primary research: laboratory, animal, computational, methods, qualitative",
    "unknown": "cannot tell from title and abstract",
}
NOULS = {
    "is_rct": "Is this paper itself a randomized controlled trial (not a protocol, not a secondary analysis of one)?",
    "human_subjects": "Does this paper report data collected from human participants or patients?",
}

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
    """a = Jev answers dict. Returns {shipped_class: score}."""
    pr = a["design"]["probabilities"]
    rct = min(a["is_rct"]["noul"], 1.0) if a["human_subjects"]["noul"] >= 0.5 else 0.0
    return {
        "rct": rct,
        "clinical_trial": max(pr.get("rct", 0), pr.get("nonrandomized_trial", 0)),
        "observational": pr.get("observational", 0),
        "case_report": pr.get("case_report", 0),
        "systematic_review": max(pr.get("systematic_review", 0), pr.get("meta_analysis", 0)),
        "meta_analysis": pr.get("meta_analysis", 0),
        "protocol": pr.get("protocol", 0),
        "other_primary_research": pr.get("other_primary_research", 0),
    }
