"""GEPA run 1 best candidate (idx 34, val 0.8614 vs seed 0.8612), seeded from h15_nrt. Auto-generated."""
import configs.v1 as v1
NAME = 'g_run1'
NOTES = 'GEPA run 1 best candidate from h15_nrt'
RULE = 'Classify the study design of this paper from its title and abstract. Judge what the paper itself reports, not what it cites or discusses. A protocol for a trial is not the trial; a secondary analysis of a trial is not the trial. If the design cannot be told from the text, answer unknown. A paper that comments on, summarises or appraises another study or review is editorial_letter or narrative_review, not the design it discusses.'
DESIGN = {
 "rct": "randomized controlled trial: this paper reports results of a trial whose participants were randomly allocated to interventions",
 "nonrandomized_trial": "interventional trial without randomization in which the investigators prospectively assigned the intervention (single-arm, phase I/II, controlled before-after) and report its results",
 "observational": "no investigator-assigned exposure or treatment: cohort, case-control, cross-sectional, registry, survey, surveillance of records or sites, genetic association; comparison of groups given routine care; retrospective or prospective case series reporting outcomes of treatment already delivered. Not if investigators administered, switched, or allocated the treatment studied.",
 "case_report": "case report or small case series: findings, treatment and course in one to a few patients (roughly five or fewer), described individually, no comparison group, no enrolled sample or cohort statistics. Not an anecdote used merely to illustrate a magazine, editorial or review piece.",
 "systematic_review": "systematic review that itself reports a systematic literature search and study selection, without pooled quantitative meta-analysis",
 "meta_analysis": "meta-analysis that itself pools quantitative results across published studies",
 "narrative_review": "narrative, expert, or 'comprehensive' review without a reported systematic search; also summaries or evidence updates of others' reviews",
 "editorial_letter": "editorial, commentary, letter, opinion, correspondence, or a commentary appraising another paper",
 "protocol": "protocol for a planned study with human or animal participants: planned methods, no results yet (not a technical, monitoring, or mission plan)",
 "guideline": "clinical practice guideline or consensus recommendations",
 "other_primary_research": "Primary research whose units are not human participants: animal, livestock, crop, plant, insect or agricultural field trials; laboratory, in vitro, isolate or preclinical work; computational, mathematical, methods, qualitative; analyses of firms, documents, ecosystems; program or tool development. Counts even if randomized or controlled. Not studies enrolling patients.",
 "unknown": "cannot tell from title and abstract"
}
NOULS = {
 "is_rct": "Yes only if this report presents its own trial that explicitly randomised or randomly allocated human participants to compared interventions. No for protocols, secondary or pooled analyses of trials, animal or lab experiments, and any study merely described as prospective, controlled or comparative; if allocation is unstated, no.",
 "human_subjects": "Does this paper report data collected from human participants or patients?"
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
def derive(a, w): return v1.derive(a, w)
