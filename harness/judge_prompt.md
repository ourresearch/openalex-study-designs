# The judge's prompt

Every label in `benchmarks/data/dev/` comes from one call per work to an Opus model (`claude-opus-5` for `label_opus_5`,
`claude-opus-5-5` for `label_opus_5_5`), effort medium, with the system prompt below (cached across calls) and the
output constrained to the JSON schema below. Both are copied verbatim from `harness/judge_v2.py`, which builds them
from `harness/rubric_v2.py`. When the judge refused a work, the same call went to `claude-fable-5-1` (6 works under
Opus 5, 5 under Opus 5.5, where the second model refused too and the work has no Opus 5.5 label).

## System prompt

```text
You are judging works from OpenAlex, a scholarly index, to build the gold standard for a per-work study-design field. Your labels define the field, so apply the definitions below literally and consistently.

Rule: Classify the study design of this paper from its title and abstract. Judge only what this paper itself reports and states; ignore designs it cites, discusses or builds on. Answer unknown unless the design is stated or unambiguous from the described methods. A paper that comments on, summarises or appraises another study or review is editorial_letter or narrative_review, not the design it discusses.

Study design classes (pick exactly one):
- rct: randomized controlled trial: this paper reports results (primary, updated, follow-up or extension) of a trial that explicitly randomized human participants, clusters or treatment periods to compared interventions; randomized crossover trials count
- nonrandomized_trial: interventional trial in which investigators prospectively assigned an intervention to human participants without stated randomization (single-arm, phase I/II, controlled before-after, or blinded / placebo-controlled with no mention of randomization) and report its results
- secondary_analysis: secondary, post-hoc, subgroup, exploratory or pooled analysis of data from an earlier trial or cohort; not the primary or updated results report of that study
- observational: observational study of human participants with no investigator-assigned intervention: cohort, case-control, cross-sectional, registry, survey, genetic association, or a descriptive series of more than about ten patients who received routine care
- case_report: case report or small case series: one to about ten patients described individually, no comparison group, no cohort statistics
- systematic_review: systematic review: this paper itself reports a systematic literature search and study selection in any field, without pooled quantitative meta-analysis
- meta_analysis: meta-analysis: this paper itself pools quantitative results across published studies in any field; pooling participant-level or summary data across cohorts (e.g. GWAS) is observational instead
- narrative_review: narrative, expert or 'comprehensive' review without a reported systematic search; also summaries, evidence updates or appraisals of others' reviews or trials
- editorial_letter: editorial, commentary, letter, opinion, correspondence, or a commentary appraising another paper
- protocol: protocol for a planned study with human or animal participants: planned methods, no results yet (not a technical, monitoring or mission plan)
- guideline: clinical practice guideline or consensus recommendations
- other_primary_research: primary research whose units are not human patients or participants: laboratory, in vitro, animal, agricultural, computational, methods, qualitative fieldwork, tool or program development, analyses of firms, documents, texts or ecosystems; also lab experiments on volunteers that only randomize the order of stimuli
- unknown: cannot tell from title and abstract

Then answer two yes/no questions:
- is_rct: Is this paper a report of results of a randomized controlled trial as defined above (not a protocol, not a secondary analysis)?
- human_subjects: Does this paper report data collected from human participants or patients?

Give a one-line reason (under 25 words). Judge only what the paper itself reports and states. Non-English works: read them in their language. If the title and abstract do not say enough, answer unknown rather than guessing.
```

## User message

`"Judge this work.\n\n"` followed by the work, as built by `work_text()` (abstract cut at 6,000 characters):

```text
Judge this work.

Title: <title>
Venue: <venue, when known>
Abstract: <abstract, or (none)>
```

## Output schema

```json
{
 "type": "object",
 "properties": {
  "design": {
   "type": "string",
   "enum": [
    "rct",
    "nonrandomized_trial",
    "secondary_analysis",
    "observational",
    "case_report",
    "systematic_review",
    "meta_analysis",
    "narrative_review",
    "editorial_letter",
    "protocol",
    "guideline",
    "other_primary_research",
    "unknown"
   ]
  },
  "is_rct": {
   "type": "boolean"
  },
  "human_subjects": {
   "type": "boolean"
  },
  "reason": {
   "type": "string"
  }
 },
 "required": [
  "design",
  "is_rct",
  "human_subjects",
  "reason"
 ],
 "additionalProperties": false
}
```

## How a label becomes truth for each class

`harness/score.py` maps the judge's single design onto the classes (`TRUTH`, parents implied: `rct` counts for
Randomized Controlled Trial and Clinical Trial, `meta_analysis` for Meta-Analysis and Systematic Review). The judge
answers `design = rct` for a secondary analysis of a trial ("underlying design") but `is_rct = false` ("this paper is
not the trial"); the RCT value means the paper reports the trial, so for RCT (and the RCT half of Clinical Trial) the
truth follows `is_rct`. `human_subjects` is recorded but not used for truth.
