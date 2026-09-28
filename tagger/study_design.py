"""Study design tagger: the request OpenAlex sends for each work, and how its answers become study-design values.

One request per work to Jev, a decision model from TypeSafe AI (https://typesafe.ai), over the work's title, venue
and abstract: a 13-option Choice (which design best describes this paper?) plus two one-clause yes/no questions
("Nouls": is this paper itself an RCT? does it report data from human participants?). Jev answers with calibrated
probabilities. `derive()` turns them into eight class scores, three code-side text gates can veto RCT, and each class
has a threshold fixed on the development set (benchmarks/data/dev/). Parents are implied: an RCT is also a Clinical
Trial, a Meta-Analysis is also a Systematic Review.

This is the module OpenAlex runs, with only headers and comments rewritten; `python -m tagger.check_same` shows that
its derivations, gates and values equal the certified configuration's on every cached development-set answer.

Two rules learned the hard way (harness/LEDGER.md): never put several works in one request (7% of answers flip at
eight works per request), and never add a question to the request without re-certifying (four times an extra
question moved every other answer).

Needs only `requests` (for the client at the bottom); everything above the client is pure Python.
"""
from __future__ import annotations

import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-1.13.0"                     # pinned: a newer snapshot can shift calibration, so re-certify before moving
RUBRIC_VERSION = "rubric-v2"                 # the definitions in harness/rubric_v2.py
CONFIG_NAME = "r2_gate4"                     # harness/configs/r2_gate4.py: the configuration that was certified
TAGGER_VERSION = f"{CONFIG_NAME}/{JEV_MODEL}"  # change the request, gates, thresholds or snapshot and this must change
RETRYABLE = {429, 500, 502, 503, 529}

# ---------------------------------------------------------------------------
# The request: rubric v2's texts with the first version's short Nouls (harness/configs/r2_shortnoul.py)
# ---------------------------------------------------------------------------

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

# One clause each. Longer Nouls with caveats cost 10 to 16 points of RCT recall, three times over.
NOULS = {
    "is_rct": "Is this paper itself a randomized controlled trial (not a protocol, not a secondary analysis of one)?",
    "human_subjects": "Does this paper report data collected from human participants or patients?",
}

ABSTRACT_CHARS = 6000


def questions() -> dict:
    q = {"design": {"type": "choice", "instructions": "Which study design best describes this paper?", "criteria": DESIGN}}
    for k, v in NOULS.items():
        q[k] = {"type": "noul", "instructions": v}
    return q


def state_for(w: dict) -> dict:
    """w: {title, venue, abstract}. Key order matters: it is the order that was certified."""
    s = {"rule_design": RULE, "title": w.get("title") or ""}
    if w.get("venue"):
        s["venue"] = w["venue"]
    if w.get("abstract"):
        s["abstract"] = w["abstract"][:ABSTRACT_CHARS]
    return s


# ---------------------------------------------------------------------------
# Derivation: Jev's answers -> eight class scores -> values
# ---------------------------------------------------------------------------

CLASSES = ["rct", "clinical_trial", "observational", "case_report", "systematic_review", "meta_analysis", "protocol",
           "other_primary_research"]

# Per-class thresholds, fixed on the development split (the lowest score whose one-sided 95% lower bound on precision
# clears the class's bar). Protocol: the development split alone picked 0.74 with no false positives; the pooled
# curve clears the 0.97 bar at 0.90, which is what ships.
THRESHOLDS = {"rct": 0.90, "meta_analysis": 0.97, "systematic_review": 0.88, "protocol": 0.90, "clinical_trial": 0.90,
              "case_report": 0.97, "observational": 0.82, "other_primary_research": 0.30}

# Value ids as served by the API, and the implied parents.
VALUE_ID = {
    "rct": "randomized-controlled-trial",
    "clinical_trial": "clinical-trial",
    "observational": "observational-study",
    "case_report": "case-report",
    "systematic_review": "systematic-review",
    "meta_analysis": "meta-analysis",
    "protocol": "study-protocol",
    "other_primary_research": "other-primary-research",
}
PARENT = {"rct": "clinical_trial", "meta_analysis": "systematic_review"}

# OpenAlex serves only PubMed's vocabulary (the seven classes below). The tagger still scores other_primary_research,
# because it is part of the certified request; the served values leave it out.
SERVED_CLASSES = [c for c in CLASSES if c != "other_primary_research"]

DISPLAY_NAME = {
    "rct": "Randomized Controlled Trial",
    "clinical_trial": "Clinical Trial",
    "observational": "Observational Study",
    "case_report": "Case Report",
    "systematic_review": "Systematic Review",
    "meta_analysis": "Meta-Analysis",
    "protocol": "Study Protocol",
}
DESCRIPTION = {   # word for word the definitions on help.openalex.org/data/study-designs
    "rct": ("A trial that assigns human participants, groups of participants or treatment periods to interventions by "
            "explicit randomization and reports its results; secondary and post-hoc analyses of a trial's data do not "
            "count."),
    "clinical_trial": ("A study that prospectively assigns human participants to one or more interventions and reports "
                       "the results, randomized or not."),
    "observational": ("A study of human participants in which the investigators do not assign an intervention, such as "
                      "a cohort, case-control, cross-sectional, registry or survey study."),
    "case_report": ("A description of one patient, or a small series of about ten or fewer described one by one, with no "
                    "comparison group."),
    "systematic_review": ("A review that reports a systematic search of the literature and explicit criteria for "
                          "selecting the studies it brings together."),
    "meta_analysis": "A study that statistically pools quantitative results from several independent studies.",
    "protocol": ("The published plan for a study, setting out its aims, design and methods before any results exist."),
}

# The three code-side gates on RCT. Under rubric v2 an RCT must state random allocation, so the stated-random regex
# (ten languages) is a hard gate, not a hint.
RAND = re.compile(r"randomi[sz]|randomly|at random|random(?:ized|ised|isation|ization)?\b|aleatori[sz]|aleat[oó]ri|randomisiert|randomisé|"
                  r"gerandomiseerd|randomiser|随机|ランダム|無作為|무작위|рандомиз|случайн|losow", re.I)
SIM = re.compile(r"\b(simulat(?:ion|or|ed)|manikin|mannequin|phantom|cadaver(?:ic|s)?|bench(?:top)?\s+(?:study|model)|in vitro)\b", re.I)
SECONDARY = re.compile(r"\b(secondary|post[- ]?hoc|exploratory|subgroup|sub-study|substudy|ancillary|pooled|mediation|moderat(?:or|ion))\s+analys|"
                       r"\b(safety|secondary|data|lessons|insights|analysis)\s+from\s+(?:a|the|two|three|\d+)\s+randomi|"
                       r"\bparticipants\s+(?:of|in|from)\s+(?:a|the)\s+randomi|\bin\s+the\s+[A-Z][A-Za-z0-9-]+\s+trial\b", re.I)


def stated_random(w: dict) -> bool:
    """Title or abstract states random allocation (any of ten languages)."""
    return bool(RAND.search((w.get("title") or "") + " " + (w.get("abstract") or "")))


def simulation_title(w: dict) -> bool:
    """Title says simulation, manikin, phantom, cadaver, bench model or in vitro."""
    return bool(SIM.search(w.get("title") or ""))


def secondary_title(w: dict) -> bool:
    """Title reads as a secondary, post-hoc or subgroup analysis, or 'data from a randomized ...', or 'in the X trial'."""
    return bool(SECONDARY.search(w.get("title") or ""))


def gates(w: dict) -> dict:
    """The three gate answers for a work, as stored in benchmarks/data/dev/dev_jev_outputs.jsonl.gz."""
    return {"stated_random": stated_random(w), "simulation_title": simulation_title(w), "secondary_title": secondary_title(w)}


def rct_allowed(g: dict) -> bool:
    """RCT may be tagged only if randomisation is stated and the title is neither a simulation nor a secondary analysis."""
    return bool(g["stated_random"]) and not g["simulation_title"] and not g["secondary_title"]


def derive_from_gates(a: dict, g: dict) -> dict:
    """derive() for when the gate answers are already known (the cached development set holds no text)."""
    pr = a["design"]["probabilities"]
    rct = min(a["is_rct"]["noul"], 1.0) if a["human_subjects"]["noul"] >= 0.5 else 0.0
    d = {
        "rct": rct,
        "clinical_trial": max(pr.get("rct", 0), pr.get("nonrandomized_trial", 0)),
        "observational": pr.get("observational", 0),
        "case_report": pr.get("case_report", 0),
        "systematic_review": max(pr.get("systematic_review", 0), pr.get("meta_analysis", 0)),
        "meta_analysis": pr.get("meta_analysis", 0),
        "protocol": pr.get("protocol", 0),
        "other_primary_research": pr.get("other_primary_research", 0),
    }
    sec = pr.get("secondary_analysis", 0)
    d["rct"] = d["rct"] * (1 - sec)
    d["clinical_trial"] = d["clinical_trial"] * (1 - sec)
    if not rct_allowed(g):
        d["rct"] = 0.0
    return d


def derive(a: dict, w: dict) -> dict:
    """a = Jev's answers, w = the work. Returns {class: score in [0, 1]} for the eight classes, gates applied."""
    return derive_from_gates(a, gates(w))


def classes_at_thresholds(scores: dict) -> list[str]:
    """Class names that clear their threshold, parents added, in CLASSES order."""
    hit = {c for c in CLASSES if scores.get(c, 0.0) >= THRESHOLDS[c]}
    for c in list(hit):
        if c in PARENT:
            hit.add(PARENT[c])
    return [c for c in CLASSES if c in hit]


def tagger_values(scores: dict) -> list[str]:
    """Value ids for the classes that clear their thresholds (other-primary-research included; OpenAlex drops it)."""
    return [VALUE_ID[c] for c in classes_at_thresholds(scores)]


def served_values(scores: dict) -> list[str]:
    """The values OpenAlex serves: tagger_values without other-primary-research."""
    return [VALUE_ID[c] for c in classes_at_thresholds(scores) if c in SERVED_CLASSES]


# ---------------------------------------------------------------------------
# PubMed's study-characteristics tags (MeSH publication types) -> the same values
# ---------------------------------------------------------------------------

# Publication formats (Editorial, Letter, Review, Guideline ...) belong to OpenAlex's `type`, not here. Scoping Review
# and the modifier tags (Comparative, Multicenter, Evaluation, Validation Study) are left out.
PUBMED_MAP = {
    "Randomized Controlled Trial": "rct",
    "Randomized Controlled Trial, Veterinary": "rct",
    "Pragmatic Clinical Trial": "rct",
    "Equivalence Trial": "rct",
    "Adaptive Clinical Trial": "rct",
    "Clinical Trial": "clinical_trial",
    "Controlled Clinical Trial": "clinical_trial",
    "Clinical Trial, Phase I": "clinical_trial",
    "Clinical Trial, Phase II": "clinical_trial",
    "Clinical Trial, Phase III": "clinical_trial",
    "Clinical Trial, Phase IV": "clinical_trial",
    "Clinical Study": "clinical_trial",
    "Clinical Trial, Veterinary": "clinical_trial",
    "Observational Study": "observational",
    "Observational Study, Veterinary": "observational",
    "Twin Study": "observational",
    "Case Reports": "case_report",
    "Systematic Review": "systematic_review",
    "Meta-Analysis": "meta_analysis",
    "Network Meta-Analysis": "meta_analysis",
    "Clinical Trial Protocol": "protocol",
}


def pubmed_classes(pub_types: list[str] | None) -> list[str]:
    """Class names implied by a PubMed record's PublicationType list (parents added), or [] if none map."""
    hit = {PUBMED_MAP[t] for t in (pub_types or []) if t in PUBMED_MAP}
    for c in list(hit):
        if c in PARENT:
            hit.add(PARENT[c])
    return [c for c in CLASSES if c in hit]


def pubmed_values(pub_types: list[str] | None) -> list[str]:
    return [VALUE_ID[c] for c in pubmed_classes(pub_types)]


# ---------------------------------------------------------------------------
# Jev client: threads + requests, paced on requests per second
# ---------------------------------------------------------------------------

def _backoff(attempt: int) -> float:
    return min(30.0, 0.5 * 2 ** attempt) * (0.5 + random.random())


class Pacer:
    """Token bucket on requests per second, shared by all threads."""

    def __init__(self, rps: float):
        self._interval = 1.0 / max(rps, 0.001)
        self._next = time.perf_counter()
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.perf_counter()
            self._next = max(self._next, now)
            delay = self._next - now
            self._next += self._interval
        if delay > 0:
            time.sleep(delay)


class JevClient:
    """TypeSafe's native API, one request per work. Retries 429 / 5xx / transport errors with jittered backoff.
    The API key comes from the JEV_API_KEY environment variable unless given."""

    def __init__(self, api_key: str | None = None, concurrency: int = 64, rps: float = 250.0, timeout: float = 60.0,
                 max_attempts: int = 6, model: str = JEV_MODEL):
        import requests  # only the client needs it

        self._requests = requests
        api_key = api_key or os.environ.get("JEV_API_KEY")
        if not api_key:
            raise RuntimeError("Jev API key missing: set JEV_API_KEY")
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._concurrency = concurrency
        self._pacer = Pacer(rps)
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._model = model
        self._local = threading.local()
        self._lock = threading.Lock()
        self.total_tokens = 0
        self.n_ok = 0
        self.n_fail = 0
        self.n_retry = 0

    def _session(self):
        s = getattr(self._local, "s", None)
        if s is None:
            s = self._requests.Session()
            self._local.s = s
        return s

    def decide(self, state: Any, qs: dict) -> dict:
        body = {"model": self._model, "state": state, "questions": qs}
        attempt = 0
        while True:
            attempt += 1
            self._pacer.wait()
            t0 = time.perf_counter()
            try:
                resp = self._session().post(JEV_URL, headers=self._headers, json=body, timeout=self._timeout)
                ms = (time.perf_counter() - t0) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    tok = int((data.get("usage") or {}).get("input_tokens") or 0)
                    with self._lock:
                        self.total_tokens += tok
                        self.n_ok += 1
                    return {"ok": True, "answers": data.get("answers", {}), "model": data.get("model"),
                            "input_tokens": tok, "latency_ms": round(ms), "attempts": attempt}
                if resp.status_code in RETRYABLE and attempt < self._max_attempts:
                    with self._lock:
                        self.n_retry += 1
                    ra = resp.headers.get("retry-after")
                    time.sleep(float(ra) if ra else _backoff(attempt))
                    continue
                with self._lock:
                    self.n_fail += 1
                return {"ok": False, "status": resp.status_code, "error": resp.text[:300], "attempts": attempt}
            except (self._requests.Timeout, self._requests.ConnectionError) as e:
                if attempt < self._max_attempts:
                    with self._lock:
                        self.n_retry += 1
                    time.sleep(_backoff(attempt))
                    continue
                with self._lock:
                    self.n_fail += 1
                return {"ok": False, "status": 0, "error": repr(e)[:300], "attempts": attempt}

    def tag_many(self, works: list[dict], on_result: Callable[[dict, dict], None] | None = None) -> list[tuple[dict, dict]]:
        """works: dicts with work_id, title, venue, abstract. Returns [(work, result)] in completion order."""
        qs = questions()
        out = []
        with ThreadPoolExecutor(self._concurrency) as ex:
            futs = {ex.submit(self.decide, state_for(w), qs): w for w in works}
            for f in as_completed(futs):
                w = futs[f]
                try:
                    r = f.result()
                except Exception as e:  # never lose the batch to one bad thread
                    r = {"ok": False, "status": -1, "error": repr(e)[:300], "attempts": 0}
                    with self._lock:
                        self.n_fail += 1
                out.append((w, r))
                if on_result:
                    on_result(w, r)
        return out


# ---------------------------------------------------------------------------
# One output row per work
# ---------------------------------------------------------------------------

def answer_row(w: dict, r: dict) -> dict | None:
    """The tagger's output for one work from a successful Jev result, or None if the answer is malformed."""
    a = r.get("answers") or {}
    try:
        probs = {k: float(v) for k, v in a["design"]["probabilities"].items()}
        is_rct = float(a["is_rct"]["noul"])
        human = float(a["human_subjects"]["noul"])
    except (KeyError, TypeError, ValueError):
        return None
    scores = derive(a, w)
    return {
        "work_id": w["work_id"],
        "values": served_values(scores),
        "tagger_values": tagger_values(scores),
        "scores": {k: float(v) for k, v in scores.items()},
        "probabilities": probs,
        "is_rct": is_rct,
        "human_subjects": human,
        "gates": gates(w),
        "abstract_chars": len(w.get("abstract") or ""),
        "tagger_version": TAGGER_VERSION,
        "jev_model": r.get("model") or JEV_MODEL,
    }
