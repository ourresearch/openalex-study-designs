"""H14: option texts sharpened on the failure modes seen in dev (failure mining, H13):
- MA/SR: the paper must itself conduct the synthesis; commentaries / evidence updates about a meta-analysis are not one;
  a review is systematic only if it reports a systematic search and selection; GWAS summary-statistic meta-analysis is observational.
- protocol: for a planned study with human or animal participants; technical, monitoring or mission plans are not.
- case_report: one patient or a handful (about five or fewer), descriptive; larger series are observational.
- observational: human participants; analyses of firms, documents, ecosystems are other primary research.
- commentaries on another study -> editorial_letter.
Nouls and derive as v1.
"""
import configs.v1 as v1
NAME = 'h14_scope'
NOTES = 'v1 with option texts sharpened from dev failure mining (synthesis scope, protocol scope, case-series size, human-only observational)'

RULE = (v1.RULE + " A paper that comments on, summarises or appraises another study or review is editorial_letter or narrative_review, "
        "not the design it discusses.")
DESIGN = {
    "rct": "randomized controlled trial: this paper reports results of a trial whose participants were randomly allocated to interventions",
    "nonrandomized_trial": "interventional clinical trial without randomization (single-arm, phase I/II, controlled before-after) reporting its results",
    "observational": "observational study of human participants with no assigned intervention: cohort, case-control, cross-sectional, registry, survey, genetic association",
    "case_report": "case report: one patient or a handful of patients (about five or fewer), described individually",
    "systematic_review": "systematic review that itself reports a systematic literature search and study selection, without pooled quantitative meta-analysis",
    "meta_analysis": "meta-analysis that itself pools quantitative results across published studies",
    "narrative_review": "narrative, expert, or 'comprehensive' review without a reported systematic search; also summaries or evidence updates of others' reviews",
    "editorial_letter": "editorial, commentary, letter, opinion, correspondence, or a commentary appraising another paper",
    "protocol": "protocol for a planned study with human or animal participants: planned methods, no results yet (not a technical, monitoring, or mission plan)",
    "guideline": "clinical practice guideline or consensus recommendations",
    "other_primary_research": "other primary research: laboratory, animal, computational, methods, qualitative, or analyses of non-human units (firms, documents, ecosystems)",
    "unknown": "cannot tell from title and abstract",
}

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
