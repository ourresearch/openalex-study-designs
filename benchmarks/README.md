# Benchmarks

Every number in the main [README](../README.md), how we got it, and how to check it. Everything here is rebuilt by

```
python3 benchmarks/score_pubmed.py
```

from two files: [`data/pubmed/sample.jsonl.gz`](data/pubmed/sample.jsonl.gz) (7,742 works: ids, both sides' tags,
the judge's label and reason) and [`data/pubmed/population.json`](data/pubmed/population.json) (the size of every
group we sampled from). No abstract text is included, because publishers own it; `tagger/fetch_works.py` rebuilds
titles and abstracts from the OpenAlex API.

## What right means

**A tag is right if the judge's reading of the paper supports it.** The judge is Claude Opus 5.5 (effort medium),
given the title, the venue and the abstract, and asked to pick one of 13 designs and answer two yes-or-no
questions. The definitions are in [`harness/rubric_v2.py`](../harness/rubric_v2.py) and the exact prompt in
[`harness/judge_prompt.md`](../harness/judge_prompt.md). They follow PubMed's vocabulary and are stricter in a few
places:

- **Randomized controlled trial:** the paper reports results of a trial that says it randomized people, clusters
  or treatment periods. "Double-blind" or "placebo-controlled" without the word "randomized" is a clinical trial,
  not a randomized one. A secondary, post-hoc or subgroup analysis of a trial is not the trial.
- **Case report:** one to about ten patients, described one by one. A larger series is observational.
- **Observational study:** people only. Studies of animals, firms or documents are other research.
- **Meta-analysis:** pools results across published studies. Pooling raw data across cohorts is observational.

The judge answered "unknown" (the text says too little) on 131 works and refused 30. Both are left out; counting
"unknown" as wrong moves no number by more than 1.5 points.

## The sample

**Stratified on the live index on 28 September 2026, weighted back to the whole.** For each design, works in MEDLINE
(PubMed's indexed journals) fall into four groups: both sides tag it, only PubMed does, only OpenAlex does, or
neither does. We sampled the first three directly and estimated the fourth from 840 random MEDLINE works. Works
outside MEDLINE that OpenAlex tags were sampled for each design too, plus 840 random works outside MEDLINE. The
5,069 works used to build and tune the tagger were excluded.

Works in each group (the population):

| Study design | Both tag it | Only PubMed | Only OpenAlex | OpenAlex, not in MEDLINE |
|---|---|---|---|---|
| Randomized Controlled Trial | 367,098 | 292,164 | 14,603 | 457,525 |
| Clinical Trial | 581,765 | 433,145 | 353,510 | 1,985,271 |
| Observational Study | 176,203 | 39,757 | 4,855,169 | 9,494,361 |
| Case Report | 1,284,169 | 377,690 | 185,970 | 1,697,257 |
| Systematic Review | 348,021 | 59,811 | 71,880 | 731,777 |
| Meta-Analysis | 197,545 | 40,950 | 10,359 | 177,820 |
| Study Protocol | 22,571 | 1,520 | 40,867 | 136,300 |

25,904,718 MEDLINE works and 140,418,866 other works were tagged (every work with an abstract).

Tags the judge supports, out of those judged:

| Study design | Both | Only PubMed | Only OpenAlex | OpenAlex, not in MEDLINE | Random MEDLINE works, neither tags it |
|---|---|---|---|---|---|
| Randomized Controlled Trial | 190 / 190 | 74 / 334 | 301 / 327 | 334 / 339 | 1 / 779 |
| Clinical Trial | 189 / 190 | 57 / 230 | 210 / 240 | 216 / 237 | 3 / 760 |
| Observational Study | 188 / 189 | 100 / 234 | 235 / 240 | 236 / 238 | 39 / 635 |
| Case Report | 189 / 190 | 126 / 213 | 235 / 240 | 237 / 240 | 4 / 740 |
| Systematic Review | 190 / 190 | 112 / 233 | 215 / 233 | 237 / 240 | 1 / 785 |
| Meta-Analysis | 190 / 190 | 107 / 234 | 198 / 226 | 233 / 236 | 2 / 794 |
| Study Protocol | 188 / 188 | 147 / 217 | 216 / 238 | 175 / 232 | 0 / 799 |

**Estimates.** Each group's rate is weighted by the group's size. PubMed's precision is its right tags in "both"
and "only PubMed" over all its tags, ours likewise, and recall divides by all works that have the design, including
the ones neither side tags. For the intervals, each group's rate is drawn 4,000 times from its Jeffreys posterior,
Beta(k + ½, n − k + ½), and the estimates recomputed: we report the median draw and the 2.5th to 97.5th percentile.
Recall intervals are wide because the "neither" group is huge and its rate rests on a handful of works.

## Results

PubMed-indexed works, both sides on the same works (median, 95% interval):

| Study design | PubMed precision | OpenAlex precision | PubMed recall | OpenAlex recall |
|---|---|---|---|---|
| Randomized Controlled Trial | 65.4% (63.5–67.5) | 99.6% (98.5–99.8) | 89.4% (72.3–96.3) | 78.6% (63.7–85.4) |
| Clinical Trial | 67.5% (65.1–70.0) | 94.8% (92.9–96.3) | 62.6% (54.6–67.3) | 80.8% (70.8–87.1) |
| Observational Study | 88.9% (87.1–90.3) | 97.9% (95.7–99.2) | 3.1% (2.9–3.3) | 79.1% (73.9–83.8) |
| Case Report | 90.1% (88.3–91.8) | 99.2% (97.6–99.7) | 82.5% (75.1–86.9) | 80.2% (73.0–84.7) |
| Systematic Review | 92.2% (90.9–93.2) | 98.5% (97.4–99.1) | 78.2% (63.8–84.4) | 86.1% (70.0–92.8) |
| Meta-Analysis | 90.5% (89.2–91.7) | 99.2% (98.1–99.5) | 73.0% (50.0–90.9) | 69.7% (47.7–86.7) |
| Study Protocol | 97.8% (96.7–98.3) | 93.9% (91.2–96.1) | 34.5% (16.7–39.3) | 87.2% (42.1–98.3) |

PubMed's "Observational Study" tag exists only since 2014, which is most of the gap in that row's recall.

OpenAlex's precision outside MEDLINE, where PubMed has no tags, and over every work we tag:

| Study design | Not in MEDLINE | All works |
|---|---|---|
| Randomized Controlled Trial | 98.5% (96.8–99.4) | 98.9% (97.9–99.5) |
| Clinical Trial | 91.0% (87.0–94.3) | 92.2% (89.4–94.5) |
| Observational Study | 99.1% (97.4–99.8) | 98.6% (97.3–99.4) |
| Case Report | 98.7% (96.7–99.7) | 98.8% (97.6–99.5) |
| Systematic Review | 98.7% (96.7–99.6) | 98.6% (97.3–99.3) |
| Meta-Analysis | 98.7% (96.6–99.6) | 98.9% (97.8–99.5) |
| Study Protocol | 75.3% (69.7–80.5) | 81.2% (77.2–84.8) |

Study Protocol and Clinical Trial outside MEDLINE fall short of our 95% bar (see Known issues in the README). Of the
57 wrong protocol tags there, 53 came from the small model that tagged most of the backlog: its protocol tags are right
72% of the time (139 of 192), Jev's 90% (36 of 40).

Recall outside MEDLINE is not reported: randomized trials, meta-analyses and protocols are so rare there that
840 random works hold almost none, and the estimate would mean nothing.

## Checks

**Full text.** PubMed's indexers read the whole article, and our judge reads the abstract. So for the disagreement
groups we took up to 40 open-access papers each from Europe PMC (436 papers, 498 tags) and judged them again on the
full text, methods first, up to 24,000 characters:

| Tags | Tags checked | Right, judged on the abstract | Right, judged on the full text |
|---|---|---|---|
| Only PubMed | 247 | 83 | 86 |
| Only OpenAlex | 251 | 234 | 227 |

If each disagreement group moved the way its open-access papers did (plain ratios, not medians):

| Study design | PubMed, abstract | PubMed, full text | OpenAlex, abstract | OpenAlex, full text |
|---|---|---|---|---|
| Randomized Controlled Trial | 65.5% | 69.4% | 99.7% | 99.4% |
| Clinical Trial | 67.6% | 68.8% | 94.9% | 94.9% |
| Observational Study | 89.0% | 89.5% | 98.0% | 100.0% |
| Case Report | 90.3% | 90.3% | 99.3% | 98.3% |
| Systematic Review | 92.4% | 92.0% | 98.7% | 97.5% |
| Meta-Analysis | 90.7% | 90.3% | 99.4% | 99.3% |
| Study Protocol | 98.0% | 97.8% | 94.0% | 94.0% |

**Veterinary and twin tags.** Our trial and observational designs cover people only, and we count PubMed's "Twin
Study" as observational, so some of PubMed's tags count against it by our definitions rather than by its own.
Leaving those tags out changes PubMed's precision by less than half a point: randomized trials 65.4% to 65.8%,
clinical trials 67.5% to 67.8%, observational studies 88.9% to 89.0%.

**Old records.** PubMed's precision on randomized trials, by publication year: 64% before 2000, 61% from 2000 to
2014, 70% from 2015 on. The gap is not an artifact of old indexing.

**The 100 most-cited randomized trials, each side.** The judge flags 10 of PubMed's 100 most-cited
"Randomized Controlled Trial" works. Two of the ten we don't count against PubMed: the
[CARE trial](https://pubmed.ncbi.nlm.nih.gov/8801446/) is randomized but its abstract doesn't say so, and the
[enterotypes paper](https://pubmed.ncbi.nlm.nih.gov/21885731/) includes a small feeding study whose randomization we
could not settle. That leaves the eight in the README. The judge flags none of our 100 most-cited, but we know one is
wrong: the [Mini-Mental State paper](https://openalex.org/W1847168837) carries another paper's abstract in
OpenAlex, which fooled the tagger and the judge alike.

## Development set

The 5,069 works we used to build the tagger: stratified toward hard cases, split into dev (thresholds chosen) and
test (held out). Ids, pools and labels are in [`data/dev/`](data/dev/), with the tagger's cached answers, so
`python3 harness/certify.py` reproduces the certification without a Jev key. Every configuration we tried, including
the ones that failed, is in [`harness/LEDGER.md`](../harness/LEDGER.md).

The set was labelled by Claude Opus 5 when we built the tagger and again by Opus 5.5 for this release. The two agree
on 93.8% of designs and 99.5% of the "is this a randomized trial" answers. Precision at the shipped thresholds, dev and
test pooled (one-sided 95% lower bound in brackets):

| Study design | Bar | Opus 5 labels | Opus 5.5 labels | Recall (Opus 5.5) |
|---|---|---|---|---|
| Randomized Controlled Trial | 99% | 100.0% (99.5) | 99.5% (98.7) | 82.0% |
| Clinical Trial | 95% | 96.6% (95.5) | 96.0% (94.8) | 78.8% |
| Observational Study | 95% | 97.6% (96.3) | 97.8% (96.5) | 70.2% |
| Case Report | 95% | 99.5% (97.8) | 99.5% (97.8) | 76.2% |
| Systematic Review | 97% | 99.0% (98.0) | 99.0% (98.0) | 83.2% |
| Meta-Analysis | 98% | 100.0% (99.1) | 99.7% (98.5) | 78.6% |
| Study Protocol | 97% | 99.3% (97.9) | 98.9% (97.4) | 87.7% |

Under the newer judge, randomized trials and clinical trials fall just short of their bars. The development set is
mostly biomedical, which is why it did not show the protocol problem outside PubMed.

## Files

| File | What it holds |
|---|---|
| `data/pubmed/sample.jsonl.gz` | 7,742 works: OpenAlex id, DOI, PMID, PMCID, year, type, citations on 28 September 2026, the groups it was drawn for, PubMed's publication types, PubMed's and OpenAlex's values, which model tagged it, the judge's label and reason, and the full-text label where there is one |
| `data/pubmed/population.json` | Size of every group on 28 September 2026 |
| `data/pubmed/results.json` | Everything `score_pubmed.py` computes |
| `data/dev/` | The development set (see above) |
| `score_pubmed.py` | Every table on this page, standard library only |
