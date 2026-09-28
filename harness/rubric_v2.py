"""Rubric v2 = the schema's own definitions, word for word what the judge and the tagger read. Single source for
both the Opus judge (judge_v2.py) and the tagger seed config (configs/r2_base.py). One line per option, <= 45 words.

Decisions encoded:
- RCT: the paper reports results (primary, updated, follow-up, extension) of a trial that explicitly randomised human
  participants, clusters or treatment periods to compared interventions; randomised crossover counts; blinded /
  placebo-controlled without the word randomised does not; randomised stimulus order in a lab experiment does not.
- Case report: patients described one by one, no comparison group, up to about ten. Larger descriptive series = observational.
- Observational: human participants only. Firms, documents, ecosystems -> other primary research.
- Other primary research kept.
- secondary_analysis is a sink: a secondary / post-hoc / subgroup analysis of a trial ships with no study design in v1.
"""
RULE = ("Classify the study design of this paper from its title and abstract. Judge only what this paper itself reports and "
        "states; ignore designs it cites, discusses or builds on. Answer unknown unless the design is stated or unambiguous "
        "from the described methods. A paper that comments on, summarises or appraises another study or review is "
        "editorial_letter or narrative_review, not the design it discusses.")

DESIGN = {
    "rct": ("randomized controlled trial: this paper reports results (primary, updated, follow-up or extension) of a trial "
            "that explicitly randomized human participants, clusters or treatment periods to compared interventions; "
            "randomized crossover trials count"),
    "nonrandomized_trial": ("interventional trial in which investigators prospectively assigned an intervention to human "
                            "participants without stated randomization (single-arm, phase I/II, controlled before-after, or "
                            "blinded / placebo-controlled with no mention of randomization) and report its results"),
    "secondary_analysis": ("secondary, post-hoc, subgroup, exploratory or pooled analysis of data from an earlier trial or "
                           "cohort; not the primary or updated results report of that study"),
    "observational": ("observational study of human participants with no investigator-assigned intervention: cohort, "
                      "case-control, cross-sectional, registry, survey, genetic association, or a descriptive series of "
                      "more than about ten patients who received routine care"),
    "case_report": ("case report or small case series: one to about ten patients described individually, no comparison "
                    "group, no cohort statistics"),
    "systematic_review": ("systematic review: this paper itself reports a systematic literature search and study selection "
                          "in any field, without pooled quantitative meta-analysis"),
    "meta_analysis": ("meta-analysis: this paper itself pools quantitative results across published studies in any field; "
                      "pooling participant-level or summary data across cohorts (e.g. GWAS) is observational instead"),
    "narrative_review": ("narrative, expert or 'comprehensive' review without a reported systematic search; also summaries, "
                         "evidence updates or appraisals of others' reviews or trials"),
    "editorial_letter": "editorial, commentary, letter, opinion, correspondence, or a commentary appraising another paper",
    "protocol": ("protocol for a planned study with human or animal participants: planned methods, no results yet "
                 "(not a technical, monitoring or mission plan)"),
    "guideline": "clinical practice guideline or consensus recommendations",
    "other_primary_research": ("primary research whose units are not human patients or participants: laboratory, in vitro, "
                               "animal, agricultural, computational, methods, qualitative fieldwork, tool or program "
                               "development, analyses of firms, documents, texts or ecosystems; also lab experiments on "
                               "volunteers that only randomize the order of stimuli"),
    "unknown": "cannot tell from title and abstract",
}

NOULS = {
    "is_rct": ("Is this paper a report of results of a randomized controlled trial as defined above (not a protocol, not a "
               "secondary analysis)?"),
    "human_subjects": "Does this paper report data collected from human participants or patients?",
}

VERSION = "rubric-v2/2026-09-22"
