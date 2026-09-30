# Benchmarks

Every number in the main [README](../README.md), how we got it, and how to check it. Everything here is rebuilt by

```
python3 benchmarks/score_pubmed.py                            # the benchmark (data/pubmed)
python3 benchmarks/score_pubmed.py --data thresholds_sample   # the sample the served thresholds were chosen on
python3 benchmarks/score_pubmed.py --data rct_check_sample    # the sample that certified them and exposed the RCT gap
```

from files in `data/`: ids, both sides' tags, the judge's label and reason, the RCT check's answer, and the size of
every group sampled from. No abstract text is included, because publishers own it; `tagger/fetch_works.py` rebuilds
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

On the benchmark the judge answered "unknown" (the text says too little) on 118 works and refused 24. Both are left
out; counting "unknown" as wrong moves no number by more than 1.5 points.

## Three samples

**We tuned on two samples and report the third.** All three were drawn from the live index on 28 September 2026 the
same way, and none overlaps another or the development set.

| Sample | Works | What it was for | OpenAlex's tags in it |
|---|---|---|---|
| [`data/thresholds_sample`](data/thresholds_sample/) | 7,742 | Showed where the first release fell short; chose the served thresholds | as served 26 to 28 September |
| [`data/rct_check_sample`](data/rct_check_sample/) | 8,299 | Certified the thresholds; its RCT errors shaped the RCT check | served thresholds, no RCT check |
| [`data/pubmed`](data/pubmed/) | 8,308 | **The benchmark.** Nothing was tuned on it | as served from 29 September |

## The benchmark sample

**Stratified on the live index, weighted back to the whole.** For each design, works in MEDLINE (PubMed's indexed
journals) fall into four groups: both sides tag it, only PubMed does, only OpenAlex does, or neither does. We sampled
the first three directly and estimated the fourth from 840 random MEDLINE works. Works outside MEDLINE that OpenAlex
tags were sampled for each design too, plus 840 random works outside MEDLINE.

Works in each group (the population):

| Study design | Both tag it | Only PubMed | Only OpenAlex | OpenAlex, not in MEDLINE |
|---|---|---|---|---|
| Randomized Controlled Trial | 310,072 | 349,207 | 7,143 | 305,712 |
| Clinical Trial | 505,125 | 509,802 | 169,300 | 1,190,553 |
| Observational Study | 176,219 | 39,757 | 4,855,411 | 9,457,578 |
| Case Report | 1,284,191 | 377,686 | 185,982 | 1,689,872 |
| Systematic Review | 348,044 | 59,820 | 71,890 | 727,098 |
| Meta-Analysis | 197,562 | 40,951 | 10,359 | 176,707 |
| Study Protocol | 21,375 | 2,718 | 30,299 | 54,324 |

25,907,179 MEDLINE works and 140,063,970 other works were tagged.

| Study design | Both | Only PubMed | Only OpenAlex | OpenAlex, not in MEDLINE | Random MEDLINE works, neither tags it |
|---|---|---|---|---|---|
| Randomized Controlled Trial | 238 / 238 | 71 / 236 | 404 / 405 | 438 / 440 | 1 / 788 |
| Clinical Trial | 184 / 190 | 61 / 187 | 272 / 283 | 333 / 338 | 9 / 765 |
| Observational Study | 188 / 190 | 88 / 187 | 282 / 289 | 331 / 340 | 36 / 636 |
| Case Report | 188 / 190 | 94 / 170 | 281 / 285 | 333 / 339 | 9 / 752 |
| Systematic Review | 189 / 190 | 79 / 186 | 257 / 281 | 334 / 339 | 0 / 792 |
| Meta-Analysis | 189 / 190 | 60 / 182 | 233 / 257 | 325 / 333 | 0 / 799 |
| Study Protocol | 185 / 185 | 139 / 156 | 285 / 286 | 327 / 337 | 0 / 807 |

**Estimates.** Each group's rate is weighted by the group's size. PubMed's precision is its right tags in "both"
and "only PubMed" over all its tags, ours likewise, and recall divides by all works that have the design, including
the ones neither side tags. For the intervals, each group's rate is drawn 4,000 times from its Jeffreys posterior,
Beta(k + ½, n − k + ½), and the estimates recomputed: we report the median draw and the 2.5th to 97.5th percentile.
Recall intervals are wide because the "neither" group is huge and its rate rests on a handful of works.

## Results

PubMed-indexed works, both sides on the same works (median, 95% interval):

| Study design | PubMed precision | OpenAlex precision | PubMed recall | OpenAlex recall |
|---|---|---|---|---|
| Randomized Controlled Trial | 62.9% (59.8–66.1) | 99.9% (99.0–100.0) | 90.4% (72.4–97.6) | 68.7% (55.1–75.9) |
| Clinical Trial | 64.5% (61.0–68.2) | 96.5% (94.2–98.1) | 58.9% (48.3–68.4) | 58.5% (47.7–68.1) |
| Observational Study | 89.3% (87.2–90.8) | 97.6% (95.5–98.9) | 3.2% (2.9–3.4) | 80.3% (75.2–84.9) |
| Case Report | 88.9% (86.6–90.9) | 98.8% (96.8–99.7) | 75.8% (67.5–82.1) | 74.5% (66.2–80.8) |
| Systematic Review | 91.0% (89.2–92.2) | 98.0% (96.4–98.8) | 83.5% (71.5–85.2) | 92.5% (79.4–94.7) |
| Meta-Analysis | 87.9% (86.2–89.2) | 98.9% (97.2–99.5) | 92.5% (70.0–95.7) | 90.6% (68.6–94.4) |
| Study Protocol | 98.6% (97.4–99.1) | 99.6% (98.8–99.9) | 38.5% (17.3–44.1) | 83.5% (37.7–95.5) |

OpenAlex precision on works outside MEDLINE, and on every tagged work

| Study design | Not in MEDLINE | All works |
|---|---|---|
| Randomized Controlled Trial | 99.5% (98.5–99.9) | 99.7% (99.1–99.9) |
| Clinical Trial | 98.5% (96.8–99.4) | 97.7% (96.4–98.7) |
| Observational Study | 97.3% (95.2–98.7) | 97.3% (95.9–98.4) |
| Case Report | 98.2% (96.5–99.2) | 98.4% (97.2–99.2) |
| Systematic Review | 98.5% (96.8–99.4) | 98.3% (97.1–99.0) |
| Meta-Analysis | 97.6% (95.5–98.9) | 98.2% (97.0–99.0) |

PubMed's "Observational Study" tag exists only since 2014, which is most of the gap in that row's recall. Recall
outside MEDLINE is not reported: randomized trials, meta-analyses and protocols are so rare there that 840 random
works hold almost none.

## How the first release fell short, and what changed

**The first release was certified on the development set, which did not look like the works we tag.** 60% of its
works had a PubMed ID, 295 of its 321 protocols came from PubMed, and its candidates were picked by the tagger's own
earlier answers. Two thirds of our protocol and clinical-trial tags are on works outside PubMed: dissertations,
research plans, lab methods, descriptive case series. On the first sample (as served 26 to 28 September):

| Study design | PubMed precision | OpenAlex precision | PubMed recall | OpenAlex recall |
|---|---|---|---|---|
| Randomized Controlled Trial | 65.4% (63.5–67.5) | 99.6% (98.5–99.8) | 89.4% (72.3–96.3) | 78.6% (63.7–85.4) |
| Clinical Trial | 67.5% (65.1–70.0) | 94.8% (92.9–96.3) | 62.6% (54.6–67.3) | 80.8% (70.8–87.1) |
| Observational Study | 88.9% (87.1–90.3) | 97.9% (95.7–99.2) | 3.1% (2.9–3.3) | 79.1% (73.9–83.8) |
| Case Report | 90.1% (88.3–91.8) | 99.2% (97.6–99.7) | 82.5% (75.1–86.9) | 80.2% (73.0–84.7) |
| Systematic Review | 92.2% (90.9–93.2) | 98.5% (97.4–99.1) | 78.2% (63.8–84.4) | 86.1% (70.0–92.8) |
| Meta-Analysis | 90.5% (89.2–91.7) | 99.2% (98.1–99.5) | 73.0% (50.0–90.9) | 69.7% (47.7–86.7) |
| Study Protocol | 97.8% (96.7–98.3) | 93.9% (91.2–96.1) | 34.5% (16.7–39.3) | 87.2% (42.1–98.3) |

Outside MEDLINE, Clinical Trial was 91%, Study Protocol 75% and Randomized Controlled Trial 98.5%. 53 of the 57
wrong protocol tags came from the small model that tagged most of the backlog.

**Fix 1, served thresholds.** On the stored scores, nothing re-tagged: Randomized Controlled Trial 0.95 (was 0.90),
Clinical Trial 0.97 (Jev 0.90, small model 0.86), Study Protocol 0.95 (Jev 0.90, small model 0.65). Text rules for
clinical trials (trial words, "retrospective") did worse than the plain threshold. The second sample certified them,
except randomized trials outside MEDLINE:


| Study design | Not in MEDLINE | All works |
|---|---|---|
| Randomized Controlled Trial | 98.6% (97.2–99.4) | 99.0% (98.0–99.5) |
| Clinical Trial | 97.6% (95.7–98.9) | 97.9% (96.6–98.8) |
| Observational Study | 98.7% (97.3–99.6) | 98.5% (97.4–99.2) |
| Case Report | 99.7% (98.6–100.0) | 99.0% (98.0–99.6) |
| Systematic Review | 97.3% (95.1–98.7) | 97.9% (96.5–98.8) |
| Meta-Analysis | 97.3% (95.2–98.6) | 98.4% (97.3–99.0) |

**Fix 2, the RCT check.** Most remaining RCT errors were digests, journal-club pieces and commentaries that reprint
another trial's abstract. A venue rule caught 5 of 60 and dropped 4 right tags; an extra Jev question and
title-abstract word overlap did no better. Claude Sonnet 5 reading each RCT-tagged work ([`tagger/rct_check.py`](../tagger/rct_check.py))
removed 43 of 58 wrong tags and 11 of 2,054 right ones on the two tuning samples (Claude Haiku 4.5: 14 of 60). It now
checks every RCT tag, 627,013 at launch; it said no to 4,296 of them. Where it says no we tag neither Randomized
Controlled Trial nor Clinical Trial.

## PubMed's tags on works with no abstract

642,057 works have no abstract, so the tagger never runs on them; until 29 September they carried PubMed's tags alone.
PubMed rarely has their abstract either. We judged 150 per design on the title, the venue and, for the 45 that are open access, the full
text:

| PubMed-only tag | Sampled | Too little text to decide | Right, where the judge could decide |
|---|---|---|---|
| Randomized Controlled Trial | 150 | 104 | 17 of 46 |
| Clinical Trial | 150 | 109 | 21 of 41 |
| Observational Study | 150 | 61 | 76 of 89 |
| Case Report | 150 | 64 | 81 of 86 |
| Systematic Review | 150 | 35 | 103 of 115 |
| Meta-Analysis | 150 | 38 | 49 of 112 |
| Study Protocol | 54 | 4 | 42 of 50 |

None clears our bar, so from 29 September these works carry no study design.

## Checks on PubMed

These ran on the first sample (`thresholds_sample`, 7,742 works). They test PubMed's tags, which do not depend on our
thresholds.

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
"Randomized Controlled Trial" works. We checked each one three ways: PubMed's current record, the paper's text (the
full text where it is open), and two models (Claude Opus 5.5 and Sonnet 5) applying PubMed's own definition of a
randomized controlled trial. Five hold up on every check and are in the README. Five we don't count against PubMed:
the [CARE trial](https://pubmed.ncbi.nlm.nih.gov/8801446/) is randomized but its abstract doesn't say so; the
[enterotypes paper](https://pubmed.ncbi.nlm.nih.gov/21885731/) includes a small feeding study whose randomization we
could not settle; the [anti-PD-1 phase 1 study](https://pubmed.ncbi.nlm.nih.gov/22658127/) randomized its dose cohorts,
which only its full text says; the [HPV paper](https://pubmed.ncbi.nlm.nih.gov/20530316/) reports its trial's randomized
comparison; and the [WOMAC validation study](https://pubmed.ncbi.nlm.nih.gov/3068365/) uses a trial's data, which makes
the tag arguable. Under the rule served from 29 September, the judge supports all of our 100
most-cited randomized trials.

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
| `data/<sample>/sample.jsonl.gz` | One row per work: OpenAlex id, DOI, PMID, PMCID, year, type, citations on 28 September 2026, the groups it was drawn for, PubMed's publication types, PubMed's and OpenAlex's values, which model tagged it, the judge's label and reason, the full-text label where there is one, and the RCT check's answer where there is one |
| `data/<sample>/population.json` | Size of every group on 28 September 2026, and which rule the sample's OpenAlex tags follow |
| `data/<sample>/results.json` | Everything `score_pubmed.py` computes |
| `data/dev/` | The development set (see above) |
| `score_pubmed.py` | Every table on this page, standard library only |
