# Changelog

The tagger uses [semantic versioning](https://semver.org). A **major** version changes what counts as a right answer
(the rubric in `harness/rubric_v2.py`) or replaces the approach. A **minor** version changes the tagger (the request,
the gates, the thresholds, the Jev snapshot or the student) and re-certifies it on the development set. A **patch**
fixes code without changing any answer. Every release reports its certification here.

## 1.0.0 (28 September 2026)

First public release: the tagger's code, its request to Jev, the development set (ids and labels), every
configuration tried, the student model and its weights.

Certified on the 5,069 judged works at the shipped thresholds (Opus 5 labels, one-sided 95% lower bound on precision):
RCT 1.000 precision (0 false positives in 555, bound 0.995) at 0.83 recall; every class clears its bar
(`python harness/certify.py`). Re-judged by Opus 5.5 (`--judge opus-5.5`), RCT is 0.995 (3 false positives, bound
0.987) and Clinical Trial 0.960 (bound 0.948), both just under their bars.

Benchmarked against PubMed on 7,742 fresh works judged by Opus 5.5 (`python3 benchmarks/score_pubmed.py`): on
PubMed-indexed works, RCT precision 99.6% (PubMed's tags: 65%). Outside PubMed, Study Protocol is 75% and Clinical
Trial 91%, below their bars (see the README's Known issues).

How it got here:

- **23 September 2026.** The tagger ships: one Jev request per work (`jev-1.13.0`), rubric v2's definitions, three
  code gates on RCT, thresholds fixed on the development set. It starts tagging every work with an abstract. From
  24 September the student, a small encoder trained on the tagger's own outputs, tags most of the backlog; works it
  is unsure about go to Jev.
- **26 September 2026.** Study designs are served. Jev tags every new work from here on; the student's tags on the
  backlog stay.
- **27 September 2026.** The rule for which source wins: automated tagging wherever it ran; PubMed's publication
  types only on works without an abstract, where the tagger did not run.
