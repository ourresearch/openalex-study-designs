"""H16: h15 + the is_rct Noul broadened toward the judge's practice (updated / follow-up / extension / prespecified-outcome
reports of a randomized trial count; protocols and secondary/post-hoc/subgroup analyses do not) + crossover and cluster
randomisation named in the rct option. Targets the dev false negatives of h15.
"""
import configs.v1 as v1, configs.h15_nrt as h15
NAME = 'h16_rctnoul'
NOTES = 'h15 + is_rct Noul names follow-up/extension/updated reports as RCT and secondary/subgroup as not; crossover/cluster in rct text'

RULE = h15.RULE
DESIGN = dict(h15.DESIGN)
DESIGN["rct"] = ("randomized controlled trial: this paper reports results (primary, updated, follow-up or extension) of a trial whose "
                 "participants, clusters, or treatment order were randomly allocated, including randomized crossover trials")
NOULS = {
    "is_rct": ("Is this paper itself a report of a randomized controlled trial's results (primary, updated, follow-up, extension, or "
               "prespecified-outcome report of a trial with random allocation, including randomized crossover)? Protocols and secondary, "
               "post-hoc or subgroup analyses of a trial's data are not."),
    "human_subjects": v1.NOULS["human_subjects"],
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
