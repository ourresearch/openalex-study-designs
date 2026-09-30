# Changelog

The tagger uses [semantic versioning](https://semver.org). A **major** version changes what counts as a right answer
(the rubric in `harness/rubric_v2.py`) or replaces the approach. A **minor** version changes the tagger (the request,
the gates, the thresholds, the Jev snapshot or the student) and re-certifies it on the development set. A **patch**
fixes code without changing any answer. Every release reports its certification here.

## Documentation correction (29 September 2026)

The README listed eight highly cited papers that PubMed tags as randomized controlled trials but that are not reports
of one. A closer check (PubMed's record, full text where open, and PubMed's own definition) keeps five: the anti-PD-1
phase 1 study randomized its dose cohorts, the HPV paper reports its trial's randomized comparison, and the WOMAC
validation study is arguable. One example from another design was dropped for the same reason. Benchmarks unchanged.

## 1.0.1 (28 September 2026)

The RCT check (`tagger/rct_check.py`) gets room for the model's reasoning (4,000 output tokens, was 800) and asks
Claude Opus 5.5 when Sonnet 5 refuses a paper. About 200 of the 627,013 works checked at launch had no answer
because of one or the other; nothing else changes.

## 1.0.0 (28 September 2026)

First public release: the tagger's code, its request to Jev, the development set (ids and labels), every
configuration tried, the student model and its weights.

Certified on the 5,069 judged works at the shipped thresholds (Opus 5 labels, one-sided 95% lower bound on precision):
RCT 1.000 precision (0 false positives in 555, bound 0.995) at 0.83 recall; every class clears its bar
(`python harness/certify.py`). Re-judged by Opus 5.5 (`--judge opus-5.5`), RCT is 0.995 (3 false positives, bound
0.987) and Clinical Trial 0.960 (bound 0.948), both just under their bars.

Benchmarked against PubMed on 8,308 fresh works judged by Opus 5.5, with the rule served from 29 September
(`python3 benchmarks/score_pubmed.py`): on PubMed-indexed works, RCT precision 99.9% (PubMed's tags: 63%); outside
PubMed every design is at least 97% and RCT 99.5%.

How it got here:

- **23 September 2026.** The tagger ships: one Jev request per work (`jev-1.13.0`), rubric v2's definitions, three
  code gates on RCT, thresholds fixed on the development set. It starts tagging every work with an abstract. From
  24 September the student, a small encoder trained on the tagger's own outputs, tags most of the backlog; works it
  is unsure about go to Jev.
- **26 September 2026.** Study designs are served. Jev tags every new work from here on; the student's tags on the
  backlog stay.
- **27 September 2026.** The rule for which source wins: automated tagging wherever it ran; PubMed's publication
  types only on works without an abstract, where the tagger did not run.
- **28 September 2026.** A population-weighted benchmark showed the development set had overstated precision on the
  works we tag (it is mostly biomedical, and its pools were picked by the tagger's own answers): Clinical Trial 92%,
  Study Protocol 81%, randomized trials outside PubMed 98.5%. Two fixes, served from 29 September: stricter served
  thresholds for three values (Randomized Controlled Trial 0.95, Clinical Trial 0.97, Study Protocol 0.95; applied to
  the stored scores, nothing re-tagged), and a second-model check on every randomized-trial tag
  (`tagger/rct_check.py`). Both were chosen on two samples (`benchmarks/data/thresholds_sample`,
  `benchmarks/data/rct_check_sample`) and scored on a third, fresh one (`benchmarks/data/pubmed`). Also from 29
  September: no more PubMed fallback. Works without an abstract used to carry PubMed's tags; judged on their titles
  those were right 37% (randomized trials) to 94% (case reports) of the time, so 642,057 works no longer get a value.
