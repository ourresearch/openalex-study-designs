"""Which works the student may tag on its own, and with which values. The rest go to Jev.

The student emits the same 13 Choice probabilities and two yes/no scores as Jev, so tagger/study_design.derive() and
its gates run unchanged on them. Per class:
- STUDENT_TAU_POS: the student's own threshold, chosen on the judged development split at the class's precision bar
  (the same rule as Jev's thresholds; student/certify.py reproduces it).
- STUDENT_TAU_NEG: the score under which the student's "no" loses at most 2% of Jev's own positives (RCT: 0.5%),
  measured on 78,000 held-out works Jev had tagged.
A work is the student's when every class score is outside its band [TAU_NEG, TAU_POS); otherwise Jev tags it.
Classes the student does not own have no TAU_POS: RCT, because no student score reached the 0.99 bar, so any
RCT score at or above TAU_NEG sends the work to Jev.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tagger.study_design import CLASSES, CONFIG_NAME, PARENT, VALUE_ID  # noqa: E402

STUDENT_ARM = "e5s"                                   # multilingual-e5-small, 512 tokens, 1 epoch over 1.5M Jev labels
STUDENT_VERSION = f"student-{STUDENT_ARM}-v1+{CONFIG_NAME}"
STUDENT_TAU_POS = {"clinical_trial": 0.86, "observational": 0.87, "meta_analysis": 0.99, "systematic_review": 0.94, "case_report": 0.98, "other_primary_research": 0.3, "protocol": 0.65}
STUDENT_TAU_NEG = {"rct": 0.629, "meta_analysis": 0.931, "systematic_review": 0.719, "protocol": 0.643, "clinical_trial": 0.643, "case_report": 0.875, "observational": 0.425, "other_primary_research": 0.115}


def student_route(scores: dict) -> str:
    """'student' when no class score sits in its band, else 'jev'. scores = derive() output (gates applied)."""
    for c in CLASSES:
        s = scores.get(c, 0.0)
        tp = STUDENT_TAU_POS.get(c)
        if tp is None:
            if s >= STUDENT_TAU_NEG[c]:
                return "jev"
        elif STUDENT_TAU_NEG[c] <= s < tp:
            return "jev"
    return "student"


def student_classes(scores: dict) -> list:
    """Owned classes clearing the student's threshold, parents added, in CLASSES order."""
    hit = {c for c, tp in STUDENT_TAU_POS.items() if scores.get(c, 0.0) >= tp}
    for c in list(hit):
        if c in PARENT:
            hit.add(PARENT[c])
    return [c for c in CLASSES if c in hit]


def student_values(scores: dict) -> list:
    return [VALUE_ID[c] for c in student_classes(scores)]


# Served thresholds (28 September 2026): the student's protocol tags outside PubMed were right 72% of the time on the
# population-weighted benchmark, and Clinical Trial fell under its bar for Jev and the student alike, so OpenAlex serves
# these two values only above 0.97 (Clinical Trial) and 0.95 (Study Protocol). Same rule as
# tagger.study_design.SERVED_THRESHOLDS; the student still never serves RCT.
STUDENT_SERVED_THRESHOLDS = {**STUDENT_TAU_POS, "clinical_trial": 0.97, "protocol": 0.95}


def student_served_values(scores: dict) -> list:
    """The values OpenAlex serves for a work the student tagged."""
    from tagger.study_design import CLASSES, PARENT, SERVED_CLASSES, VALUE_ID, SCORE_EPS
    hit = {c for c in SERVED_CLASSES if c in STUDENT_SERVED_THRESHOLDS and scores.get(c, 0.0) >= STUDENT_SERVED_THRESHOLDS[c] - SCORE_EPS}
    for c in list(hit):
        if c in PARENT:
            hit.add(PARENT[c])
    return [VALUE_ID[c] for c in CLASSES if c in hit]
