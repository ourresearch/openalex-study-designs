"""r2_v3: rubric v2 options + v1 short is_rct Noul + two more short Nouls used as gates:
- health_outcome: outcomes on the participants' own health/behaviour (not task performance on a simulator) -> gates rct
- prospective_assignment: investigators prospectively assigned the intervention (stated) -> gates clinical_trial
plus the code gate: rct only if the text states randomisation (textsig.stated_random)."""
import configs.v1 as v1, configs.r2_base as b, textsig
NAME = 'r2_v3'
NOTES = 'r2_shortnoul + Nouls health_outcome (gates rct) + prospective_assignment (gates clinical_trial) + stated-random text gate'
RULE = b.RULE; DESIGN = dict(b.DESIGN)
NOULS = dict(v1.NOULS)
NOULS["health_outcome"] = "Are the outcomes measured on the participants' own health, symptoms, physiology or behaviour (not their performance on a task, device or simulator)?"
NOULS["prospective_assignment"] = "Does the text state that the investigators prospectively assigned the intervention to participants?"
def questions():
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": DESIGN}}
    for k, v in NOULS.items(): q[k] = {"type": "noul", "instructions": v}
    return q
def state_for(w): return b.state_for(w)
def derive(a, w):
    d = b.derive(a, w)
    d["rct"] = min(d["rct"], a["health_outcome"]["noul"]) if textsig.stated_random(w) else 0.0
    d["clinical_trial"] = min(d["clinical_trial"], a["prospective_assignment"]["noul"])
    return d
