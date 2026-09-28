# Reproduce

Every number here comes from files in the repo: Jev's answers, the judge's labels and the student's outputs are
cached, so no path below needs a Jev key, an Anthropic key, a GPU or any private resource until you choose to call a
model yourself. The repo holds no titles or abstracts; `tagger/fetch_works.py` rebuilds them from the public OpenAlex
API when a step needs text.

You need Python 3.10 or later.

```bash
git clone https://github.com/ourresearch/openalex-study-designs
cd openalex-study-designs
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

## The development set and the certification (seconds, a laptop)

```bash
python harness/certify.py
```

scores the shipped tagger's cached answers on the 5,069 judged works (`benchmarks/data/dev/`) through
`tagger/study_design.py` itself, at the shipped thresholds, against the Opus 5 labels. It should print:

```
| Class | bar | t | positives | FP | precision | one-sided 95% lower | recall |
|---|---|---|---|---|---|---|---|
| rct | 0.99 | 0.90 | 555 | 0 | 1.0000 | 0.9951 | 0.830 |
| meta_analysis | 0.98 | 0.97 | 292 | 0 | 1.0000 | 0.9908 | 0.789 |
| systematic_review | 0.97 | 0.88 | 579 | 6 | 0.9896 | 0.9801 | 0.839 |
| protocol | 0.97 | 0.90 | 280 | 2 | 0.9929 | 0.9786 | 0.866 |
| clinical_trial | 0.95 | 0.90 | 962 | 33 | 0.9657 | 0.9547 | 0.783 |
| case_report | 0.95 | 0.97 | 204 | 1 | 0.9951 | 0.9783 | 0.760 |
| observational | 0.95 | 0.82 | 550 | 13 | 0.9764 | 0.9631 | 0.728 |
| other_primary_research | 0.95 | 0.30 | 1099 | 33 | 0.9700 | 0.9603 | 0.865 |
```

Positives are works at or over the threshold; a false positive is one the judge says is not that class. The bound is
the one-sided 95% Wilson lower bound on precision, which is what each bar is checked against. Recall is relative to
the development set, which oversamples hard cases (`benchmarks/data/dev/README.md`).

More from the same files:

| Command | What it shows |
|---|---|
| `python harness/certify.py --judge opus-5.5` | the same answers against an independent re-judge by Opus 5.5 |
| `python harness/certify.py --thresholds dev` | thresholds re-picked on the dev split (Protocol picks 0.74; the shipped 0.90 comes from the pooled curve) |
| `python harness/holdout.py --configs r2_gate4` | thresholds from dev, scored on the held-out test split only (RCT: 0 false positives in 230) |
| `python -m tagger.check_same` | the public module derives exactly what the certified config derives: 0 mismatches on 5,069 answers |

Against the Opus 5.5 labels, at the same thresholds:

```
| rct | 0.99 | 0.90 | 555 | 3 | 0.9946 | 0.9866 (point ok, bound short) | 0.820 |
| meta_analysis | 0.98 | 0.97 | 292 | 1 | 0.9966 | 0.9848 | 0.786 |
| systematic_review | 0.97 | 0.88 | 579 | 6 | 0.9896 | 0.9801 | 0.832 |
| protocol | 0.97 | 0.90 | 280 | 3 | 0.9893 | 0.9735 | 0.877 |
| clinical_trial | 0.95 | 0.90 | 962 | 39 | 0.9595 | 0.9476 (point ok, bound short) | 0.788 |
| case_report | 0.95 | 0.97 | 203 | 1 | 0.9951 | 0.9782 | 0.762 |
| observational | 0.95 | 0.82 | 550 | 12 | 0.9782 | 0.9654 | 0.702 |
| other_primary_research | 0.95 | 0.30 | 1095 | 61 | 0.9443 | 0.9318 <-- BELOW BAR | 0.898 |
```

The two judges agree on the design of 93.8% of works and on "is this paper itself an RCT" for 99.5%. The thresholds
were fixed on the Opus 5 labels and were not re-tuned.

## The tagger

`tagger/study_design.py` is the module OpenAlex runs: the request (the rule, 13 option texts, two yes/no questions),
the derivation, the three RCT gates, the thresholds and the PubMed mapping.

**Check it** without text (seconds) or with the text rebuilt from the API (a minute, about 50 API calls):

```bash
python -m tagger.check_same
python -m tagger.fetch_works --ids benchmarks/data/dev/dev_set.jsonl.gz --out works.jsonl
python -m tagger.check_same --works works.jsonl
```

With text, it also recomputes the three gates and the Jev request (`state_for`) for every work. In September 2026
the API served 5,057 of the 5,069 works; every one gave the same gate answers as the text the tagger read.

**Tag new works** (needs a Jev key from [TypeSafe AI](https://typesafe.ai); one request per work, about 1,500 input
tokens):

```bash
export JEV_API_KEY=...
python -m tagger.fetch_works --ids my_ids.txt --out works.jsonl
python -m tagger.tag --input works.jsonl --out tagged.jsonl
```

Each output row carries the values OpenAlex would serve, the eight class scores and Jev's two yes/no scores. Jev is
not bit-deterministic: re-tagging 29 development-set works gave the same values for all 29, with probabilities moving
by up to 0.13.

## The improvement loop

`harness/LEDGER.md` lists every configuration tried, with its hypothesis, its result and why it was kept or dropped.
Each config's answers from Jev are cached in `harness/runs/`, so

```bash
python harness/compare.py --split dev          # every config, recall at the bar per class
python harness/holdout.py --configs h15_nrt,g_mix,e_div3
python harness/run.py --config r2_gate4        # one config's full table
```

rescore them all in seconds. A new idea is a new file in `harness/configs/`; `python harness/run.py --config
<name> --works works.jsonl` sends its request to Jev for the 5,069 works (with `JEV_API_KEY` set) and caches the
answers under a hash of the config's source.

To judge the works again: `ANTHROPIC_API_KEY=... python harness/judge_v2.py --inp works.jsonl --out judge.jsonl
--model claude-opus-5-5`. The prompt and output schema are in `harness/judge_prompt.md`.

## The student

`student/` is the small encoder that tagged most of the backlog (`student/README.md`).

```bash
python student/certify.py                     # its certification from cached outputs (no GPU, no torch)
```

To run the released weights:

```bash
curl -LO https://github.com/ourresearch/openalex-study-designs/releases/download/v1.0.0/student-e5s-v1.tar.gz
shasum -a 256 student-e5s-v1.tar.gz            # bc34c29778e64600f0367e5afe468e2db68340eee3f9fcba1fb6cf7d9af4e414
tar -xzf student-e5s-v1.tar.gz                 # -> student-e5s/
pip install torch "transformers>=4.51" sentencepiece
python student/infer.py --model student-e5s --input works.jsonl --out student.jsonl
python student/certify.py --preds student.jsonl
```

On Apple silicon (fp32) the first 300 development-set works ran at about 120 works a second and matched the
production GPU outputs to within 0.007 in every probability, with the same route and values for all 300.
`student/train.py` retrains it from any set of works with Jev's outputs (format in its header).

## Benchmark vs PubMed

Every table in [benchmarks/README.md](benchmarks/README.md) and the README's two charts, from the files in the repo
(standard library, about a second):

```
python3 benchmarks/score_pubmed.py      # prints the tables, writes benchmarks/data/pubmed/results.json
python3 docs/charts/make_charts.py      # redraws docs/img/*.svg from results.json
```

To judge the sample again, rebuild its texts from the API, then run the judge (needs `pip install anthropic` and
`ANTHROPIC_API_KEY`; about 7,700 calls):

```
python3 tagger/fetch_works.py --ids benchmarks/data/pubmed/sample.jsonl.gz --out /tmp/pubmed_texts.jsonl --mailto you@example.org
python3 harness/judge_v2.py --model claude-opus-5-5 --inp /tmp/pubmed_texts.jsonl --out /tmp/judge.jsonl
```

The texts come from today's OpenAlex, so a few abstracts will differ from the ones judged on 28 September 2026, and
a few works may have been merged or removed. The full-text check used Europe PMC's open-access XML
(`https://www.ebi.ac.uk/europepmc/webservices/rest/<PMCID>/fullTextXML`, methods sections first, 24,000
characters) with `--cap 24000`; the PMCIDs are in the sample file.

The sample itself was drawn with SQL over OpenAlex's internal tables on 28 September 2026 and cannot be redrawn
from outside. `population.json` holds every group's size, which is all the weighting needs.
