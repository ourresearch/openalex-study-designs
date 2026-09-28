"""H4: atomic decomposition. No 12-way Choice; eight yes/no Nouls and code derives the shipped classes.
Interpretable failures; may be sharper than one Choice. The v1 Choice is kept too (cheap) so the two can be compared
work by work, but derive() below uses only the Nouls.
"""
import configs.v1 as v1
NAME = 'h4_atomic'
NOTES = 'eight atomic Nouls; classes derived by rules (Choice kept in the request but unused)'

RULE = v1.RULE
NOULS = {
    "human": "Does this paper report data collected from human participants or patients?",
    "intervention": "Did the study this paper reports assign an intervention (treatment, drug, procedure, program) to participants?",
    "randomized": "Were participants (or clusters) randomly allocated to interventions in the study this paper reports?",
    "primary_report": "Is this paper the primary report of the study's results, rather than a protocol, secondary or post-hoc analysis, sub-study, follow-up, or pooled analysis?",
    "protocol_only": "Does this paper describe planned methods for a study whose results are not yet reported (a protocol)?",
    "single_patient": "Does this paper describe one patient or a small series of patients (a case report or case series)?",
    "systematic_search": "Does this paper report a systematic literature search and selection of studies (a systematic or scoping review)?",
    "pooled_synthesis": "Does this paper pool quantitative results across studies (a meta-analysis)?",
    "observational_human": "Is this an observational human study (cohort, case-control, cross-sectional, registry, survey) with no assigned intervention?",
}

def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": v1.DESIGN}}
    for k, v in NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q

def state_for(w): return v1.state_for(w)

def n(a, k): return a[k]["noul"]

def derive(a, w):
    human = n(a, "human"); prim = n(a, "primary_report"); prot = n(a, "protocol_only")
    rct = min(human, n(a, "intervention"), n(a, "randomized"), prim, 1 - prot)
    trial = min(human, n(a, "intervention"), prim, 1 - prot)
    sr = min(n(a, "systematic_search"), 1 - prot); ma = min(n(a, "pooled_synthesis"), 1 - prot)
    return {
        "rct": rct,
        "clinical_trial": trial,
        "observational": min(n(a, "observational_human"), 1 - n(a, "intervention"), 1 - prot, 1 - n(a, "single_patient")),
        "case_report": min(n(a, "single_patient"), 1 - prot),
        "systematic_review": max(sr, ma),
        "meta_analysis": ma,
        "protocol": prot,
        "other_primary_research": a["design"]["probabilities"].get("other_primary_research", 0),
    }
