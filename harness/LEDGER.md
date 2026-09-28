# Ledger: every configuration tried

The tagger was built by a loop: write a hypothesis as a config (`configs/`), run it once over the development set,
score it the same way as every other config, keep it only if it moves the number. This is every config that ran,
failures included, in the order they ran.

**The number.** For each class, recall on the dev split at the lowest threshold whose one-sided 95% lower bound on
precision clears the class's bar (RCT 0.99, Meta-Analysis 0.98, Systematic Review and Study Protocol 0.97, the rest
0.95), with at least 20 positives; "—" means no threshold clears the bar. Recall is relative to the development set,
which oversamples hard cases. Adoption was checked on the held-out test split (`holdout.py`).

**Two answer keys.** Wave 1 (rows 1 to 20) was scored against the labels of a first rubric, written before the
field had its own definitions. Those labels showed the judge itself was inconsistent at two boundaries (case series of
6 to 22 patients; non-clinical empirical studies), so the rubric was rewritten as the schema's definitions
(`rubric_v2.py`) and every work was judged again: that is `label_opus_5`, the key of wave 2 and of the certification.
The first rubric's labels are not in this repo; the last table rescores every config on the final key, from the
cached answers, in two seconds (`python harness/compare.py --split dev`).

## The configs

| # | Config | Hypothesis | Result on dev at the time | Verdict |
|---|---|---|---|---|
| 1 | `v1` | Baseline: the first version of the request (12-option Choice, two short yes/no questions) | RCT 0.857; Study Protocol never clears | Baseline |
| 2 | `h5_features` | Code-extracted facts in the input (registry ids, "randomized" in the title, abstract sections, length, type, year, language) help Jev | RCT 0.841; Protocol clears for the first time (0.850); Meta-Analysis stops clearing | Dropped: helped Protocol only; the option texts of row 10 did more |
| 3 | `h3_sinks` | Extra "sink" options (secondary analysis, trial follow-up, economic modelling) pull confusers out of the trial classes | RCT 0.829; Systematic Review 0.651 | Idea kept: a secondary-analysis sink is in the shipped request |
| 4 | `h2_conj` | RCT must pass three yes/no questions (randomised allocation, primary report, human participants) | RCT 0.801 | Dropped: within noise, two more questions |
| 5 | `h10_rule` | A stricter, more explicit rule text | RCT 0.792; Meta-Analysis never clears | Dropped |
| 6 | `h7_paraphrase` | Three phrasings of the RCT question, keep the minimum | RCT 0.827 | Dropped: within noise |
| 7 | `h6_order` | Put the Methods sentences of a structured abstract first | RCT 0.797 | Dropped |
| 8 | `h4_atomic` | Eight yes/no questions, classes derived by rules, instead of one Choice | RCT and Meta-Analysis never clear; Systematic Review 0.485 | Dropped: worse almost everywhere |
| 9 | `h12_title_only` | How far a title alone goes (coverage for works without an abstract) | RCT never clears; Systematic Review 0.710; Protocol 0.762 | Not shipped: titles carry syntheses and protocols, not trials |
| 10 | `h14_scope` | Option texts sharpened from the dev failures (the paper must do the synthesis itself; commentaries are editorials; protocols need participants; case reports are a handful of patients) | Meta-Analysis 0.65 to 0.81; Systematic Review 0.58 to 0.82; Protocol 0.927; RCT 0.811 | Kept: the biggest gain of wave 1 |
| 11 | `h15_nrt` | Row 10 plus a sharper line between non-randomised trials (investigators assign the intervention) and observational series | RCT 0.834; every class clears on the pooled set; test: RCT 1 false positive in 245 | Kept: the wave-1 candidate; its texts became rubric v2 |
| 12 | `h15b_nrt_v1rct` | Attribution: row 11 with the first rule and RCT text, to see what moved RCT recall | RCT 0.843 | Attribution only: the difference is within noise |
| 13 | `h16_rctnoul` | A longer RCT question naming follow-up and extension reports as RCTs and secondary analyses as not | RCT 0.722 | Dropped: long yes/no questions cost recall |
| 14 | `h_combo1` | Rows 5 + 2 + 3 + 4 together | RCT 0.680 | Dropped |
| 15 | `h_combo2` | Rows 10 + 2 + a primary-report gate + a sink | RCT 0.743; Clinical Trial 0.525 | Dropped |
| 16 | `e_mean` | Offline average of four configs' scores (no new calls) | RCT 0.876 | Dropped with row 17 |
| 17 | `e_div3` | Offline average of three different configs (rows 8, 15, 11) | RCT 0.883; test at the dev threshold: 4 RCT false positives (0.984) | Dropped: the dev gain was threshold noise |
| 18 | `g_run1` | Automatic prompt search (GEPA over the rule, the option texts and the two questions, seeded with row 11; 40 candidates) | Search score flat (0.8614 vs 0.8612); its long RCT question cut RCT recall 0.834 to 0.673 | Dropped; three of its option texts went to row 19 |
| 19 | `g_mix` | Row 11 plus the search's observational, case-report and other-primary texts, short RCT question kept | Observational on test 0.456 to 0.596; RCT on test 3 false positives in 250 | Texts kept for rubric v2; not shipped for RCT |
| 20 | `h15_nrt` on `jev-latest` | Does a newer Jev snapshot help? | RCT 0.825 vs 0.834; the rest within noise | Stay pinned to `jev-1.13.0` |
| 21 | `r2_base` | The request built straight from rubric v2 (13 options with a secondary-analysis sink, the rubric's longer RCT question) | RCT never clears: 12 of its 15 false positives at 0.90 are trials that never say "randomised" | Dropped for row 22 |
| 22 | `r2_shortnoul` | Rubric v2 options with the first version's one-clause RCT question | RCT never clears (12 of 13 false positives at 0.90 never say "randomised"); every other class up | Kept: **the request that ships** |
| 23 | `r2_gate` | A code gate: no RCT unless the text states randomisation (a regex in ten languages) | RCT clears again (0.744) | Kept |
| 24 | `r2_gate2` | A second gate: no RCT when the title says simulation, manikin, phantom, cadaver or in vitro | RCT 0.739; on the first 4,282 re-judged works, pooled: 0 false positives in 537 | Kept |
| 25 | `r2_v3` | Two more yes/no questions as gates (health outcome; prospective assignment) instead of code | Clinical Trial 0.134 (from 0.800) | Dropped: the fourth time an extra question moved every other answer |
| 26 | `r2_gate3` | A third gate: no RCT when the title reads as a secondary analysis | First draft also removed 4 judged primary reports ("results from a randomized ...") | Narrowed into row 27 |
| 27 | `r2_gate4` | The narrowed secondary-analysis gate (removes 0 of 669 judged RCTs) | RCT 0.831 at 0.90; test: RCT 1.000 precision, 0 false positives in 230 | **Ships** (`tagger/study_design.py`) |

Two more experiments ran outside `configs/`. A second-stage verifier (a Claude model asked two focused questions on the
140 dev works with an RCT score between 0.5 and 0.9) accepted 52 at 0.846 precision; its "false positives" were the
rubric's grey zone (randomised order of stimuli, secondary analyses restating the parent trial), so RCT recall of about
0.80 to 0.85 at 0.99 precision was the ceiling under that rubric and the lever was the rubric itself. And, before this
loop, putting several works in one request flipped 7% of answers at eight works per request.

## Wave 1 at the time (first answer key)

Recall at the bar on the dev split, as measured then (rows 1 to 20):

| Config | RCT | Meta-Analysis | Systematic Review | Study Protocol | Clinical Trial | Case Report | Observational | Other primary |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `v1` | 0.857 | 0.654 | 0.583 | — | 0.694 | 0.760 | 0.587 | 0.731 |
| `h5_features` | 0.841 | — | 0.707 | 0.850 | 0.729 | 0.754 | 0.643 | 0.752 |
| `h3_sinks` | 0.829 | 0.623 | 0.651 | — | 0.736 | 0.743 | 0.532 | 0.702 |
| `h2_conj` | 0.801 | 0.649 | 0.580 | — | 0.709 | 0.766 | 0.614 | 0.719 |
| `h10_rule` | 0.792 | — | 0.712 | — | 0.690 | 0.784 | 0.559 | 0.720 |
| `h7_paraphrase` | 0.827 | 0.654 | 0.588 | — | 0.689 | 0.766 | 0.595 | 0.701 |
| `h6_order` | 0.797 | — | 0.666 | — | 0.690 | 0.707 | 0.603 | 0.723 |
| `h4_atomic` | — | — | 0.485 | 0.756 | 0.584 | — | 0.436 | 0.700 |
| `h12_title_only` | — | — | 0.710 | 0.762 | — | — | — | 0.409 |
| `h14_scope` | 0.811 | 0.811 | 0.820 | 0.927 | 0.549 | 0.749 | 0.597 | 0.728 |
| `h15_nrt` | 0.834 | 0.785 | 0.822 | 0.933 | 0.722 | 0.749 | 0.478 | 0.720 |
| `h15b_nrt_v1rct` | 0.843 | 0.803 | 0.783 | 0.860 | 0.746 | 0.754 | — | 0.720 |
| `h16_rctnoul` | 0.722 | 0.811 | 0.817 | 0.927 | 0.680 | 0.760 | — | 0.721 |
| `h_combo1` | 0.680 | — | 0.737 | 0.813 | 0.670 | 0.814 | 0.499 | 0.735 |
| `h_combo2` | 0.743 | 0.785 | 0.788 | 0.917 | 0.525 | 0.766 | 0.470 | 0.706 |
| `e_mean` | 0.876 | 0.776 | 0.720 | 0.813 | 0.757 | 0.772 | 0.658 | 0.756 |
| `e_div3` | 0.883 | 0.789 | 0.822 | 0.902 | 0.772 | 0.778 | 0.589 | 0.744 |
| `g_run1` | 0.673 | 0.825 | 0.824 | 0.927 | 0.670 | 0.749 | 0.589 | 0.788 |
| `g_mix` | 0.848 | 0.807 | 0.827 | 0.922 | 0.684 | 0.766 | 0.591 | 0.782 |
| `h15_nrt` on `jev-latest` | 0.825 | 0.811 | 0.815 | 0.927 | 0.737 | 0.754 | 0.480 | 0.728 |

## Every config on the final answer key

The same cached answers rescored on `label_opus_5` (dev split; `python harness/compare.py --split dev`). The final key
requires an RCT to state randomisation, so no config without the code gate clears the RCT bar; the rubric's own texts
(rows 21 to 27) lift Observational and other primary research more than any prompt change did.

| Config | RCT | Meta-Analysis | Systematic Review | Study Protocol | Clinical Trial | Case Report | Observational | Other primary |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `v1` | — | — | 0.588 | — | 0.605 | 0.662 | — | 0.706 |
| `h5_features` | — | — | — | 0.854 | 0.614 | 0.682 | — | 0.722 |
| `h3_sinks` | — | — | 0.576 | — | 0.723 | — | 0.504 | 0.705 |
| `h2_conj` | 0.729 | — | 0.586 | — | 0.601 | — | — | 0.684 |
| `h10_rule` | — | — | — | — | 0.605 | — | — | 0.661 |
| `h7_paraphrase` | 0.688 | — | 0.593 | — | 0.548 | 0.669 | — | 0.688 |
| `h6_order` | — | — | 0.598 | — | 0.602 | 0.662 | — | 0.698 |
| `h4_atomic` | 0.775 | — | 0.491 | 0.760 | 0.602 | — | 0.285 | 0.686 |
| `h12_title_only` | — | — | — | 0.766 | — | — | — | 0.395 |
| `h14_scope` | — | 0.759 | 0.794 | 0.932 | — | 0.669 | 0.548 | 0.809 |
| `h15_nrt` | — | 0.711 | 0.782 | 0.938 | 0.641 | 0.656 | 0.546 | 0.824 |
| `h15b_nrt_v1rct` | — | 0.689 | 0.792 | 0.917 | 0.637 | 0.605 | — | 0.808 |
| `h16_rctnoul` | — | 0.711 | 0.789 | 0.932 | 0.575 | 0.643 | 0.476 | 0.824 |
| `h_combo1` | — | — | — | 0.818 | 0.633 | — | 0.491 | 0.749 |
| `h_combo2` | — | 0.702 | 0.799 | 0.922 | 0.464 | 0.669 | 0.581 | 0.824 |
| `e_mean` | — | 0.596 | 0.692 | 0.818 | 0.669 | 0.662 | 0.544 | 0.750 |
| `e_div3` | — | — | 0.801 | 0.906 | 0.702 | 0.586 | 0.601 | 0.834 |
| `g_run1` | — | 0.711 | 0.804 | 0.932 | 0.630 | 0.688 | 0.601 | 0.838 |
| `g_mix` | — | 0.715 | 0.789 | 0.927 | 0.630 | 0.662 | 0.594 | 0.829 |
| `h15_nrt` on `jev-latest` | — | 0.719 | 0.787 | 0.932 | 0.607 | 0.643 | 0.546 | 0.814 |
| `r2_base` | — | 0.759 | 0.841 | 0.901 | 0.764 | 0.745 | 0.708 | 0.869 |
| `r2_shortnoul` | — | 0.754 | 0.829 | 0.911 | 0.800 | 0.752 | 0.735 | 0.876 |
| `r2_gate` | 0.744 | 0.754 | 0.829 | 0.911 | 0.800 | 0.752 | 0.735 | 0.876 |
| `r2_gate2` | 0.739 | 0.754 | 0.829 | 0.911 | 0.800 | 0.752 | 0.735 | 0.876 |
| `r2_v3` | — | 0.746 | 0.841 | 0.911 | 0.134 | 0.739 | 0.724 | 0.869 |
| `r2_gate3` | 0.831 | 0.754 | 0.829 | 0.911 | 0.800 | 0.752 | 0.735 | 0.876 |
| `r2_gate4` | 0.831 | 0.754 | 0.829 | 0.911 | 0.800 | 0.752 | 0.735 | 0.876 |

`r2_gate3` scores like `r2_gate4` here because its draft regex was narrowed in place in `textsig.py`. `r2_gate` and
`r2_gate2` clear RCT only at 0.94: one secondary analysis titled "Safety data from a randomized controlled trial"
scores 0.93, which the third gate removes. The shipped Protocol threshold is 0.90, not the 0.74 the dev split picks;
see `harness/certify.py`.

## What the loop taught

1. **Failure mining beat every generic trick.** Reading the dev false positives and writing one sharper line per
   cluster (rows 10, 11) moved Meta-Analysis, Systematic Review and Protocol by 15 to 35 points. Stricter rules,
   conjunctions, paraphrases, reordering and an automatic prompt search moved RCT within noise.
2. **Keep yes/no questions to one clause, and add none without re-certifying.** Long questions with caveats cost 11
   and 16 points of RCT recall (rows 13 and 18). Extra questions in the request hurt four times, the last one worst
   (row 25: Clinical Trial 0.800 to 0.134).
3. **Put literal checks in code.** Under a rubric that requires stated randomisation, a regex gate plus Jev's
   calibrated RCT score is the cheapest possible verifier, and it fixed what no prompt did (rows 23 to 27).
4. **A consistent answer key moves more than a prompt.** Rewriting the rubric as the schema's own definitions lifted
   Observational recall from 0.47 to 0.71 and other primary research from 0.73 to 0.86 (pooled, at the time).
5. **Pick thresholds on dev, check on test.** Ensembles looked best on dev and failed the RCT bar on test (row 17).
