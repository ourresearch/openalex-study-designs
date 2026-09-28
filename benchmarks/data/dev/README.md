# The development set

5,069 OpenAlex works, each judged by an Opus model under the rubric in `harness/rubric_v2.py`. The tagger was built
and certified on this set: every configuration in `harness/LEDGER.md` was scored on it, and each class's threshold was
fixed on its `dev` split (3,053 works), then checked on the held-out `test` split (2,016 works). It is not a random
sample of OpenAlex: it oversamples the hard cases on purpose (see Pools), so its recall numbers are relative to this
pool, not to the corpus.

The files hold ids, labels and model outputs only. No titles or abstracts (publishers hold their copyright);
`python -m tagger.fetch_works --ids benchmarks/data/dev/dev_set.jsonl.gz --out works.jsonl` rebuilds them from the
OpenAlex API. In September 2026 it returned 5,057 of the 5,069 works (12 have since been deleted), with the same
abstract as the tagger read for 5,051 and the same answer on all three RCT gates for all 5,057.

## Files

`dev_set.jsonl.gz`, one row per work:

| Field | What |
|---|---|
| `work_id` | OpenAlex id (`W...`) |
| `doi`, `pmid` | when known (DOI 4,215 works, PMID 3,033) |
| `pool` | how the work was drawn (below) |
| `split` | `dev` (thresholds are chosen here) or `test` (held out) |
| `label_opus_5` | the judge's study design, one of 13 (`harness/judge_prompt.md`); **the answer key the tagger was certified on** |
| `is_rct_opus_5`, `human_subjects_opus_5` | the judge's two yes/no answers; RCT truth follows `is_rct` |
| `reason_opus_5` | the judge's one-line reason |
| `model_opus_5` | `claude-opus-5`, or `claude-fable-5-1` for the 6 works Opus refused |
| `label_opus_5_5` ... `model_opus_5_5` | the same from a re-judge with `claude-opus-5-5` (same prompt, effort medium); null for the 5 works both models refused |

The two judges agree on the design for 4,748 of 5,064 works (93.8%) and on `is_rct` for 99.5%.

`dev_jev_outputs.jsonl.gz`: the shipped tagger's cached answers, one per work: Jev's 13 Choice probabilities and two
yes/no scores (`answers`), the three RCT gate answers computed from the text (`gates`), the eight class scores after
the gates (`scores`), and the values at the shipped thresholds (`values` as served; `tagger_values` also keeps
other-primary-research). `harness/certify.py` and `tagger/check_same.py` read it.

`dev_student_outputs.jsonl.gz`: the student's outputs on the same works (probabilities, scores, `route`, `values`),
from the released weights. `student/certify.py` reads it.

## Pools

The works come from a stratified sample of 200,000 OpenAlex works with abstracts (strata by PubMed publication type,
language and script, field, publication year and work type), from the part of it held out from every model trained on
it. An earlier version of the tagger (close to `harness/configs/v1.py`) scored every work in the sample; the pools
below were then filled in this order, a work going to the first pool whose rule it meets, no stratum taking more than
45% of a pool. The last four pools come from an earlier, 1,000-work judged set and were re-judged here.

| Pool | Works | Rule |
|---|---:|---|
| `rct_candidates` | 1,107 | the earlier tagger's RCT probability ≥ 0.1 |
| `pubmed_rct_low_score` | 90 | PubMed tags it Randomized Controlled Trial, the earlier tagger's RCT probability < 0.1 |
| `randomized_in_title` | 120 | "randomised" / "randomized" in the title, the earlier tagger's RCT probability < 0.1 |
| `nonrandomized_trial_candidates` | 400 | the earlier tagger's non-randomised-trial probability ≥ 0.3 |
| `protocol_candidates` | 251 | protocol probability ≥ 0.3 |
| `systematic_review_candidates` | 350 | systematic-review probability ≥ 0.3 |
| `meta_analysis_candidates` | 302 | meta-analysis probability ≥ 0.3 |
| `observational_candidates` | 400 | observational probability ≥ 0.3 |
| `case_report_candidates` | 350 | case-report probability ≥ 0.3 |
| `other_primary_research_candidates` | 300 | other-primary-research probability ≥ 0.5, from the sample's random strata |
| `random` | 400 | the sample's random strata (works with an abstract, by publication year and work type) |
| `pubmed_tagged` | 400 | 40 MEDLINE records each tagged RCT, Clinical Trial, Clinical Trial Protocol, Guideline, Meta-Analysis, Systematic Review, Observational Study, Case Reports, Review, and Editorial / Letter / Comment |
| `pubmed_untyped_recent` | 299 | 2023 or later, PubMed tags only "Journal Article" (MEDLINE, or not yet indexed) |
| `biomedical_not_in_pubmed` | 200 | English health and life-sciences articles and reviews with no PMID |
| `non_english` | 100 | 25 each: Latin-script languages other than English, Chinese / Japanese / Korean, Cyrillic, other scripts |

The split is 60 / 40 within each pool and stratum. Judge counts (Opus 5): other primary research 1,232, observational
738, RCT 669, non-randomised trial 517, meta-analysis 370, protocol 321, systematic review 313, narrative review 285,
case report 267, editorial or letter 130, secondary analysis 130, unknown 51, guideline 46.

## License

CC0, like all OpenAlex data.
