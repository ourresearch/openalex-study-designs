# The student

A small multilingual encoder, [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small),
fine-tuned to give the same answers as the tagger. It learned from the tagger's own outputs: 1,496,608 works Jev had
already tagged, with Jev's 13 Choice probabilities and two yes/no scores as soft targets (one epoch, 512 tokens of
title + venue + abstract). It emits the same 15 numbers Jev does, so `tagger/study_design.derive()`, the three RCT
gates and the thresholds run on its answers unchanged.

**What it did.** During the first backfill (23 to 26 September 2026) the student tagged most of the backlog: about 115
million of the 167 million works with an abstract. Works it was unsure about went to Jev. Since 26 September 2026 Jev
tags every new work; the student's tags on the backlog stay in place.

**Where it falls short.** On the fresh benchmark outside PubMed ([benchmarks/](../benchmarks/README.md)), the
student's Study Protocol tags are right 72% of the time (139 of 192), against Jev's 90%: it takes dissertations,
research plans and lab methods for protocols. Its development-set numbers below did not show this, because that set
is mostly biomedical.

**When its answer stands.** Per class the student has its own threshold, chosen on the judged development set at the
class's precision bar, and a lower cut under which its "no" loses at most 2% of Jev's own positives (RCT: 0.5%). A
work is the student's only when no class score falls between the two (`route.py`); otherwise it goes to Jev. The
student never tags RCT: no student score reached the 0.99 bar (its false positives are protocols, non-randomised
trials and secondary analyses that mention randomisation), so any work with a non-negligible RCT score goes to Jev. On
a uniform sample of 100,485 works, 13.7% went to Jev; on the works the student kept, its values equalled Jev's on
97.1%.

**How good it is** on the 5,069 judged works, at its own thresholds (`python student/certify.py`, no GPU needed):

| Class | bar | threshold | positives | false positives | precision | one-sided 95% lower bound | recall |
|---|---|---|---|---|---|---|---|
| Randomized Controlled Trial | 0.99 | none (left to Jev) | | | | | |
| Meta-Analysis | 0.98 | 0.99 | 266 | 0 | 1.000 | 0.990 | 0.719 |
| Systematic Review | 0.97 | 0.94 | 526 | 9 | 0.983 | 0.971 | 0.757 |
| Study Protocol | 0.97 | 0.65 | 303 | 4 | 0.987 | 0.971 | 0.931 |
| Clinical Trial | 0.95 | 0.86 | 956 | 32 | 0.967 | 0.956 | 0.779 |
| Case Report | 0.95 | 0.98 | 180 | 1 | 0.994 | 0.975 | 0.670 |
| Observational Study | 0.95 | 0.87 | 437 | 11 | 0.975 | 0.959 | 0.577 |
| Other primary research | 0.95 | 0.30 | 1,055 | 40 | 0.962 | 0.951 | 0.824 |

Labels: Opus 5 (`label_opus_5`). Observational recall is 15 points under Jev's, which is why most observational
studies still went to Jev.

## Run it

The weights are a release asset (422 MB; sizes and checksums of every file in `models/MANIFEST.json`):

```bash
curl -LO https://github.com/ourresearch/openalex-study-designs/releases/download/v1.0.0/student-e5s-v1.tar.gz
shasum -a 256 student-e5s-v1.tar.gz   # bc34c29778e64600f0367e5afe468e2db68340eee3f9fcba1fb6cf7d9af4e414
tar -xzf student-e5s-v1.tar.gz        # -> student-e5s/
pip install torch "transformers>=4.51" sentencepiece
python -m tagger.fetch_works --ids ids.txt --out works.jsonl
python student/infer.py --model student-e5s --input works.jsonl --out student.jsonl
```

Each output row has the student's probabilities, the eight class scores, `route` (`student` or `jev`) and, when the
route is `student`, the values. The script fetches the base model's configuration and weights from the Hugging Face
Hub once; the fine-tuned weights then replace every weight. It runs on a GPU (bf16, about 400 works a second on an
A10G), on Apple silicon or on a CPU (fp32). On 300 development-set works, Apple-silicon fp32 outputs differed from
the production GPU outputs by at most 0.007 in any probability, and every route and value was the same.

## Files

| File | What |
|---|---|
| `common.py` | the 13 output columns, the input text, the model (encoder + two linear heads) |
| `train.py` | training: soft cross-entropy to Jev's probabilities + binary cross-entropy to the two yes/no scores |
| `infer.py` | inference, scores, route and values for new works |
| `route.py` | the two threshold tables and the routing rule, as run in production |
| `certify.py` | the table above, from `benchmarks/data/dev/dev_student_outputs.jsonl.gz` or your own `infer.py` output |

The training set (works with Jev's outputs) is not in the repo; `train.py` documents its format, and
`python -m tagger.fetch_works` rebuilds the text for any list of work ids.
