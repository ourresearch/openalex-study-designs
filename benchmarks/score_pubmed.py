"""Score the PubMed benchmark: PubMed's tags and OpenAlex's on the same works, one judge.

    python3 benchmarks/score_pubmed.py            # prints every table, writes benchmarks/data/pubmed/results.json

Standard library only; reads benchmarks/data/pubmed/{sample.jsonl.gz, population.json}. How the sample was drawn and
why the estimates are weighted: benchmarks/README.md.

Per study design v, works indexed in MEDLINE fall into four cells: both (PubMed and OpenAlex tag v), pubmed_only,
openalex_only, and neither. The first three were sampled on their own; neither is estimated from a random sample of
MEDLINE works. Each cell's share of right tags is weighted by the cell's size:
  precision(PubMed)   = (N_both p_both + N_pubmed_only p_pubmed_only) / (N_both + N_pubmed_only)
  precision(OpenAlex) = (N_both p_both + N_openalex_only p_openalex_only) / (N_both + N_openalex_only)
  recall(X)           = X's right tags / all works that are v (the four cells)
Each cell's rate is drawn from its Jeffreys posterior, Beta(k + 1/2, n - k + 1/2), 4,000 times and the estimates are
recomputed per draw: the reported value is the median draw and the 95% interval the 2.5th to 97.5th percentile (a cell
with no errors then counts as slightly below perfect, never as exactly 100%). Works the judge answered "unknown" (the text says too little) are left out.
"""
import gzip, json, random
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).parent / "data" / "pubmed"
VALUES = ["randomized-controlled-trial", "clinical-trial", "observational-study", "case-report", "systematic-review",
          "meta-analysis", "study-protocol"]
NAME = {"randomized-controlled-trial": "Randomized Controlled Trial", "clinical-trial": "Clinical Trial",
        "observational-study": "Observational Study", "case-report": "Case Report",
        "systematic-review": "Systematic Review", "meta-analysis": "Meta-Analysis", "study-protocol": "Study Protocol"}

# The judge picks one design per work (harness/rubric_v2.py); these are the served values each design counts as.
TRUTH = {"rct": {"randomized-controlled-trial", "clinical-trial"}, "nonrandomized_trial": {"clinical-trial"},
         "observational": {"observational-study"}, "case_report": {"case-report"},
         "systematic_review": {"systematic-review"}, "meta_analysis": {"meta-analysis", "systematic-review"},
         "protocol": {"study-protocol"}}
# PubMed publication types other than the veterinary and twin tags (for the sensitivity check).
CORE = {"randomized-controlled-trial": {"Randomized Controlled Trial", "Pragmatic Clinical Trial", "Equivalence Trial",
                                        "Adaptive Clinical Trial"},
        "observational-study": {"Observational Study"}}
CORE["clinical-trial"] = CORE["randomized-controlled-trial"] | {
    "Clinical Trial", "Controlled Clinical Trial", "Clinical Trial, Phase I", "Clinical Trial, Phase II",
    "Clinical Trial, Phase III", "Clinical Trial, Phase IV", "Clinical Study"}


def truth(label):
    """Served values the judge's answer supports. A secondary analysis of a trial is not an RCT (is_rct false)."""
    t = set(TRUTH.get(label["design"], set()))
    if label["design"] == "rct" and not label["is_rct"]:
        t -= {"randomized-controlled-trial", "clinical-trial"}
    return t


def load():
    rows = [json.loads(l) for l in gzip.open(DATA / "sample.jsonl.gz", "rt")]
    pop = json.loads((DATA / "population.json").read_text())
    return rows, pop


def cells(v, rows, judge="judge", core_only=False):
    """{cell: [right?]} for value v. Random-sample works count in the neither cell of every value neither side tags."""
    out = defaultdict(list)
    for r in rows:
        lab = r[judge]
        if not lab or lab["design"] == "unknown":
            continue
        right = v in truth(lab)
        pm = v in r["pubmed_values"]
        if core_only and pm and v in CORE and not set(r["pubmed_publication_types"]) & CORE[v]:
            continue                      # drop PubMed tags that come only from veterinary / twin types
        for s in r["strata"]:
            if s.startswith(v + ":"):
                out[s.split(":")[1]].append(right)
            elif s == "random_medline" and not pm and v not in r["openalex_values"]:
                out["neither"].append(right)
    return out


def estimate(N, p):
    g = lambda c: N[c] * p.get(c, 0.0)
    tp_pm, tp_oa = g("both") + g("pubmed_only"), g("both") + g("openalex_only")
    tp_all = tp_pm + g("openalex_only") + g("neither")
    return {"precision_pubmed": tp_pm / (N["both"] + N["pubmed_only"]),
            "precision_openalex": tp_oa / (N["both"] + N["openalex_only"]),
            "recall_pubmed": tp_pm / tp_all, "recall_openalex": tp_oa / tp_all,
            "precision_openalex_not_in_medline": p.get("openalex_not_in_medline"),
            "precision_openalex_all_works": (tp_oa + g("openalex_not_in_medline")) /
                                            (N["both"] + N["openalex_only"] + N["openalex_not_in_medline"])}


def score(rows, pop, judge="judge", core_only=False, draws=4000, seed=7):
    rng, res = random.Random(seed), {}
    for v in VALUES:
        s = cells(v, rows, judge, core_only)
        N = {c: pop["cells"].get(f"{v}:{c}", 0) for c in ("both", "pubmed_only", "openalex_only", "openalex_not_in_medline")}
        N["neither"] = pop["medline_works"] - N["both"] - N["pubmed_only"] - N["openalex_only"]
        p = {c: sum(x) / len(x) for c, x in s.items() if x}
        plug_in, boot = estimate(N, p), defaultdict(list)
        for _ in range(draws):
            for k, val in estimate(N, {c: rng.betavariate(sum(x) + .5, len(x) - sum(x) + .5) for c, x in s.items() if x}).items():
                if val is not None:
                    boot[k].append(val)
        ci = {k: [sorted(b)[int(.025 * len(b))], sorted(b)[int(.975 * len(b)) - 1]] for k, b in boot.items()}
        est = {k: sorted(b)[len(b) // 2] for k, b in boot.items()}
        res[v] = {"est": est, "plug_in": plug_in, "ci": ci, "judged": {c: len(x) for c, x in s.items()}, "right": {c: sum(x) for c, x in s.items()},
                  "population": N}
    return res


def most_cited(rows, stratum, judge="judge"):
    ws = sorted((r for r in rows if stratum in r["strata"]), key=lambda r: -r["cited_by_count"])[:100]
    return [r for r in ws if r[judge] and "randomized-controlled-trial" not in truth(r[judge])]


def full_text(rows):
    """Disagreement works judged twice: on title + abstract, and on the open-access full text."""
    out = {}
    for side in ("pubmed_only", "openalex_only"):
        n = a = f = 0
        for r in rows:
            if not (r["judge"] and r["judge_full_text"]):
                continue
            for s in r["strata"]:
                if s.endswith(":" + side):
                    v = s.split(":")[0]; n += 1
                    a += v in truth(r["judge"]); f += v in truth(r["judge_full_text"])
        out[side] = {"tags": n, "right_abstract_judge": a, "right_full_text_judge": f}
    return out


def full_text_adjusted(rows, pop):
    """Plug-in precision after shifting each disagreement cell's rate by what the full text changed in its
    open-access subsample: p + (right on full text - right on abstract) / n. A sensitivity check, not the headline."""
    out = {}
    for v in VALUES:
        s = cells(v, rows)
        N = {c: pop["cells"].get(f"{v}:{c}", 0) for c in ("both", "pubmed_only", "openalex_only", "openalex_not_in_medline")}
        N["neither"] = pop["medline_works"] - N["both"] - N["pubmed_only"] - N["openalex_only"]
        p = {c: sum(x) / len(x) for c, x in s.items() if x}
        shift = {}
        for c in ("pubmed_only", "openalex_only"):
            both = [r for r in rows if f"{v}:{c}" in r["strata"] and r["judge"] and r["judge_full_text"]
                    and r["judge"]["design"] != "unknown"]
            if both:
                shift[c] = (sum(v in truth(r["judge_full_text"]) for r in both) - sum(v in truth(r["judge"]) for r in both)) / len(both)
                p[c] = min(1.0, max(0.0, p[c] + shift[c]))
        e = estimate(N, p)
        out[v] = {"precision_pubmed": e["precision_pubmed"], "precision_openalex": e["precision_openalex"], "shift": shift,
                  "full_text_works": {c: sum(1 for r in rows if f"{v}:{c}" in r["strata"] and r["judge"] and r["judge_full_text"]
                                             and r["judge"]["design"] != "unknown") for c in ("pubmed_only", "openalex_only")}}
    return out


def main():
    rows, pop = load()
    res = score(rows, pop)
    core = score(rows, pop, core_only=True, draws=500)
    pct = lambda v, k, r=res: f"{100 * r[v]['est'][k]:.1f}% ({100 * r[v]['ci'][k][0]:.1f}–{100 * r[v]['ci'][k][1]:.1f})"
    print(f"{len(rows):,} works; MEDLINE population {pop['medline_works']:,}, as of {pop['as_of']}\n")
    print("PubMed-indexed (MEDLINE) works: PubMed's tags and OpenAlex's on the same works\n")
    print("| Study design | PubMed precision | OpenAlex precision | PubMed recall | OpenAlex recall |")
    print("|---|---|---|---|---|")
    for v in VALUES:
        print(f"| {NAME[v]} | {pct(v, 'precision_pubmed')} | {pct(v, 'precision_openalex')} | {pct(v, 'recall_pubmed')} | {pct(v, 'recall_openalex')} |")
    print("\nOpenAlex precision on works outside MEDLINE, and on every tagged work\n")
    print("| Study design | Not in MEDLINE | All works |"); print("|---|---|---|")
    for v in VALUES:
        print(f"| {NAME[v]} | {pct(v, 'precision_openalex_not_in_medline')} | {pct(v, 'precision_openalex_all_works')} |")
    print("\nSensitivity: PubMed precision without its veterinary and twin tags\n")
    print("| Study design | All mapped tags | Without veterinary and twin tags |"); print("|---|---|---|")
    for v in ("randomized-controlled-trial", "clinical-trial", "observational-study"):
        print(f"| {NAME[v]} | {100 * res[v]['est']['precision_pubmed']:.1f}% | {100 * core[v]['est']['precision_pubmed']:.1f}% |")
    ft = full_text(rows)
    print("\nFull-text check on disagreements (open-access papers judged twice)\n")
    print("| Tags | Works | Right, judged on abstract | Right, judged on full text |"); print("|---|---|---|---|")
    for side, d in ft.items():
        print(f"| {side.replace('_', ' ')} | {d['tags']} | {d['right_abstract_judge']} | {d['right_full_text_judge']} |")
    fta = full_text_adjusted(rows, pop)
    print("\nSensitivity: precision if the disagreement cells moved as their open-access subsamples did on full text\n")
    print("| Study design | PubMed, abstract | PubMed, full-text adjusted | OpenAlex, abstract | OpenAlex, full-text adjusted | Full-text works (PubMed only / OpenAlex only) |")
    print("|---|---|---|---|---|---|")
    for v in VALUES:
        a = fta[v]; fw = a["full_text_works"]
        print(f"| {NAME[v]} | {100 * res[v]['plug_in']['precision_pubmed']:.1f}% | {100 * a['precision_pubmed']:.1f}% | "
              f"{100 * res[v]['plug_in']['precision_openalex']:.1f}% | {100 * a['precision_openalex']:.1f}% | {fw['pubmed_only']} / {fw['openalex_only']} |")
    top = {s: most_cited(rows, s) for s in ("most_cited_pubmed_rct", "most_cited_openalex_rct")}
    print("\nThe 100 most-cited works each side tags as a randomized controlled trial: the judge says not an RCT report\n")
    for s, ws in top.items():
        print(f"{s}: {len(ws)} of 100")
        for r in ws:
            print(f"  {r['work_id']} PMID {r['pmid']} ({r['publication_year']}, {r['cited_by_count']:,} citations): {r['judge']['design']}. {r['judge']['reason']}")
    counts = {v: {"judged": res[v]["judged"], "right": res[v]["right"]} for v in VALUES}
    (DATA / "results.json").write_text(json.dumps({v: {"est": res[v]["est"], "ci": res[v]["ci"], "plug_in": res[v]["plug_in"], **counts[v],
                                                        "population": res[v]["population"]} for v in VALUES} |
                                                  {"_full_text": ft, "_full_text_adjusted": fta, "_core_precision_pubmed": {v: core[v]["est"]["precision_pubmed"] for v in VALUES},
                                                   "_most_cited_not_rct": {s: [r["work_id"] for r in ws] for s, ws in top.items()}}, indent=1))


if __name__ == "__main__":
    main()
